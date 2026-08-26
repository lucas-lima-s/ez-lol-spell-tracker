from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SpellSlot:
    spell_id: str
    display_name: str
    base_cooldown: float
    icon_file: str


@dataclass(frozen=True, slots=True)
class Enemy:
    champion_id: str
    champion_name: str
    riot_id: str
    team: str
    is_bot: bool
    spells: tuple[SpellSlot, SpellSlot]
    level: int = 0
    item_ids: tuple[int, ...] = ()
