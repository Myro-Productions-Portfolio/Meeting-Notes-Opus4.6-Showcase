"""Core parsing logic -- turn raw meeting text into structured ActionItems."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta


@dataclass(frozen=True, slots=True)
class ActionItem:
    """A single action item extracted from meeting notes."""

    task: str
    owner: str = "unassigned"
    due_date: str = ""          # ISO-8601 date string, e.g. "2026-02-14"
    priority: str = "normal"    # low | normal | high | critical
    raw_line: str = ""


# ---------------------------------------------------------------------------
# Month-name lookup
# ---------------------------------------------------------------------------

_MONTH_NAMES: dict[str, int] = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

# ---------------------------------------------------------------------------
# Day-of-week lookup (Monday=0 ... Sunday=6, matching date.weekday())
# ---------------------------------------------------------------------------

_DAY_NAMES: dict[str, int] = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thurs": 3, "thur": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}

# ---------------------------------------------------------------------------
# Priority mapping
# ---------------------------------------------------------------------------

_PRIORITY_MAP: dict[str, str] = {
    "p0": "critical",
    "p1": "high",
    "p2": "normal",
}


# ===================================================================
# normalize_date
# ===================================================================

def normalize_date(raw: str) -> str:
    """Best-effort conversion of a free-form date string to ISO-8601.

    Returns an empty string when the input cannot be interpreted.

    Parameters
    ----------
    raw:
        A human-written date fragment, e.g. "Feb 14", "2026-02-14", "next Friday".

    Returns
    -------
    str
        An ISO-8601 date string (YYYY-MM-DD) or ``""`` on failure.
    """
    raw = raw.strip()
    if not raw:
        return ""

    today = date.today()

    # 1) Already ISO-8601: "2026-02-28"
    try:
        parsed = date.fromisoformat(raw)
        return parsed.isoformat()
    except ValueError:
        pass

    lowered = raw.lower()

    # 2) Quarter references (Q1, Q2, etc.) -- not precise enough
    if re.fullmatch(r"q[1-4]", lowered):
        return ""

    # 3) Relative day: "next Monday", "next Friday", etc.
    m_relative = re.fullmatch(r"next\s+(\w+)", lowered)
    if m_relative:
        day_name = m_relative.group(1)
        target_weekday = _DAY_NAMES.get(day_name)
        if target_weekday is not None:
            current_weekday = today.weekday()
            days_ahead = (target_weekday - current_weekday) % 7
            # "next X" always means the *coming* occurrence, at least 7 days
            # out if today IS that day, otherwise the nearest future occurrence
            # that is strictly in the next week-cycle.
            if days_ahead == 0:
                days_ahead = 7
            result = today + timedelta(days=days_ahead)
            return result.isoformat()
        return ""

    # 4) "today" / "tomorrow"
    if lowered == "today":
        return today.isoformat()
    if lowered == "tomorrow":
        return (today + timedelta(days=1)).isoformat()

    # 5) US-style slash date: "2/20", "2/20/2026", "02/20/2026"
    m_slash = re.fullmatch(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?", raw)
    if m_slash:
        month = int(m_slash.group(1))
        day = int(m_slash.group(2))
        year_str = m_slash.group(3)
        if year_str:
            year = int(year_str)
            if year < 100:
                year += 2000
        else:
            year = today.year
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return ""

    # 6) Month-name date: "March 1", "Feb 14", "February 14, 2026",
    #    "14 March", "14 March 2026"
    # Pattern A: "Month Day[, Year]"
    m_month_day = re.fullmatch(
        r"(\w+)\s+(\d{1,2})(?:\s*,?\s*(\d{4}))?", raw, re.IGNORECASE
    )
    if m_month_day:
        month_str = m_month_day.group(1).lower()
        month = _MONTH_NAMES.get(month_str)
        if month is not None:
            day = int(m_month_day.group(2))
            year = int(m_month_day.group(3)) if m_month_day.group(3) else today.year
            try:
                return date(year, month, day).isoformat()
            except ValueError:
                return ""

    # Pattern B: "Day Month[, Year]"
    m_day_month = re.fullmatch(
        r"(\d{1,2})\s+(\w+)(?:\s*,?\s*(\d{4}))?", raw, re.IGNORECASE
    )
    if m_day_month:
        day = int(m_day_month.group(1))
        month_str = m_day_month.group(2).lower()
        month = _MONTH_NAMES.get(month_str)
        if month is not None:
            year = int(m_day_month.group(3)) if m_day_month.group(3) else today.year
            try:
                return date(year, month, day).isoformat()
            except ValueError:
                return ""

    # Nothing matched
    return ""


# ===================================================================
# Internal helpers for parse_meeting_notes
# ===================================================================

def _extract_priority(line: str) -> str:
    """Return the priority level found in *line*, or ``"normal"``."""
    m = re.search(r"\(?\b(P[012])\b\)?", line, re.IGNORECASE)
    if m:
        return _PRIORITY_MAP.get(m.group(1).lower(), "normal")

    m2 = re.search(r"Priority:\s*(P[012])\b", line, re.IGNORECASE)
    if m2:
        return _PRIORITY_MAP.get(m2.group(1).lower(), "normal")

    return "normal"


def _extract_owner(line: str) -> str:
    """Return the owner name found in *line*, or ``"unassigned"``."""
    # "Owner: Name" (possibly followed by punctuation / semicolon / period)
    m = re.search(r"Owner:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", line)
    if m:
        return m.group(1).strip()

    # "(owner Name)"
    m2 = re.search(r"\(owner\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\)", line, re.IGNORECASE)
    if m2:
        return m2.group(1).strip()

    # Detect "(no owner yet)" and similar explicit unassigned markers
    if re.search(r"\(no\s+owner", line, re.IGNORECASE):
        return "unassigned"

    return "unassigned"


def _extract_due_date(line: str) -> str:
    """Return a normalized due date found in *line*, or ``""``."""
    # "Due: <date>" or "due <date>" -- capture until punctuation/semicolon/EOL
    m = re.search(r"[Dd]ue:?\s+([^;.\n]+)", line)
    if m:
        raw_date = m.group(1).strip().rstrip(".")
        # Remove trailing priority tags like "(P1)" from the date string
        raw_date = re.sub(r"\s*\(P[012]\)\s*$", "", raw_date, flags=re.IGNORECASE)
        result = normalize_date(raw_date)
        if result:
            return result

    # "by <date>" pattern
    m2 = re.search(r"\bby\s+([^;.\n]+)", line, re.IGNORECASE)
    if m2:
        raw_date = m2.group(1).strip().rstrip(".")
        raw_date = re.sub(r"\s*\(P[012]\)\s*$", "", raw_date, flags=re.IGNORECASE)
        result = normalize_date(raw_date)
        if result:
            return result

    return ""


def _clean_task_text(task: str) -> str:
    """Remove inline metadata annotations from extracted task text."""
    # Strip "Owner: Name" fragments
    task = re.sub(r"\s*;?\s*Owner:\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s*;?", "", task)
    # Strip "(owner Name)" fragments
    task = re.sub(r"\s*\(owner\s+\w+\)", "", task, flags=re.IGNORECASE)
    # Strip "Due: ..." fragments
    task = re.sub(r"\s*;?\s*[Dd]ue:?\s+[^;.\n]+", "", task)
    # Strip "by <date>" fragments only when they look like a date
    task = re.sub(r"\s+by\s+(?:next\s+\w+|\d{1,2}/\d{1,2}(?:/\d{2,4})?|"
                  r"\d{4}-\d{2}-\d{2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2}(?:\s*,?\s*\d{4})?)",
                  "", task, flags=re.IGNORECASE)
    # Strip "Priority: P0/P1/P2"
    task = re.sub(r"\s*;?\s*Priority:\s*P[012]\s*;?", "", task, flags=re.IGNORECASE)
    # Strip standalone "(P0)", "(P1)", "(P2)"
    task = re.sub(r"\s*\(P[012]\)", "", task, flags=re.IGNORECASE)
    # Strip "(no owner yet)" and similar
    task = re.sub(r"\s*\(no\s+owner\s+\w*\)", "", task, flags=re.IGNORECASE)
    # Clean up residual punctuation/whitespace
    task = re.sub(r"\s*;\s*$", "", task)
    task = re.sub(r"\s{2,}", " ", task)
    return task.strip().rstrip(".").strip()


# ===================================================================
# parse_meeting_notes
# ===================================================================

# Patterns that indicate a line is an action item
_RE_TODO = re.compile(r"^TODO:\s*(.+)", re.IGNORECASE)
_RE_ACTION = re.compile(r"^Action:\s*(.+)", re.IGNORECASE)
_RE_ACTION_ITEM = re.compile(r"^ACTION\s+ITEM\s*(?:--|[\u2014:\-])\s*(.+)", re.IGNORECASE)
_RE_REMINDER = re.compile(r"^Reminder:\s*(.+)", re.IGNORECASE)
_RE_NAME_TO_VERB = re.compile(
    r"^([A-Z][a-z]+)\s+to\s+(draft|send|create|write|fix|update|review|prepare|"
    r"build|design|implement|schedule|reach|migrate|set\s+up|check|follow|complete|"
    r"submit|finalize|organize|coordinate|investigate|test|deploy|audit|document|"
    r"analyze|configure|remove|add|refactor|propose|plan|outline|establish)\b(.+)?",
    re.IGNORECASE,
)

# Patterns that indicate a line is NOT an action item
_RE_DECISION = re.compile(r"(?:^|\W)Decisions?:\s*", re.IGNORECASE)

# Priority-only lines: lines that contain (P0)/(P1)/(P2) suggesting urgency
_RE_PRIORITY_TAG = re.compile(r"\(P[012]\)", re.IGNORECASE)


def parse_meeting_notes(text: str) -> list[ActionItem]:
    """Extract action items from unstructured meeting-note text.

    Parameters
    ----------
    text:
        The full content of a meeting-notes document.

    Returns
    -------
    list[ActionItem]
        Zero or more action items found in *text*, in document order.
    """
    items: list[ActionItem] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # ---- Skip non-action lines ----
        if _RE_DECISION.search(line):
            continue

        task_text: str | None = None
        owner = "unassigned"

        # 1) "TODO: ..."
        m = _RE_TODO.match(line)
        if m:
            task_text = m.group(1)

        # 2) "Action: ..."
        if task_text is None:
            m = _RE_ACTION.match(line)
            if m:
                task_text = m.group(1)

        # 3) "ACTION ITEM -- ..."
        if task_text is None:
            m = _RE_ACTION_ITEM.match(line)
            if m:
                task_text = m.group(1)

        # 4) "Reminder: ..."
        if task_text is None:
            m = _RE_REMINDER.match(line)
            if m:
                task_text = m.group(1)

        # 5) "Name to verb..." pattern
        if task_text is None:
            m = _RE_NAME_TO_VERB.match(line)
            if m:
                owner = m.group(1)
                verb = m.group(2)
                rest = m.group(3) or ""
                task_text = f"{verb}{rest}".strip()

        # 6) Lines with a priority tag like (P1) that are not decisions
        if task_text is None and _RE_PRIORITY_TAG.search(line):
            task_text = line

        # If nothing matched, skip this line
        if task_text is None:
            continue

        # ---- Extract metadata ----
        # Owner: check full original line first so we don't miss metadata
        extracted_owner = _extract_owner(line)
        if extracted_owner != "unassigned":
            owner = extracted_owner
        # (owner from "Name to verb" pattern is already set above)

        due = _extract_due_date(line)
        priority = _extract_priority(line)

        # ---- Clean task text ----
        clean_task = _clean_task_text(task_text)
        if not clean_task:
            continue

        items.append(ActionItem(
            task=clean_task,
            owner=owner,
            due_date=due,
            priority=priority,
            raw_line=raw_line.strip(),
        ))

    return items
