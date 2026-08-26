import logging
import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QApplication, QWidget

from src.core.config import Config
from src.core.cooldowns import HasteTracker, base_cooldown_for, effective_cooldown
from src.core.models import Enemy, SpellSlot
from src.core.paths import CHAMPIONS_DIR, SPELLS_DIR
from src.core.timers import SpellTimerBoard
from src.overlay import win32

logger = logging.getLogger(__name__)

REPAINT_INTERVAL_MS = 250


@dataclass(frozen=True, slots=True)
class OverlayMetrics:
    margin: int = 20
    spacing: int = 10
    square: int = 50
    champion_gap: int = 20
    header: int = 22


METRICS = OverlayMetrics()


def resolution_key() -> str:
    screen = QApplication.primaryScreen()
    if screen is None:
        return "unknown"
    size = screen.geometry().size()
    dpr = screen.devicePixelRatio()
    return f"{round(size.width() * dpr)}x{round(size.height() * dpr)}"


def fmt_mmss(seconds: float) -> str:
    total = max(0, math.ceil(seconds))
    return f"{total // 60}:{total % 60:02d}"


def _initials(name: str) -> str:
    words = (name or "").split()
    if not words:
        return "?"
    return "".join(word[0] for word in words[:2]).upper()


class OverlayWindow(QWidget):
    drag_state_changed = Signal(bool)
    locked_changed = Signal(bool)

    def __init__(
        self,
        config: Config,
        board: SpellTimerBoard,
        haste: HasteTracker | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setWindowTitle("")
        self._config = config
        self._board = board
        self._haste = haste or HasteTracker()
        self._monotonic = monotonic
        overlay = config.get("overlay") or {}
        self._scale = max(0.25, float(self._profile().get("scale") or 0.7))
        self._locked = bool(overlay.get("locked", False))
        self._enemies: list[Enemy] = []
        self._drag_offset: QPoint | None = None
        self._pixmaps: dict[str, QPixmap] = {}
        self._gray_pixmaps: dict[str, QPixmap] = {}
        self._repaint_timer = QTimer(self)
        self._repaint_timer.timeout.connect(self.update)
        self.setWindowOpacity(max(0.2, min(1.0, float(overlay.get("opacity") or 0.9))))
        self._apply_size()
        self._position_window()

    def set_enemies(self, enemies: list[Enemy]) -> None:
        incoming = list(enemies[:5])
        if [e.champion_id for e in incoming] != [e.champion_id for e in self._enemies]:
            self._pixmaps.clear()
            self._gray_pixmaps.clear()
        self._enemies = incoming
        self.update()

    def clear_enemies(self) -> None:
        self.set_enemies([])

    def enemies(self) -> list[Enemy]:
        return list(self._enemies)

    def set_scale(self, scale: float) -> None:
        self._scale = max(0.25, float(scale))
        self._apply_size()
        self.update()

    def set_opacity(self, opacity: float) -> None:
        self.setWindowOpacity(max(0.2, min(1.0, float(opacity))))

    def set_locked(self, locked: bool) -> None:
        self._locked = bool(locked)
        self.update()

    def is_locked(self) -> bool:
        return self._locked

    def is_dragging(self) -> bool:
        return self._drag_offset is not None

    def apply_capture_exclusion(self, excluded: bool) -> bool:
        return win32.set_capture_exclusion(int(self.winId()), excluded)

    def reset_position(self) -> None:
        self.move(self._default_pos())
        self._persist_position()

    def cell_rect(self, row: int, col: int) -> QRect:
        s = self._scale
        margin = int(METRICS.margin * s)
        spacing = int(METRICS.spacing * s)
        square = int(METRICS.square * s)
        gap = int(METRICS.champion_gap * s)
        header = int(METRICS.header * s)
        x = margin + col * (square + spacing) + (gap if col > 0 else 0)
        y = header + margin + row * (square + spacing)
        return QRect(x, y, square, square)

    def lock_rect(self) -> QRect:
        s = self._scale
        size = max(14, int(16 * s))
        return QRect(self.width() - size - max(4, int(6 * s)), max(3, int(4 * s)), size, size)

    def _content_size(self) -> QSize:
        s = self._scale
        margin = int(METRICS.margin * s)
        spacing = int(METRICS.spacing * s)
        square = int(METRICS.square * s)
        gap = int(METRICS.champion_gap * s)
        header = int(METRICS.header * s)
        width = 2 * margin + 3 * square + 2 * spacing + gap
        height = header + 2 * margin + 5 * square + 4 * spacing
        return QSize(width, height)

    def _apply_size(self) -> None:
        self.setFixedSize(self._content_size())

    def _position_window(self) -> None:
        profile = self._profile()
        x, y = profile.get("x"), profile.get("y")
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            point = QPoint(int(x), int(y))
            if self._is_on_screen(point):
                self.move(point)
                return
        self.move(self._default_pos())

    def _profile(self) -> dict:
        overlay = dict(self._config.get("overlay") or {})
        profiles = overlay.get("profiles") or {}
        profile = dict(profiles.get(resolution_key()) or {})
        for key in ("x", "y", "scale"):
            if profile.get(key) is None and overlay.get(key) is not None:
                profile[key] = overlay.get(key)
        return profile

    def _persist_profile(self, **values) -> None:
        overlay = dict(self._config.get("overlay") or {})
        profiles = dict(overlay.get("profiles") or {})
        profile = dict(profiles.get(resolution_key()) or {})
        profile.update(values)
        profiles[resolution_key()] = profile
        overlay["profiles"] = profiles
        self._config.set("overlay", overlay)

    def persist_scale(self, scale: float) -> None:
        self._persist_profile(scale=round(float(scale), 2))

    def current_scale(self) -> float:
        return self._scale

    def reload_profile(self) -> None:
        profile = self._profile()
        self.set_scale(float(profile.get("scale") or 0.7))
        self._position_window()

    def _default_pos(self) -> QPoint:
        screen = QApplication.primaryScreen()
        if screen is None:
            return QPoint(40, 200)
        geo = screen.availableGeometry()
        return QPoint(geo.x() + 40, geo.center().y() - self.height() // 2)

    def _is_on_screen(self, point: QPoint) -> bool:
        rect = QRect(point, self.size())
        return any(screen.availableGeometry().intersects(rect) for screen in QApplication.screens())

    def _persist_position(self) -> None:
        point = self.frameGeometry().topLeft()
        self._persist_profile(x=int(point.x()), y=int(point.y()))

    def _toggle_lock(self) -> None:
        self.set_locked(not self._locked)
        overlay = dict(self._config.get("overlay") or {})
        overlay["locked"] = self._locked
        self._config.set("overlay", overlay)
        self.locked_changed.emit(self._locked)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        hwnd = int(self.winId())
        win32.set_no_activate(hwnd)
        overlay = self._config.get("overlay") or {}
        if overlay.get("hide_from_capture"):
            win32.set_capture_exclusion(hwnd, True)
        win32.force_topmost(hwnd)
        self._repaint_timer.start(REPAINT_INTERVAL_MS)

    def hideEvent(self, event) -> None:
        self._repaint_timer.stop()
        if self._drag_offset is not None:
            self._drag_offset = None
            self.drag_state_changed.emit(False)
        super().hideEvent(event)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            s = self._scale
            radius = max(6, int(8 * s))
            panel = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
            alpha = 170 if self._drag_offset is not None else 140
            painter.setBrush(QColor(30, 30, 30, alpha))
            if self._locked:
                painter.setPen(Qt.PenStyle.NoPen)
            else:
                painter.setPen(QColor(255, 255, 255, 60))
            painter.drawRoundedRect(panel, 12 * s, 12 * s)
            self._paint_lock(painter, s)
            now = self._monotonic()
            for row, enemy in enumerate(self._enemies):
                self._paint_champion(painter, self.cell_rect(row, 0), enemy, s)
                for col in (1, 2):
                    self._paint_spell(
                        painter,
                        self.cell_rect(row, col),
                        row,
                        col - 1,
                        enemy.spells[col - 1],
                        radius,
                        s,
                        now,
                    )
        finally:
            painter.end()

    def _paint_lock(self, painter: QPainter, s: float) -> None:
        rect = self.lock_rect()
        painter.save()
        font = QFont()
        font.setPixelSize(max(11, int(13 * s)))
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255, 200 if self._locked else 140))
        glyph = "\U0001f512" if self._locked else "\U0001f513"
        painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), glyph)
        painter.restore()

    def _pixmap(self, path: Path) -> QPixmap | None:
        key = str(path)
        cached = self._pixmaps.get(key)
        if cached is None:
            cached = QPixmap(key) if path.is_file() else QPixmap()
            if not cached.isNull():
                self._pixmaps[key] = cached
        return cached if not cached.isNull() else None

    def _scaled_for_rect(self, pixmap: QPixmap, rect: QRect) -> QPixmap:
        dpr = self.devicePixelRatioF()
        scaled = pixmap.scaled(
            rect.size() * dpr,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        scaled.setDevicePixelRatio(dpr)
        return scaled

    def _gray_pixmap(self, path: Path) -> QPixmap | None:
        key = str(path)
        cached = self._gray_pixmaps.get(key)
        if cached is None:
            cached = QPixmap()
            if path.is_file():
                image = QImage(key).convertToFormat(QImage.Format.Format_Grayscale8)
                cached = QPixmap.fromImage(image)
            if not cached.isNull():
                self._gray_pixmaps[key] = cached
        return cached if not cached.isNull() else None

    def _paint_champion(self, painter: QPainter, rect: QRect, enemy: Enemy, s: float) -> None:
        clip = QPainterPath()
        clip.addEllipse(QRectF(rect))
        pixmap = None
        if enemy.champion_id:
            pixmap = self._pixmap(CHAMPIONS_DIR / f"{enemy.champion_id}.png")
        painter.save()
        painter.setClipPath(clip)
        if pixmap is not None:
            painter.drawPixmap(rect, self._scaled_for_rect(pixmap, rect))
        else:
            painter.fillRect(rect, QColor(60, 60, 60, 200))
            font = QFont()
            font.setBold(True)
            font.setPixelSize(max(9, int(16 * s)))
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255, 230))
            painter.drawText(
                rect,
                int(Qt.AlignmentFlag.AlignCenter),
                _initials(enemy.champion_name),
            )
        painter.restore()
        row = self._enemies.index(enemy) if enemy in self._enemies else -1
        if row >= 0:
            self._paint_haste_badges(painter, rect, row, s)

    def _paint_haste_badges(self, painter: QPainter, rect: QRect, row: int, s: float) -> None:
        size = max(6, int(9 * s))
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        if self._haste.has_insight(row):
            painter.setBrush(QColor(255, 204, 0, 230))
            painter.drawEllipse(QRect(rect.right() - size, rect.top(), size, size))
        if self._haste.has_boots(row):
            painter.setBrush(QColor(0, 200, 255, 230))
            painter.drawEllipse(QRect(rect.right() - size, rect.bottom() - size, size, size))
        painter.restore()

    def _paint_spell(
        self,
        painter: QPainter,
        rect: QRect,
        row: int,
        slot_index: int,
        slot: SpellSlot,
        radius: int,
        s: float,
        now: float,
    ) -> None:
        remaining = self._board.remaining(row, slot_index, now)
        on_cooldown = remaining > 0
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(rect), radius, radius)
        pixmap = None
        if slot.icon_file:
            icon_path = SPELLS_DIR / slot.icon_file
            pixmap = self._gray_pixmap(icon_path) if on_cooldown else self._pixmap(icon_path)
        painter.save()
        painter.setClipPath(clip)
        if pixmap is not None:
            painter.drawPixmap(rect, self._scaled_for_rect(pixmap, rect))
        else:
            painter.fillRect(rect, QColor(45, 45, 45, 200))
            font = QFont()
            font.setPixelSize(max(7, int(11 * s)))
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255, 220))
            painter.drawText(
                rect,
                int(Qt.AlignmentFlag.AlignCenter) | int(Qt.TextFlag.TextWordWrap),
                slot.display_name or "?",
            )
        if on_cooldown:
            painter.fillRect(rect, QColor(0, 0, 0, 150))
            text = fmt_mmss(remaining)
            font = QFont()
            font.setBold(True)
            font.setPixelSize(max(10, int(16 * s)))
            painter.setFont(font)
            painter.setPen(QColor(0, 0, 0, 200))
            painter.drawText(rect.adjusted(1, 1, 1, 1), int(Qt.AlignmentFlag.AlignCenter), text)
            painter.setPen(QColor(255, 255, 255, 235))
            painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), text)
        painter.restore()

    def mousePressEvent(self, event) -> None:
        pos = event.position().toPoint()
        if event.button() == Qt.MouseButton.LeftButton and self.lock_rect().contains(pos):
            self._toggle_lock()
            self.update()
            event.accept()
            return
        for row in range(len(self._enemies)):
            for col in (1, 2):
                if self.cell_rect(row, col).contains(pos):
                    self._handle_spell_click(row, col - 1, event.button())
                    event.accept()
                    return
        if event.button() == Qt.MouseButton.RightButton:
            for row in range(len(self._enemies)):
                if self.cell_rect(row, 0).contains(pos):
                    self._haste.toggle_insight(row)
                    self.update()
                    event.accept()
                    return
        if event.button() == Qt.MouseButton.LeftButton and not self._locked:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.drag_state_changed.emit(True)
            self.update()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._drag_offset is not None:
            self._drag_offset = None
            self._persist_position()
            self.drag_state_changed.emit(False)
            self.update()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:
        pos = event.position().toPoint()
        for row in range(len(self._enemies)):
            for col in (1, 2):
                if self.cell_rect(row, col).contains(pos):
                    if self._board.remaining(row, col - 1, self._monotonic()) > 0:
                        steps = event.angleDelta().y() / 120
                        self._board.adjust(row, col - 1, -5.0 * steps)
                        self.update()
                    event.accept()
                    return
        super().wheelEvent(event)

    def _handle_spell_click(self, row: int, slot_index: int, button) -> None:
        if button == Qt.MouseButton.RightButton:
            self._board.reset(row, slot_index)
            self.update()
            return
        if button != Qt.MouseButton.LeftButton:
            return
        enemy = self._enemies[row]
        slot = enemy.spells[slot_index]
        cooldown = self._cooldown_for(enemy, slot, row)
        if self._board.start(row, slot_index, cooldown, self._monotonic()):
            self.update()
        else:
            logger.debug("Ignored click on spell slot with unknown cooldown")

    def _cooldown_for(self, enemy: Enemy, slot: SpellSlot, row: int) -> float:
        game_time = self._board.game_now(self._monotonic()) or 0.0
        base = base_cooldown_for(slot.spell_id, slot.base_cooldown, enemy.level, game_time)
        cooldown = effective_cooldown(base, self._haste.haste(row))
        offset = float(self._config.get("click_cast_offset") or 0)
        return max(0.0, cooldown - offset)
