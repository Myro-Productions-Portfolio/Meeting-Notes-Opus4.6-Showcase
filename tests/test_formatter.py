"""Tests for actionize.formatter -- sort_items, format_markdown, format_json."""

from __future__ import annotations

import json

import pytest

from actionize.formatter import format_json, format_markdown, sort_items
from actionize.parser import ActionItem


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture()
def assigned_items() -> list[ActionItem]:
    """Three items with distinct owners and due dates for sorting tests."""
    return [
        ActionItem(task="Task C", owner="Charlie", due_date="2026-03-15"),
        ActionItem(task="Task A", owner="Alice", due_date="2026-02-10"),
        ActionItem(task="Task B", owner="Bob", due_date="2026-02-20"),
    ]


@pytest.fixture()
def mixed_items() -> list[ActionItem]:
    """Items with a mix of assigned/unassigned owners and present/empty dates."""
    return [
        ActionItem(task="Unassigned late", owner="unassigned", due_date="2026-04-01"),
        ActionItem(task="Bob early", owner="Bob", due_date="2026-01-15"),
        ActionItem(task="Alice no date", owner="Alice", due_date=""),
        ActionItem(task="Unassigned no date", owner="unassigned", due_date=""),
        ActionItem(task="Alice early", owner="Alice", due_date="2026-02-01"),
        ActionItem(task="Bob late", owner="Bob", due_date="2026-06-01"),
    ]


# ===================================================================
# sort_items
# ===================================================================


class TestSortItems:
    """Unit tests for the sort_items function."""

    def test_assigned_before_unassigned(self) -> None:
        """Items with real owners sort before 'unassigned' items."""
        items = [
            ActionItem(task="No owner", owner="unassigned", due_date="2026-01-01"),
            ActionItem(task="Has owner", owner="Zara", due_date="2026-12-31"),
        ]
        result = sort_items(items)
        assert result[0].owner == "Zara"
        assert result[1].owner == "unassigned"

    def test_alphabetical_by_owner(self, assigned_items: list[ActionItem]) -> None:
        """Assigned owners are sorted alphabetically (case-insensitive)."""
        result = sort_items(assigned_items)
        owners = [item.owner for item in result]
        assert owners == ["Alice", "Bob", "Charlie"]

    def test_same_owner_sorted_by_due_date(self) -> None:
        """Among items with the same owner, earlier due_date comes first."""
        items = [
            ActionItem(task="Later", owner="Dan", due_date="2026-06-01"),
            ActionItem(task="Earlier", owner="Dan", due_date="2026-02-01"),
        ]
        result = sort_items(items)
        assert result[0].task == "Earlier"
        assert result[1].task == "Later"

    def test_empty_due_date_sorts_last_within_owner(self) -> None:
        """Items with no due_date sort after items with a due_date for the
        same owner."""
        items = [
            ActionItem(task="No date", owner="Eve", due_date=""),
            ActionItem(task="Has date", owner="Eve", due_date="2026-03-01"),
        ]
        result = sort_items(items)
        assert result[0].task == "Has date"
        assert result[1].task == "No date"

    def test_empty_list(self) -> None:
        """Sorting an empty list returns an empty list."""
        assert sort_items([]) == []

    def test_single_item(self, sample_action_item: ActionItem) -> None:
        """Sorting a single item returns a list with that item."""
        result = sort_items([sample_action_item])
        assert len(result) == 1
        assert result[0] is sample_action_item

    def test_full_deterministic_order(self, mixed_items: list[ActionItem]) -> None:
        """Verify the complete deterministic sort order with mixed data."""
        result = sort_items(mixed_items)
        tasks = [item.task for item in result]
        # Expected: assigned owners first (alphabetically), then by date
        # (empty last); then unassigned owners, then by date (empty last).
        expected = [
            "Alice early",       # Alice, 2026-02-01
            "Alice no date",     # Alice, "" (empty last)
            "Bob early",         # Bob, 2026-01-15
            "Bob late",          # Bob, 2026-06-01
            "Unassigned late",   # unassigned, 2026-04-01
            "Unassigned no date",  # unassigned, "" (empty last)
        ]
        assert tasks == expected

    def test_sort_is_stable_for_equal_keys(self) -> None:
        """Items with identical sort keys maintain their original order."""
        items = [
            ActionItem(task="First", owner="unassigned", due_date=""),
            ActionItem(task="Second", owner="unassigned", due_date=""),
            ActionItem(task="Third", owner="unassigned", due_date=""),
        ]
        result = sort_items(items)
        assert [i.task for i in result] == ["First", "Second", "Third"]


# ===================================================================
# format_markdown
# ===================================================================


