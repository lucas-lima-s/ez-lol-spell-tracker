import ctypes
import ctypes.wintypes
import logging
import sys

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication, QObject, Signal

logger = logging.getLogger(__name__)

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
HOTKEY_ID = 0xE57
VK_F1 = 0x70

_MODIFIER_NAMES = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "meta": MOD_WIN,
}


def parse_hotkey(text: str) -> tuple[int, int] | None:
    parts = [part.strip() for part in (text or "").split("+") if part.strip()]
    if not parts:
        return None
    modifiers = 0
    key = None
    for part in parts:
        modifier = _MODIFIER_NAMES.get(part.lower())
        if modifier is not None:
            modifiers |= modifier
            continue
        if key is not None:
            return None
        key = part
    if key is None:
        return None
    upper = key.upper()
    if len(upper) == 1 and (upper.isalpha() or upper.isdigit()):
        return modifiers, ord(upper)
    if upper.startswith("F") and upper[1:].isdigit():
        number = int(upper[1:])
        if 1 <= number <= 24:
            return modifiers, VK_F1 + number - 1
    return None


class _HotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, callback) -> None:
        super().__init__()
        self._callback = callback

    def nativeEventFilter(self, event_type, message):
        if event_type == b"windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                self._callback()
        return False, 0


class GlobalHotkey(QObject):
    triggered = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._registered = False
        self._filter = _HotkeyFilter(self.triggered.emit)
        app = QCoreApplication.instance()
        if app is not None:
            app.installNativeEventFilter(self._filter)

    def register(self, text: str) -> bool:
        self.unregister()
        if not sys.platform.startswith("win"):
            return False
        parsed = parse_hotkey(text)
        if parsed is None:
            return False
        modifiers, vk = parsed
        try:
            result = ctypes.windll.user32.RegisterHotKey(
                None, HOTKEY_ID, modifiers | MOD_NOREPEAT, vk
            )
        except Exception:
            return False
        self._registered = bool(result)
        if not self._registered:
            logger.warning("Failed to register global hotkey %r", text)
        return self._registered

    def unregister(self) -> None:
        if not self._registered:
            return
        try:
            ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID)
        except Exception:
            pass
        self._registered = False
