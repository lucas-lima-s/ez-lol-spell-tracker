import logging
import logging.handlers
import sys
from pathlib import Path

from src.core.paths import LOGS_DIR

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def setup_logging(
    level: str = "INFO",
    max_bytes: int = 1_048_576,
    backup_count: int = 5,
    logs_dir: Path = LOGS_DIR,
) -> None:
    root = logging.getLogger()
    for handler in [h for h in root.handlers if getattr(h, "_ezst_managed", False)]:
        root.removeHandler(handler)
        handler.close()
    logs_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(LOG_FORMAT)
    file_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "app.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    setattr(file_handler, "_ezst_managed", True)
    root.addHandler(file_handler)
    if sys.stderr is not None:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        setattr(console_handler, "_ezst_managed", True)
        root.addHandler(console_handler)
    root.setLevel(level)
