import logging
import sys

from src.core.paths import PROJECT_ROOT

try:
    import winreg
except ImportError:
    winreg = None

logger = logging.getLogger(__name__)

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "EzSpellTracker"


def launch_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    return f'cmd /c "{PROJECT_ROOT / "run.bat"}"'


def is_enabled() -> bool:
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, RUN_VALUE_NAME)
        return True
    except FileNotFoundError:
        return False
    except OSError as exc:
        logger.warning("Could not read autostart registry value: %s", exc)
        return False


def set_enabled(enabled: bool) -> bool:
    if winreg is None:
        return False
    if enabled:
        try:
            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE
            ) as key:
                winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ, launch_command())
            return True
        except OSError as exc:
            logger.warning("Could not enable autostart: %s", exc)
            return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, RUN_VALUE_NAME)
        return True
    except FileNotFoundError:
        return True
    except OSError as exc:
        logger.warning("Could not disable autostart: %s", exc)
        return False
