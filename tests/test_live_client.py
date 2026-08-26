from unittest.mock import Mock

import pytest
import requests

from src.core.paths import RIOT_CERT_FILE
from src.riot.live_client import (
    CONNECT_TIMEOUT,
    READ_TIMEOUT,
    LiveClient,
    NotInGameError,
    TransientApiError,
)
from src.riot.parser import (
    RosterNotReady,
    extract_champion_alias,
    extract_enemies,
    extract_spell_id,
)
from src.riot.static_data import StaticData
from tests.conftest import load_fixture


def _client(session):
    return LiveClient(session=session, cert_file=RIOT_CERT_FILE)


def _response(status=200, payload=None):
    response = Mock()
    response.status_code = status
    response.json.return_value = payload if payload is not None else {}
    return response


def test_get_uses_pinned_cert_and_timeouts():
    session = Mock(spec=requests.Session)
    stats = load_fixture("gamestats.json")
    session.get.return_value = _response(payload=stats)
    client = _client(session)
    assert client.get_game_stats() == stats
    kwargs = session.get.call_args.kwargs
    assert kwargs["verify"] == str(RIOT_CERT_FILE)
    assert kwargs["timeout"] == (CONNECT_TIMEOUT, READ_TIMEOUT)


def test_default_session_ignores_proxy_env():
    client = LiveClient(cert_file=RIOT_CERT_FILE)
    assert client._session.trust_env is False


def test_connection_error_maps_to_not_in_game():
    session = Mock(spec=requests.Session)
    session.get.side_effect = requests.exceptions.ConnectionError("refused")
    with pytest.raises(NotInGameError):
        _client(session).get_game_stats()


def test_connect_timeout_maps_to_transient():
    session = Mock(spec=requests.Session)
    session.get.side_effect = requests.exceptions.ConnectTimeout("slow connect")
    with pytest.raises(TransientApiError):
        _client(session).get_game_stats()


def test_other_request_exceptions_map_to_transient():
    session = Mock(spec=requests.Session)
    session.get.side_effect = requests.exceptions.ChunkedEncodingError("broken body")
    with pytest.raises(TransientApiError):
        _client(session).get_all_game_data()


def test_ssl_error_maps_to_transient():
    session = Mock(spec=requests.Session)
    session.get.side_effect = requests.exceptions.SSLError("bad cert")
    with pytest.raises(TransientApiError):
        _client(session).get_game_stats()


def test_read_timeout_maps_to_transient():
    session = Mock(spec=requests.Session)
    session.get.side_effect = requests.exceptions.ReadTimeout("slow")
    with pytest.raises(TransientApiError):
        _client(session).get_game_stats()


def test_non_200_maps_to_transient():
    session = Mock(spec=requests.Session)
    session.get.return_value = _response(status=404)
    with pytest.raises(TransientApiError):
        _client(session).get_all_game_data()


def test_invalid_json_maps_to_transient():
    session = Mock(spec=requests.Session)
    response = _response()
    response.json.side_effect = ValueError("not json")
    session.get.return_value = response
    with pytest.raises(TransientApiError):
        _client(session).get_game_stats()


def test_missing_cert_fails_fast(tmp_path):
    with pytest.raises(FileNotFoundError):
        LiveClient(cert_file=tmp_path / "missing.pem")


def test_is_in_game_mapping():
    session = Mock(spec=requests.Session)
    session.get.return_value = _response(payload={})
    assert _client(session).is_in_game() is True
    session.get.side_effect = requests.exceptions.ConnectionError("refused")
    assert _client(session).is_in_game() is False


def test_static_data_loads_fixture(fixture_static):
    flash = fixture_static.spell("SummonerFlash")
    assert flash is not None
    assert flash.cooldown == 300.0
    assert flash.icon_file == "SummonerFlash.png"
    assert fixture_static.champion_by_alias("fiddlesticks") is not None
    assert fixture_static.champion_by_alias("FiddleSticks").champion_id == "Fiddlesticks"


def test_static_data_spell_ids_sorted_longest_first(fixture_static):
    lengths = [len(spell_id) for spell_id in fixture_static.spell_ids]
    assert lengths == sorted(lengths, reverse=True)


def test_committed_snapshot_is_usable():
    static = StaticData()
    flash = static.spell("SummonerFlash")
    assert flash is not None
    assert flash.cooldown == 300.0
    assert static.champion_by_alias("Fiddlesticks") is not None
    assert static.champion_by_alias("MonkeyKing").name == "Wukong"


def test_extract_spell_id_exact_match(fixture_static):
    raw = "GeneratedTip_SummonerSpell_SummonerFlash_DisplayName"
    assert extract_spell_id(raw, fixture_static.spell_ids) == "SummonerFlash"


def test_extract_spell_id_upgrade_falls_back_to_base(fixture_static):
    raw = "GeneratedTip_SummonerSpell_S12_SummonerTeleportUpgrade_DisplayName"
    assert extract_spell_id(raw, fixture_static.spell_ids) == "SummonerTeleport"


def test_extract_spell_id_hexflash_falls_back_to_flash(fixture_static):
    raw = "GeneratedTip_SummonerSpell_SummonerFlashPerksHextechFlashtraptionV2_DisplayName"
    assert extract_spell_id(raw, fixture_static.spell_ids) == "SummonerFlash"


