import logging
import logging.handlers

from src.core.log_setup import setup_logging


def _managed_handlers():
    return [h for h in logging.getLogger().handlers if getattr(h, "_ezst_managed", False)]


def test_file_handler_configuration(tmp_path):
    setup_logging(logs_dir=tmp_path)
    file_handlers = [
        h for h in _managed_handlers() if isinstance(h, logging.handlers.RotatingFileHandler)
    ]
    assert len(file_handlers) == 1
    handler = file_handlers[0]
    assert handler.maxBytes == 1_048_576
    assert handler.backupCount == 5
    assert handler.encoding == "utf-8"
    assert handler.baseFilename.endswith("app.log")


def test_reconfigure_does_not_duplicate_handlers(tmp_path):
    setup_logging(logs_dir=tmp_path)
    count = len(_managed_handlers())
    assert count >= 1
    setup_logging(logs_dir=tmp_path)
    assert len(_managed_handlers()) == count


def test_rotation(tmp_path):
    setup_logging(level="INFO", max_bytes=200, backup_count=2, logs_dir=tmp_path)
    logger = logging.getLogger("rotation-test")
    for _ in range(50):
        logger.info("x" * 40)
    assert (tmp_path / "app.log.1").is_file()