class TestFormatMarkdown:
    """Unit tests for the format_markdown function."""

    def test_empty_list(self) -> None:
        """An empty items list produces the 'no items' placeholder."""
        result = format_markdown([])
        assert result == "# Action Items\n\n_No action items found._\n"

    def test_single_normal_item(self) -> None:
        """A single item with normal priority renders without a priority tag."""
        items = [
            ActionItem(
                task="Write docs",
                owner="Alice",
                due_date="2026-03-01",
                priority="normal",
            ),
        ]
        result = format_markdown(items)
        assert "- [ ] Write docs @Alice (due 2026-03-01)" in result
        # Normal priority should NOT have a tag
        assert "[normal]" not in result

    def test_high_priority_tag(self) -> None:
        """High priority items show the [high] tag."""
        items = [ActionItem(task="Fix bug", priority="high")]
        result = format_markdown(items)
        assert "[high]" in result

    def test_critical_priority_tag(self) -> None:
        """Critical priority items show the [critical] tag."""
        items = [ActionItem(task="Outage", priority="critical")]
        result = format_markdown(items)
        assert "[critical]" in result

    def test_owner_prefix(self) -> None:
        """Assigned owners appear as @Owner in the output."""
        items = [ActionItem(task="Review PR", owner="Bob")]
        result = format_markdown(items)
        assert "@Bob" in result

    def test_unassigned_owner_omitted(self) -> None:
        """Unassigned items do not show an @owner tag."""
        items = [ActionItem(task="Orphan task", owner="unassigned")]
        result = format_markdown(items)
        assert "@unassigned" not in result

    def test_due_date_formatted(self) -> None:
        """Due dates appear in parentheses."""
        items = [ActionItem(task="Ship it", due_date="2026-05-01")]
        result = format_markdown(items)
        assert "(due 2026-05-01)" in result

    def test_no_due_date_omits_parentheses(self) -> None:
        """Items without a due date do not show (due ...)."""
        items = [ActionItem(task="Someday task")]
        result = format_markdown(items)
        assert "(due" not in result

    def test_heading_present(self) -> None:
        """Output always starts with the '# Action Items' heading."""
        result = format_markdown([ActionItem(task="X")])
        assert result.startswith("# Action Items\n")

    def test_trailing_newline(self) -> None:
        """Output ends with a trailing newline."""
        result = format_markdown([ActionItem(task="X")])
        assert result.endswith("\n")

    def test_items_are_sorted_in_output(self) -> None:
        """format_markdown sorts items internally before rendering."""
        items = [
            ActionItem(task="Zulu task", owner="Zara"),
            ActionItem(task="Alpha task", owner="Alice"),
        ]
        result = format_markdown(items)
        lines = [l for l in result.splitlines() if l.startswith("- [ ]")]
        assert "Alpha task" in lines[0]
        assert "Zulu task" in lines[1]

    def test_checkbox_format(self) -> None:
        """Each action item line starts with '- [ ] '."""
        items = [ActionItem(task="Checkbox test")]
        result = format_markdown(items)
        assert "- [ ] Checkbox test" in result

    def test_multiple_items_each_on_own_line(self) -> None:
        """Multiple items produce one checkbox line each."""
        items = [
            ActionItem(task="A", owner="Alice"),
            ActionItem(task="B", owner="Bob"),
            ActionItem(task="C", owner="Charlie"),
        ]
        result = format_markdown(items)
        checkbox_lines = [l for l in result.splitlines() if l.startswith("- [ ]")]
        assert len(checkbox_lines) == 3

    def test_conftest_fixture_renders(self, sample_action_item: ActionItem) -> None:
        """The shared sample_action_item fixture from conftest renders properly."""
        result = format_markdown([sample_action_item])
        assert "@Alice" in result
        assert "(due 2026-02-14)" in result
        assert "[high]" in result


# ===================================================================
# format_json
# ===================================================================


class TestFormatJson:
    """Unit tests for the format_json function."""

    def test_empty_list_valid_json(self) -> None:
        """An empty items list produces valid JSON with count 0."""
        result = format_json([])
        data = json.loads(result)
        assert data["count"] == 0
        assert data["action_items"] == []

    def test_output_is_valid_json(self) -> None:
        """Output is always valid JSON regardless of content."""
        items = [ActionItem(task="Parse me", owner="Tester", due_date="2026-01-01")]
        data = json.loads(format_json(items))
        assert isinstance(data, dict)

    def test_keys_are_sorted(self) -> None:
        """Top-level JSON keys appear in alphabetical order (sort_keys=True)."""
        result = format_json([ActionItem(task="X")])
        # "action_items" should come before "count" alphabetically
        ai_pos = result.index('"action_items"')
        count_pos = result.index('"count"')
        assert ai_pos < count_pos

    def test_count_matches_items(self) -> None:
        """The 'count' field matches the number of action_items."""
        items = [
            ActionItem(task="One"),
            ActionItem(task="Two"),
            ActionItem(task="Three"),
        ]
        data = json.loads(format_json(items))
        assert data["count"] == 3
        assert len(data["action_items"]) == 3

    def test_item_fields_present(self) -> None:
        """Each serialized item contains all ActionItem fields."""
        items = [
            ActionItem(
                task="Full item",
                owner="Grace",
                due_date="2026-04-01",
                priority="high",
                raw_line="original line",
            )
        ]
        data = json.loads(format_json(items))
        item_dict = data["action_items"][0]
        assert item_dict["task"] == "Full item"
        assert item_dict["owner"] == "Grace"
        assert item_dict["due_date"] == "2026-04-01"
        assert item_dict["priority"] == "high"
        assert item_dict["raw_line"] == "original line"

    def test_items_are_sorted_in_output(self) -> None:
        """format_json sorts items internally before serializing."""
        items = [
            ActionItem(task="Second", owner="Zara"),
            ActionItem(task="First", owner="Alice"),
        ]
        data = json.loads(format_json(items))
        assert data["action_items"][0]["owner"] == "Alice"
        assert data["action_items"][1]["owner"] == "Zara"

    def test_trailing_newline(self) -> None:
        """JSON output ends with a trailing newline."""
        result = format_json([])
        assert result.endswith("\n")

    def test_indented_output(self) -> None:
        """JSON output uses 2-space indentation."""
        result = format_json([ActionItem(task="Indented")])
        # The "action_items" key should be indented 2 spaces inside the object
        assert '  "action_items"' in result

    def test_conftest_fixture_serializes(self, sample_action_item: ActionItem) -> None:
        """The shared sample_action_item fixture from conftest serializes properly."""
        data = json.loads(format_json([sample_action_item]))
        assert data["count"] == 1
        assert data["action_items"][0]["task"] == "Draft the Q1 budget proposal"
        assert data["action_items"][0]["priority"] == "high"
