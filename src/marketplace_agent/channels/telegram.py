from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from langgraph.types import Command
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from marketplace_agent.domain.catalog import CatalogRepository
from marketplace_agent.domain.models import ItemCase, WorkflowStatus


def parse_field_updates(raw: str) -> dict[str, Any]:
    """Accept friendly key=value pairs while retaining JSON for advanced edits."""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        return parsed
    updates: dict[str, Any] = {}
    for part in raw.replace("\n", ";").split(";"):
        if not part.strip():
            continue
        key, separator, value = part.partition("=")
        if not separator or not key.strip() or not value.strip():
            raise ValueError("expected field=value pairs")
        updates[key.strip()] = value.strip()
    if not updates:
        raise ValueError("no updates")
    return updates


def render_interrupt(value: dict[str, Any]) -> str:
    kind = value.get("kind")
    if kind == "fact":
        return (
            f"Pole: {value['field']}\nWartość: {value['value']}\n"
            f"Pewność modelu: {value['confidence']:.0%}\n\n"
            "Akceptuj albo użyj: /zmien nowa wartość"
        )
    if kind == "portals":
        rows = [
            f"• {portal}: {value.get('reasons', {}).get(portal, '')}"
            for portal in value["recommended"]
        ]
        return (
            "Proponowane portale:\n"
            + "\n".join(rows)
            + "\n\n/zmien olx,allegro_lokalnie"
        )
    if kind == "missing_info":
        questions = "\n".join(f"• {question}" for question in value["questions"])
        return (
            f"Model zauważył możliwe braki:\n{questions}\n\n"
            "Odpowiedz zwykłym zdaniem, użyj /zmien pole=wartość albo napisz „nie wiem”."
        )
    if kind == "price":
        summary = value["summary"]
        active_distribution = summary.get("active_distribution", {})
        counts = ", ".join(
            f"{row['count']} x {row['price_pln']:.0f} zł"
            for row in active_distribution.get("exact_price_counts", summary["exact_price_counts"])
        )
        recommendations = ", ".join(
            f"{row['strategy']}: {row['price_pln']:.0f} zł" for row in summary["recommendations"]
        )
        return (
            f"Zweryfikowano {summary['reachable_count']} linków; porównywalnych: "
            f"{summary['comparable_count']}; kwarantanna: "
            f"{summary.get('quarantined_count', 0)}.\n"
            f"Aktywne ceny ofertowe: {summary.get('active_count', 0)}; "
            f"sprzedane: {summary.get('sold_count', 0)}.\n"
            f"Rozkład aktywnych ofert: {counts or 'brak danych'}\n"
            f"Rekomendacje: {recommendations or 'brak'}\n\n"
            "Akceptuj cenę rynkową albo /zmien 120"
        )
    if kind == "copy":
        draft = value["draft"]
        warning = ""
        if value.get("warnings"):
            warning = (
                "\n\nGuard zastąpił szkic bezpiecznym szablonem. Wykryto: "
                f"{', '.join(value['warnings'])}."
            )
        return (
            f"Tekst dla {value['portal']}\n\n{draft['title']}\n\n{draft['description']}\n\n"
            f"Kategoria: {draft['category']}; cena: {draft['price_pln']} zł\n"
            'Akceptuj albo /zmien {"title": "...", "description": "..."}'
            f"{warning}"
        )
    if kind == "fill_authorization":
        rows = []
        for preview in value.get("previews", []):
            draft = preview["draft"]
            photos = ", ".join(
                f"{photo['name']} ({photo['sha256']})" for photo in preview["photos"]
            )
            rows.append(
                f"{preview['portal']} — snapshot v{preview['version']} "
                f"({preview['content_hash']})\n"
                f"Tytuł: {draft['title']}\nCena: {draft['price_pln']} zł\n"
                f"Kategoria: {draft['category']}\nStan: {draft.get('condition') or 'nie podano'}\n"
                f"Rodzaj sprzedaży: {draft.get('sale_type') or 'nie podano'}\n"
                f"Lokalizacja: {draft.get('location') or 'nie podano'}\n"
                f"Dostawa: {draft.get('delivery') or 'nie podano'}\n"
                f"Opis: {draft['description']}\nZdjęcia: {photos or 'brak'}"
            )
        return (
            "Pełny podgląd danych przekazywanych do formularzy:\n\n"
            + "\n\n".join(rows)
            + "\n\nAkceptacja dotyczy dokładnie tych snapshotów. Publikacja pozostaje ręczna."
        )
    if kind == "publish_authorization":
        draft = value["draft"]
        return (
            "OSTATECZNA ZGODA NA PUBLIKACJĘ\n\n"
            f"Portal: {value['portal']}\nSnapshot: v{value['version']} "
            f"({value['content_hash']})\nTytuł: {draft['title']}\n"
            f"Cena: {draft['price_pln']} zł\nKategoria: {draft['category']}\n"
            f"Opis: {draft['description']}\n\n"
            "Przycisk jest jednorazowy. Zmiana danych unieważnia zgodę."
        )
    return json.dumps(value, ensure_ascii=False, indent=2)


