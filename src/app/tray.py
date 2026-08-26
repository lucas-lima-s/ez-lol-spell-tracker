import logging

from PySide6.QtGui import QAction, QColor, QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from src.app.settings_window import SettingsWindow
from src.app.strings import tr
from src.core.config import Config
from src.core.paths import TRAY_ICON_FILE
from src.overlay.controller import OverlayController

logger = logging.getLogger(__name__)


def _load_icon() -> QIcon:
    if TRAY_ICON_FILE.is_file():
        icon = QIcon(str(TRAY_ICON_FILE))
        if not icon.isNull():
            return icon
    logger.warning("Tray icon asset missing, using fallback color icon")
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor("#C8AA6E"))
    return QIcon(pixmap)


class TrayIcon(QSystemTrayIcon):
    def __init__(self, config: Config, overlay: OverlayController) -> None:
        super().__init__(_load_icon())
        self._config = config
        self._overlay = overlay
        self.setToolTip(tr("tray.tooltip"))
        self._settings_window: SettingsWindow | None = None
        self._menu = QMenu()
        settings_action = QAction(tr("menu.settings"), self._menu)
        settings_action.triggered.connect(self._show_settings)
        self._overlay_action = QAction(tr("menu.show_overlay"), self._menu)
        self._overlay_action.setCheckable(True)
        self._overlay_action.triggered.connect(self._on_overlay_action)
        overlay.preview_changed.connect(self._overlay_action.setChecked)
        exit_action = QAction(tr("menu.exit"), self._menu)
        exit_action.triggered.connect(self._quit)
        self._menu.addAction(settings_action)
        self._menu.addAction(self._overlay_action)
        self._menu.addSeparator()
        self._menu.addAction(exit_action)
        self.setContextMenu(self._menu)
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_settings()

    def _on_overlay_action(self) -> None:
        self._overlay.toggle_preview()

    def _show_settings(self) -> None:
        if self._settings_window is None:
            self._settings_window = SettingsWindow(self._config, self._overlay)
        window = self._settings_window
        window.show()
        window.raise_()
        window.activateWindow()

    def _quit(self) -> None:
        logger.info("Exit requested from tray menu")
        self.hide()
        QApplication.quit()
