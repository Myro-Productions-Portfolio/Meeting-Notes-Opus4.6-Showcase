"""Tests for actionize.parser -- normalize_date and parse_meeting_notes."""

from __future__ import annotations

import pytest

from actionize.parser import ActionItem, normalize_date, parse_meeting_notes


# ===================================================================
# normalize_date
# ===================================================================


class TestNormalizeDate:
    """Unit tests for the normalize_date helper."""

    def test_iso_passthrough(self) -> None:
        """An ISO-8601 date is returned unchanged."""
        assert normalize_date("2026-02-28") == "2026-02-28"

    def test_us_slash_without_year(self) -> None:
        """A US-style slash date with no year assumes the current year."""
        # NOTE: This test assumes execution in the year 2026. If run in a
        # different year the expected value must be adjusted.
        assert normalize_date("2/20") == "2026-02-20"

    def test_us_slash_with_year(self) -> None:
        """A US-style slash date with an explicit four-digit year."""
        assert normalize_date("2/20/2026") == "2026-02-20"

    def test_us_slash_with_two_digit_year(self) -> None:
        """A two-digit year is treated as 20xx."""
        assert normalize_date("2/20/26") == "2026-02-20"

    def test_month_name_without_year(self) -> None:
        """'March 1' resolves to 2026-03-01 in the current year."""
        assert normalize_date("March 1") == "2026-03-01"

    def test_month_name_with_year(self) -> None:
        """'February 14, 2026' resolves to 2026-02-14."""
        assert normalize_date("February 14, 2026") == "2026-02-14"

    def test_abbreviated_month_name(self) -> None:
        """Abbreviated month names like 'Feb 14' are recognized."""
        assert normalize_date("Feb 14") == "2026-02-14"

    def test_day_month_order(self) -> None:
        """'14 March' (day-first) is recognized."""
        assert normalize_date("14 March") == "2026-03-14"

    def test_quarter_returns_empty(self) -> None:
        """Quarter references like 'Q2' are too vague and return empty."""
        assert normalize_date("Q2") == ""

    def test_empty_string_returns_empty(self) -> None:
        """An empty input string returns empty."""
        assert normalize_date("") == ""

    def test_whitespace_only_returns_empty(self) -> None:
        """Whitespace-only input returns empty after stripping."""
        assert normalize_date("   ") == ""

    def test_garbage_returns_empty(self) -> None:
        """Unrecognizable input returns empty."""
        assert normalize_date("asdfgh") == ""

    def test_today(self) -> None:
        """'today' resolves to today's date."""
        from datetime import date

        assert normalize_date("today") == date.today().isoformat()

    def test_tomorrow(self) -> None:
        """'tomorrow' resolves to tomorrow's date."""
        from datetime import date, timedelta

        expected = (date.today() + timedelta(days=1)).isoformat()
        assert normalize_date("tomorrow") == expected

    def test_next_day_name(self) -> None:
        """'next Monday' resolves to the upcoming Monday.

        NOTE: This test is deterministic only when run on 2026-02-06
        (a Friday).  On that date, next Monday = 2026-02-09.
        """
        # 2026-02-06 is a Friday (weekday 4). The nearest Monday is 3
        # days later -> 2026-02-09.
        assert normalize_date("next Monday") == "2026-02-09"

    def test_invalid_date_values(self) -> None:
        """A slash date with impossible day/month returns empty."""
        assert normalize_date("13/40") == ""

    def test_all_quarters_return_empty(self) -> None:
        """All single-digit quarter references are rejected."""
        for q in ("Q1", "Q2", "Q3", "Q4"):
            assert normalize_date(q) == "", f"Expected empty for {q}"


# ===================================================================
# parse_meeting_notes -- golden input
# ===================================================================


# The canonical meeting-notes sample used as the golden input.
GOLDEN_INPUT = """\
Kickoff sync \u2014 Decisions: use SSO for internal users.

TODO: Update onboarding doc. Owner: Priya. Due: next Friday.

Action: Reach out to vendor about pricing tiers (owner Sam) due 2/20

We should probably fix flaky CI tests soon (P1)

John to draft API rate limit proposal by March 1

Reminder: Send customer follow-up email (no owner yet)

Decision: move launch to Q2.

ACTION ITEM \u2014 Migrate staging database; Owner: Mei; Due: 2026-02-28; Priority: P0
"""

