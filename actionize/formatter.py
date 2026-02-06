"""Output formatters -- render ActionItems as Markdown or JSON."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from actionize.parser import ActionItem


def sort_items(items: list[ActionItem]) -> list[ActionItem]:
    """Sort action items by owner (ascending) then due_date (ascending).

    Items whose owner is ``"unassigned"`` or whose due_date is empty are
    placed at the end of their respective sort groups.

    Parameters
    ----------
    items:
        The unsorted action items.

    Returns
    -------
    list[ActionItem]
        A new list in deterministic order.
    """

    def _sort_key(item: ActionItem) -> tuple[bool, str, bool, str]:
        owner_unknown = item.owner.lower() in ("", "unassigned")
        date_unknown = item.due_date == ""
        return (owner_unknown, item.owner.lower(), date_unknown, item.due_date)

    return sorted(items, key=_sort_key)


def format_markdown(items: list[ActionItem]) -> str:
    """Render a sorted list of action items as a Markdown checklist.

    Parameters
    ----------
    items:
        Action items to render (will be sorted internally).

    Returns
    -------
    str
        A complete Markdown document.
    """
    sorted_items = sort_items(items)
    lines: list[str] = ["# Action Items", ""]

    if not sorted_items:
        lines.append("_No action items found._")
        lines.append("")
        return "\n".join(lines)

    for item in sorted_items:
        due = f" (due {item.due_date})" if item.due_date else ""
        owner = f" @{item.owner}" if item.owner != "unassigned" else ""
        priority_tag = f" [{item.priority}]" if item.priority != "normal" else ""
        lines.append(f"- [ ] {item.task}{owner}{due}{priority_tag}")

    lines.append("")  # trailing newline
    return "\n".join(lines)


def format_json(items: list[ActionItem]) -> str:
    """Render a sorted list of action items as a JSON document.

    Parameters
    ----------
    items:
        Action items to render (will be sorted internally).

    Returns
    -------
    str
        A pretty-printed JSON string with deterministic key order.
    """
    sorted_items = sort_items(items)
    payload = {
        "action_items": [asdict(item) for item in sorted_items],
        "count": len(sorted_items),
    }
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
