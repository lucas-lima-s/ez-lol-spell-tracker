import logging

from PySide6.QtCore import QThread, Signal

from src.riot import ddragon

logger = logging.getLogger(__name__)

CHECK_INTERVAL_MS = 6 * 60 * 60 * 1000


class AssetUpdateWorker(QThread):
    finished_update = Signal(str, int, int)

    def __init__(self, lang: str = "pt_BR", parent=None) -> None:
        super().__init__(parent)
        self._lang = lang

    def run(self) -> None:
        try:
            report = ddragon.update_snapshot(
                lang=self._lang, should_stop=self.isInterruptionRequested
            )
        except Exception as exc:
            logger.warning("Asset update check failed: %s", exc)
            return
        self.finished_update.emit(
            report.version, report.downloaded, len(report.failures)
        )
