import pytest

from src.core.cooldowns import (
    COSMIC_INSIGHT_HASTE,
    IONIAN_BOOTS_HASTE,
    SMITE_RECHARGE,
    HasteTracker,
    base_cooldown_for,
    effective_cooldown,
    unleashed_teleport_cooldown,
)


def test_no_haste_keeps_base():
    assert effective_cooldown(300.0) == 300.0


def test_haste_reduces_cooldown():
    assert effective_cooldown(300.0, 10.0) == pytest.approx(272.727, rel=1e-3)


def test_cosmic_insight_haste():
    assert effective_cooldown(300.0, 18.0) == pytest.approx(254.237, rel=1e-3)


def test_zero_base_stays_zero():
    assert effective_cooldown(0.0, 50.0) == 0.0


def test_smite_uses_recharge_time():
    assert base_cooldown_for("SummonerSmite", 15.0, 10, 1200.0) == SMITE_RECHARGE


def test_teleport_before_upgrade_uses_base():
    assert base_cooldown_for("SummonerTeleport", 300.0, 8, 599.0) == 300.0


def test_teleport_after_upgrade_scales_with_level():
    assert base_cooldown_for("SummonerTeleport", 300.0, 1, 600.0) == 330.0
    assert base_cooldown_for("SummonerTeleport", 300.0, 18, 600.0) == 240.0
    mid = base_cooldown_for("SummonerTeleport", 300.0, 9, 600.0)
    assert 240.0 < mid < 330.0


def test_unleashed_teleport_unknown_level_falls_back():
    assert unleashed_teleport_cooldown(0) == unleashed_teleport_cooldown(9)


def test_haste_tracker_accumulates():
    tracker = HasteTracker()
    assert tracker.haste(0) == 0.0
    tracker.set_boots(0, True)
    assert tracker.haste(0) == IONIAN_BOOTS_HASTE
    assert tracker.toggle_insight(0) is True
    assert tracker.haste(0) == IONIAN_BOOTS_HASTE + COSMIC_INSIGHT_HASTE
    assert tracker.toggle_insight(0) is False
    tracker.set_boots(0, False)
    assert tracker.haste(0) == 0.0


def test_haste_tracker_clear():
    tracker = HasteTracker()
    tracker.set_boots(1, True)
    tracker.toggle_insight(2)
    tracker.clear()
    assert tracker.haste(1) == 0.0
    assert tracker.haste(2) == 0.0
