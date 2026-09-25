from __future__ import annotations

from typing import Any, TypedDict


class ListingState(TypedDict, total=False):
    """Serializable state persisted by the LangGraph checkpointer."""

    item: dict[str, Any]
    run_id: str
    user_notes: str
    missing_questions: list[str]
    portal_reasons: dict[str, str]
    copy_warnings: dict[str, list[str]]
    copy_deadline_at: str
    fill_approval_id: str
    execution_job_ids: list[str]
    error: str


def approval_value(response: Any, current: Any) -> tuple[bool, Any]:
    """Normalize UI-independent accept/edit responses from any channel."""
    if response == "accept":
        return True, current
    if isinstance(response, dict):
        action = response.get("action")
        if action == "accept":
            return True, current
        if action == "edit":
            return True, response.get("value")
    return False, current
