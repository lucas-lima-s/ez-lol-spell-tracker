# Architecture audit

Every claim below was verified by reading the referenced file. Line numbers reflect the tree
after the ruff-format pass that shipped alongside this audit.

## Strengths

1. **Strict layer direction, enforced by imports.** `src/core/*` and `src/riot/*` import zero
   PySide6; only `src/overlay/*` and `src/app/*` do. Verified: `grep -rl PySide6 src/core
   src/riot` returns nothing. This is exactly why 158 test functions (187 with parametrize) run
   headless.

2. **Timers anchored to game time, not wall clock.** `src/core/timers.py:6-33` --
   `GameClock.ingest(game_time, monotonic_now)` stores both clocks; `SpellTimerBoard` stores
   expiries in *game* seconds. Pause detection (`PAUSE_EPSILON=0.05`, `MIN_PAUSE_GAP=1.0`,
   `src/core/timers.py:1-2`) freezes `now()`, and `EXTRAPOLATION_CAP=10.0`
   (`src/core/timers.py:3`) bounds drift when polls are missed. This survives Practice Tool
   pauses and reconnects -- the single best decision in the codebase.

3. **Locale independence by construction.** `src/riot/parser.py:18-27` resolves spells from
   `rawDisplayName` (`GeneratedTip_SummonerSpell_<Id>_DisplayName`) and champions from
   `rawChampionName` (`game_character_displayname_<Alias>`, `src/riot/parser.py:30-34`), never
   from the localized `displayName`. Proven against a real Portuguese-client capture in
   `tests/fixtures/allgamedata_ptbr.json`.

4. **TLS pinning instead of `verify=False`.** `src/riot/live_client.py:50` passes
   `verify=str(self._cert_file)` against the bundled Riot certificate, and warns exactly once on
   rotation (`_ssl_warned`, `src/riot/live_client.py:42,52-61`). Almost every other project
   talking to `127.0.0.1:2999` disables verification outright.

5. **Atomic persistence everywhere.** `Config.save` (`src/core/config.py:62-71`) writes
   `.json.tmp` then `os.replace`; `ddragon.write_bytes` (`src/riot/ddragon.py:54-61`) writes
   `.part`, `fsync`s, then `os.replace`. Corrupt settings are moved to `.json.bak` and defaults
   restored (`src/core/config.py:43-60`).

6. **Correct Qt threading.** `GameWatcher` (`src/app/game_watcher.py`) and `AssetUpdateWorker`
   are `QThread`s that only emit signals; no widget is touched off the GUI thread. Shutdown is
   cooperative and bounded (`src/main.py:65,71`, `wait(5000)` / `wait(15000)`), and the download
   loop takes a `should_stop` callback (`src/riot/ddragon.py:77-121`).

7. **Deliberate non-scope with recorded reasons** -- no memory reads, no DLL injection, no
   DirectX hooks, no ultimate tracking, no ads. The policy analysis is part of the design rather
   than an afterthought (`docs/DESIGN.md`, "Non-scope" table).

8. **Test doubles over blanket mocking.** `tests/qt_fakes.py` (`FakeHotkey`), real captured JSON
   fixtures, and `monotonic` injected as a constructor parameter into `OverlayController`
   (`src/overlay/controller.py:38`) and `OverlayWindow` (`src/overlay/overlay_window.py:66`)
   give deterministic time without `freezegun`.

## Risks and debts

All twelve are reported; none are fixed except where noted below.

1. **Wrong-row haste badges (correctness).** `src/overlay/overlay_window.py:339` --
   `_paint_champion` recovers its row with `self._enemies.index(enemy)` even though `paintEvent`
   already holds `row` as the loop variable. `Enemy` is a frozen dataclass, so equality is by
   value: two rows with identical field values resolve to the first index. Reachable today in
   preview mode, where `_build_preview_enemies` gives all five entries `riot_id="preview"` -- a
   duplicated champion would paint both rows' badges on the first one. One-line fix (thread
   `row` down) but out of scope here: the top debt.

2. **Roster-guard keyed on a field that can be empty.** `src/overlay/controller.py:97-104`
   protects running timers by comparing `riot_id` lists. `src/riot/parser.py:81` falls back
   `riotId -> summonerName -> ""`; if both are absent for every player, all five keys collapse
   to `""` and a genuine roster reorder passes the guard.

