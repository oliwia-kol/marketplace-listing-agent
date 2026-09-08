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
        return "Proponowane portale:\n" + "\n".join(rows) + "\n\n/zmien olx,vinted"
    if kind == "missing_info":
        questions = "\n".join(f"• {question}" for question in value["questions"])
        return (
            f"Model zauważył możliwe braki:\n{questions}\n\n"
            'Możesz je pominąć albo dodać: /zmien {"material": "wełna"}'
        )
    if kind == "price":
        summary = value["summary"]
        counts = ", ".join(
            f"{row['count']} x {row['price_pln']:.0f} zł" for row in summary["exact_price_counts"]
        )
        recommendations = ", ".join(
            f"{row['strategy']}: {row['price_pln']:.0f} zł" for row in summary["recommendations"]
        )
        return (
            f"Zweryfikowano {summary['reachable_count']} linków; porównywalnych: "
            f"{summary['comparable_count']}; kwarantanna: "
            f"{summary.get('quarantined_count', 0)}.\n"
            f"Rozkład: {counts or 'brak danych'}\n"
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
        return "Formularze są gotowe do wypełnienia. Chrome zostanie otwarty; publikujesz ręcznie."
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
        self.pending: dict[int, dict[str, Any]] = {}
        self.application = Application.builder().token(token).build()
        self.application.add_handler(CommandHandler("start", self.help))
        self.application.add_handler(CommandHandler("pomoc", self.help))
        self.application.add_handler(CommandHandler("nowa", self.new_item))
        self.application.add_handler(CommandHandler("gotowe", self.process_item))
        self.application.add_handler(CommandHandler("status", self.status))
        self.application.add_handler(CommandHandler("zaakceptuj", self.accept))
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
            context.chat_data["notes"] = "\n".join(
                part for part in [context.chat_data.get("notes", ""), caption] if part
            )
        await update.effective_message.reply_text(f"Mam zdjęcie {len(item.photo_paths)}.")

    async def note(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._reject(update):
            return
        item_id = self._item_id(update.effective_chat.id)
        item = self.catalog.get_item(item_id) if item_id else None
        if item is None or item.status != WorkflowStatus.NEW:
            return
        text = update.effective_message.text.strip()
        context.chat_data["notes"] = "\n".join(
            part for part in [context.chat_data.get("notes", ""), text] if part
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
                "user_notes": context.chat_data.get("notes", ""),
            },
            config={"configurable": {"thread_id": item.item_id}},
        )
        await self._show_result(update, result)

    async def _show_result(self, update: Update, result: dict[str, Any]) -> None:
        interrupts = result.get("__interrupt__", ())
        if interrupts:
            value = interrupts[0].value
            self.pending[update.effective_chat.id] = value
            await update.effective_message.reply_text(
                render_interrupt(value),
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("Akceptuję", callback_data="accept")]]
                ),
            )
            return
        item = ItemCase.model_validate(result["item"])
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
        if not await self._reject(update):
            await self._resume(update, {"action": "accept"})

    async def edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._reject(update):
            return
        raw = " ".join(context.args).strip()
        if not raw:
            await update.effective_message.reply_text("Podaj nową wartość po /zmien.")
            return
        kind = self.pending.get(update.effective_chat.id, {}).get("kind")
        try:
            if kind == "price":
                value: Any = float(raw.replace(",", "."))
            elif kind == "portals":
                value = [part.strip() for part in raw.split(",") if part.strip()]
            elif kind in {"copy", "missing_info"}:
                value = json.loads(raw)
            else:
                value = raw
        except (ValueError, json.JSONDecodeError):
            await update.effective_message.reply_text("Nie rozumiem formatu poprawki.")
            return
        await self._resume(update, {"action": "edit", "value": value})

    async def button(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        if await self._reject(update):
            return
        await self._resume(update, {"action": "accept"})

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._reject(update):
            return
        item_id = self._item_id(update.effective_chat.id)
        item = self.catalog.get_item(item_id) if item_id else None
        await update.effective_message.reply_text(
            f"Status: {item.status.value}; zdjęć: {len(item.photo_paths)}"
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
