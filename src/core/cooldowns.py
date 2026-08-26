IONIAN_BOOTS_ITEM_ID = 3158
IONIAN_BOOTS_HASTE = 10.0
COSMIC_INSIGHT_HASTE = 18.0
SMITE_RECHARGE = 90.0
TELEPORT_UPGRADE_GAME_TIME = 600.0
UNLEASHED_TELEPORT_MAX = 330.0
UNLEASHED_TELEPORT_MIN = 240.0


def effective_cooldown(base_seconds: float, haste: float = 0.0) -> float:
    return base_seconds / (1 + haste / 100)


def unleashed_teleport_cooldown(level: int) -> float:
    clamped = min(18, max(1, level or 9))
    span = UNLEASHED_TELEPORT_MAX - UNLEASHED_TELEPORT_MIN
    return UNLEASHED_TELEPORT_MAX - span * (clamped - 1) / 17


def base_cooldown_for(
    spell_id: str, default_base: float, enemy_level: int, game_time: float
) -> float:
    if spell_id == "SummonerSmite":
        return SMITE_RECHARGE
    if spell_id == "SummonerTeleport" and game_time >= TELEPORT_UPGRADE_GAME_TIME:
        return unleashed_teleport_cooldown(enemy_level)
    return default_base


class HasteTracker:
    def __init__(self) -> None:
        self._boots: set[int] = set()
        self._insight: set[int] = set()

    def set_boots(self, enemy_index: int, has_boots: bool) -> None:
        if has_boots:
            self._boots.add(enemy_index)
        else:
            self._boots.discard(enemy_index)

    def has_boots(self, enemy_index: int) -> bool:
        return enemy_index in self._boots

    def toggle_insight(self, enemy_index: int) -> bool:
        if enemy_index in self._insight:
            self._insight.discard(enemy_index)
            return False
        self._insight.add(enemy_index)
        return True

    def has_insight(self, enemy_index: int) -> bool:
        return enemy_index in self._insight

    def haste(self, enemy_index: int) -> float:
        total = 0.0
        if enemy_index in self._boots:
            total += IONIAN_BOOTS_HASTE
        if enemy_index in self._insight:
            total += COSMIC_INSIGHT_HASTE
        return total

    def clear(self) -> None:
        self._boots.clear()
        self._insight.clear()
