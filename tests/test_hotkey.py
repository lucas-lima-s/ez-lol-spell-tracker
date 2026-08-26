import pytest

from src.overlay.hotkey import (
    MOD_ALT,
    MOD_CONTROL,
    MOD_SHIFT,
    MOD_WIN,
    VK_F1,
    parse_hotkey,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("F8", (0, VK_F1 + 7)),
        ("f1", (0, VK_F1)),
        ("F24", (0, VK_F1 + 23)),
        ("Ctrl+Shift+F8", (MOD_CONTROL | MOD_SHIFT, VK_F1 + 7)),
        ("Alt+A", (MOD_ALT, ord("A"))),
        ("ctrl+1", (MOD_CONTROL, ord("1"))),
        ("Win+F2", (MOD_WIN, VK_F1 + 1)),
        ("Meta+Z", (MOD_WIN, ord("Z"))),
    ],
)
def test_parse_hotkey_valid(text, expected):
    assert parse_hotkey(text) == expected


@pytest.mark.parametrize(
    "text",
    ["", "   ", "Ctrl+", "Ctrl+A+B", "Esc", "F25", "F0", "++", None],
)
def test_parse_hotkey_invalid(text):
    assert parse_hotkey(text) is None