class TelegramChannel:
    def __init__(
        self,
        token: str,
        allowed_chat_id: int,
        graph: Any,
        catalog: CatalogRepository,
        data_dir: Path,
    ) -> None:
        self.allowed_chat_id = allowed_chat_id
        self.graph = graph
        self.catalog = catalog
        self.data_dir = data_dir
        self.application = Application.builder().token(token).build()
        self.application.add_handler(CommandHandler("start", self.help))
        self.application.add_handler(CommandHandler("pomoc", self.help))
        self.application.add_handler(CommandHandler("nowa", self.new_item))
        self.application.add_handler(CommandHandler("gotowe", self.process_item))
        self.application.add_handler(CommandHandler("status", self.status))
        self.application.add_handler(CommandHandler("zaakceptuj", self.accept))
        self.application.add_handler(CommandHandler("wystaw", self.publish))
        self.application.add_handler(CommandHandler("zmien", self.edit))
        self.application.add_handler(CommandHandler("anuluj", self.cancel))
        self.application.add_handler(CallbackQueryHandler(self.button))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.photo))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.note))

    def _allowed(self, update: Update) -> bool:
        return (
            update.effective_chat is not None and update.effective_chat.id == self.allowed_chat_id
        )

    async def _reject(self, update: Update) -> bool:
        if self._allowed(update):
            return False
        if update.effective_message:
            await update.effective_message.reply_text("Ten bot jest prywatny.")
        return True

    def _item_id(self, chat_id: int) -> str | None:
        return self.catalog.get_active_item(str(chat_id))

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._reject(update):
            return
        await update.effective_message.reply_text(
            "/nowa — zacznij przedmiot\nWyślij zdjęcia i opcjonalny opis\n"
            "/gotowe — rozpocznij analizę\n/zaakceptuj lub przycisk — zatwierdź krok\n"
            "/zmien wartość — popraw bieżący krok\n/status — sprawdź stan\n"
            "/wystaw JOB_ID — pokaż końcowy podgląd i poproś o zgodę\n"
            "/anuluj — porzuć przedmiot"
        )

    async def new_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._reject(update):
            return
        existing_id = self._item_id(update.effective_chat.id)
        existing = self.catalog.get_item(existing_id) if existing_id else None
        if existing and existing.status not in {WorkflowStatus.ARCHIVED, WorkflowStatus.PUBLISHED}:
            await update.effective_message.reply_text(
                "Masz już aktywny przedmiot. Dokończ go albo użyj /anuluj."
            )
            return
        item = ItemCase()
        self.catalog.save_item(item)
        chat_id = update.effective_chat.id
        self.catalog.set_active_item(str(chat_id), item.item_id)
        self.catalog.record_conversation_event(str(chat_id), item.item_id, "item_created", {})
        (self.data_dir / "items" / item.item_id / "photos").mkdir(parents=True, exist_ok=True)
        await update.effective_message.reply_text(
            f"Nowy przedmiot: {item.item_id[:8]}. Wyślij zdjęcia, potem /gotowe."
        )

    async def photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._reject(update):
            return
        chat_id = update.effective_chat.id
        item_id = self._item_id(chat_id)
        if not item_id:
            await update.effective_message.reply_text("Najpierw użyj /nowa.")
            return
        item = self.catalog.get_item(item_id)
        if item is None or item.status != WorkflowStatus.NEW:
            await update.effective_message.reply_text("Zdjęcia można dodawać przed /gotowe.")
            return
        photo_dir = self.data_dir / "items" / item_id / "photos"
        photo_dir.mkdir(parents=True, exist_ok=True)
        path = photo_dir / f"{len(item.photo_paths) + 1:02d}.jpg"
        telegram_file = await update.effective_message.photo[-1].get_file()
        await telegram_file.download_to_drive(path)
        item.photo_paths.append(path)
        self.catalog.save_item(item)
        caption = update.effective_message.caption
        if caption:
            self.catalog.append_note(str(chat_id), item_id, caption)
        self.catalog.record_conversation_event(
            str(chat_id), item_id, "photo_added", {"file_name": path.name}
        )
        await update.effective_message.reply_text(f"Mam zdjęcie {len(item.photo_paths)}.")

    async def note(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._reject(update):
            return
        item_id = self._item_id(update.effective_chat.id)
        item = self.catalog.get_item(item_id) if item_id else None
        text = update.effective_message.text.strip()
        pending = self.catalog.pending_approval(str(update.effective_chat.id), item_id or "")
        if (
            pending
            and pending["step"] == "missing_info"
        ):
            if text.casefold() in {"nie wiem", "pomijam"}:
                await self._consume_and_resume(update, pending["token"], pending)
            else:
                self.catalog.revoke_pending_approval(str(update.effective_chat.id), item_id or "")
                await self._resume(
                    update,
                    {
                        "action": "edit",
                        "value": {"attribute.additional_details": text},
                    },
                )
            return
        if item is None or item.status != WorkflowStatus.NEW:
            return
        self.catalog.append_note(str(update.effective_chat.id), item.item_id, text)
        self.catalog.record_conversation_event(
            str(update.effective_chat.id), item.item_id, "note_added", {"length": len(text)}
        )
        await update.effective_message.reply_text("Dodałam tę informację do przedmiotu.")

    async def process_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._reject(update):
            return
        item_id = self._item_id(update.effective_chat.id)
        item = self.catalog.get_item(item_id) if item_id else None
        if item is None or not item.photo_paths:
            await update.effective_message.reply_text("Dodaj co najmniej jedno zdjęcie.")
            return
        await update.effective_message.reply_text("Analizuję zdjęcia…")
        result = await self.graph.ainvoke(
            {
                "item": item.model_dump(mode="json"),
                "user_notes": self.catalog.get_notes(str(update.effective_chat.id), item.item_id),
            },
            config={"configurable": {"thread_id": item.item_id}},
        )
        await self._show_result(update, result)

    async def _show_result(self, update: Update, result: dict[str, Any]) -> None:
        interrupts = result.get("__interrupt__", ())
        if interrupts:
            value = interrupts[0].value
            snapshot_ids = value.get("snapshot_ids", {})
            record = self.catalog.issue_approval(
                channel_id=str(update.effective_chat.id),
                item_id=value["item_id"],
                step=value["kind"],
                payload=value,
                snapshot_ids=(
                    list(snapshot_ids.values())
                    if isinstance(snapshot_ids, dict)
                    else list(snapshot_ids)
                ),
            )
            self.catalog.record_conversation_event(
                str(update.effective_chat.id),
                value["item_id"],
                "approval_requested",
                {
                    "step": value["kind"],
                    "approval_id": record["approval_id"],
                },
            )
            await update.effective_message.reply_text(
                render_interrupt(value),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "Akceptuję", callback_data=f"approve:{record['token']}"
                            )
                        ]
                    ]
                ),
            )
            return
        item = ItemCase.model_validate(result["item"])
        if result.get("execution_job_ids"):
            jobs = ", ".join(job_id[:8] for job_id in result["execution_job_ids"])
            await update.effective_message.reply_text(
                f"Zadania wykonawcze zapisane w kolejce: {jobs}. Status sprawdzisz przez /status."
            )
            return
        statuses = ", ".join(f"{row.portal}: {row.status}" for row in item.fill_results)
        await update.effective_message.reply_text(
            "Gotowe. Formularze czekają w Chrome na Twoją kontrolę i ręczne kliknięcie "
            f"publikacji. {statuses}"
        )

    async def _resume(self, update: Update, response: Any) -> None:
        item_id = self._item_id(update.effective_chat.id)
        if not item_id:
            await update.effective_message.reply_text("Brak aktywnego przedmiotu.")
            return
        result = await self.graph.ainvoke(
            Command(resume=response),
            config={"configurable": {"thread_id": item_id}},
        )
        await self._show_result(update, result)

    async def accept(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._reject(update):
            return
        item_id = self._item_id(update.effective_chat.id)
        pending = self.catalog.pending_approval(str(update.effective_chat.id), item_id or "")
        if item_id is None or pending is None:
            await update.effective_message.reply_text("Brak aktualnej decyzji do zatwierdzenia.")
            return
        await self._consume_and_resume(update, pending["token"], pending)

    async def publish(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Create a concrete final preview; this command does not click the portal."""
        if await self._reject(update):
            return
        job_id = " ".join(context.args).strip()
        if not job_id:
            await update.effective_message.reply_text("Podaj pełny identyfikator: /wystaw JOB_ID")
            return
        job = self.catalog.get_execution_job(job_id)
        snapshot = self.catalog.get_snapshot(job["snapshot_id"]) if job else None
        item_id = self._item_id(update.effective_chat.id)
        if (
            job is None
            or snapshot is None
            or snapshot["item_id"] != item_id
            or job["status"] != "ready"
        ):
            await update.effective_message.reply_text(
                "To zadanie nie należy do aktywnego przedmiotu albo nie ma statusu ready."
            )
            return
        value = {
            "kind": "publish_authorization",
            "item_id": item_id,
            "job_id": job_id,
            "portal": job["portal"],
            "snapshot_ids": [job["snapshot_id"]],
            "version": snapshot["version"],
            "content_hash": snapshot["content_hash"][:16],
            "draft": snapshot["payload"]["draft"],
        }
        record = self.catalog.issue_approval(
            channel_id=str(update.effective_chat.id),
            item_id=item_id,
            step="publish_authorization",
            payload=value,
            snapshot_ids=[job["snapshot_id"]],
        )
        await update.effective_message.reply_text(
            render_interrupt(value),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Wystaw tę wersję", callback_data=f"publish:{record['token']}"
                        )
                    ]
                ]
            ),
        )

    async def edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._reject(update):
            return
        raw = " ".join(context.args).strip()
        if not raw:
            await update.effective_message.reply_text("Podaj nową wartość po /zmien.")
            return
        item_id = self._item_id(update.effective_chat.id)
        pending = self.catalog.pending_approval(str(update.effective_chat.id), item_id or "")
        kind = pending["step"] if pending else None
        try:
            if kind == "price":
                value: Any = float(raw.replace(",", "."))
            elif kind == "portals":
                value = [part.strip() for part in raw.split(",") if part.strip()]
            elif kind == "missing_info":
                value = parse_field_updates(raw)
            elif kind == "copy":
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = None
                value = parsed if isinstance(parsed, dict) else {"description": raw}
            else:
                value = raw
        except (ValueError, json.JSONDecodeError):
            await update.effective_message.reply_text("Nie rozumiem formatu poprawki.")
            return
        if item_id:
            self.catalog.revoke_pending_approval(str(update.effective_chat.id), item_id)
        await self._resume(update, {"action": "edit", "value": value})

    async def button(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        if await self._reject(update):
            return
        raw = query.data or ""
        if not raw.startswith(("approve:", "publish:")):
            await update.effective_message.reply_text("Nieaktualny format przycisku.")
            return
        item_id = self._item_id(update.effective_chat.id)
        pending = self.catalog.pending_approval(str(update.effective_chat.id), item_id or "")
        if item_id is None or pending is None:
            await update.effective_message.reply_text("Ta decyzja nie jest już aktualna.")
            return
        token = raw.split(":", 1)[1]
        await self._consume_and_resume(update, token, pending)

    async def _consume_and_resume(
        self, update: Update, token: str, pending: dict[str, Any]
    ) -> None:
        item_id = self._item_id(update.effective_chat.id)
        if item_id is None:
            await update.effective_message.reply_text("Brak aktywnego przedmiotu.")
            return
        try:
            approval = self.catalog.consume_approval(
                token=token,
                channel_id=str(update.effective_chat.id),
                item_id=item_id,
                expected_step=pending["step"],
            )
        except PermissionError as error:
            await update.effective_message.reply_text(f"Nie mogę użyć tej zgody: {error}.")
            return
        if pending["step"] == "publish_authorization":
            self.catalog.attach_publish_approval(
                pending["payload"]["job_id"], approval["approval_id"]
            )
            await update.effective_message.reply_text(
                "Zgoda zapisana. Worker wykona ponowny readback i dopiero wtedy kliknie publikację."
            )
            return
        await self._resume(
            update,
            {"action": "accept", "approval_id": approval["approval_id"]},
        )

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._reject(update):
            return
        item_id = self._item_id(update.effective_chat.id)
        item = self.catalog.get_item(item_id) if item_id else None
        pending = (
            self.catalog.pending_approval(str(update.effective_chat.id), item_id)
            if item_id
            else None
        )
        if pending:
            await update.effective_message.reply_text(
                render_interrupt(pending["payload"]),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "Akceptuję", callback_data=f"approve:{pending['token']}"
                            )
                        ]
                    ]
                ),
            )
            return
        jobs = self.catalog.list_execution_jobs(item_id) if item_id else []
        job_status = "; ".join(f"{job['portal']}: {job['status']}" for job in jobs)
        await update.effective_message.reply_text(
            f"Status: {item.status.value}; zdjęć: {len(item.photo_paths)}"
            + (f"; wykonanie: {job_status}" if job_status else "")
            if item
            else "Brak aktywnego przedmiotu."
        )

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._reject(update):
            return
        item_id = self._item_id(update.effective_chat.id)
        item = self.catalog.get_item(item_id) if item_id else None
        if item:
            item.status = WorkflowStatus.ARCHIVED
            self.catalog.save_item(item)
            self.catalog.revoke_pending_approval(str(update.effective_chat.id), item.item_id)
        self.catalog.clear_active_item(str(update.effective_chat.id))
        await update.effective_message.reply_text(
            "Przedmiot zarchiwizowany; zdjęcia pozostają lokalnie."
        )

    async def run(self) -> None:
        await self.application.initialize()
        await self.application.start()
        assert self.application.updater is not None
        await self.application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        try:
            await asyncio.Event().wait()
        finally:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
