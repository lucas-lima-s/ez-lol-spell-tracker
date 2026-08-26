from PySide6.QtCore import Qt

from src.core.config import Config
from src.overlay import overlay_window, win32
from src.overlay.controller import OverlayController
from src.riot.parser import extract_enemies
from tests.conftest import load_fixture
from tests.qt_fakes import FakeHotkey


def _controller(tmp_path, fixture_static, mono_state):
    config = Config(tmp_path / "settings.json")
    hotkey = FakeHotkey()
    controller = OverlayController(
        config,
        fixture_static,
        monotonic=lambda: mono_state["now"],
        hotkey=hotkey,
    )
    controller._visibility_timer.stop()
    return controller, config


def _real_enemies(fixture_static):
    return extract_enemies(load_fixture("allgamedata_ptbr.json"), fixture_static)


def test_preview_toggle_populates_placeholders(qapp, tmp_path, fixture_static):
    state = {"now": 50.0}
    controller, _ = _controller(tmp_path, fixture_static, state)
    events = []
    controller.preview_changed.connect(events.append)
    controller.toggle_preview()
    assert events == [True]
    enemies = controller.window().enemies()
    assert len(enemies) == 5
    assert all(slot.base_cooldown > 0 for e in enemies for slot in e.spells)
    assert controller.window().isVisible()
    controller.toggle_preview()
    assert events == [True, False]
    assert not controller.window().isVisible()


def test_preview_timers_work_via_synthetic_clock(qapp, tmp_path, fixture_static):
    state = {"now": 50.0}
    controller, _ = _controller(tmp_path, fixture_static, state)
    controller.toggle_preview()
    controller._visibility_tick()
    window = controller.window()
    window._handle_spell_click(0, 0, Qt.MouseButton.LeftButton)
    assert controller._board.remaining(0, 0, state["now"]) == 300.0


def test_game_started_replaces_preview_and_shows(
    qapp, tmp_path, fixture_static, monkeypatch
):
    state = {"now": 50.0}
    controller, _ = _controller(tmp_path, fixture_static, state)
    monkeypatch.setattr(
        win32, "get_foreground_window_title", lambda: "League of Legends (TM) Client"
    )
    events = []
    controller.preview_changed.connect(events.append)
    controller.toggle_preview()
    controller.on_game_started(_real_enemies(fixture_static))
    assert events == [True, False]
    assert controller.window().isVisible()
    assert controller.window().enemies()[0].champion_id == "Fiddlesticks"


def test_game_started_while_alt_tabbed_does_not_flash(
    qapp, tmp_path, fixture_static, monkeypatch
):
    state = {"now": 50.0}
    controller, _ = _controller(tmp_path, fixture_static, state)
    monkeypatch.setattr(win32, "get_foreground_window_title", lambda: "Notepad")
    controller.on_game_started(_real_enemies(fixture_static))
    assert not controller.window().isVisible()


def test_game_ended_hides_and_clears(qapp, tmp_path, fixture_static):
    state = {"now": 50.0}
    controller, _ = _controller(tmp_path, fixture_static, state)
    controller.on_game_started(_real_enemies(fixture_static))
    controller.on_game_time(100.0)
    controller._board.start(0, 0, 300.0, state["now"])
    controller.on_game_ended()
    assert not controller.window().isVisible()
    assert controller.window().enemies() == []
    assert controller._board.remaining(0, 0, state["now"]) == 0.0


def test_game_time_feeds_clock(qapp, tmp_path, fixture_static):
    state = {"now": 50.0}
    controller, _ = _controller(tmp_path, fixture_static, state)
    controller.on_game_time(120.0)
    state["now"] = 53.0
    assert controller._clock.now(state["now"]) == 123.0


def test_visibility_tick_hides_when_alt_tabbed(qapp, tmp_path, fixture_static, monkeypatch):
    state = {"now": 50.0}
    controller, _ = _controller(tmp_path, fixture_static, state)
    controller.on_game_started(_real_enemies(fixture_static))
    monkeypatch.setattr(win32, "get_foreground_window_title", lambda: "Notepad")
    controller._visibility_tick()
    assert not controller.window().isVisible()
    monkeypatch.setattr(
        win32,
        "get_foreground_window_title",
        lambda: "League of Legends (TM) Client",
    )
    controller._visibility_tick()
    assert controller.window().isVisible()


def test_preview_ignores_foreground(qapp, tmp_path, fixture_static, monkeypatch):
    state = {"now": 50.0}
    controller, _ = _controller(tmp_path, fixture_static, state)
    controller.toggle_preview()
    monkeypatch.setattr(win32, "get_foreground_window_title", lambda: "Notepad")
    controller._visibility_tick()
    assert controller.window().isVisible()


def test_settings_open_enables_preview_and_close_keeps_user_preview(
    qapp, tmp_path, fixture_static
):
    state = {"now": 50.0}
    controller, _ = _controller(tmp_path, fixture_static, state)
    controller.set_settings_open(True)
    assert controller.preview_active()
    assert controller.window().isVisible()
    controller.set_settings_open(False)
    assert not controller.preview_active()
    assert not controller.window().isVisible()
    controller.toggle_preview()
    controller.set_settings_open(True)
    controller.set_settings_open(False)
    assert controller.preview_active()
    assert controller.window().isVisible()


