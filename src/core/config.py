import copy
import json
import logging
import os
from pathlib import Path
from typing import Any

from src.core.paths import SETTINGS_FILE

logger = logging.getLogger(__name__)

DEFAULTS: dict[str, Any] = {
    "schemaVersion": 1,
    "logLevel": "INFO",
    "language": "pt-BR",
    "overlay": {
        "opacity": 0.9,
        "locked": False,
        "hide_from_capture": False,
        "profiles": {},
    },
    "start_with_windows": False,
    "hotkey_toggle_overlay": "F8",
    "click_cast_offset": 0,
}


def _deep_merge(base: dict, override: dict) -> dict:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


class Config:
    def __init__(self, path: Path = SETTINGS_FILE) -> None:
        self._path = path
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        if not self._path.is_file():
            return copy.deepcopy(DEFAULTS)
        try:
            content = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(content, dict):
                raise ValueError("settings root must be a JSON object")
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            logger.warning("Settings file corrupt, falling back to defaults: %s", exc)
            self._backup_corrupt()
            return copy.deepcopy(DEFAULTS)
        return _deep_merge(DEFAULTS, content)

    def _backup_corrupt(self) -> None:
        try:
            self._path.replace(self._path.with_suffix(".json.bak"))
        except OSError as exc:
            logger.warning("Could not back up corrupt settings file: %s", exc)

    def save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self._path.with_suffix(".json.tmp")
            tmp_path.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            os.replace(tmp_path, self._path)
        except OSError as exc:
            logger.warning("Could not save settings: %s", exc)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()