# NOTE: The due_date for item 1 ("next Friday") is computed relative to
# today's date.  This golden expectation is valid when today == 2026-02-06.
# If tests are run on a different date the "next Friday" value will differ and
# this test will fail.  This is by design -- the golden file locks a known
# snapshot so regressions are immediately visible.
GOLDEN_EXPECTED: list[dict[str, str]] = [
    {
        "task": "Update onboarding doc",
        "owner": "Priya",
        "due_date": "2026-02-13",
        "priority": "normal",
    },
    {
        "task": "Reach out to vendor about pricing tiers",
        "owner": "Sam",
        "due_date": "2026-02-20",
        "priority": "normal",
    },
    {
        "task": "We should probably fix flaky CI tests soon",
        "owner": "unassigned",
        "due_date": "",
        "priority": "high",
    },
    {
        "task": "draft API rate limit proposal",
        "owner": "John",
        "due_date": "2026-03-01",
        "priority": "normal",
    },
    {
        "task": "Send customer follow-up email",
        "owner": "unassigned",
        "due_date": "",
        "priority": "normal",
    },
    {
        "task": "Migrate staging database",
        "owner": "Mei",
        "due_date": "2026-02-28",
        "priority": "critical",
    },
]


class TestParseMeetingNotesGolden:
    """Golden-file style assertions against the canonical meeting notes."""

    @pytest.fixture()
    def parsed_items(self) -> list[ActionItem]:
        """Parse the golden input once for all tests in this class."""
        return parse_meeting_notes(GOLDEN_INPUT)

    def test_item_count(self, parsed_items: list[ActionItem]) -> None:
        """Exactly six action items are extracted."""
        assert len(parsed_items) == 6

    @pytest.mark.parametrize(
        "index",
        range(len(GOLDEN_EXPECTED)),
        ids=[f"item_{i}_{GOLDEN_EXPECTED[i]['task'][:30]}" for i in range(len(GOLDEN_EXPECTED))],
    )
    def test_item_fields(self, parsed_items: list[ActionItem], index: int) -> None:
        """Each parsed item matches its golden expectation for task, owner,
        due_date, and priority."""
        expected = GOLDEN_EXPECTED[index]
        actual = parsed_items[index]
        assert actual.task == expected["task"], f"task mismatch at index {index}"
        assert actual.owner == expected["owner"], f"owner mismatch at index {index}"
        assert actual.due_date == expected["due_date"], f"due_date mismatch at index {index}"
        assert actual.priority == expected["priority"], f"priority mismatch at index {index}"

    def test_raw_lines_are_populated(self, parsed_items: list[ActionItem]) -> None:
        """Every parsed item preserves its original raw_line."""
        for item in parsed_items:
            assert item.raw_line != "", f"raw_line empty for task={item.task!r}"

    def test_deterministic_ordering(self, parsed_items: list[ActionItem]) -> None:
        """Items appear in document order (not sorted)."""
        tasks = [item.task for item in parsed_items]
        expected_tasks = [e["task"] for e in GOLDEN_EXPECTED]
        assert tasks == expected_tasks


# ===================================================================
# parse_meeting_notes -- edge cases
# ===================================================================


