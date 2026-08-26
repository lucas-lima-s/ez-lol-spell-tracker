import pytest

from src.overlay import win32
from src.overlay.visibility import is_league_title, should_show


@pytest.mark.parametrize(
    ("in_game", "fg_league", "dragging", "preview", "expected"),
    [
        (False, False, False, True, True),
        (True, True, False, True, True),
        (True, True, False, False, True),
        (True, True, True, False, True),
        (True, False, True, False, True),
        (True, False, False, False, False),
        (False, True, False, False, False),
        (False, False, True, False, False),
        (False, False, False, False, False),
    ],
)
def test_should_show_decision_table(in_game, fg_league, dragging, preview, expected):
    assert should_show(in_game, fg_league, dragging, preview) is expected


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("League of Legends (TM) Client", True),
        ("League of Legends", True),
        ("League of Legends - Summoner", False),
        ("League of Legends Wiki - Browser", False),
        ("", False),
        ("Notepad", False),
        ("league of legends", False),
    ],
)
def test_is_league_title(title, expected):
    assert is_league_title(title) is expected


def test_win32_helpers_reject_null_hwnd():
    assert win32.set_no_activate(0) is False
    assert win32.force_topmost(0) is False
    assert win32.set_capture_exclusion(0, True) is False


def test_win32_foreground_title_returns_string():
    assert isinstance(win32.get_foreground_window_title(), str)
