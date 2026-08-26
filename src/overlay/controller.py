import logging
import time
from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, Signal

from src.core.config import Config
from src.core.cooldowns import IONIAN_BOOTS_ITEM_ID, HasteTracker
from src.core.models import Enemy, SpellSlot
from src.core.timers import GameClock, SpellTimerBoard
from src.overlay import overlay_window, win32
from src.overlay.hotkey import GlobalHotkey
from src.overlay.overlay_window import OverlayWindow
from src.overlay.visibility import is_league_title, should_show
from src.riot.static_data import StaticData

logger = logging.getLogger(__name__)

VISIBILITY_TICK_MS = 500
TOPMOST_EVERY_TICKS = 4
PREVIEW_ROSTER = (
    ("Annie", "SummonerFlash", "SummonerDot"),
    ("Ahri", "SummonerFlash", "SummonerTeleport"),
    ("Garen", "SummonerFlash", "SummonerHaste"),
    ("Lux", "SummonerFlash", "SummonerBarrier"),
    ("Teemo", "SummonerFlash", "SummonerExhaust"),
)


class OverlayController(QObject):
    preview_changed = Signal(bool)

    def __init__(
        self,
        config: Config,
        static: StaticData,
        parent=None,
        monotonic: Callable[[], float] = time.monotonic,
        hotkey: GlobalHotkey | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._static = static
        self._monotonic = monotonic
        self._clock = GameClock()
        self._board = SpellTimerBoard(self._clock)
        self._haste = HasteTracker()
        self._window = OverlayWindow(
            config, self._board, haste=self._haste, monotonic=monotonic
        )
        self._in_game = False
        self._preview_user = False
        self._preview_settings = False
        self._user_hidden = False
        self._tick_count = 0
        self._resolution = overlay_window.resolution_key()
        self._hotkey = hotkey or GlobalHotkey(self)
        self._hotkey.triggered.connect(self.toggle_user_hidden)
        configured = str(config.get("hotkey_toggle_overlay") or "")
        if configured and not self._hotkey.register(configured):
            logger.warning("Could not register overlay hotkey %r", configured)
        self._visibility_timer = QTimer(self)
        self._visibility_timer.timeout.connect(self._visibility_tick)
        self._visibility_timer.start(VISIBILITY_TICK_MS)

    def window(self) -> OverlayWindow:
        return self._window

    def preview_active(self) -> bool:
        return self._preview_user or self._preview_settings

    def on_game_started(self, enemies: list) -> None:
        self._clock.reset()
        self._board.clear()
        self._haste.clear()
        self._update_haste_from_roster(enemies)
        self._in_game = True
        self._user_hidden = False
        if self._preview_user:
            self._preview_user = False
            self.preview_changed.emit(False)
        self._window.set_enemies(enemies)
        self._visibility_tick()

    def on_game_ended(self) -> None:
        self._in_game = False
        self._board.clear()
        self._clock.reset()
        self._haste.clear()
        if self.preview_active():
            self._window.set_enemies(self._build_preview_enemies())
        else:
            self._window.clear_enemies()
            self._window.hide()

    def on_game_time(self, game_time: float) -> None:
        self._clock.ingest(float(game_time), self._monotonic())

    def on_roster_updated(self, enemies: list) -> None:
        if not self._in_game or not enemies:
            return
        current = [enemy.riot_id for enemy in self._window.enemies()]
        incoming = [enemy.riot_id for enemy in enemies[:5]]
        if current and incoming != current:
            logger.warning("Roster order changed, skipping update to protect timers")
            return
        self._window.set_enemies(enemies)
        self._update_haste_from_roster(enemies)

    def _update_haste_from_roster(self, enemies: list) -> None:
        for index, enemy in enumerate(enemies[:5]):
            self._haste.set_boots(index, IONIAN_BOOTS_ITEM_ID in enemy.item_ids)

    def toggle_preview(self) -> None:
        self._set_preview_user(not self._preview_user)

    def toggle_user_hidden(self) -> None:
        self._user_hidden = not self._user_hidden
        logger.info("Overlay %s by hotkey", "hidden" if self._user_hidden else "shown")
        self._visibility_tick()

    def set_hotkey(self, text: str) -> bool:
        cleaned = str(text or "").strip()
        if not cleaned:
            self._hotkey.unregister()
            self._config.set("hotkey_toggle_overlay", "")
            return True
        if self._hotkey.register(cleaned):
            self._config.set("hotkey_toggle_overlay", cleaned)
            return True
        previous = str(self._config.get("hotkey_toggle_overlay") or "")
        if previous:
            self._hotkey.register(previous)
        return False

    def set_settings_open(self, is_open: bool) -> None:
        if self._preview_settings == bool(is_open):
            return
        self._preview_settings = bool(is_open)
        self._refresh_preview_content()

    def set_scale(self, scale: float, persist: bool = True) -> None:
        self._window.set_scale(scale)
        if persist:
            self._window.persist_scale(scale)

    def set_opacity(self, opacity: float, persist: bool = True) -> None:
        self._window.set_opacity(opacity)
        if persist:
            self._persist_overlay("opacity", round(float(opacity), 2))

    def set_locked(self, locked: bool) -> None:
        self._window.set_locked(locked)
        self._persist_overlay("locked", bool(locked))

    def set_hide_from_capture(self, hide: bool) -> bool:
        ok = self._window.apply_capture_exclusion(bool(hide))
        self._persist_overlay("hide_from_capture", bool(hide) and ok)
        return ok

    def reset_position(self) -> None:
        self._window.reset_position()

    def shutdown(self) -> None:
        self._visibility_timer.stop()
        self._hotkey.unregister()
        self._window.hide()

    def _set_preview_user(self, active: bool) -> None:
        if self._preview_user == active:
            return
        self._preview_user = active
        self.preview_changed.emit(active)
        self._refresh_preview_content()

    def _refresh_preview_content(self) -> None:
        if self._in_game:
            return
        if self.preview_active():
            self._window.set_enemies(self._build_preview_enemies())
            self._window.show()
            win32.force_topmost(int(self._window.winId()))
        else:
            self._board.clear()
            self._clock.reset()
            self._haste.clear()
            self._window.clear_enemies()
            self._window.hide()

    def _persist_overlay(self, key: str, value) -> None:
        overlay = dict(self._config.get("overlay") or {})
        overlay[key] = value
        self._config.set("overlay", overlay)

    def _visibility_tick(self) -> None:
        resolution = overlay_window.resolution_key()
        if resolution != self._resolution:
            logger.info("Resolution changed to %s, reloading overlay profile", resolution)
            self._resolution = resolution
            self._window.reload_profile()
        if self.preview_active() and not self._in_game:
            now = self._monotonic()
            self._clock.ingest(now, now)
        fg_league = is_league_title(win32.get_foreground_window_title())
        show = (
            should_show(
                self._in_game,
                fg_league,
                self._window.is_dragging(),
                self.preview_active(),
            )
            and not self._user_hidden
        )
        if show and not self._window.isVisible():
            self._window.show()
        elif not show and self._window.isVisible():
            self._window.hide()
        if show:
            self._tick_count += 1
            if self._tick_count >= TOPMOST_EVERY_TICKS:
                self._tick_count = 0
                win32.force_topmost(int(self._window.winId()))

    def _build_preview_enemies(self) -> list[Enemy]:
        enemies = []
        for champion, spell_one, spell_two in PREVIEW_ROSTER:
            info = self._static.champion_by_alias(champion)
            enemies.append(
                Enemy(
                    champion_id=info.champion_id if info else champion,
                    champion_name=info.name if info else champion,
                    riot_id="preview",
                    team="CHAOS",
                    is_bot=True,
                    spells=(
                        self._preview_slot(spell_one),
                        self._preview_slot(spell_two),
                    ),
                )
            )
        return enemies

    def _preview_slot(self, spell_id: str) -> SpellSlot:
        info = self._static.spell(spell_id)
        if info is None:
            return SpellSlot(
                spell_id=spell_id,
                display_name=spell_id,
                base_cooldown=0.0,
                icon_file="",
            )
        return SpellSlot(
            spell_id=info.spell_id,
            display_name=info.name,
            base_cooldown=info.cooldown,
            icon_file=info.icon_file,
        )
