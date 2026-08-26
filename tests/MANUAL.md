# Manual validation checklist

> These checks require a live League of Legends client (or Practice Tool) and cannot be
> automated. Check off each item as it is validated.

## Pending validations overview

The automated test suite passes, but the following live validations are still outstanding:

- [ ] **Live roster** -- Practice Tool roster validation with 5 bots on a Portuguese client;
      confirm `riotId` on the real `activePlayer`.
- [ ] **Real match** -- full manual checklist: real match at 2560x1440 Borderless, NOACTIVATE
      focus test (Notepad and in-game), pause freezing the timers, capture exclusion verified
      against OBS, autostart across a logoff/logon, exclusive-fullscreen behaviour (currently an
      open question).
- [ ] **UI features** -- per-resolution profiles, lock icon, show/hide hotkey (default F8),
      opacity.
- [ ] **Background asset updates** -- background asset auto-update (delete a sprite / roll back
      `version.txt` and confirm re-download; version label in settings).
- [ ] **Auto-adjusted cooldowns** -- boots detected via the API (blue dot), Cosmic Insight manual
      toggle (right-click on the portrait, yellow dot), mouse wheel +-5s, click compensation,
      Smite 90s, Unleashed Teleport after 10:00. Constants checked against the wiki on
      2026-06-11 -- re-check per patch.

## Live roster

- [ ] Open the app (`run.bat`), create a Practice Tool match with 5 enemy bots -> `logs\app.log`
      shows `Game detected` and one line per enemy with champion (canonical id) and correct
      spells on a Portuguese client.
- [ ] Check the log for whether the real `activePlayer` exposed `riotId` (open question from the
      old sample).
- [ ] Practice Tool with no bots -> warning "Game started with no enemies on roster".
- [ ] Leave the match -> `Game ended` within ~6s.

## Overlay preview and positioning

- [ ] Tray -> "Show overlay" displays 5 placeholder rows (Annie/Ahri/Garen/Lux/Teemo) with real
      sprites.
- [ ] Dragging the overlay repositions it; the position persists after closing/reopening the app.
- [ ] Settings -> Lock position prevents dragging; the border disappears when locked.
- [ ] Scale/opacity sliders apply live; Reset position returns to the default.
- [ ] Left-click on an icon starts a M:SS timer with a greyed-out icon; right-click resets it.
- [ ] Opacity slider applies live to the overlay and persists.

## Focus (NOACTIVATE)

- [ ] Notepad test: type continuously in Notepad and click several overlay icons (preview) -- the
      text cursor stays in Notepad, typing is not interrupted, and Notepad's title bar keeps the
      active-window color.
- [ ] In-game: hold a movement command / type in chat and click the overlay -- the character keeps
      responding, chat keeps focus, the game never minimizes.

## Real match

- [ ] Overlay appears on its own after loading and disappears at the end of the match.
- [ ] 5 correct enemies (Portuguese client), timers correct compared against a stopwatch.
- [ ] Pause (Practice Tool) freezes the timers; unpausing resumes them.
- [ ] Alt-tab hides the overlay; returning to the game shows it again; the overlay stays on top of
      the game for the whole match (heartbeat).
- [ ] Also test exclusive fullscreen and record the result here (open question): ___________

## Per-resolution profiles

- [ ] Position/scale the overlay at 2560x1440; change the Windows (or in-game Borderless)
      resolution to 1920x1080 -> the overlay reloads position/scale from the new resolution's
      profile (defaults on first use); switching back to 2560x1440 restores the original
      position/scale with no manual adjustment.
- [ ] The settings window shows the correct "Current resolution profile: <WxH>".
- [ ] `config/settings.json` stores separate profiles under `overlay.profiles`.

## Lock icon

- [ ] The lock icon appears at the top-right of the overlay (open = unlocked, with border; closed
      = locked, no border).
- [ ] Clicking the lock IN-GAME locks/unlocks without stealing focus from the game.
- [ ] Locked: dragging does not move the overlay; spell clicks keep working.
- [ ] The "Lock position" checkbox in settings reflects the state when clicking the lock icon
      (and vice versa).

## Global hotkey

- [ ] With the default F8: pressing it IN-GAME (game focused) hides the overlay; pressing it
      again shows it. Also works in preview mode.
- [ ] Changing the shortcut in settings (e.g. Ctrl+F9) -> the new shortcut works immediately and
      persists after restarting the app.
- [ ] A conflicting shortcut (already registered by another app) -> a warning appears and the
      previous shortcut keeps working.
- [ ] Starting a new game resets the hidden state (the overlay reappears).

## Capture exclusion and autostart

- [ ] "Hide from recordings and captures": recording with OBS/Xbox Game Bar -> the overlay is
      invisible in the recording, visible on screen.
- [ ] "Start with Windows": logoff/logon -> the app comes up in the tray on its own.

## Background asset updates

- [ ] Delete a sprite from `assets/champions/` and open the app -> the sprite is re-downloaded on
      its own within seconds (log "Assets updated"/"already up to date").
- [ ] Edit `assets/data/version.txt` to an older version -> the app rolls the full snapshot
      forward in the background without blocking the UI.
- [ ] The settings window shows "Patch data: <version>".

## Auto-adjusted cooldowns

- [ ] Practice Tool: buy Ionian Boots of Lucidity on an enemy bot -> within ~10s the BLUE dot
      appears on the portrait and the next spell click uses the reduced cooldown (~9% lower;
      Flash 300s -> ~273s).
- [ ] Right-click on the portrait toggles Cosmic Insight (YELLOW dot) -> Flash with boots+rune ~=
      234s (300/1.28). Check against a stopwatch.
- [ ] Mouse wheel over a running timer adjusts it +-5s per wheel click.
- [ ] "Late-click compensation" in settings (e.g. 5s) -> the timer starts already discounted.
- [ ] Smite: clicking starts a 90s timer (real recharge), not the 15s from Data Dragon.
- [ ] Teleport after 10:00 of game time: clicking uses the Unleashed cooldown (330-240s depending
      on the enemy's level -- level comes from the API).
- [ ] CHECK AGAINST THE CURRENT PATCH (hardcoded values, checked against the wiki on 2026-06-11):
      Ionian Boots = 10 haste; Cosmic Insight = 18; Smite = 90s; TP upgrade at 10:00.

## Self-contained release

- [ ] `build_release.bat` produces `dist\EzSpellTracker\` (exe + `_internal\` + `assets\`).
- [ ] Local smoke test: run the exe in a shell with `set PATH=C:\Windows;C:\Windows\System32` and
      `set PYTHONPATH=` -> the tray icon comes up, settings open, preview works, `logs\` and
      `config\` are created next to the exe.
- [ ] Real criterion: copy the folder to a machine/VM/Windows user without Python installed and
      repeat the smoke test.
