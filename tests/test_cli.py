"""Tests for actionize.__main__ -- CLI end-to-end integration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from actionize.__main__ import main


# The same golden input used in test_parser.py, duplicated here so CLI tests
# are self-contained.
MEETING_NOTES = """\
Kickoff sync \u2014 Decisions: use SSO for internal users.

TODO: Update onboarding doc. Owner: Priya. Due: next Friday.

Action: Reach out to vendor about pricing tiers (owner Sam) due 2/20

We should probably fix flaky CI tests soon (P1)

John to draft API rate limit proposal by March 1

Reminder: Send customer follow-up email (no owner yet)

Decision: move launch to Q2.

ACTION ITEM \u2014 Migrate staging database; Owner: Mei; Due: 2026-02-28; Priority: P0
"""


class TestCLIEndToEnd:
    """Integration tests that invoke the CLI entry point and inspect output files."""

    @pytest.fixture()
    def input_file(self, tmp_path: Path) -> Path:
        """Write the golden meeting notes to a temp file."""
        path = tmp_path / "meeting_notes.txt"
        path.write_text(MEETING_NOTES, encoding="utf-8")
        return path

    @pytest.fixture()
    def output_dir(self, tmp_path: Path) -> Path:
        """Return a temp directory for CLI output."""
        return tmp_path / "output"

    def test_successful_run_returns_zero(
        self, input_file: Path, output_dir: Path
    ) -> None:
        """main() returns 0 on a valid input file."""
        rc = main([str(input_file), "--out", str(output_dir)])
        assert rc == 0

    def test_markdown_file_created(
        self, input_file: Path, output_dir: Path
    ) -> None:
        """The Markdown output file is created in the output directory."""
        main([str(input_file), "--out", str(output_dir)])
        md_path = output_dir / "action_items.md"
        assert md_path.exists()
        assert md_path.stat().st_size > 0

    def test_json_file_created(
        self, input_file: Path, output_dir: Path
    ) -> None:
        """The JSON output file is created in the output directory."""
        main([str(input_file), "--out", str(output_dir)])
        json_path = output_dir / "action_items.json"
        assert json_path.exists()
        assert json_path.stat().st_size > 0

    def test_json_output_is_valid(
        self, input_file: Path, output_dir: Path
    ) -> None:
        """The JSON output file contains valid JSON with the expected structure."""
        main([str(input_file), "--out", str(output_dir)])
        json_path = output_dir / "action_items.json"
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert "action_items" in data
        assert "count" in data
        assert isinstance(data["action_items"], list)
        assert data["count"] == len(data["action_items"])

    def test_json_item_count_matches(
        self, input_file: Path, output_dir: Path
    ) -> None:
        """The JSON file reports the correct number of action items."""
        main([str(input_file), "--out", str(output_dir)])
        json_path = output_dir / "action_items.json"
        data = json.loads(json_path.read_text(encoding="utf-8"))
        # The golden input produces 6 action items
        assert data["count"] == 6

    def test_markdown_contains_checkboxes(
        self, input_file: Path, output_dir: Path
    ) -> None:
        """The Markdown file contains checkbox lines."""
        main([str(input_file), "--out", str(output_dir)])
        md_path = output_dir / "action_items.md"
        content = md_path.read_text(encoding="utf-8")
        checkbox_lines = [l for l in content.splitlines() if l.startswith("- [ ]")]
        assert len(checkbox_lines) == 6

    def test_output_dir_created_if_missing(
        self, input_file: Path, tmp_path: Path
    ) -> None:
        """The output directory is created automatically if it does not exist."""
        nested_dir = tmp_path / "deep" / "nested" / "output"
        assert not nested_dir.exists()
        rc = main([str(input_file), "--out", str(nested_dir)])
        assert rc == 0
        assert nested_dir.exists()
        assert (nested_dir / "action_items.md").exists()
        assert (nested_dir / "action_items.json").exists()


class TestCLIMissingInput:
    """Tests for error handling when the input file is missing."""

    def test_missing_file_returns_one(self, tmp_path: Path) -> None:
        """main() returns 1 when the input file does not exist."""
        nonexistent = tmp_path / "does_not_exist.txt"
        rc = main([str(nonexistent), "--out", str(tmp_path / "out")])
        assert rc == 1

    def test_missing_file_no_output_created(self, tmp_path: Path) -> None:
        """No output files are created when the input file is missing."""
        nonexistent = tmp_path / "nope.txt"
        out_dir = tmp_path / "out"
        main([str(nonexistent), "--out", str(out_dir)])
        assert not out_dir.exists()


class TestCLIEmptyInput:
    """Tests for CLI behavior with an empty input file."""

    def test_empty_file_returns_zero(self, tmp_path: Path) -> None:
        """An empty input file is valid and returns 0."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding="utf-8")
        rc = main([str(empty_file), "--out", str(tmp_path / "out")])
        assert rc == 0

    def test_empty_file_produces_no_items_markdown(self, tmp_path: Path) -> None:
        """An empty input produces the 'no items' Markdown output."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding="utf-8")
        out_dir = tmp_path / "out"
        main([str(empty_file), "--out", str(out_dir)])
        md_content = (out_dir / "action_items.md").read_text(encoding="utf-8")
        assert "_No action items found._" in md_content

    def test_empty_file_produces_zero_count_json(self, tmp_path: Path) -> None:
        """An empty input produces JSON with count 0."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding="utf-8")
        out_dir = tmp_path / "out"
        main([str(empty_file), "--out", str(out_dir)])
        data = json.loads((out_dir / "action_items.json").read_text(encoding="utf-8"))
        assert data["count"] == 0
