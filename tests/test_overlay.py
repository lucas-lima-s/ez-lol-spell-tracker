import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent

from src.core.config import Config
from src.core.models import Enemy, SpellSlot
from src.core.timers import GameClock, SpellTimerBoard
from src.overlay.overlay_window import OverlayWindow, fmt_mmss, resolution_key


def _slot(spell_id="SummonerFlash", cooldown=300.0):
    return SpellSlot(
        spell_id=spell_id,
        display_name=spell_id,
        base_cooldown=cooldown,
        icon_file=f"{spell_id}.png" if spell_id else "",
    )


def _enemies():
    champions = ["Annie", "Ahri", "Garen", "Lux", "Teemo"]
    return [
        Enemy(
            champion_id=champion,
            champion_name=champion,
            riot_id=f"{champion}#BR1",
            team="CHAOS",
            is_bot=False,
            spells=(_slot(), _slot("SummonerDot", 180.0)),
        )
        for champion in champions
    ]


def _window(tmp_path, mono_state):
    clock = GameClock()
    clock.ingest(100.0, mono_state["now"])
    board = SpellTimerBoard(clock)
    config = Config(tmp_path / "settings.json")
    window = OverlayWindow(config, board, monotonic=lambda: mono_state["now"])
    window.set_enemies(_enemies())
    return window, board, config


def _mouse(window, etype, local, button, buttons=None):
    if buttons is None:
        buttons = button
    global_pos = QPointF(window.frameGeometry().topLeft() + local)
    return QMouseEvent(
        etype,
        QPointF(local),
        global_pos,
        button,
        buttons,
        Qt.KeyboardModifier.NoModifier,
    )


def test_window_flags_and_attributes(qapp, tmp_path):
    window, _, _ = _window(tmp_path, {"now": 50.0})
    flags = window.windowFlags()
    assert flags & Qt.WindowType.FramelessWindowHint
    assert flags & Qt.WindowType.WindowStaysOnTopHint
    assert flags & Qt.WindowType.Tool
    assert flags & Qt.WindowType.WindowDoesNotAcceptFocus
    assert window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    assert window.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)


def test_window_size_matches_metrics(qapp, tmp_path):
    window, _, _ = _window(tmp_path, {"now": 50.0})
    assert window.width() == window._content_size().width()
    window.set_scale(1.0)
    assert window.size().width() == 230
    assert window.size().height() == 352


def test_left_click_starts_timer(qapp, tmp_path):
    state = {"now": 50.0}
    window, board, _ = _window(tmp_path, state)
    center = window.cell_rect(2, 1).center()
    window.mousePressEvent(
        _mouse(window, QEvent.Type.MouseButtonPress, center, Qt.MouseButton.LeftButton)
    )
    assert board.remaining(2, 0, state["now"]) == 300.0
    state["now"] = 60.0
    assert board.remaining(2, 0, state["now"]) == 290.0


def test_right_click_resets_timer(qapp, tmp_path):
    state = {"now": 50.0}
    window, board, _ = _window(tmp_path, state)
    center = window.cell_rect(1, 2).center()
    window.mousePressEvent(
        _mouse(window, QEvent.Type.MouseButtonPress, center, Qt.MouseButton.LeftButton)
    )
    assert board.remaining(1, 1, state["now"]) > 0
    window.mousePressEvent(
        _mouse(window, QEvent.Type.MouseButtonPress, center, Qt.MouseButton.RightButton)
    )
    assert board.remaining(1, 1, state["now"]) == 0.0


def test_unknown_spell_click_is_ignored(qapp, tmp_path):
    state = {"now": 50.0}
    window, board, _ = _window(tmp_path, state)
    enemies = _enemies()
    enemies[0] = Enemy(
        champion_id="",
        champion_name="Novo",
        riot_id="x#BR1",
        team="CHAOS",
        is_bot=False,
        spells=(_slot("", 0.0), _slot()),
    )
    window.set_enemies(enemies)
    center = window.cell_rect(0, 1).center()
    window.mousePressEvent(
        _mouse(window, QEvent.Type.MouseButtonPress, center, Qt.MouseButton.LeftButton)
    )
    assert board.remaining(0, 0, state["now"]) == 0.0


