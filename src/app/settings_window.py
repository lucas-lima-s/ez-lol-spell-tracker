import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)

from src.app import autostart
from src.app.strings import tr
from src.core.config import Config
from src.core.paths import DATA_VERSION_FILE, TRAY_ICON_FILE
from src.overlay import overlay_window
from src.overlay.controller import OverlayController

logger = logging.getLogger(__name__)


class SettingsWindow(QDialog):
    def __init__(self, config: Config, overlay: OverlayController) -> None:
        super().__init__()
        self._config = config
        self._overlay = overlay
        self.setWindowTitle(tr("settings.title"))
        if TRAY_ICON_FILE.is_file():
            self.setWindowIcon(QIcon(str(TRAY_ICON_FILE)))
        overlay_settings = config.get("overlay") or {}
        root = QVBoxLayout(self)
        root.addWidget(self._build_overlay_group(overlay_settings))
        root.addWidget(self._build_general_group())
        root.addStretch(1)
        self.resize(420, 400)

    def _build_overlay_group(self, overlay_settings: dict) -> QGroupBox:
        group = QGroupBox(tr("settings.group.overlay"))
        form = QFormLayout(group)

        self.resolution_label = QLabel()
        self._refresh_resolution_label()
        form.addRow(self.resolution_label)

        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(50, 150)
        self.scale_slider.setValue(round(self._overlay.window().current_scale() * 100))
        self.scale_label = QLabel(f"{self.scale_slider.value()}%")
        self.scale_slider.valueChanged.connect(self._on_scale_changed)
        self.scale_slider.sliderReleased.connect(self._persist_sliders)
        scale_row = QHBoxLayout()
        scale_row.addWidget(self.scale_slider, 1)
        scale_row.addWidget(self.scale_label)
        form.addRow(tr("settings.scale"), scale_row)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setValue(
            round(float(overlay_settings.get("opacity") or 0.9) * 100)
        )
        self.opacity_label = QLabel(f"{self.opacity_slider.value()}%")
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        self.opacity_slider.sliderReleased.connect(self._persist_sliders)
        opacity_row = QHBoxLayout()
        opacity_row.addWidget(self.opacity_slider, 1)
        opacity_row.addWidget(self.opacity_label)
        form.addRow(tr("settings.opacity"), opacity_row)

        self.locked_check = QCheckBox(tr("settings.locked"))
        self.locked_check.setChecked(bool(overlay_settings.get("locked", False)))
        self.locked_check.toggled.connect(self._overlay.set_locked)
        self._overlay.window().locked_changed.connect(self._on_overlay_lock_changed)
        form.addRow(self.locked_check)

        self.hotkey_edit = QKeySequenceEdit()
        self.hotkey_edit.setClearButtonEnabled(True)
        configured = str(self._config.get("hotkey_toggle_overlay") or "")
        if configured:
            self.hotkey_edit.setKeySequence(QKeySequence(configured))
        self.hotkey_edit.editingFinished.connect(self._on_hotkey_changed)
        form.addRow(tr("settings.hotkey"), self.hotkey_edit)
        self.hotkey_warning = QLabel(tr("settings.hotkey_failed"))
        self.hotkey_warning.setVisible(False)
        form.addRow(self.hotkey_warning)

        self.capture_check = QCheckBox(tr("settings.hide_from_capture"))
        self.capture_check.setChecked(
            bool(overlay_settings.get("hide_from_capture", False))
        )
        self.capture_check.toggled.connect(self._on_capture_toggled)
        form.addRow(self.capture_check)
        self.capture_warning = QLabel(tr("settings.hide_from_capture_unsupported"))
        self.capture_warning.setVisible(False)
        form.addRow(self.capture_warning)

        self.cast_offset_spin = QSpinBox()
        self.cast_offset_spin.setRange(0, 30)
        self.cast_offset_spin.setValue(int(self._config.get("click_cast_offset") or 0))
        self.cast_offset_spin.valueChanged.connect(
            lambda value: self._config.set("click_cast_offset", int(value))
        )
        form.addRow(tr("settings.cast_offset"), self.cast_offset_spin)

        self.reset_button = QPushButton(tr("settings.reset_position"))
        self.reset_button.clicked.connect(self._overlay.reset_position)
        form.addRow(self.reset_button)

        help_label = QLabel(tr("settings.help.controls"))
        help_label.setWordWrap(True)
        form.addRow(help_label)
        return group

    def _build_general_group(self) -> QGroupBox:
        group = QGroupBox(tr("settings.group.general"))
        layout = QVBoxLayout(group)
        self.autostart_check = QCheckBox(tr("settings.start_with_windows"))
        self.autostart_check.setChecked(autostart.is_enabled())
        self.autostart_check.toggled.connect(self._on_autostart_toggled)
        layout.addWidget(self.autostart_check)
        self.autostart_warning = QLabel(tr("settings.start_with_windows_failed"))
        self.autostart_warning.setVisible(False)
        layout.addWidget(self.autostart_warning)
        self.data_version_label = QLabel()
        self._refresh_data_version_label()
        layout.addWidget(self.data_version_label)
        return group

    def _on_scale_changed(self, value: int) -> None:
        self.scale_label.setText(f"{value}%")
        self._overlay.set_scale(value / 100, persist=False)

    def _on_opacity_changed(self, value: int) -> None:
        self.opacity_label.setText(f"{value}%")
        self._overlay.set_opacity(value / 100, persist=False)

    def _persist_sliders(self) -> None:
        self._overlay.set_scale(self.scale_slider.value() / 100)
        self._overlay.set_opacity(self.opacity_slider.value() / 100)

    def _refresh_resolution_label(self) -> None:
        self.resolution_label.setText(
            f"{tr('settings.resolution_profile')} {overlay_window.resolution_key()}"
        )

    def _refresh_data_version_label(self) -> None:
        version = "?"
        try:
            if DATA_VERSION_FILE.is_file():
                version = DATA_VERSION_FILE.read_text(encoding="utf-8").strip() or "?"
        except OSError:
            pass
        self.data_version_label.setText(f"{tr('settings.data_version')} {version}")

    def _on_overlay_lock_changed(self, locked: bool) -> None:
        self.locked_check.blockSignals(True)
        self.locked_check.setChecked(locked)
        self.locked_check.blockSignals(False)

    def _on_hotkey_changed(self) -> None:
        text = self.hotkey_edit.keySequence().toString()
        ok = self._overlay.set_hotkey(text)
        self.hotkey_warning.setVisible(not ok)
        if not ok:
            previous = str(self._config.get("hotkey_toggle_overlay") or "")
            self.hotkey_edit.blockSignals(True)
            self.hotkey_edit.setKeySequence(QKeySequence(previous))
            self.hotkey_edit.blockSignals(False)

    def _on_capture_toggled(self, checked: bool) -> None:
        ok = self._overlay.set_hide_from_capture(checked)
        if checked and not ok:
            self.capture_check.blockSignals(True)
            self.capture_check.setChecked(False)
            self.capture_check.blockSignals(False)
            self.capture_check.setEnabled(False)
            self.capture_warning.setVisible(True)

    def _on_autostart_toggled(self, checked: bool) -> None:
        if autostart.set_enabled(checked):
            self.autostart_warning.setVisible(False)
            self._config.set("start_with_windows", checked)
            return
        logger.warning("Failed to update autostart to %s", checked)
        self.autostart_check.blockSignals(True)
        self.autostart_check.setChecked(not checked)
        self.autostart_check.blockSignals(False)
        self.autostart_warning.setVisible(True)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._refresh_resolution_label()
        self._refresh_data_version_label()
        self.scale_slider.blockSignals(True)
        self.scale_slider.setValue(round(self._overlay.window().current_scale() * 100))
        self.scale_slider.blockSignals(False)
        self.scale_label.setText(f"{self.scale_slider.value()}%")
        self._overlay.set_settings_open(True)

    def hideEvent(self, event) -> None:
        self._persist_sliders()
        self._overlay.set_settings_open(False)
        super().hideEvent(event)