class TestParseMeetingNotesEdgeCases:
    """Edge-case tests for parse_meeting_notes."""

    def test_empty_input(self) -> None:
        """Empty string produces an empty list."""
        assert parse_meeting_notes("") == []

    def test_whitespace_only_input(self) -> None:
        """Input containing only whitespace produces an empty list."""
        assert parse_meeting_notes("   \n  \n\t\n") == []

    def test_decisions_only_input(self) -> None:
        """Lines that only contain decisions produce no action items."""
        text = (
            "Decisions: use Postgres for storage.\n"
            "Decision: target Q2 launch.\n"
        )
        assert parse_meeting_notes(text) == []

    def test_single_todo_line(self) -> None:
        """A single TODO line is correctly parsed."""
        items = parse_meeting_notes("TODO: Write integration tests.")
        assert len(items) == 1
        assert items[0].task == "Write integration tests"
        assert items[0].owner == "unassigned"
        assert items[0].due_date == ""
        assert items[0].priority == "normal"

    def test_single_action_line(self) -> None:
        """A single Action line is correctly parsed."""
        items = parse_meeting_notes("Action: Review pull request (owner Bob) due 2/15")
        assert len(items) == 1
        assert items[0].owner == "Bob"

    def test_name_to_verb_pattern(self) -> None:
        """'Name to verb ...' pattern extracts owner and task."""
        items = parse_meeting_notes("Alice to review the deployment plan by March 10")
        assert len(items) == 1
        assert items[0].owner == "Alice"
        assert items[0].due_date == "2026-03-10"

    def test_priority_p0_maps_to_critical(self) -> None:
        """P0 priority maps to 'critical'."""
        items = parse_meeting_notes("ACTION ITEM -- Fix production outage; Priority: P0")
        assert len(items) == 1
        assert items[0].priority == "critical"

    def test_priority_p2_maps_to_normal(self) -> None:
        """P2 priority maps to 'normal'."""
        items = parse_meeting_notes("ACTION ITEM -- Improve logging; Priority: P2")
        assert len(items) == 1
        assert items[0].priority == "normal"

    def test_missing_owner_defaults_to_unassigned(self) -> None:
        """When no owner is specified the default is 'unassigned'."""
        items = parse_meeting_notes("TODO: Fix the bug.")
        assert len(items) == 1
        assert items[0].owner == "unassigned"

    def test_explicit_no_owner_is_unassigned(self) -> None:
        """'(no owner yet)' is recognized as unassigned."""
        items = parse_meeting_notes("Reminder: Check server logs (no owner yet)")
        assert len(items) == 1
        assert items[0].owner == "unassigned"

    def test_multiple_items_preserve_document_order(self) -> None:
        """Multiple items are returned in the order they appear in text."""
        text = (
            "TODO: First task. Owner: Alpha.\n"
            "TODO: Second task. Owner: Bravo.\n"
            "TODO: Third task. Owner: Charlie.\n"
        )
        items = parse_meeting_notes(text)
        assert len(items) == 3
        assert items[0].owner == "Alpha"
        assert items[1].owner == "Bravo"
        assert items[2].owner == "Charlie"

    def test_ambiguous_date_formats(self) -> None:
        """Ensure 'by March 1' and 'due 3/1' both resolve to the same date."""
        items_a = parse_meeting_notes("TODO: Task A. Due: March 1.")
        items_b = parse_meeting_notes("TODO: Task B. Due: 3/1.")
        assert items_a[0].due_date == items_b[0].due_date == "2026-03-01"

    def test_action_item_with_em_dash(self) -> None:
        """ACTION ITEM with an em-dash separator is recognized."""
        items = parse_meeting_notes(
            "ACTION ITEM \u2014 Deploy hotfix; Owner: Kim; Due: 2026-03-15"
        )
        assert len(items) == 1
        assert items[0].task == "Deploy hotfix"
        assert items[0].owner == "Kim"

    def test_reminder_line(self) -> None:
        """Reminder lines are parsed as action items."""
        items = parse_meeting_notes("Reminder: Update the wiki.")
        assert len(items) == 1
        assert items[0].task == "Update the wiki"

    def test_case_insensitive_todo(self) -> None:
        """'todo:' in various cases is recognized."""
        for prefix in ("TODO:", "todo:", "Todo:"):
            items = parse_meeting_notes(f"{prefix} Do something.")
            assert len(items) == 1, f"Failed for prefix {prefix!r}"


# ===================================================================
# ActionItem dataclass
# ===================================================================


class TestActionItem:
    """Tests for the ActionItem dataclass itself."""

    def test_default_values(self) -> None:
        """ActionItem has sensible defaults for optional fields."""
        item = ActionItem(task="Test task")
        assert item.owner == "unassigned"
        assert item.due_date == ""
        assert item.priority == "normal"
        assert item.raw_line == ""

    def test_frozen(self) -> None:
        """ActionItem is immutable (frozen=True)."""
        item = ActionItem(task="Immutable task")
        with pytest.raises(AttributeError):
            item.task = "mutated"  # type: ignore[misc]

    def test_equality(self) -> None:
        """Two ActionItems with the same fields are equal."""
        a = ActionItem(task="Same", owner="Alice", due_date="2026-01-01")
        b = ActionItem(task="Same", owner="Alice", due_date="2026-01-01")
        assert a == b

    def test_inequality(self) -> None:
        """ActionItems with different fields are not equal."""
        a = ActionItem(task="Task A")
        b = ActionItem(task="Task B")
        assert a != b