def test_champion_cell_click_starts_drag_not_timer(qapp, tmp_path):
    state = {"now": 50.0}
    window, board, _ = _window(tmp_path, state)
    center = window.cell_rect(0, 0).center()
    window.mousePressEvent(
        _mouse(window, QEvent.Type.MouseButtonPress, center, Qt.MouseButton.LeftButton)
    )
    assert window.is_dragging()
    assert all(
        board.remaining(row, slot, state["now"]) == 0.0
        for row in range(5)
        for slot in (0, 1)
    )


def test_drag_moves_window_and_persists(qapp, tmp_path):
    state = {"now": 50.0}
    window, _, config = _window(tmp_path, state)
    start_pos = window.frameGeometry().topLeft()
    press_local = QPoint(5, 5)
    window.mousePressEvent(
        _mouse(window, QEvent.Type.MouseButtonPress, press_local, Qt.MouseButton.LeftButton)
    )
    assert window.is_dragging()
    move_event = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(press_local),
        QPointF(start_pos + QPoint(120, 80) + press_local),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.mouseMoveEvent(move_event)
    window.mouseReleaseEvent(
        _mouse(window, QEvent.Type.MouseButtonRelease, press_local, Qt.MouseButton.LeftButton)
    )
    assert not window.is_dragging()
    moved = window.frameGeometry().topLeft()
    assert moved == start_pos + QPoint(120, 80)
    profile = config.get("overlay")["profiles"][resolution_key()]
    assert profile["x"] == moved.x()
    assert profile["y"] == moved.y()


def test_locked_window_does_not_drag(qapp, tmp_path):
    state = {"now": 50.0}
    window, _, _ = _window(tmp_path, state)
    window.set_locked(True)
    window.mousePressEvent(
        _mouse(window, QEvent.Type.MouseButtonPress, QPoint(5, 5), Qt.MouseButton.LeftButton)
    )
    assert not window.is_dragging()


def test_reset_position_persists(qapp, tmp_path):
    state = {"now": 50.0}
    window, _, config = _window(tmp_path, state)
    window.move(window.frameGeometry().topLeft() + QPoint(200, 200))
    window.reset_position()
    profile = config.get("overlay")["profiles"][resolution_key()]
    assert profile["x"] == window.frameGeometry().topLeft().x()


def test_lock_icon_click_toggles_and_persists(qapp, tmp_path):
    state = {"now": 50.0}
    window, board, config = _window(tmp_path, state)
    events = []
    window.locked_changed.connect(events.append)
    center = window.lock_rect().center()
    window.mousePressEvent(
        _mouse(window, QEvent.Type.MouseButtonPress, center, Qt.MouseButton.LeftButton)
    )
    assert window.is_locked()
    assert not window.is_dragging()
    assert config.get("overlay")["locked"] is True
    assert events == [True]
    window.mousePressEvent(
        _mouse(window, QEvent.Type.MouseButtonPress, center, Qt.MouseButton.LeftButton)
    )
    assert not window.is_locked()
    assert config.get("overlay")["locked"] is False
    assert events == [True, False]


def test_lock_icon_works_while_locked(qapp, tmp_path):
    state = {"now": 50.0}
    window, _, _ = _window(tmp_path, state)
    window.set_locked(True)
    center = window.lock_rect().center()
    window.mousePressEvent(
        _mouse(window, QEvent.Type.MouseButtonPress, center, Qt.MouseButton.LeftButton)
    )
    assert not window.is_locked()


def test_hide_mid_drag_clears_drag_state(qapp, tmp_path):
    state = {"now": 50.0}
    window, _, _ = _window(tmp_path, state)
    window.show()
    window.mousePressEvent(
        _mouse(window, QEvent.Type.MouseButtonPress, QPoint(5, 5), Qt.MouseButton.LeftButton)
    )
    assert window.is_dragging()
    window.hide()
    assert not window.is_dragging()


