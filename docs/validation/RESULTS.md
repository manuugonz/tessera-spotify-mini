# Local validation — 2026-10-26

The source revisions used are pinned in `../upstream-lock.json`. Tests ran without a Spotify account and without changing the Echo Show 8.

| Check | Result | Record |
| --- | --- | --- |
| Tessera SDK `tools/check.py` | Pass: manifest, structure, translations, 1280×720 `store.png` | `check.log` |
| Tessera `tools/preview.py --strict` | Pass: CYD, Guition, Waveshare 4.3 portrait and JC8012P4A1; 0 warnings with the player and menu redesign | `preview-menu.log`, ignored local `.preview/` |
| LVGL interaction bench | Pass: player, devices, menu, library, two-character touch input, search, play selection and automatic return, in light and dark themes; 0 warnings | `interaction-menu.log`, ignored local `.interaction/` |
| Home Assistant + Spotify API Python tests | Pass: 32 tests, one warning from Home Assistant's own aiohttp inheritance | `backend-tests.log` |
| TECHO5 stock capability probe | Pass: demonstrates missing plugin capability and renderer | `techo-probe.log` |
| TECHO5 adapter receiver tests | Pass: patch applies cleanly to pinned source, receiver/controls tests pass | `techo-adapter.log` |
| TECHO5 display test | Cross-compiles to Linux ARM64 ELF; cannot execute on the macOS host | `techo-display-build.log` |
| Spotify OAuth and playback on a real account | Pending: requires the user's account and active Spotify Connect receiver | — |
| TECHO5 on a physical Echo Show 8 | Pending: patch has not been installed, touch, audio and handshake not measured | — |

The first minimal prototype and its render are saved separately as `../probe.cpp.txt` and `probe-preview.log`. That first render warned about dark text contrast. The complete plugin's final strict preview above has zero warnings. The final player also renders connection and device errors inside the compact card. Selected screenshots from the passing benches are in `../../design/previews/`. Spotify OAuth and physical Echo Show behavior remain untested.
