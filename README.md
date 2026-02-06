# Actionize

Parse messy meeting notes and extract structured action items as Markdown checklists and JSON.

---

## Features

- Detects action items from `TODO:`, `Action:`, `ACTION ITEM`, `Reminder:`, and natural "Name to verb..." patterns
- Extracts owner, due date, and priority from inline metadata
- Normalizes dates to ISO-8601 -- handles `next Friday`, `2/20`, `March 1`, `2026-02-28`, and more
- Assigns priority levels from `P0` (critical), `P1` (high), and `P2` (normal) tags
- Sorts output by owner then due date, with unassigned items last
- Outputs both a Markdown checklist and a structured JSON file
- Zero external dependencies -- Python standard library only

---

## Quick Start

```powershell
cd D:\Projects\01-New\Claude-Test-Space\actionize-project
pip install -e ".[test]"
python -m actionize examples\meeting_notes.txt --out out\
```

The `--out` flag sets the output directory (defaults to `.\out`).

---

## Example: Before and After

This is what Actionize does in a single command. Eight messy lines go in, six clean action items come out -- decisions filtered, owners extracted, dates normalized, priorities mapped.

### Raw input -- `examples\meeting_notes.txt`

```
Kickoff sync -- Decisions: use SSO for internal users.        <-- filtered out (decision, not action)

TODO: Update onboarding doc. Owner: Priya. Due: next Friday.  <-- three different metadata formats in one line

Action: Reach out to vendor about pricing tiers (owner Sam) due 2/20

We should probably fix flaky CI tests soon (P1)               <-- no keyword prefix, detected by priority tag

John to draft API rate limit proposal by March 1              <-- natural language "Name to verb" pattern

Reminder: Send customer follow-up email (no owner yet)        <-- explicit unassigned marker

Decision: move launch to Q2.                                  <-- filtered out (decision, not action)

ACTION ITEM -- Migrate staging database; Owner: Mei; Due: 2026-02-28; Priority: P0
```

### Markdown output -- `out\action_items.md`

```markdown
# Action Items

- [ ] draft API rate limit proposal @John (due 2026-03-01)
- [ ] Migrate staging database @Mei (due 2026-02-28) [critical]
- [ ] Update onboarding doc @Priya (due 2026-02-13)
- [ ] Reach out to vendor about pricing tiers @Sam (due 2026-02-20)
- [ ] We should probably fix flaky CI tests soon [high]
- [ ] Send customer follow-up email
```

What happened:

| Input | Output | What the parser did |
|-------|--------|---------------------|
| `Owner: Priya` | `@Priya` | Extracted from `Owner: Name` format |
| `(owner Sam)` | `@Sam` | Extracted from parenthetical format |
| `John to draft...` | `@John` | Recognized natural language pattern |
| `next Friday` | `2026-02-13` | Computed relative date from today |
| `2/20` | `2026-02-20` | Normalized US slash date with inferred year |
| `March 1` | `2026-03-01` | Normalized month-name date |
| `(P1)` | `[high]` | Mapped priority tag |
| `Priority: P0` | `[critical]` | Mapped priority annotation |
| 2 decision lines | *(dropped)* | Filtered out non-action items |

### JSON output -- `out\action_items.json`

Machine-readable structured data, sorted by owner then due date, ready to feed into other tools:

