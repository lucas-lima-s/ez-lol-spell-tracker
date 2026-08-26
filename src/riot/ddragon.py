import json
import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import requests

from src.core.paths import (
    CHAMPIONS_DATA_FILE,
    CHAMPIONS_DIR,
    DATA_VERSION_FILE,
    RIOT_CERT_FILE,
    SPELLS_DIR,
    SUMMONER_DATA_FILE,
)

logger = logging.getLogger(__name__)

DDRAGON_BASE = "https://ddragon.leagueoflegends.com"
PEM_URL = "https://static.developer.riotgames.com/docs/lol/riotgames.pem"
TIMEOUT = 10
RETRIES = 3


@dataclass(slots=True)
class UpdateReport:
    version: str
    refreshed: bool
    downloaded: int = 0
    failures: list[str] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return not self.failures


def fetch(url: str) -> requests.Response:
    last_error = ""
    for attempt in range(RETRIES):
        try:
            response = requests.get(url, timeout=TIMEOUT)
            if response.ok:
                return response
            last_error = f"HTTP {response.status_code}"
        except requests.RequestException as exc:
            last_error = str(exc)
        time.sleep(0.6 * (attempt + 1))
    raise RuntimeError(f"Failed to GET {url}: {last_error}")


def write_bytes(dest: Path, content: bytes) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    with open(part, "wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(part, dest)


def download(url: str, dest: Path, force: bool) -> bool:
    if dest.is_file() and not force:
        return False
    write_bytes(dest, fetch(url).content)
    return True


def cached_version() -> str:
    if DATA_VERSION_FILE.is_file():
        return DATA_VERSION_FILE.read_text(encoding="utf-8").strip()
    return ""


def update_snapshot(
    lang: str = "pt_BR",
    force: bool = False,
    should_stop: Callable[[], bool] | None = None,
) -> UpdateReport:
    version = fetch(f"{DDRAGON_BASE}/api/versions.json").json()[0]
    refresh = force or cached_version() != version
    report = UpdateReport(version=version, refreshed=refresh)

    summoner = fetch(f"{DDRAGON_BASE}/cdn/{version}/data/{lang}/summoner.json").json()
    champions = fetch(f"{DDRAGON_BASE}/cdn/{version}/data/{lang}/champion.json").json()
    slim = {
        "version": version,
        "data": {
            champion_id: {
                "name": entry.get("name", champion_id),
                "key": entry.get("key", ""),
            }
            for champion_id, entry in champions.get("data", {}).items()
        },
    }

    targets = [
        (
            f"{DDRAGON_BASE}/cdn/{version}/img/champion/{champion_id}.png",
            CHAMPIONS_DIR / f"{champion_id}.png",
        )
        for champion_id in slim["data"]
    ]
    for entry in summoner.get("data", {}).values():
        spell_id = entry["id"]
        icon = entry.get("image", {}).get("full") or f"{spell_id}.png"
        targets.append(
            (f"{DDRAGON_BASE}/cdn/{version}/img/spell/{icon}", SPELLS_DIR / f"{spell_id}.png")
        )

    for url, dest in targets:
        if should_stop is not None and should_stop():
            report.failures.append("cancelled by shutdown")
            break
        try:
            if download(url, dest, refresh):
                report.downloaded += 1
        except (RuntimeError, OSError) as exc:
            report.failures.append(str(exc))

    if report.failures:
        logger.warning(
            "Snapshot update incomplete: %d failures, data files not updated",
            len(report.failures),
        )
        return report

    if force or not RIOT_CERT_FILE.is_file():
        write_bytes(RIOT_CERT_FILE, fetch(PEM_URL).content)
    if not refresh:
        return report

    write_bytes(
        SUMMONER_DATA_FILE,
        json.dumps(summoner, ensure_ascii=False, indent=2).encode("utf-8"),
    )
    write_bytes(
        CHAMPIONS_DATA_FILE,
        json.dumps(slim, ensure_ascii=False, indent=2).encode("utf-8"),
    )
    write_bytes(DATA_VERSION_FILE, version.encode("utf-8"))
    logger.info(
        "Snapshot updated to %s (%d files downloaded)", version, report.downloaded
    )
    return report
