import sys
from contextlib import contextmanager

import pytest

from src.app import autostart


class FakeWinreg:
    HKEY_CURRENT_USER = "HKCU"
    KEY_READ = 1
    KEY_SET_VALUE = 2
    REG_SZ = 1

    def __init__(self):
        self.values: dict[str, str] = {}
        self.fail_open = False

    @contextmanager
    def OpenKey(self, hive, path, reserved, access):
        if self.fail_open:
            raise OSError("access denied")
        yield (hive, path)

    @contextmanager
    def CreateKeyEx(self, hive, path, reserved, access):
        if self.fail_open:
            raise OSError("access denied")
        yield (hive, path)

    def SetValueEx(self, key, name, reserved, kind, value):
        self.values[name] = value

    def QueryValueEx(self, key, name):
        if name not in self.values:
            raise FileNotFoundError(name)
        return (self.values[name], self.REG_SZ)

    def DeleteValue(self, key, name):
        if name not in self.values:
            raise FileNotFoundError(name)
        del self.values[name]


@pytest.fixture
def fake_winreg(monkeypatch):
    fake = FakeWinreg()
    monkeypatch.setattr(autostart, "winreg", fake)
    return fake


def test_enable_writes_launch_command(fake_winreg):
    assert autostart.set_enabled(True)
    assert fake_winreg.values[autostart.RUN_VALUE_NAME] == autostart.launch_command()
    assert autostart.is_enabled()


def test_disable_removes_value(fake_winreg):
    autostart.set_enabled(True)
    assert autostart.set_enabled(False)
    assert not autostart.is_enabled()


def test_disable_when_absent_is_success(fake_winreg):
    assert autostart.set_enabled(False)


def test_registry_failure_returns_false(fake_winreg):
    fake_winreg.fail_open = True
    assert autostart.set_enabled(True) is False
    assert autostart.is_enabled() is False


def test_no_winreg_module(monkeypatch):
    monkeypatch.setattr(autostart, "winreg", None)
    assert autostart.set_enabled(True) is False
    assert autostart.is_enabled() is False


def test_launch_command_dev_points_to_run_bat():
    command = autostart.launch_command()
    assert "run.bat" in command
    assert command.startswith("cmd /c ")


def test_launch_command_frozen_points_to_exe(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\apps\EzSpellTracker.exe")
    assert autostart.launch_command() == r'"C:\apps\EzSpellTracker.exe"'
