import json

import pytest

from src.riot import ddragon

SUMMONER_PAYLOAD = {
    "data": {
        "SummonerFlash": {
            "id": "SummonerFlash",
            "name": "Flash",
            "cooldown": [300],
            "image": {"full": "SummonerFlash.png"},
        }
    }
}
CHAMPION_PAYLOAD = {
    "data": {
        "Annie": {"name": "Annie", "key": "1"},
        "Ahri": {"name": "Ahri", "key": "103"},
    }
}


class FakeResponse:
    def __init__(self, payload=None, content=b"png-bytes"):
        self._payload = payload
        self.content = content

    def json(self):
        return self._payload


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(ddragon, "CHAMPIONS_DIR", tmp_path / "champions")
    monkeypatch.setattr(ddragon, "SPELLS_DIR", tmp_path / "spells")
    monkeypatch.setattr(ddragon, "SUMMONER_DATA_FILE", tmp_path / "data" / "summoner.json")
    monkeypatch.setattr(ddragon, "CHAMPIONS_DATA_FILE", tmp_path / "data" / "champions.json")
    monkeypatch.setattr(ddragon, "DATA_VERSION_FILE", tmp_path / "data" / "version.txt")
    monkeypatch.setattr(ddragon, "RIOT_CERT_FILE", tmp_path / "certs" / "riotgames.pem")
    return tmp_path


def _fake_fetch(fail_urls=()):
    def fetch(url):
        if any(part in url for part in fail_urls):
            raise RuntimeError(f"Failed to GET {url}: HTTP 404")
        if url.endswith("/api/versions.json"):
            return FakeResponse(payload=["16.13.1", "16.12.1"])
        if url.endswith("summoner.json"):
            return FakeResponse(payload=SUMMONER_PAYLOAD)
        if url.endswith("champion.json"):
            return FakeResponse(payload=CHAMPION_PAYLOAD)
        return FakeResponse()

    return fetch


def test_fresh_update_downloads_everything(sandbox, monkeypatch):
    monkeypatch.setattr(ddragon, "fetch", _fake_fetch())
    report = ddragon.update_snapshot()
    assert report.complete
    assert report.refreshed
    assert report.downloaded == 3
    assert (sandbox / "champions" / "Annie.png").is_file()
    assert (sandbox / "spells" / "SummonerFlash.png").is_file()
    assert (sandbox / "certs" / "riotgames.pem").is_file()
    assert (sandbox / "data" / "version.txt").read_text(encoding="utf-8") == "16.13.1"
    saved = json.loads((sandbox / "data" / "champions.json").read_text(encoding="utf-8"))
    assert saved["data"]["Ahri"]["name"] == "Ahri"


def test_same_version_fills_missing_only(sandbox, monkeypatch):
    monkeypatch.setattr(ddragon, "fetch", _fake_fetch())
    ddragon.update_snapshot()
    (sandbox / "champions" / "Annie.png").unlink()
    report = ddragon.update_snapshot()
    assert report.complete
    assert not report.refreshed
    assert report.downloaded == 1
    assert (sandbox / "champions" / "Annie.png").is_file()


def test_failure_keeps_old_data_files(sandbox, monkeypatch):
    monkeypatch.setattr(ddragon, "fetch", _fake_fetch())
    ddragon.update_snapshot()
    monkeypatch.setattr(
        ddragon, "fetch", _fake_fetch(fail_urls=("img/champion/Ahri.png",))
    )
    (sandbox / "champions" / "Ahri.png").unlink()
    old_version = (sandbox / "data" / "version.txt").read_text(encoding="utf-8")
    report = ddragon.update_snapshot(force=True)
    assert not report.complete
    assert len(report.failures) == 1
    assert (sandbox / "data" / "version.txt").read_text(encoding="utf-8") == old_version


def test_pem_not_refetched_when_present(sandbox, monkeypatch):
    monkeypatch.setattr(ddragon, "fetch", _fake_fetch())
    ddragon.update_snapshot()
    monkeypatch.setattr(
        ddragon, "fetch", _fake_fetch(fail_urls=("riotgames.pem",))
    )
    report = ddragon.update_snapshot()
    assert report.complete


def test_should_stop_cancels_and_keeps_data_files(sandbox, monkeypatch):
    monkeypatch.setattr(ddragon, "fetch", _fake_fetch())
    report = ddragon.update_snapshot(should_stop=lambda: True)
    assert not report.complete
    assert "cancelled by shutdown" in report.failures
    assert not (sandbox / "data" / "version.txt").is_file()


def test_same_version_check_does_not_rewrite_data_files(sandbox, monkeypatch):
    monkeypatch.setattr(ddragon, "fetch", _fake_fetch())
    ddragon.update_snapshot()
    marker = sandbox / "data" / "summoner.json"
    marker.write_text("sentinel", encoding="utf-8")
    report = ddragon.update_snapshot()
    assert report.complete
    assert marker.read_text(encoding="utf-8") == "sentinel"
