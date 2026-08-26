# ez-spell-tracker -- design notes

## Overview

An enemy summoner-spell cooldown tracker for League of Legends: a system-tray app that detects
the match automatically, populates the 5 enemies (champion + spells), and shows a draggable
in-game overlay where one click starts the spell's cooldown timer. 100% local, entirely within
Riot's third-party policy for this kind of tool.

## Architecture decisions

### Stack

- **Python 3.13+ (3.14 on the reference machine) + PySide6** for the overlay, tray icon, and
  settings UI, `requests` for the HTTP calls, `pytest` for the test suite. Note: free-threaded
  builds (3.14t) are not supported -- PySide6 ships no wheels for them, and the dev bootstrap
  scripts reject them automatically.
- **Dev environment:** a self-contained setup -- `build_environment.bat` vendors the dependencies
  into `lib/` (`pip install --target=lib`), `run.bat` runs the app with `PYTHONPATH=lib`. The
  `.bat` scripts parse `configs.json` through a small Python bootstrap script, never through
  `findstr`, so the config format stays a single well-defined JSON file instead of being
  re-parsed ad hoc in batch syntax.
- **Release:** PyInstaller **onedir** (never onefile) with the assets copied next to the
  executable -- a self-contained folder that needs no runtime installed by the user.

### Data sources (all official)

| Data | Source |
|---|---|
| Active match, roster, champions, equipped spells, items | Live Client Data API -- `https://127.0.0.1:2999/liveclientdata/` (`/allgamedata`, `/playerlist`, `/gamestats`) |
| Base summoner-spell cooldowns per patch | Data Dragon `summoner.json` (with a manually validated fallback table) |
| Sprites (champions, spells) and patch version | Data Dragon `versions.json` + `/cdn/{ver}/img/...`; CommunityDragon `latest` as a fallback on patch day |

Design rules that follow from these sources:

- **Zero external network dependency on the critical path** -- the game only ever talks to
  `127.0.0.1:2999`; Data Dragon is used only to refresh the local asset/data cache. No hosted
  backend, no account.
- **Client-locale independence** (the reference client runs in Brazilian Portuguese): spells are
  identified by `rawDisplayName` (e.g. `..._SummonerFlash_...`), never by the localized
  `displayName`.
- Cooldowns are anchored to the API's `gameTime`, not the wall clock (this survives
  pauses/reconnects -- see "Non-obvious invariants" below).

### Anti-detection (strategy: nothing to detect)

Riot Vanguard's official FAQ states: *"Overlays and internal tools using the API, game client,
and in-game APIs should continue to function."* What Vanguard targets is injection and memory
reads.

1. The overlay window is **external** (frameless, transparent, topmost) -- zero DLL injection,
   zero DirectX hooking, zero reading of the game's memory or process.
2. Only official local APIs are used (the `2999` endpoint, which Riot endorses for this purpose).
3. Neutral, generic window title/class; `Qt.Tool` (outside the taskbar and Alt+Tab).
4. A settings toggle: **hide the overlay from recordings/replays/streams**
   (`SetWindowDisplayAffinity WDA_EXCLUDEFROMCAPTURE`, Windows 10 2004+). Off by default.
