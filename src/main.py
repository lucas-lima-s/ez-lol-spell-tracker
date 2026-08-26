import logging
import sys

from PySide6.QtCore import QDir, QLockFile, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from src.app.asset_update_worker import CHECK_INTERVAL_MS, AssetUpdateWorker
from src.app.game_watcher import GameWatcher
from src.app.strings import tr
from src.app.tray import TrayIcon
from src.core.config import Config
from src.core.log_setup import setup_logging
from src.core.models import Enemy
from src.overlay.controller import OverlayController
from src.riot.static_data import StaticData

logger = logging.getLogger(__name__)


def _on_game_started(enemies: list[Enemy]) -> None:
    if not enemies:
        logger.warning("Game started with no enemies on roster")
        return
    logger.info("Game started with %d enemies", len(enemies))
    for enemy in enemies:
        spells = " / ".join(
            f"{slot.spell_id or slot.display_name or '?'} ({slot.base_cooldown:.0f}s)"
            for slot in enemy.spells
        )
        logger.info(
            "Enemy: %s (%s) [%s]: %s",
            enemy.champion_name,
            enemy.champion_id or "?",
            enemy.riot_id,
            spells,
        )


def _on_game_ended() -> None:
    logger.info("Game ended")


def _load_static_data(lang: str) -> StaticData:
    try:
        return StaticData()
    except Exception:
        logger.exception("Static data unreadable, attempting snapshot repair")
        from src.riot import ddragon

        ddragon.update_snapshot(lang=lang, force=True)
        return StaticData()


def _on_assets_updated(version: str, downloaded: int, failures: int) -> None:
    if failures:
        logger.warning("Asset update for %s incomplete (%d failures)", version, failures)
    elif downloaded:
        logger.info("Assets updated to %s (%d files)", version, downloaded)
    else:
        logger.info("Assets already up to date (%s)", version)


def _stop_watcher(watcher: GameWatcher) -> None:
    watcher.stop()
    if not watcher.wait(5000):
        logger.warning("Game watcher thread did not stop cleanly")


def _stop_updater(updater: AssetUpdateWorker) -> None:
    updater.requestInterruption()
    if updater.isRunning() and not updater.wait(15000):
        logger.warning("Asset updater thread did not stop cleanly")


def main() -> int:
    app = QApplication(sys.argv)
    lock_file = QLockFile(QDir.tempPath() + "/EzSpellTracker.lock")
    if not lock_file.tryLock(0):
        QMessageBox.warning(
            None,
            tr("error.already_running.title"),
            tr("error.already_running.text"),
        )
        return 1
    setup_logging()
    config = Config()
    level_name = str(config.get("logLevel", "INFO")).upper()
    if level_name not in logging.getLevelNamesMapping():
        logger.warning("Invalid logLevel %r in settings, using INFO", level_name)
        level_name = "INFO"
    logging.getLogger().setLevel(level_name)
    config.save()
    logger.info("Starting EzSpellTracker")
    app.setQuitOnLastWindowClosed(False)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        logger.error("System tray unavailable, cannot start")
        QMessageBox.critical(None, tr("error.no_tray.title"), tr("error.no_tray.text"))
        return 1
    lang = str(config.get("language") or "pt-BR").replace("-", "_")
    try:
        static = _load_static_data(lang)
        controller = OverlayController(config, static)
        watcher = GameWatcher(static=static)
    except Exception:
        logger.exception("Failed to initialize overlay and game watcher")
        QMessageBox.critical(None, tr("error.startup.title"), tr("error.startup.text"))
        return 1
    tray = TrayIcon(config, controller)
    tray.show()
    watcher.game_started.connect(_on_game_started)
    watcher.game_started.connect(controller.on_game_started)
    watcher.game_ended.connect(_on_game_ended)
    watcher.game_ended.connect(controller.on_game_ended)
    watcher.game_time.connect(controller.on_game_time)
    watcher.roster_updated.connect(controller.on_roster_updated)
    watcher.start()
    updater = AssetUpdateWorker(lang=lang)
    updater.finished_update.connect(_on_assets_updated)
    updater.start()
    update_timer = QTimer()
    update_timer.timeout.connect(lambda: updater.start() if not updater.isRunning() else None)
    update_timer.start(CHECK_INTERVAL_MS)
    app.aboutToQuit.connect(lambda: _stop_updater(updater))
    app.aboutToQuit.connect(controller.shutdown)
    app.aboutToQuit.connect(lambda: _stop_watcher(watcher))
    app.aboutToQuit.connect(lambda: logger.info("Application shutting down"))
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
