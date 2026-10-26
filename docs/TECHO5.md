# TECHO5 / Echo Show 8 integration status

## Finding

At the pinned TECHO5 revision (`docs/upstream-lock.json`), the Go display/receiver does not load Tessera C++ plugins and its hello does not advertise the `plugins` feature or a `plugin_api` version. The Tessera Home Assistant add-on refuses to send a plugin tile to a screen without that feature (`screen_manager/app/page_delivery.py`, plugin check in `send_layout`). The upstream probe in `adaptations/techo5/upstream_probe_test.go` and `docs/validation/techo-probe.log` confirms the stock mismatch. A GitHub link alone cannot put Spotify Mini's C++ player on the Echo Show.

## Local adaptation

`spotify-mini.patch` applies to the pinned TECHO5 source revision. It introduces an explicit native adapter for `plugin:spotify_mini.player`, advertises only Spotify Mini 0.1.0 in the hello, validates the configured `media_player` entity, maps Spotify Mini's state into TECHO5's existing media tile, and retains its playback and detail controls. Unknown plugin tile IDs are refused. The Go tests cover the hello, mapping, updates, touch and rendered hit zones.

This patch does **not** embed or run the C++ plugin. TECHO5's media renderer has no Spotify Mini artwork, library, search keyboard or Spotify Mini card. Its service bridge also does not implement the request/response path for `spotify_mini.browse` used by the C++ card. That work is needed for feature parity. Applying the patch requires a TECHO5 firmware build and installation; neither has been done on the user's device.

The TECHO5 screen is managed from its own YAML rather than Tessera's build profile. The Tessera app will show `own_yaml` sidecar instructions after adding a link; it will not build the TECHO5 firmware automatically. The local adapter is a firmware change, so those sidecar instructions alone cannot enable it.

## Reproduce source tests

```sh
# Start with the pinned TECHO5 commit from docs/upstream-lock.json.
git apply --check /path/to/tessera-spotify-mini/adaptations/techo5/spotify-mini.patch
git apply /path/to/tessera-spotify-mini/adaptations/techo5/spotify-mini.patch
cd echod
go test ./internal/feature/tessera
```

The display test is guarded by the same build tags as TECHO5's display package and needs its Linux hardware dependencies. In this workspace it was cross-compiled for Linux ARM to confirm the Go code builds, but was not executed on the Echo Show. The Tessera receiver tests ran locally. These tests do not prove Spotify account access, actual audio or physical touch behavior.

## Required work before calling TECHO5 fully supported

1. Build and install a TECHO5 image with the adapter on a test Echo Show 8, then verify the Tessera handshake, layout, state updates, tap zones and recovery path.
2. Decide how TECHO5 will expose the library and search flow: implement its own UI and service response bridge, or add a runtime that can actually host Tessera C++/LVGL plugins.
3. Verify Spotify Connect appears to the Spotify account and playback actions reach the intended device.
4. Repeat tests against the exact deployed Tessera and TECHO5 revisions; both projects can change their plugin and wire contracts.
