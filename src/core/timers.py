PAUSE_EPSILON = 0.05
MIN_PAUSE_GAP = 1.0
EXTRAPOLATION_CAP = 10.0


class GameClock:
    def __init__(self) -> None:
        self._game_time: float | None = None
        self._monotonic: float | None = None
        self._paused = False

    def reset(self) -> None:
        self._game_time = None
        self._monotonic = None
        self._paused = False

    def ingest(self, game_time: float, monotonic_now: float) -> None:
        if (
            self._game_time is not None
            and self._monotonic is not None
            and monotonic_now - self._monotonic >= MIN_PAUSE_GAP
        ):
            self._paused = game_time - self._game_time < PAUSE_EPSILON
        self._game_time = game_time
        self._monotonic = monotonic_now

    def now(self, monotonic_now: float) -> float | None:
        if self._game_time is None or self._monotonic is None:
            return None
        if self._paused:
            return self._game_time
        elapsed = monotonic_now - self._monotonic
        return self._game_time + min(max(elapsed, 0.0), EXTRAPOLATION_CAP)

    @property
    def paused(self) -> bool:
        return self._paused


class SpellTimerBoard:
    def __init__(self, clock: GameClock) -> None:
        self._clock = clock
        self._expires: dict[tuple[int, int], float] = {}

    def start(
        self,
        enemy_index: int,
        slot_index: int,
        cooldown_seconds: float,
        monotonic_now: float,
    ) -> bool:
        if cooldown_seconds <= 0:
            return False
        game_now = self._clock.now(monotonic_now)
        if game_now is None:
            return False
        self._expires[(enemy_index, slot_index)] = game_now + cooldown_seconds
        return True

    def reset(self, enemy_index: int, slot_index: int) -> None:
        self._expires.pop((enemy_index, slot_index), None)

    def adjust(self, enemy_index: int, slot_index: int, delta_seconds: float) -> None:
        key = (enemy_index, slot_index)
        if key in self._expires:
            self._expires[key] += delta_seconds

    def game_now(self, monotonic_now: float) -> float | None:
        return self._clock.now(monotonic_now)

    def remaining(
        self, enemy_index: int, slot_index: int, monotonic_now: float
    ) -> float:
        expires = self._expires.get((enemy_index, slot_index))
        if expires is None:
            return 0.0
        game_now = self._clock.now(monotonic_now)
        if game_now is None:
            return 0.0
        left = expires - game_now
        return left if left > 0 else 0.0

    def clear(self) -> None:
        self._expires.clear()