3. **`assert` as a shipping control-flow guarantee.** `src/riot/parser.py:112` -- under
   `python -O` the assert is stripped and the next line raises `AttributeError`. Unreachable
   today (`StaticData.spell_ids` and `StaticData.spell` are built from the same dict) but it is
   an assert doing real work.

4. **Load-bearing coupling across modules with no home for the rationale.**
   `extract_spell_id` (`src/riot/parser.py:18-27`) falls back to a substring scan over all known
   ids; determinism depends entirely on `StaticData.__init__` pre-sorting `_spell_ids`
   longest-first (`src/riot/static_data.py:31`) so `SummonerSmite` is tried before any shorter id
   that is a substring. The project bans code comments, so this contract now lives in
   `docs/DESIGN.md` ("Non-obvious invariants").

5. **`LOADING` state has no timeout.** `src/app/game_watcher.py:78-99` --
   `GameWatcher._tick_loading` warns once at 30 polls (`ROSTER_WARN_TICKS=30`,
   `src/app/game_watcher.py:15`, at a 2s poll interval that is 60s) and then loops forever.
   Spectator mode is the known trigger.

6. **Writable state is `PROJECT_ROOT`-relative.** `src/core/paths.py:4-10` puts `config/` and
   `logs/` next to the executable. Correct for a portable onedir release; it breaks the day
   there is an installer writing under `Program Files`.

7. **`i18n`-shaped API with no i18n.** `src/app/strings.py` is a single hardcoded
   Brazilian-Portuguese table behind `tr(key)`, while `config["language"]` exists and is used
   only to pick the Data Dragon locale (`src/main.py:99`). The naming promises a locale
   dimension that does not exist.

8. **Silent Win32 failures.** Every function in `src/overlay/win32.py` swallows exceptions into
   `return False` with no logging, so a permanently failing `SetWindowDisplayAffinity` is
   indistinguishable from "unsupported on this Windows build". The settings UI already handles
   the unsupported path, so this is acceptable but undiagnosable.

9. **Thread-affine global hotkey.** `src/overlay/hotkey.py:88-91` calls
   `RegisterHotKey(None, ...)`, which binds the hotkey to the *calling thread*; `unregister`
   must run on the same thread. It does today (both calls come from the GUI thread) but nothing
   enforces it.

10. **Vendored 689 MB `lib/`, no lockfile.** `build_environment.bat` runs `pip install --target
    lib`. Correct for the "no venv, double-click a .bat" goal and correctly gitignored
    (`git ls-files` has zero entries under `lib/`, `build/`, `dist/`, verified), but the only
    pinning used to be `requirements.txt` hand-maintained by hand. This is fixed in this pass:
    `pyproject.toml` plus `uv.lock` are now the source of truth, and `requirements.txt` is
    generated from the lock (see the publication audit).

11. **Test-runner traps (measured, not theorised).** From the repo root: bare `pytest` used to
    collect `lib/` -- 623 tests collected, 36 collection errors. And with `PYTHONSAFEPATH=1`
    (which is what the `pytest` console script effectively gives you, versus
    `python -m pytest`), all 16 test modules failed to import, because `from src...` and
    `from tests.qt_fakes import ...` need the repo root on `sys.path` and nothing put it there.
    This is fixed in this pass by `pyproject.toml`'s `testpaths = ["tests"]` and
    `pythonpath = ["."]` (see the publication audit).

12. **Unsynchronised `isRunning()` check.** `src/main.py:71,121` restarts the asset updater from
    a `QTimer` lambda guarded by `updater.isRunning()`, read from the GUI thread without
    synchronisation. The 6-hour interval makes the race unreachable in practice.

## What I would change first

Not done in this pass, by instruction -- this publication pass is audit, sanitization,
packaging, and docs only, with no behaviour changes beyond the five ruff findings.

1. Pass `row` into `_paint_champion` instead of recovering it via `.index()` (risk 1).
2. Give the `LOADING` state a deadline (risk 5).
3. Move writable state to `%LOCALAPPDATA%` instead of next to the executable (risk 6).
