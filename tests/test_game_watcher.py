from src.app.game_watcher import END_CONFIRM_TICKS, GameWatcher
from src.riot.live_client import NotInGameError, TransientApiError
from tests.conftest import load_fixture

STATS = {"gameMode": "PRACTICETOOL", "gameTime": 12.34}


class FakeClient:
    def __init__(self):
        self.stats_results = []
        self.data_results = []

    def get_game_stats(self):
        return self._next(self.stats_results)

    def get_all_game_data(self):
        return self._next(self.data_results)

    @staticmethod
    def _next(queue):
        result = queue.pop(0) if queue else NotInGameError("nothing scheduled")
        if isinstance(result, Exception):
            raise result
        return result


def _watcher(fixture_static, client):
    watcher = GameWatcher(client=client, static=fixture_static)
    started = []
    ended = []
    watcher.game_started.connect(started.append)
    watcher.game_ended.connect(lambda: ended.append(True))
    return watcher, started, ended


def test_in_game_tick_emits_game_time(qapp, fixture_static):
    client = FakeClient()
    client.stats_results = [STATS]
    client.data_results = [load_fixture("allgamedata_ptbr.json")]
    watcher = GameWatcher(client=client, static=fixture_static)
    times = []
    watcher.game_time.connect(times.append)
    watcher._tick()
    watcher._tick()
    assert times == []
    client.stats_results = [STATS, {"gameMode": "X"}]
    watcher._tick()
    assert times == [STATS["gameTime"]]
    watcher._tick()
    assert times == [STATS["gameTime"]]


def test_loading_with_game_data_emits_game_time_after_started(qapp, fixture_static):
    client = FakeClient()
    client.stats_results = [STATS]
    payload = load_fixture("allgamedata_ptbr.json")
    payload["gameData"] = {"gameTime": 7.5}
    client.data_results = [payload]
    watcher = GameWatcher(client=client, static=fixture_static)
    order = []
    watcher.game_time.connect(lambda value: order.append(("time", value)))
    watcher.game_started.connect(lambda enemies: order.append(("started", len(enemies))))
    watcher._tick()
    watcher._tick()
    assert order == [("started", 5), ("time", 7.5)]


def test_roster_refresh_emitted_periodically(qapp, fixture_static):
    from src.app.game_watcher import ROSTER_REFRESH_TICKS

    client = FakeClient()
    client.stats_results = [STATS]
    client.data_results = [load_fixture("allgamedata_ptbr.json")]
    watcher = GameWatcher(client=client, static=fixture_static)
    rosters = []
    watcher.roster_updated.connect(rosters.append)
    watcher._tick()
    watcher._tick()
    client.stats_results = [STATS] * (ROSTER_REFRESH_TICKS + 1)
    client.data_results = [load_fixture("allgamedata_ptbr.json")]
    for _tick in range(ROSTER_REFRESH_TICKS - 1):
        watcher._tick()
    assert rosters == []
    watcher._tick()
    assert len(rosters) == 1
    assert len(rosters[0]) == 5


def test_rising_edge_emits_game_started_once(qapp, fixture_static):
    client = FakeClient()
    client.stats_results = [STATS]
    client.data_results = [load_fixture("allgamedata_ptbr.json")]
    watcher, started, ended = _watcher(fixture_static, client)
    watcher._tick()
    assert started == []
    watcher._tick()
    assert len(started) == 1
    assert len(started[0]) == 5
    client.stats_results = [STATS, STATS]
    watcher._tick()
    watcher._tick()
    assert len(started) == 1
    assert ended == []


def test_roster_not_ready_retries_until_success(qapp, fixture_static):
    client = FakeClient()
    client.stats_results = [STATS]
    client.data_results = [
        load_fixture("allgamedata_loading.json"),
        load_fixture("allgamedata_loading.json"),
        load_fixture("allgamedata_ptbr.json"),
    ]
    watcher, started, _ = _watcher(fixture_static, client)
    for _tick in range(4):
        watcher._tick()
    assert len(started) == 1


def test_transient_error_while_loading_retries(qapp, fixture_static):
    client = FakeClient()
    client.stats_results = [STATS]
    client.data_results = [
        TransientApiError("loading screen"),
        load_fixture("allgamedata_ptbr.json"),
    ]
    watcher, started, _ = _watcher(fixture_static, client)
    for _tick in range(3):
        watcher._tick()
    assert len(started) == 1


def test_game_end_requires_consecutive_failures(qapp, fixture_static):
    client = FakeClient()
    client.stats_results = [STATS]
    client.data_results = [load_fixture("allgamedata_ptbr.json")]
    watcher, started, ended = _watcher(fixture_static, client)
    watcher._tick()
    watcher._tick()
    client.stats_results = [
        NotInGameError("hiccup"),
        STATS,
        NotInGameError("gone"),
        NotInGameError("gone"),
    ]
    watcher._tick()
    assert ended == []
    watcher._tick()
    assert ended == []
    for _tick in range(END_CONFIRM_TICKS):
        watcher._tick()
    assert len(ended) == 1
    assert len(started) == 1


def test_no_game_ended_without_game_started(qapp, fixture_static):
    client = FakeClient()
    client.stats_results = [STATS]
    client.data_results = [NotInGameError("vanished")]
    watcher, started, ended = _watcher(fixture_static, client)
    watcher._tick()
    watcher._tick()
    for _tick in range(3):
        watcher._tick()
    assert started == []
    assert ended == []


def test_empty_roster_still_emits_game_started(qapp, fixture_static):
    client = FakeClient()
    client.stats_results = [STATS]
    client.data_results = [load_fixture("allgamedata_sample.json")]
    watcher, started, _ = _watcher(fixture_static, client)
    watcher._tick()
    watcher._tick()
    assert started == [[]]


def test_transient_error_does_not_reset_end_counter(qapp, fixture_static):
    client = FakeClient()
    client.stats_results = [STATS]
    client.data_results = [load_fixture("allgamedata_ptbr.json")]
    watcher, _, ended = _watcher(fixture_static, client)
    watcher._tick()
    watcher._tick()
    client.stats_results = [
        NotInGameError("gone"),
        TransientApiError("hiccup"),
        NotInGameError("gone"),
    ]
    watcher._tick()
    watcher._tick()
    assert ended == []
    watcher._tick()
    assert len(ended) == 1


def test_stop_unblocks_run_quickly(qapp, fixture_static):
    watcher = GameWatcher(client=FakeClient(), static=fixture_static)
    watcher.start()
    watcher.stop()
    assert watcher.wait(2000)


def test_run_survives_unexpected_errors(qapp, fixture_static):
    class ExplodingClient:
        def get_game_stats(self):
            raise ValueError("boom")

        def get_all_game_data(self):
            raise ValueError("boom")

    watcher = GameWatcher(client=ExplodingClient(), static=fixture_static)
    watcher.start()
    assert not watcher.wait(150)
    assert watcher.isRunning()
    watcher.stop()
    assert watcher.wait(2000)
