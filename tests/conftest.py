import json
import logging
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def close_top_level_widgets():
    yield
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is not None:
        for widget in QApplication.topLevelWidgets():
            widget.close()


@pytest.fixture(autouse=True)
def restore_root_logger():
    root = logging.getLogger()
    level = root.level
    yield
    for handler in [h for h in root.handlers if getattr(h, "_ezst_managed", False)]:
        root.removeHandler(handler)
        handler.close()
    root.setLevel(level)


@pytest.fixture
def fixture_static():
    from src.riot.static_data import StaticData

    return StaticData(
        summoner_file=FIXTURES_DIR / "static" / "summoner.json",
        champions_file=FIXTURES_DIR / "static" / "champions.json",
    )


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))
