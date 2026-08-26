import logging
import threading
from enum import Enum, auto

from PySide6.QtCore import QThread, Signal

from src.riot.live_client import LiveClient, LiveClientError, NotInGameError
from src.riot.parser import RosterNotReady, extract_enemies
from src.riot.static_data import StaticData

logger = logging.getLogger(__name__)

POLL_INTERVAL_MS = 2000
END_CONFIRM_TICKS = 2
ROSTER_WARN_TICKS = 30
ROSTER_REFRESH_TICKS = 5


class _State(Enum):
    IDLE = auto()
    LOADING = auto()
    IN_GAME = auto()


class GameWatcher(QThread):
    game_started = Signal(list)
    game_ended = Signal()
    game_time = Signal(float)
    roster_updated = Signal(list)

    def __init__(
        self,
        client: LiveClient | None = None,
        static: StaticData | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._client = client or LiveClient()
        self._static = static or StaticData()
        self._stop_event = threading.Event()
        self._state = _State.IDLE
        self._end_fail_count = 0
        self._roster_ticks = 0
        self._in_game_ticks = 0

    def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception:
                logger.exception("Unexpected error in game watcher tick")
            self._stop_event.wait(POLL_INTERVAL_MS / 1000)

    def stop(self) -> None:
        self._stop_event.set()

    def _tick(self) -> None:
        if self._state is _State.IDLE:
            self._tick_idle()
        elif self._state is _State.LOADING:
            self._tick_loading()
        else:
            self._tick_in_game()

    def _tick_idle(self) -> None:
        try:
            stats = self._client.get_game_stats()
        except LiveClientError:
            return
        logger.info(
            "Game detected (mode=%s, time=%.0fs)",
            stats.get("gameMode", "?"),
            stats.get("gameTime", 0.0),
        )
        self._roster_ticks = 0
        self._state = _State.LOADING

    def _tick_loading(self) -> None:
        try:
            data = self._client.get_all_game_data()
            enemies = extract_enemies(data, self._static)
        except RosterNotReady as exc:
            self._roster_ticks += 1
            if self._roster_ticks == ROSTER_WARN_TICKS:
                logger.warning(
                    "Roster still not ready after %d polls (%s) - spectator mode?",
                    self._roster_ticks,
                    exc,
                )
            else:
                logger.debug("Roster not ready: %s", exc)
            return
        except NotInGameError:
            logger.info("Game vanished while loading roster")
            self._state = _State.IDLE
            return
        except LiveClientError as exc:
            logger.debug("Transient error while loading roster: %s", exc)
            return
        self._end_fail_count = 0
        self._in_game_ticks = 0
        self._state = _State.IN_GAME
        self.game_started.emit(enemies)
        self._emit_game_time((data.get("gameData") or {}).get("gameTime"))

    def _tick_in_game(self) -> None:
        try:
            stats = self._client.get_game_stats()
        except NotInGameError:
            self._end_fail_count += 1
            if self._end_fail_count >= END_CONFIRM_TICKS:
                self._state = _State.IDLE
                self.game_ended.emit()
            return
        except LiveClientError:
            return
        self._end_fail_count = 0
        self._emit_game_time(stats.get("gameTime"))
        self._in_game_ticks += 1
        if self._in_game_ticks >= ROSTER_REFRESH_TICKS:
            self._in_game_ticks = 0
            self._refresh_roster()

    def _refresh_roster(self) -> None:
        try:
            data = self._client.get_all_game_data()
            enemies = extract_enemies(data, self._static)
        except (RosterNotReady, LiveClientError) as exc:
            logger.debug("Roster refresh skipped: %s", exc)
            return
        self.roster_updated.emit(enemies)

    def _emit_game_time(self, value) -> None:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            self.game_time.emit(float(value))
