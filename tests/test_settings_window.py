import pytest

from src.app import autostart
from src.app.settings_window import SettingsWindow
from src.core.config import Config
from src.overlay import win32
from src.overlay.controller import OverlayController
from src.overlay.overlay_window import resolution_key
from tests.qt_fakes import FakeHotkey


@pytest.fixture
def build(tmp_path, fixture_static, monkeypatch):
    monkeypatch.setattr(autostart, "is_enabled", lambda: False)

    def factory():
        config = Config(tmp_path / "settings.json")
        controller = OverlayController(config, fixture_static, hotkey=FakeHotkey())
        controller._visibility_timer.stop()
        window = SettingsWindow(config, controller)
        return config, controller, window

    return factory


def test_scale_slider_applies_live_and_persists_on_release(qapp, build):
    config, controller, window = build()
    window.scale_slider.setValue(100)
    assert window.scale_label.text() == "100%"
    assert controller.window().width() == 230
    assert config.get("overlay").get("profiles", {}) == {}
    window.scale_slider.sliderReleased.emit()
    assert config.get("overlay")["profiles"][resolution_key()]["scale"] == 1.0


def test_opacity_slider_applies_live_and_persists_on_release(qapp, build):
    config, controller, window = build()
    window.opacity_slider.setValue(50)
    assert window.opacity_label.text() == "50%"
    assert controller.window().windowOpacity() == pytest.approx(0.5, abs=0.01)
    window.opacity_slider.sliderReleased.emit()
    assert config.get("overlay")["opacity"] == 0.5


def test_locked_checkbox_applies_and_persists(qapp, build):
    config, controller, window = build()
    window.locked_check.setChecked(True)
    assert controller.window().is_locked()
    assert config.get("overlay")["locked"] is True


def test_reset_position_button(qapp, build):
    config, controller, window = build()
    window.reset_button.click()
    profile = config.get("overlay")["profiles"][resolution_key()]
    assert profile["x"] == controller.window().frameGeometry().topLeft().x()


def test_resolution_label_shows_current_key(qapp, build):
    _, _, window = build()
    assert resolution_key() in window.resolution_label.text()


def test_hotkey_edit_applies_and_persists(qapp, build):
    config, controller, window = build()
    from PySide6.QtGui import QKeySequence

    window.hotkey_edit.setKeySequence(QKeySequence("Ctrl+F9"))
    window.hotkey_edit.editingFinished.emit()
    assert config.get("hotkey_toggle_overlay") == "Ctrl+F9"
    assert not window.hotkey_warning.isVisibleTo(window)


def test_hotkey_edit_failure_shows_warning_and_reverts(qapp, build):
    config, controller, window = build()
    from PySide6.QtGui import QKeySequence

    controller._hotkey.register_result = False
    window.hotkey_edit.setKeySequence(QKeySequence("F10"))
    window.hotkey_edit.editingFinished.emit()
    assert window.hotkey_warning.isVisibleTo(window)
    assert config.get("hotkey_toggle_overlay") == "F8"
    assert window.hotkey_edit.keySequence().toString() == "F8"


def test_overlay_lock_icon_syncs_settings_checkbox(qapp, build):
    _, controller, window = build()
    controller.window()._toggle_lock()
    assert window.locked_check.isChecked()
    controller.window()._toggle_lock()
    assert not window.locked_check.isChecked()


def test_capture_failure_reverts_and_disables(qapp, build, monkeypatch):
    monkeypatch.setattr(win32, "set_capture_exclusion", lambda hwnd, value: False)
    config, _, window = build()
    window.capture_check.setChecked(True)
    assert not window.capture_check.isChecked()
    assert not window.capture_check.isEnabled()
    assert window.capture_warning.isVisibleTo(window)
    assert config.get("overlay")["hide_from_capture"] is False


def test_capture_success_persists(qapp, build, monkeypatch):
    monkeypatch.setattr(win32, "set_capture_exclusion", lambda hwnd, value: True)
    config, _, window = build()
    window.capture_check.setChecked(True)
    assert window.capture_check.isChecked()
    assert config.get("overlay")["hide_from_capture"] is True


def test_autostart_success_persists(qapp, build, monkeypatch):
    calls = []
    monkeypatch.setattr(autostart, "set_enabled", lambda value: calls.append(value) or True)
    config, _, window = build()
    window.autostart_check.setChecked(True)
    assert calls == [True]
    assert config.get("start_with_windows") is True


def test_autostart_failure_reverts(qapp, build, monkeypatch):
    monkeypatch.setattr(autostart, "set_enabled", lambda value: False)
    config, _, window = build()
    window.autostart_check.setChecked(True)
    assert not window.autostart_check.isChecked()
    assert config.get("start_with_windows") is False


def test_show_and_hide_toggle_settings_preview(qapp, build):
    _, controller, window = build()
    window.show()
    assert controller.preview_active()
    window.hide()
    assert not controller.preview_active()
