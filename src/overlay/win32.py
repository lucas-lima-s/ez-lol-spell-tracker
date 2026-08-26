import ctypes
import sys

GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
WDA_NONE = 0x0
WDA_EXCLUDEFROMCAPTURE = 0x11


def _user32():
    if not sys.platform.startswith("win"):
        return None
    return ctypes.windll.user32


def set_no_activate(hwnd: int) -> bool:
    user32 = _user32()
    if user32 is None or not hwnd:
        return False
    try:
        style = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE)
        return True
    except Exception:
        return False


def force_topmost(hwnd: int) -> bool:
    user32 = _user32()
    if user32 is None or not hwnd:
        return False
    try:
        result = user32.SetWindowPos(
            hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
        )
        return bool(result)
    except Exception:
        return False


def set_capture_exclusion(hwnd: int, excluded: bool) -> bool:
    user32 = _user32()
    if user32 is None or not hwnd:
        return False
    affinity = WDA_EXCLUDEFROMCAPTURE if excluded else WDA_NONE
    try:
        result = user32.SetWindowDisplayAffinity(hwnd, affinity)
        return bool(result)
    except Exception:
        return False


def get_foreground_window_title() -> str:
    user32 = _user32()
    if user32 is None:
        return ""
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value
    except Exception:
        return ""
