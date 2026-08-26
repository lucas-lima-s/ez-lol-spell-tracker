# Publication audit

What blocked publication of this repository as `ez-spell-tracker`, and how each item was
resolved. All items below were verified directly (file reads, `git log`, `git grep`, `git
ls-files`) before this pass.

| Blocker | Evidence | Resolution |
|---|---|---|
| No README / LICENSE / pyproject / CI | Files absent from the tree | `README.md` and `LICENSE` (commit "Add MIT license and English README"); `pyproject.toml`, `uv.lock`, `requirements.txt` (commit "Add pyproject with pinned deps, ruff config and pytest testpaths"); `.github/workflows/ci.yml` and `release.yml` (commit "Add CI and tagged release workflows") |
| The developer's real gamer handle appeared in 4 files | `tests/fixtures/allgamedata_loading.json:3-4`, `tests/fixtures/allgamedata_ptbr.json` (6 hits), `tests/test_live_client.py:226,234,235`, `tests/test_visibility.py:30` | Replaced with the neutral placeholder `Summoner` and the region tag `BR1`/`EUW` with `NA1` (a second, distinct `NA2` tag was used for one synthetic impostor identity in `test_live_client.py` so the test's riotId-vs-summonerName collision case still exercises two different identities). Baked into the initial commit. This document deliberately does not reprint the original handle. |
| Every original commit was authored under a previous employer's company email domain | `git log --format='%ae'` piped through `sort -u` returned a single address at that domain | History was rebuilt from scratch (`rm -rf .git && git init -b main`) with `user.name`/`user.email` set repo-local to the publication identity. |
| Fork-lineage references in `ROADMAP.md` | Lines 4-5, 21-22, 74 and 135 named a prior open-source project this tool was studied against by name, and attributed an abandoned cross-client sync feature to a third-party dependency that broke that earlier project | `ROADMAP.md` deleted; content moved to `docs/DESIGN.md`, translated, with every fork-lineage sentence removed and the surrounding claims rewritten as first-person design decisions (commit "Translate design doc and manual checklist to English"). |
| Whole design doc + manual checklist in Portuguese | `ROADMAP.md`, `tests/MANUAL.md` | Translated in full to `docs/DESIGN.md` and `tests/MANUAL.md` (same commit as above). |
| Dangling product name: the public name with a bare "V2" suffix appended, with no public v1 ever released | `src/main.py:77,93`, `src/app/autostart.py:14`, `build_release.bat:37,40,50,58`, `tests/test_autostart.py:88-89` | Renamed to the plain public name everywhere; `_ezst_managed` left untouched (it is an internal attribute name, not a product-name string). Baked into the initial commit. This document deliberately does not reprint the old dangling name. |
| Riot art and certificate redistributed with no disclaimer | `assets/champions/*.png` (195), `assets/spells/*.png` (16), `assets/certs/riotgames.pem` | README carries the verbatim Riot legal disclaimer plus a statement that art comes from Data Dragon and the app only ever talks to Riot's official local endpoint and Data Dragon (commit "Add MIT license and English README"). |
| No repo description / topics | `gh repo view` (repo did not exist yet) | Set at `gh repo create` time: description and 5 topics (`league-of-legends`, `overlay`, `pyside6`, `riot-api`, `windows`). Tracked as a GitHub-side step, not a file in this tree. |
| A recursive plain-text scan of `docs/` (checking for stray non-English prose, i.e. Latin-1 letters with diacritics) also reads every binary file underneath it; a PNG's compressed byte stream statistically contains the same two-byte sequences those diacritic letters encode to in UTF-8 (confirmed: the 96 KB mockup alone produced 9,049 incidental hits, and even a trivial 98-byte flat PNG produced one), so no image can ever live under `docs/` and pass that scan | `docs/overlay-mock.png` (as it was originally placed) tripped a recursive grep for diacritic bytes across `docs/` | Moved the rendered mockup to `.github/images/overlay-mock.png`, a directory outside both `docs/` (kept text-only) and `assets/` (kept to runtime data the release build copies next to the executable). `README.md` and `scripts/render_mockup.py`'s `--out` default were updated to the new path. |

## Negative results (checked, nothing found)

- `git ls-files` contains **zero** entries under `lib/`, `build/`, `dist/`, `logs/`,
  `.pytest_cache/`, and `config/settings.json`. `.gitignore` already covered all of them before
  this pass and was left as-is except for the additions in the packaging step
  (`.venv/`, `.ruff_cache/`, `*.spec`, `.github/images/*.tmp.png`).
- `.gitattributes` (`* text=auto`, `*.bat text eol=crlf`, `*.png binary`) was already correct and
  needed no change.
