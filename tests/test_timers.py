from src.core.timers import EXTRAPOLATION_CAP, GameClock, SpellTimerBoard


def test_clock_empty_returns_none():
    assert GameClock().now(10.0) is None


def test_clock_extrapolates_between_samples():
    clock = GameClock()
    clock.ingest(100.0, 50.0)
    assert clock.now(51.0) == 101.0


def test_clock_caps_extrapolation():
    clock = GameClock()
    clock.ingest(100.0, 50.0)
    assert clock.now(50.0 + EXTRAPOLATION_CAP + 20.0) == 100.0 + EXTRAPOLATION_CAP


def test_clock_freezes_on_pause():
    clock = GameClock()
    clock.ingest(100.0, 50.0)
    clock.ingest(100.0, 52.0)
    assert clock.paused
    assert clock.now(55.0) == 100.0


def test_clock_resumes_after_pause():
    clock = GameClock()
    clock.ingest(100.0, 50.0)
    clock.ingest(100.0, 52.0)
    clock.ingest(103.0, 54.0)
    assert not clock.paused
    assert clock.now(55.0) == 104.0


def test_clock_rapid_ingest_does_not_flag_pause():
    clock = GameClock()
    clock.ingest(100.0, 50.0)
    clock.ingest(100.0, 50.5)
    assert not clock.paused


def test_clock_backwards_game_time_freezes_then_reanchors():
    clock = GameClock()
    clock.ingest(100.0, 50.0)
    clock.ingest(90.0, 52.0)
    assert clock.paused
    assert clock.now(53.0) == 90.0
    clock.ingest(93.0, 54.0)
    assert not clock.paused


def test_clock_reset():
    clock = GameClock()
    clock.ingest(100.0, 50.0)
    clock.reset()
    assert clock.now(51.0) is None


def test_board_start_and_countdown():
    clock = GameClock()
    clock.ingest(100.0, 50.0)
    board = SpellTimerBoard(clock)
    assert board.start(0, 0, 300.0, 50.0)
    assert board.remaining(0, 0, 50.0) == 300.0
    assert board.remaining(0, 0, 60.0) == 290.0


def test_board_remaining_freezes_during_pause():
    clock = GameClock()
    clock.ingest(100.0, 50.0)
    board = SpellTimerBoard(clock)
    board.start(0, 0, 300.0, 50.0)
    clock.ingest(100.0, 52.0)
    assert board.remaining(0, 0, 55.0) == 300.0


def test_board_expiry_returns_zero():
    clock = GameClock()
    clock.ingest(100.0, 50.0)
    board = SpellTimerBoard(clock)
    board.start(0, 1, 5.0, 50.0)
    clock.ingest(106.0, 56.0)
    assert board.remaining(0, 1, 56.0) == 0.0
    assert board.remaining(0, 1, 56.0) == 0.0


def test_board_timer_resurrects_when_clock_snaps_back():
    clock = GameClock()
    clock.ingest(100.0, 50.0)
    board = SpellTimerBoard(clock)
    board.start(0, 0, 5.0, 50.0)
    assert board.remaining(0, 0, 57.0) == 0.0
    clock.ingest(100.0, 58.0)
    assert clock.paused
    assert board.remaining(0, 0, 58.0) == 5.0


def test_board_reset_mid_cooldown():
    clock = GameClock()
    clock.ingest(100.0, 50.0)
    board = SpellTimerBoard(clock)
    board.start(2, 1, 300.0, 50.0)
    board.reset(2, 1)
    assert board.remaining(2, 1, 51.0) == 0.0


def test_board_rejects_zero_cooldown():
    clock = GameClock()
    clock.ingest(100.0, 50.0)
    board = SpellTimerBoard(clock)
    assert not board.start(0, 0, 0.0, 50.0)
    assert board.remaining(0, 0, 50.0) == 0.0


def test_board_rejects_empty_clock():
    board = SpellTimerBoard(GameClock())
    assert not board.start(0, 0, 300.0, 50.0)


def test_board_clear():
    clock = GameClock()
    clock.ingest(100.0, 50.0)
    board = SpellTimerBoard(clock)
    board.start(0, 0, 300.0, 50.0)
    board.start(1, 1, 200.0, 50.0)
    board.clear()
    assert board.remaining(0, 0, 51.0) == 0.0
    assert board.remaining(1, 1, 51.0) == 0.0