5. TLS with an embedded `riotgames.pem` (pinning Riot's self-signed certificate) instead of
   `verify=False`.

### Known constraints (not bugs)

- **Enemy spell usage cannot be detected automatically** through any legitimate channel: the API
  exposes no enemy cooldown/cast state, and the scoreboard renders nothing a computer-vision
  approach could read. Starting a timer is manual by design -- the standard across this whole
  category of tool.
- **League must run in Borderless** for the external overlay to reliably render on top.
  Exclusive fullscreen sometimes works on Windows 11 (FSO) but with no guarantee -- this is
  tracked as a known unknown below.
- Enemy runes (Cosmic Insight) are not exposed by the API, so they need a manual toggle.

## Non-scope (recorded decisions)

| Item | Reason |
|---|---|
| Ultimate-ability tracking | Banned by Riot as of 2025-03-13 (manual or automatic; treated as cheating and enforced via Vanguard). Removed from scope. |
| Cross-team timer sync | Out of scope. It would require a hosted backend, and this tool is deliberately 100% local. |
| Memory reads / injection / hooks | Policy violation and a Vanguard detection target. Never. |
| Automatic cast detection via computer vision | Technically impossible (nothing renders on screen that would indicate it) and a policy grey area regardless. |
| Ads in the overlay | Banned by Riot as of 2025-05-29. |

## Folder structure

```
ez-spell-tracker/
|-- run.bat                  # dev: PYTHONPATH=lib + python src/main.py
|-- build_environment.bat    # dev: vendors deps into lib/
|-- build_release.bat        # self-contained PyInstaller onedir build
|-- configs.json             # bootstrap (pythonPath) -- used only by the dev .bat scripts
|-- requirements.txt         # pinned deps, generated from uv.lock
|-- assets/                  # embedded snapshot (works offline on first run)
|   |-- champions/           # square champion sprites
|   |-- spells/               # summoner-spell icons
|   `-- data/                # summoner.json, champions.json, version.txt (cache per patch)
|-- lib/                     # vendored deps (gitignored)
|-- src/
|   |-- main.py               # entrypoint: tray + event loop
|   |-- app/                  # tray icon, settings window, game watcher, asset updater
|   |-- core/                 # config, logging, models, cooldown math, paths
|   |-- riot/                 # live_client.py, ddragon.py, parser.py, static_data.py
|   `-- overlay/               # OverlayWindow, controller, hotkey, win32 helpers
`-- tests/
```

## Build log

The five shipped milestones, in the order they landed:

### v0.1 -- Foundation

Project skeleton in the structure above; `build_environment.bat`/`run.bat` with the
Python-based `configs.json` bootstrap; user config (`settings.json`) with persistence; rotating
logging; a working tray app (`QSystemTrayIcon`): double-click opened the settings window (then
still empty), context menu with Settings/Show overlay/Quit.

Completion criteria met: `build_environment.bat` installed everything into `lib/` on a clean
machine; `run.bat` brought the app up in the tray; double-click opened the window; quitting shut
down cleanly.

### v0.2 -- Riot integration

Live Client Data API client (polling `/gamestats` to detect a match, `/allgamedata` for the
roster) with Riot's certificate pinned; enemy-team identification via `activePlayer` + `riotId`;
champion and spell extraction by `rawDisplayName` (locale-independent, validated against a
Portuguese client); domain models (`Enemy`, `SpellSlot`, cooldown math
`base / (1 + haste/100)`); Data Dragon snapshot downloaded by `scripts/fetch_assets.py` (sprites
named canonically by id); base cooldown table loaded from the embedded `summoner.json`.

Completion criteria met: with a live match (or Practice Tool) running, the log showed the 5
enemies with the correct champion and spells on a Portuguese client; parser tests passed against
real captured JSON fixtures.

### v1.0 -- Overlay tracker (usable MVP)

Overlay laid out as a vertical column (champion portrait + 2 spell icons), with the cooldown
timer overlaid on the icon as MM:SS; left-click starts a timer, right-click resets it;
draggable with a lock toggle; shows automatically when a match is detected and hides when it
ends; only shows while the League window is active; topmost heartbeat; a full settings window --
**every setting configurable from the UI**: position (reset), scale, opacity, lock, hide from
recordings (WDA), start with Windows; `build_release.bat` producing a self-contained folder
tested on a clean machine.

Completion criteria met: a full real match played start to finish using the tracker at
2560x1440; correct timers; the overlay does not steal focus from the game on click
(`WS_EX_NOACTIVATE`); the onedir release runs with no Python installed.

### v1.0.1 -- UI features

Per-resolution overlay profiles; a lock icon on the overlay; a configurable global show/hide
hotkey (default F8); opacity control.

Completion criteria met: switching resolution loaded the right profile automatically; the lock
icon toggled drag-ability without stealing game focus; the hotkey worked in-game and persisted
across restarts.

### v1.1 + v2.0 -- Background asset updates and auto-adjusted cooldowns

`AssetUpdateWorker` -- on startup (and periodically), compares the latest Data Dragon version
against the local cache and downloads `champion.json`, `summoner.json`, and any missing sprites,
asynchronously so the overlay is never blocked; periodic `/playerlist` polling for enemy items,
detecting Ionian Boots of Lucidity automatically (summoner-spell haste applied to the cooldown
math); a manual per-enemy toggle for Cosmic Insight (runes are not exposed by the API); a mouse
wheel adjustment (+-5s) for a running timer; special cases for Teleport (Unleashed Teleport by
game time) and Smite (charge-based recharge).

Completion criteria met: an enemy buying Ionian Boots got a reduced cooldown on the next timer
with no user input; haste values were checked against the then-current patch.

## Known unknowns

Three items genuinely need a live game or a patch check and are deliberately left open:

- **Exclusive-fullscreen behaviour.** The external overlay is only guaranteed to render on top
  in Borderless. It sometimes works in exclusive fullscreen on Windows 11 (FSO), but this has
  not been validated end to end.
- **Current-patch Ionian Boots of Lucidity summoner-spell haste.** Hardcoded as `10.0`; sources
  disagreed (10 vs 12) when last checked against the wiki on 2026-06-11.
- **Shape of `riotId` on older clients.** The parser falls back from `riotId` to `summonerName`
  when `riotId` is absent; this fallback path has not been exercised against a live older
  client.

## Non-obvious invariants

Rationale that the project's no-comments code style keeps out of the source, recorded here
instead:

- **`StaticData._spell_ids` is sorted longest-first.** `extract_spell_id`'s fallback path does a
  substring scan over every known spell id when the display name doesn't match the expected
  `GeneratedTip_SummonerSpell_<Id>_DisplayName` shape. That scan is only deterministic because
  `StaticData.__init__` pre-sorts `_spell_ids` by length, descending, so a longer id (e.g.
  `SummonerSmite`) is always tried before any shorter id that happens to be one of its
  substrings. Reordering that sort breaks the fallback silently.
- **Timers are anchored to game time, with bounded extrapolation.** `GameClock.ingest` stores
  both the API's `gameTime` and the local monotonic clock at the moment of the poll.
  `PAUSE_EPSILON` (0.05s) and `MIN_PAUSE_GAP` (1.0s) are the thresholds used to detect that the
  game clock stopped advancing between two polls spaced far enough apart -- that is what freezes
  timers during a Practice Tool pause. Between polls, `now()` extrapolates from the last known
  game time using the local monotonic delta, but caps that extrapolation at
  `EXTRAPOLATION_CAP` (10.0s) so a missed poll or a reconnect never lets timers run far ahead of
  the real game clock.
- **The overlay window needs all three of `WS_EX_NOACTIVATE`, `Qt.Tool`, and
  `WindowDoesNotAcceptFocus`, not just one.** `WS_EX_NOACTIVATE` is the native Win32 extended
  style that stops Windows from activating the window (and therefore stealing focus from the
  game) when it is clicked. `Qt.Tool` keeps it out of the taskbar and Alt+Tab so it never
  appears as a switchable application window. `WindowDoesNotAcceptFocus` is a Qt-level flag,
  independent of the native style, that tells Qt's own focus manager never to route
  keyboard/mouse focus to the widget. Dropping any one of the three reopens a path to focus
  theft or taskbar clutter that the other two do not cover.
- **Assets must live next to the frozen executable, not inside PyInstaller's `_internal/`.**
  `src/core/paths.py` resolves `PROJECT_ROOT` to `Path(sys.executable).parent` when the app is
  frozen. The release workflow copies `assets/` to `dist/EzSpellTracker/assets/`, next to the
  exe -- copying it into `_internal/` instead would leave `PROJECT_ROOT / "assets"` pointing at an
  empty directory and the overlay would render with no sprites, silently.