```json
{
  "action_items": [
    {
      "due_date": "2026-03-01",
      "owner": "John",
      "priority": "normal",
      "raw_line": "John to draft API rate limit proposal by March 1",
      "task": "draft API rate limit proposal"
    },
    {
      "due_date": "2026-02-28",
      "owner": "Mei",
      "priority": "critical",
      "raw_line": "ACTION ITEM -- Migrate staging database; Owner: Mei; Due: 2026-02-28; Priority: P0",
      "task": "Migrate staging database"
    },
    {
      "due_date": "2026-02-13",
      "owner": "Priya",
      "priority": "normal",
      "raw_line": "TODO: Update onboarding doc. Owner: Priya. Due: next Friday.",
      "task": "Update onboarding doc"
    },
    {
      "due_date": "2026-02-20",
      "owner": "Sam",
      "priority": "normal",
      "raw_line": "Action: Reach out to vendor about pricing tiers (owner Sam) due 2/20",
      "task": "Reach out to vendor about pricing tiers"
    },
    {
      "due_date": "",
      "owner": "unassigned",
      "priority": "high",
      "raw_line": "We should probably fix flaky CI tests soon (P1)",
      "task": "We should probably fix flaky CI tests soon"
    },
    {
      "due_date": "",
      "owner": "unassigned",
      "priority": "normal",
      "raw_line": "Reminder: Send customer follow-up email (no owner yet)",
      "task": "Send customer follow-up email"
    }
  ],
  "count": 6
}
```

---

## How It Works

Actionize reads each line of the input file and tests it against a series of regex-based heuristics:

1. **Prefix patterns** -- Lines starting with `TODO:`, `Action:`, `ACTION ITEM`, or `Reminder:` are treated as action items immediately.
2. **Natural language** -- Lines matching `Name to verb...` (e.g., "John to draft...") are recognized with a curated verb list (draft, send, fix, migrate, deploy, etc.).
3. **Priority tags** -- Any remaining line containing `(P0)`, `(P1)`, or `(P2)` is assumed to be an action item with implied urgency.
4. **Decision filtering** -- Lines containing `Decision:` or `Decisions:` are explicitly skipped to avoid false positives.

After a line is identified as an action item, metadata is extracted:

- **Owner** -- from `Owner: Name`, `(owner Name)`, or the leading name in "Name to verb..." patterns.
- **Due date** -- from `Due: ...` or `by ...` fragments. Dates are normalized through a multi-format parser that handles ISO-8601, US slash dates, month-name dates, relative days (`next Friday`, `tomorrow`), and more.
- **Priority** -- from `P0`/`P1`/`P2` tags or `Priority: P0` annotations. Mapped to `critical`, `high`, and `normal` respectively.

The cleaned task text has all metadata fragments stripped out so the final output is readable.

---

## Output Formats

### Markdown (`action_items.md`)

Each item is rendered as a GitHub-compatible checklist entry:

```
- [ ] task description @Owner (due YYYY-MM-DD) [priority]
```

- The `@Owner` tag is omitted for unassigned items.
- The `(due ...)` tag is omitted when no date is found.
- The `[priority]` tag is omitted when priority is `normal`.

### JSON (`action_items.json`)

A single object with two keys:

| Key            | Type   | Description                          |
|----------------|--------|--------------------------------------|
| `action_items` | array  | Sorted list of action item objects   |
| `count`        | int    | Total number of items extracted      |

Each action item object contains: `task`, `owner`, `due_date`, `priority`, and `raw_line`.

---

## Running Tests

```powershell
cd D:\Projects\01-New\Claude-Test-Space\actionize-project
pytest
```

Tests cover the parser, formatter, and CLI entry point. The test dependency (`pytest>=7.0`) is installed automatically with the `.[test]` extra.

---

## Project Structure

```
actionize-project\
    pyproject.toml          Project metadata and build config
    README.md               This file
    actionize\
        __init__.py         Package exports (ActionItem, parse_meeting_notes)
        __main__.py         CLI entry point (python -m actionize)
        parser.py           Pattern matching, date normalization, extraction
        formatter.py        Markdown and JSON output renderers
    tests\
        __init__.py
        conftest.py         Shared pytest fixtures
        test_parser.py      Tests for parsing and date normalization
        test_formatter.py   Tests for Markdown and JSON formatting
        test_cli.py         End-to-end CLI tests
    examples\
        meeting_notes.txt   Sample input file
```

---

## Requirements

- Python 3.11 or later
- No external runtime dependencies
- `pytest >= 7.0` for running tests (install with `pip install -e ".[test]"`)

---

## License

MIT
