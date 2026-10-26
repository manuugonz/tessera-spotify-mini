# Spotify Mini

Spotify Mini is a touch controller for Tessera. Its tile and card show the current track, artwork, progress and playback controls. The player has a device selector at top left and a three-line menu at top right. The menu combines music search, recent songs, recommended playlists and library access, with a back arrow to the player. Audio plays on a Spotify Connect device; no music is streamed to the Tessera screen.

The Spotify account and OAuth credentials stay in Home Assistant. The screen receives only short metadata, a validated artwork identifier and service replies. The plugin targets Tessera plugin API 0.13 and was checked against the upstream revisions in `docs/upstream-lock.json`.

**TECHO5 / Echo Show 8:** stock TECHO5 does not advertise Tessera plugin support. The adapter in `adaptations/techo5/spotify-mini.patch` is an uninstalled, locally tested starting point for TECHO5 firmware. It maps the player tile to TECHO5's existing media renderer and controls. It does not provide the Tessera C++ card, artwork, library or keyboard on TECHO5. See [TECHO5 status](docs/TECHO5.md) before attempting to use the link with that device.

## Set up

1. Use Home Assistant 2026.10 or newer and a Spotify Premium account with a Spotify Developer application. Set the app's redirect URI to `https://my.home-assistant.io/redirect/oauth` and select **Web API**. If My Home Assistant is disabled, use `<HOME_ASSISTANT_URL>/auth/external/callback` with the exact URL used during authorization. Add your Spotify account to the application's user allowlist if the application is in Development Mode. [Home Assistant's Spotify setup guide](https://www.home-assistant.io/integrations/spotify/) explains these Spotify portal steps.
2. Copy this repository's `custom_components/spotify_mini` directory to `/config/custom_components/spotify_mini` on the Home Assistant host. Restart Home Assistant. This is a separate integration: Tessera's **Add with a link** does not install Home Assistant custom integrations.
3. In Home Assistant, go to **Settings → Devices & services → Add integration → Spotify Mini**. Enter the Spotify **Client ID** and **Client secret** in Home Assistant's Application credentials prompt and finish OAuth in the browser. Do not paste either credential into Tessera or send it in chat. Confirm that the new `media_player` entity works in Home Assistant; its entity ID may differ from `media_player.spotify_mini`.
4. On a Tessera screen with the native plugin API, open **Plugins → Add with a link** and enter `https://github.com/manuugonz/tessera-spotify-mini`. You can also copy the whole plugin directory to `/config/tessera-plugins/spotify_mini` for a local test without GitHub. Add the plugin to the screen and let Tessera build and install the screen firmware. Then place its **Spotify Mini** tile in Layout and select the media player entity from step 3.
5. Start Spotify on a Spotify Connect device once, or open **Devices** in the card and choose an available device. Select the TECHO5's Spotify Connect receiver if you want sound from the Echo Show. The Web API cannot wake a device that Spotify has not discovered. [Home Assistant's Spotify guidance](https://www.home-assistant.io/integrations/spotify/#selecting-output-source) covers device visibility.

The plugin uses Tessera's current light or dark theme. Search supports tracks, artists, albums and playlists, with three results per page. The menu uses recently played tracks and searches for playlists matching a recently heard artist. When there is no recent artist, the recommendation section is empty. It does not depend on Spotify's deprecated featured-playlists endpoint. Home Assistant keeps up to 20 playlists selected through this integration as internal history.

The player adapts to the tile's shape: nearly square or portrait tiles emphasize the album cover and open the full card on tap; wide tiles place the cover on the left with track details and transport controls on the right. The expanded card gives the cover more space and separates the progress line from the transport buttons. Volume is handled by the device's physical buttons. Its buttons and progress line use Tessera's theme colours, with a restrained monochrome layout.

## What works where

| Feature | Tessera firmware with plugin API | Stock TECHO5 | TECHO5 with local adapter patch |
| --- | --- | --- | --- |
| Install link and native Spotify Mini tile | Supported, after GitHub publication or local folder install | No | Partial: Tessera records the plugin but TECHO5 uses its own firmware |
| Track details and transport controls | Yes | No Spotify Mini tile | Yes, using TECHO5's existing media sheet |
| Artwork, menu, touch search and Spotify Mini card | Yes | No | No |
| Sound from Echo Show 8 | Through its separate Spotify Connect receiver | Spotify Connect is independent of this plugin | Same |

The TECHO5 adapter has not been installed on a physical device. The desktop tests do not establish live hardware compatibility. Do not flash the Echo Show to try this package without reviewing the adapter and a recovery path.

## Privacy and limits

- Spotify Client ID, Client secret, access token and refresh token remain in Home Assistant's credential and config entry storage. The plugin does not ask for them or log them.
- Home Assistant calls `api.spotify.com`; the screen may request album artwork only from `i.scdn.co`. No audio is downloaded or proxied.
- Spotify API errors are shown as short status messages. A 429 response observes `Retry-After` locally; an expired OAuth grant starts Home Assistant reauthentication.
- Spotify's current Development Mode requires a Premium app owner and allows up to five authorized users. Spotify refresh tokens expire after six months and require a new sign-in. These are [Spotify platform rules](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide) and its [refresh token policy](https://developer.spotify.com/documentation/web-api/tutorials/refreshing-tokens).
- Playback depends on a Spotify Connect device, account permissions, availability in the current market and the device's supported actions. The Web API does not deliver audio to the screen.

## Verify locally

With the upstream Tessera plugins SDK, ESPHome and its preview dependencies installed:

```sh
python3 /path/to/tessera-plugins/tools/check.py .
python3 /path/to/tessera-plugins/tools/preview.py . --strict
python3 tools/interaction_bench.py /path/to/tessera-plugins . --board guition --strict
python3 -m pytest -q
```

The local validation record is in `docs/validation/`. The preview exercises four screen shapes and both themes with fixture data. The interaction bench simulates devices, menu, keyboard, search and play selection. The Python tests use fake Spotify responses and a Home Assistant test host; no real Spotify account or Echo Show was used. See [TECHO5 status](docs/TECHO5.md) for the separate Go tests and remaining integration gap.

## Source and license

Spotify Mini is MIT licensed. It uses Spotify's Web API and artwork host under Spotify's platform terms; Spotify and Tessera are separate projects. The TECHO5 adapter is source code only. Upstream revision pins appear in `docs/upstream-lock.json`.