def test_setters_persist_to_config(qapp, tmp_path, fixture_static):
    state = {"now": 50.0}
    controller, config = _controller(tmp_path, fixture_static, state)
    controller.set_scale(1.0)
    controller.set_opacity(0.5)
    controller.set_locked(True)
    overlay = config.get("overlay")
    assert overlay["profiles"][overlay_window.resolution_key()]["scale"] == 1.0
    assert overlay["opacity"] == 0.5
    assert overlay["locked"] is True
    assert controller.window().is_locked()


def test_hide_from_capture_failure_persists_false(
    qapp, tmp_path, fixture_static, monkeypatch
):
    state = {"now": 50.0}
    controller, config = _controller(tmp_path, fixture_static, state)
    monkeypatch.setattr(win32, "set_capture_exclusion", lambda hwnd, value: False)
    assert controller.set_hide_from_capture(True) is False
    assert config.get("overlay")["hide_from_capture"] is False
    monkeypatch.setattr(win32, "set_capture_exclusion", lambda hwnd, value: True)
    assert controller.set_hide_from_capture(True) is True
    assert config.get("overlay")["hide_from_capture"] is True


def test_roster_update_skipped_when_order_changes(qapp, tmp_path, fixture_static):
    state = {"now": 50.0}
    controller, _ = _controller(tmp_path, fixture_static, state)
    enemies = _real_enemies(fixture_static)
    controller.on_game_started(enemies)
    reordered = [enemies[1], enemies[0], *enemies[2:]]
    controller.on_roster_updated(reordered)
    assert controller.window().enemies()[0].champion_id == "Fiddlesticks"


def test_preview_insight_cleared_when_preview_closes(qapp, tmp_path, fixture_static):
    state = {"now": 50.0}
    controller, _ = _controller(tmp_path, fixture_static, state)
    controller.toggle_preview()
    controller._haste.toggle_insight(0)
    controller.toggle_preview()
    assert controller._haste.haste(0) == 0.0


def test_roster_update_sets_boots_haste(qapp, tmp_path, fixture_static):
    from src.core.cooldowns import IONIAN_BOOTS_HASTE

    state = {"now": 50.0}
    controller, _ = _controller(tmp_path, fixture_static, state)
    enemies = _real_enemies(fixture_static)
    controller.on_game_started(enemies)
    assert controller._haste.has_boots(0)
    assert controller._haste.haste(0) == IONIAN_BOOTS_HASTE
    assert not controller._haste.has_boots(1)
    controller.on_roster_updated(enemies)
    assert controller._haste.has_boots(0)
    controller.on_game_ended()
    assert controller._haste.haste(0) == 0.0


def test_shutdown_stops_timer_and_hides(qapp, tmp_path, fixture_static):
    state = {"now": 50.0}
    controller, _ = _controller(tmp_path, fixture_static, state)
    controller.toggle_preview()
    controller.shutdown()
    assert not controller.window().isVisible()
    assert not controller._visibility_timer.isActive()
    assert controller._hotkey.unregistered >= 1


def test_hotkey_registered_from_config_on_init(qapp, tmp_path, fixture_static):
    state = {"now": 50.0}
    controller, _ = _controller(tmp_path, fixture_static, state)
    assert controller._hotkey.registered == ["F8"]


def test_user_hidden_toggle_hides_even_in_game(
    qapp, tmp_path, fixture_static, monkeypatch
):
    state = {"now": 50.0}
    controller, _ = _controller(tmp_path, fixture_static, state)
    monkeypatch.setattr(
        win32, "get_foreground_window_title", lambda: "League of Legends (TM) Client"
    )
    controller.on_game_started(_real_enemies(fixture_static))
    assert controller.window().isVisible()
    controller._hotkey.triggered.emit()
    assert not controller.window().isVisible()
    controller._hotkey.triggered.emit()
    assert controller.window().isVisible()


def test_game_start_resets_user_hidden(qapp, tmp_path, fixture_static, monkeypatch):
    state = {"now": 50.0}
    controller, _ = _controller(tmp_path, fixture_static, state)
    monkeypatch.setattr(
        win32, "get_foreground_window_title", lambda: "League of Legends (TM) Client"
    )
    controller.toggle_user_hidden()
    controller.on_game_started(_real_enemies(fixture_static))
    assert controller.window().isVisible()


def test_set_hotkey_persists_and_reverts_on_failure(qapp, tmp_path, fixture_static):
    state = {"now": 50.0}
    controller, config = _controller(tmp_path, fixture_static, state)
    assert controller.set_hotkey("Ctrl+F9")
    assert config.get("hotkey_toggle_overlay") == "Ctrl+F9"
    controller._hotkey.register_result = False
    assert not controller.set_hotkey("F10")
    assert config.get("hotkey_toggle_overlay") == "Ctrl+F9"
    assert controller._hotkey.registered[-1] == "Ctrl+F9"


def test_set_hotkey_empty_unregisters(qapp, tmp_path, fixture_static):
    state = {"now": 50.0}
    controller, config = _controller(tmp_path, fixture_static, state)
    assert controller.set_hotkey("")
    assert config.get("hotkey_toggle_overlay") == ""
    assert controller._hotkey.unregistered >= 1


def test_resolution_change_reloads_profile(
    qapp, tmp_path, fixture_static, monkeypatch
):
    state = {"now": 50.0}
    controller, config = _controller(tmp_path, fixture_static, state)
    controller.window().persist_scale(1.3)
    monkeypatch.setattr(overlay_window, "resolution_key", lambda: "1920x1080")
    controller.window().persist_scale(0.5)
    controller.window().set_scale(1.3)
    controller._visibility_tick()
    assert controller.window().current_scale() == 0.5
