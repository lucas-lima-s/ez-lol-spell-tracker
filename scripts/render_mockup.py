import argparse
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QRectF, Qt  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QColor,
    QFont,
    QFontDatabase,
    QImage,
    QLinearGradient,
    QPainter,
)
from PySide6.QtWidgets import QApplication  # noqa: E402

from src.core.config import Config  # noqa: E402
from src.core.cooldowns import HasteTracker  # noqa: E402
from src.core.models import Enemy, SpellSlot  # noqa: E402
from src.core.timers import GameClock, SpellTimerBoard  # noqa: E402
from src.overlay.overlay_window import OverlayWindow  # noqa: E402
from src.riot.static_data import StaticData  # noqa: E402

FAKE_MONOTONIC = 1_000.0
FAKE_GAME_TIME = 900.0
PADDING = 48
LABEL_HEIGHT = 52
BACKDROP_TOP = QColor(0x10, 0x14, 0x18)
BACKDROP_BOTTOM = QColor(0x1B, 0x20, 0x27)
LABEL_TEXT = (
    "SYNTHETIC MOCKUP — rendered offscreen from the app's own widget, not a live game capture"
)

MOCK_ROSTER = (
    ("Annie", "SummonerFlash", "SummonerDot"),
    ("Ahri", "SummonerFlash", "SummonerTeleport"),
    ("Garen", "SummonerFlash", "SummonerHaste"),
    ("Lux", "SummonerFlash", "SummonerBarrier"),
    ("Teemo", "SummonerFlash", "SummonerExhaust"),
)

FIXED_TIMERS = (
    (0, 0, 252.0),
    (1, 1, 125.0),
    (4, 1, 37.0),
)

WINDOWS_FONTS_DIR = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
FONT_CANDIDATES = (
    WINDOWS_FONTS_DIR / "segoeui.ttf",
    WINDOWS_FONTS_DIR / "arial.ttf",
    WINDOWS_FONTS_DIR / "tahoma.ttf",
)


def _fake_monotonic() -> float:
    return FAKE_MONOTONIC


def _install_default_font(app: QApplication) -> None:
    for candidate in FONT_CANDIDATES:
        if not candidate.is_file():
            continue
        font_id = QFontDatabase.addApplicationFont(str(candidate))
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            app.setFont(QFont(families[0]))
            return


def _build_slot(static: StaticData, spell_id: str) -> SpellSlot:
    info = static.spell(spell_id)
    if info is None:
        return SpellSlot(spell_id=spell_id, display_name=spell_id, base_cooldown=0.0, icon_file="")
    return SpellSlot(
        spell_id=info.spell_id,
        display_name=info.name,
        base_cooldown=info.cooldown,
        icon_file=info.icon_file,
    )


def _build_roster(static: StaticData) -> list[Enemy]:
    enemies = []
    for champion, spell_one, spell_two in MOCK_ROSTER:
        info = static.champion_by_alias(champion)
        enemies.append(
            Enemy(
                champion_id=info.champion_id if info else champion,
                champion_name=info.name if info else champion,
                riot_id=f"{champion}#NA1",
                team="CHAOS",
                is_bot=True,
                spells=(_build_slot(static, spell_one), _build_slot(static, spell_two)),
            )
        )
    return enemies


def _compose(overlay_image: QImage, scale: float) -> QImage:
    canvas_width = overlay_image.width() + 2 * PADDING
    canvas_height = overlay_image.height() + 2 * PADDING + LABEL_HEIGHT
    canvas = QImage(canvas_width, canvas_height, QImage.Format.Format_ARGB32_Premultiplied)
    painter = QPainter(canvas)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient = QLinearGradient(0, 0, 0, canvas_height)
        gradient.setColorAt(0.0, BACKDROP_TOP)
        gradient.setColorAt(1.0, BACKDROP_BOTTOM)
        painter.fillRect(QRectF(0, 0, canvas_width, canvas_height), gradient)
        painter.drawImage(PADDING, PADDING, overlay_image)
        painter.setPen(QColor(255, 255, 255, 180))
        font = QFont()
        font.setPixelSize(max(9, int(10 * scale)))
        painter.setFont(font)
        label_rect = QRectF(8, canvas_height - LABEL_HEIGHT, canvas_width - 16, LABEL_HEIGHT - 6)
        flags = int(Qt.AlignmentFlag.AlignCenter) | int(Qt.TextFlag.TextWordWrap)
        painter.drawText(label_rect, flags, LABEL_TEXT)
    finally:
        painter.end()
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render a synthetic ez-spell-tracker overlay mockup"
    )
    parser.add_argument("--out", default="docs/overlay-mock.png")
    parser.add_argument("--scale", type=float, default=1.0)
    args = parser.parse_args()

    app = QApplication.instance() or QApplication(sys.argv[:1])
    _install_default_font(app)

    with tempfile.TemporaryDirectory(prefix="ezst-mockup-") as tmp_dir:
        config = Config(path=Path(tmp_dir) / "settings.json")
        static = StaticData()
        clock = GameClock()
        clock.ingest(FAKE_GAME_TIME, FAKE_MONOTONIC)
        board = SpellTimerBoard(clock)
        haste = HasteTracker()

        window = OverlayWindow(config, board, haste=haste, monotonic=_fake_monotonic)
        window.set_scale(args.scale)
        window.set_enemies(_build_roster(static))

        for row, slot, remaining in FIXED_TIMERS:
            board.start(row, slot, remaining, FAKE_MONOTONIC)

        haste.set_boots(1, True)
        haste.toggle_insight(3)

        overlay_image = QImage(window.size(), QImage.Format.Format_ARGB32_Premultiplied)
        overlay_image.fill(Qt.GlobalColor.transparent)
        window.render(overlay_image)

        final_image = _compose(overlay_image, args.scale)

        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if not final_image.save(str(out_path), "PNG"):
            print(f"Failed to save mockup to {out_path}", file=sys.stderr)
            return 1

    print(str(out_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
