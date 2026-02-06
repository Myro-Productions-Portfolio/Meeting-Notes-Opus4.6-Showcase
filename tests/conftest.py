"""Shared pytest fixtures for the actionize test suite."""

from __future__ import annotations

import pytest

from actionize.parser import ActionItem


@pytest.fixture()
def sample_action_item() -> ActionItem:
    """Return a fully-populated ActionItem for use in formatter tests."""
    return ActionItem(
        task="Draft the Q1 budget proposal",
        owner="Alice",
        due_date="2026-02-14",
        priority="high",
        raw_line="ACTION: Alice to draft the Q1 budget proposal by Feb 14 [high]",
    )
