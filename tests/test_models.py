import dataclasses

import pytest

from src.core.models import Enemy, SpellSlot


def _slot(spell_id="SummonerFlash"):
    return SpellSlot(
        spell_id=spell_id,
        display_name="Flash",
        base_cooldown=300.0,
        icon_file=f"{spell_id}.png",
    )


def _enemy():
    return Enemy(
        champion_id="Annie",
        champion_name="Annie",
        riot_id="player#BR1",
        team="CHAOS",
        is_bot=False,
        spells=(_slot(), _slot("SummonerDot")),
    )


def test_spell_slot_is_immutable():
    with pytest.raises(dataclasses.FrozenInstanceError):
        _slot().spell_id = "Other"


def test_enemy_is_immutable():
    with pytest.raises(dataclasses.FrozenInstanceError):
        _enemy().team = "ORDER"


def test_enemy_holds_two_spells():
    enemy = _enemy()
    assert len(enemy.spells) == 2
    assert enemy.spells[0].spell_id == "SummonerFlash"
    assert enemy.spells[1].spell_id == "SummonerDot"
