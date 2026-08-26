from PySide6.QtWidgets import QSystemTrayIcon

from src.app.settings_window import SettingsWindow
from src.app.strings import tr
from src.app.tray import TrayIcon
from src.core.config import Config
from src.overlay.controller import OverlayController
from tests.qt_fakes import FakeHotkey


def _build(tmp_path, fixture_static):
    config = Config(tmp_path / "settings.json")
    controller = OverlayController(config, fixture_static, hotkey=FakeHotkey())
    controller._visibility_timer.stop()
    return config, controller


def test_settings_window_title(qapp, tmp_path, fixture_static):
    config, controller = _build(tmp_path, fixture_static)
    window = SettingsWindow(config, controller)
    assert window.windowTitle() == tr("settings.title")


def test_tray_menu_actions(qapp, tmp_path, fixture_static):
    config, controller = _build(tmp_path, fixture_static)
    tray = TrayIcon(config, controller)
    actions = tray.contextMenu().actions()
    texts = [a.text() for a in actions if not a.isSeparator()]
    assert texts == [tr("menu.settings"), tr("menu.show_overlay"), tr("menu.exit")]
    overlay_action = actions[1]
    assert overlay_action.isEnabled()
    assert overlay_action.isCheckable()


def test_tray_icon_not_null(qapp, tmp_path, fixture_static):
    config, controller = _build(tmp_path, fixture_static)
    tray = TrayIcon(config, controller)
    assert not tray.icon().isNull()


def test_tray_overlay_action_toggles_preview(qapp, tmp_path, fixture_static):
    config, controller = _build(tmp_path, fixture_static)
    tray = TrayIcon(config, controller)
    action = tray.contextMenu().actions()[1]
    action.trigger()
    assert controller.preview_active()
    assert action.isChecked()
    action.trigger()
    assert not controller.preview_active()
    assert not action.isChecked()


def test_double_click_opens_and_reuses_settings_window(qapp, tmp_path, fixture_static):
    config, controller = _build(tmp_path, fixture_static)
    tray = TrayIcon(config, controller)
    tray._on_activated(QSystemTrayIcon.ActivationReason.DoubleClick)
    first = tray._settings_window
    assert first is not None
    assert first.isVisible()
    tray._on_activated(QSystemTrayIcon.ActivationReason.DoubleClick)
    assert tray._settings_window is first
    first.hide()
