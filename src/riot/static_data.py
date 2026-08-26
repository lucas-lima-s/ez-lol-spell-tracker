import json
from dataclasses import dataclass
from pathlib import Path

from src.core.paths import CHAMPIONS_DATA_FILE, SUMMONER_DATA_FILE


@dataclass(frozen=True, slots=True)
class SpellInfo:
    spell_id: str
    name: str
    cooldown: float
    icon_file: str


@dataclass(frozen=True, slots=True)
class ChampionInfo:
    champion_id: str
    name: str
    key: str


class StaticData:
    def __init__(
        self,
        summoner_file: Path = SUMMONER_DATA_FILE,
        champions_file: Path = CHAMPIONS_DATA_FILE,
    ) -> None:
        self._spells = self._load_spells(summoner_file)
        self._champions = self._load_champions(champions_file)
        self._spell_ids = tuple(sorted(self._spells, key=len, reverse=True))

    @staticmethod
    def _load_spells(path: Path) -> dict[str, "SpellInfo"]:
        data = json.loads(path.read_text(encoding="utf-8"))
        spells = {}
        for entry in data.get("data", {}).values():
            spell_id = entry["id"]
            cooldowns = entry.get("cooldown") or [0]
            spells[spell_id] = SpellInfo(
                spell_id=spell_id,
                name=entry.get("name", spell_id),
                cooldown=float(cooldowns[0]),
                icon_file=f"{spell_id}.png",
            )
        return spells

    @staticmethod
    def _load_champions(path: Path) -> dict[str, "ChampionInfo"]:
        data = json.loads(path.read_text(encoding="utf-8"))
        champions = {}
        for champion_id, entry in data.get("data", {}).items():
            champions[champion_id.lower()] = ChampionInfo(
                champion_id=champion_id,
                name=entry.get("name", champion_id),
                key=str(entry.get("key", "")),
            )
        return champions

    @property
    def spell_ids(self) -> tuple[str, ...]:
        return self._spell_ids

    def spell(self, spell_id: str) -> SpellInfo | None:
        return self._spells.get(spell_id)

    def champion_by_alias(self, alias: str) -> ChampionInfo | None:
        return self._champions.get(alias.lower())