def test_extract_spell_id_unknown_returns_none(fixture_static):
    raw = "GeneratedTip_SummonerSpell_SummonerWeirdNew_DisplayName"
    assert extract_spell_id(raw, fixture_static.spell_ids) is None


def test_extract_champion_alias():
    assert extract_champion_alias("game_character_displayname_FiddleSticks") == "FiddleSticks"
    assert extract_champion_alias("unexpected") is None
    assert extract_champion_alias("") is None


def test_extract_enemies_ptbr_fixture(fixture_static):
    enemies = extract_enemies(load_fixture("allgamedata_ptbr.json"), fixture_static)
    assert [e.champion_id for e in enemies] == [
        "Fiddlesticks",
        "MonkeyKing",
        "Ziggs",
        "Sett",
        "Brand",
    ]
    assert enemies[1].champion_name == "Wukong"
    assert all(e.team == "CHAOS" for e in enemies)
    assert all(e.is_bot for e in enemies)
    assert enemies[0].riot_id == "Fiddle Bot#BOT"
    assert [s.spell_id for s in enemies[0].spells] == ["SummonerFlash", "SummonerDot"]
    assert [s.spell_id for s in enemies[1].spells] == ["SummonerTeleport", "SummonerSmite"]
    assert [s.spell_id for s in enemies[2].spells] == ["SummonerFlash", "SummonerHeal"]
    assert [s.spell_id for s in enemies[3].spells] == ["SummonerHaste", "SummonerExhaust"]
    assert enemies[0].spells[0].base_cooldown == 300.0
    assert enemies[1].spells[1].base_cooldown == 15.0
    assert enemies[0].level == 12
    assert enemies[0].item_ids == (3158, 1052)
    assert enemies[1].item_ids == ()


def test_extract_enemies_unknown_spell_degrades(fixture_static):
    enemies = extract_enemies(load_fixture("allgamedata_ptbr.json"), fixture_static)
    degraded = enemies[4].spells[1]
    assert degraded.spell_id == ""
    assert degraded.display_name == "Magia Nova"
    assert degraded.base_cooldown == 0.0
    assert degraded.icon_file == ""


def test_extract_enemies_unknown_champion_degrades(fixture_static):
    data = load_fixture("allgamedata_ptbr.json")
    data["allPlayers"][1]["rawChampionName"] = "game_character_displayname_BrandNewChamp"
    data["allPlayers"][1]["championName"] = "Campeão Novo"
    enemies = extract_enemies(data, fixture_static)
    assert enemies[0].champion_id == ""
    assert enemies[0].champion_name == "Campeão Novo"
    assert len(enemies) == 5


def test_extract_enemies_official_sample_has_no_enemies(fixture_static):
    enemies = extract_enemies(load_fixture("allgamedata_sample.json"), fixture_static)
    assert enemies == []


def test_extract_enemies_empty_roster_raises(fixture_static):
    with pytest.raises(RosterNotReady):
        extract_enemies(load_fixture("allgamedata_loading.json"), fixture_static)


def test_extract_enemies_unmatched_active_player_raises(fixture_static):
    data = load_fixture("allgamedata_ptbr.json")
    data["activePlayer"] = {"riotId": "Stranger#XX1", "summonerName": "Stranger"}
    with pytest.raises(RosterNotReady):
        extract_enemies(data, fixture_static)


def test_extract_enemies_matches_by_summoner_name_only(fixture_static):
    data = load_fixture("allgamedata_ptbr.json")
    data["activePlayer"] = {"summonerName": "Summoner"}
    enemies = extract_enemies(data, fixture_static)
    assert len(enemies) == 5


def test_extract_enemies_riot_id_beats_summoner_name_collision(fixture_static):
    data = load_fixture("allgamedata_ptbr.json")
    impostor = {
        "riotId": "Summoner#NA2",
        "summonerName": "Summoner",
        "championName": "Brand",
        "rawChampionName": "game_character_displayname_Brand",
        "team": "CHAOS",
        "isBot": False,
        "summonerSpells": {},
    }
    data["allPlayers"].insert(0, impostor)
    enemies = extract_enemies(data, fixture_static)
    assert all(e.team == "CHAOS" for e in enemies)
    assert len(enemies) == 6


def test_extract_enemies_skips_players_without_team(fixture_static):
    data = load_fixture("allgamedata_ptbr.json")
    data["allPlayers"].append({"riotId": "Ghost#XX1", "summonerName": "Ghost"})
    data["allPlayers"].append({"riotId": "Null#XX1", "team": None})
    enemies = extract_enemies(data, fixture_static)
    assert len(enemies) == 5


def test_extract_enemies_null_values_stay_strings(fixture_static):
    data = load_fixture("allgamedata_ptbr.json")
    enemy = data["allPlayers"][4]
    enemy["championName"] = None
    enemy["rawChampionName"] = "game_character_displayname_BrandNewChamp"
    enemy["summonerSpells"]["summonerSpellOne"]["displayName"] = None
    enemy["summonerSpells"]["summonerSpellOne"]["rawDisplayName"] = "Unknown_Raw"
    enemies = extract_enemies(data, fixture_static)
    degraded = enemies[3]
    assert degraded.champion_name == ""
    assert degraded.spells[0].display_name == ""