def test_profile_per_resolution_isolated(qapp, tmp_path, monkeypatch):
    state = {"now": 50.0}
    window, _, config = _window(tmp_path, state)
    window.move(QPoint(111, 222))
    window._persist_position()
    window.persist_scale(1.2)
    import src.overlay.overlay_window as ow

    monkeypatch.setattr(ow, "resolution_key", lambda: "1920x1080")
    window.persist_scale(0.6)
    profiles = config.get("overlay")["profiles"]
    assert len(profiles) == 2
    other = [k for k in profiles if k != "1920x1080"][0]
    assert profiles[other]["scale"] == 1.2
    assert profiles["1920x1080"]["scale"] == 0.6
    assert profiles[other]["x"] == 111


def test_right_click_portrait_toggles_insight_and_reduces_cooldown(qapp, tmp_path):
    state = {"now": 50.0}
    window, board, _ = _window(tmp_path, state)
    portrait = window.cell_rect(0, 0).center()
    window.mousePressEvent(
        _mouse(window, QEvent.Type.MouseButtonPress, portrait, Qt.MouseButton.RightButton)
    )
    assert window._haste.has_insight(0)
    spell = window.cell_rect(0, 1).center()
    window.mousePressEvent(
        _mouse(window, QEvent.Type.MouseButtonPress, spell, Qt.MouseButton.LeftButton)
    )
    expected = 300.0 / 1.18
    assert board.remaining(0, 0, state["now"]) == pytest.approx(expected, rel=1e-3)


def test_wheel_adjusts_running_timer(qapp, tmp_path):
    state = {"now": 50.0}
    window, board, _ = _window(tmp_path, state)
    spell = window.cell_rect(0, 1).center()
    window.mousePressEvent(
        _mouse(window, QEvent.Type.MouseButtonPress, spell, Qt.MouseButton.LeftButton)
    )
    assert board.remaining(0, 0, state["now"]) == 300.0
    event = QWheelEvent(
        QPointF(spell),
        QPointF(spell),
        QPoint(0, 0),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    window.wheelEvent(event)
    assert board.remaining(0, 0, state["now"]) == 295.0


def test_click_cast_offset_applied(qapp, tmp_path):
    state = {"now": 50.0}
    window, board, config = _window(tmp_path, state)
    config.set("click_cast_offset", 10)
    spell = window.cell_rect(1, 1).center()
    window.mousePressEvent(
        _mouse(window, QEvent.Type.MouseButtonPress, spell, Qt.MouseButton.LeftButton)
    )
    assert board.remaining(1, 0, state["now"]) == 290.0


def test_smite_click_uses_recharge(qapp, tmp_path):
    state = {"now": 50.0}
    window, board, _ = _window(tmp_path, state)
    enemies = _enemies()
    enemies[0] = Enemy(
        champion_id="Annie",
        champion_name="Annie",
        riot_id="x#BR1",
        team="CHAOS",
        is_bot=False,
        spells=(_slot("SummonerSmite", 15.0), _slot()),
        level=10,
    )
    window.set_enemies(enemies)
    spell = window.cell_rect(0, 1).center()
    window.mousePressEvent(
        _mouse(window, QEvent.Type.MouseButtonPress, spell, Qt.MouseButton.LeftButton)
    )
    assert board.remaining(0, 0, state["now"]) == 90.0


def test_wheel_does_not_resurrect_expired_timer(qapp, tmp_path):
    state = {"now": 50.0}
    window, board, _ = _window(tmp_path, state)
    board.start(0, 0, 5.0, state["now"])
    state["now"] = 60.0
    assert board.remaining(0, 0, state["now"]) == 0.0
    spell = window.cell_rect(0, 1).center()
    event = QWheelEvent(
        QPointF(spell),
        QPointF(spell),
        QPoint(0, 0),
        QPoint(0, -240),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    window.wheelEvent(event)
    assert board.remaining(0, 0, state["now"]) == 0.0


def test_fmt_mmss():
    assert fmt_mmss(0.0) == "0:00"
    assert fmt_mmss(0.2) == "0:01"
    assert fmt_mmss(61.0) == "1:01"
    assert fmt_mmss(299.1) == "5:00"
    assert fmt_mmss(300.0) == "5:00"
    assert fmt_mmss(-5.0) == "0:00"
