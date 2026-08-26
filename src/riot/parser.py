import logging
from collections.abc import Sequence

from src.core.models import Enemy, SpellSlot
from src.riot.static_data import StaticData

logger = logging.getLogger(__name__)

SPELL_PREFIX = "GeneratedTip_SummonerSpell_"
SPELL_SUFFIX = "_DisplayName"
CHAMPION_PREFIX = "game_character_displayname_"


class RosterNotReady(Exception):
    pass


def extract_spell_id(raw_display_name: str, known_ids: Sequence[str]) -> str | None:
    raw = raw_display_name or ""
    if raw.startswith(SPELL_PREFIX) and raw.endswith(SPELL_SUFFIX):
        candidate = raw[len(SPELL_PREFIX) : -len(SPELL_SUFFIX)]
        if candidate in known_ids:
            return candidate
    for spell_id in known_ids:
        if spell_id and spell_id in raw:
            return spell_id
    return None


def extract_champion_alias(raw_champion_name: str) -> str | None:
    raw = raw_champion_name or ""
    if raw.startswith(CHAMPION_PREFIX):
        return raw[len(CHAMPION_PREFIX) :] or None
    return None


def extract_enemies(data: dict, static: StaticData) -> list[Enemy]:
    players = data.get("allPlayers") or []
    if not players:
        raise RosterNotReady("allPlayers is empty")
    active = data.get("activePlayer") or {}
    my_team = _find_my_team(active, players)
    if not my_team:
        raise RosterNotReady("active player team not resolved yet")
    return [
        _build_enemy(player, static)
        for player in players
        if player.get("team") and player.get("team") != my_team
    ]


def _find_my_team(active: dict, players: list[dict]) -> str | None:
    riot_id = active.get("riotId")
    if riot_id:
        for player in players:
            if player.get("riotId") == riot_id:
                return player.get("team")
    summoner_name = active.get("summonerName")
    if summoner_name:
        for player in players:
            if player.get("summonerName") == summoner_name:
                return player.get("team")
    return None


def _build_enemy(player: dict, static: StaticData) -> Enemy:
    alias = extract_champion_alias(player.get("rawChampionName", ""))
    info = static.champion_by_alias(alias) if alias else None
    if info is None:
        logger.warning("Unknown champion: %r", player.get("rawChampionName", ""))
        champion_id = ""
        champion_name = player.get("championName") or ""
    else:
        champion_id = info.champion_id
        champion_name = info.name
    spells_payload = player.get("summonerSpells") or {}
    slots = (
        _build_spell_slot(spells_payload.get("summonerSpellOne") or {}, static),
        _build_spell_slot(spells_payload.get("summonerSpellTwo") or {}, static),
    )
    riot_id = player.get("riotId") or player.get("summonerName") or ""
    return Enemy(
        champion_id=champion_id,
        champion_name=champion_name,
        riot_id=riot_id,
        team=player.get("team") or "",
        is_bot=bool(player.get("isBot", False)),
        spells=slots,
        level=int(player.get("level") or 0),
        item_ids=_extract_item_ids(player),
    )


def _extract_item_ids(player: dict) -> tuple[int, ...]:
    items = player.get("items") or []
    ids = []
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("itemID"), int):
            ids.append(item["itemID"])
    return tuple(ids)


def _build_spell_slot(payload: dict, static: StaticData) -> SpellSlot:
    raw = payload.get("rawDisplayName") or ""
    display_name = payload.get("displayName") or ""
    spell_id = extract_spell_id(raw, static.spell_ids)
    if spell_id is None:
        if raw or display_name:
            logger.warning("Unknown summoner spell: %r", raw or display_name)
        return SpellSlot(
            spell_id="", display_name=display_name, base_cooldown=0.0, icon_file=""
        )
    info = static.spell(spell_id)
    assert info is not None
    return SpellSlot(
        spell_id=spell_id,
        display_name=display_name or info.name,
        base_cooldown=info.cooldown,
        icon_file=info.icon_file,
    )
