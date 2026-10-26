import pytest
from custom_components.spotify_mini.api import SpotifyAPI, SpotifyError, cover_id, item_view, short

TRACK = "spotify:track:" + "A" * 22
PLAYLIST = "spotify:playlist:" + "B" * 22
DEVICE = {"id": "device-secret-opaque" * 5, "name": "Echo Show 8", "supports_volume": True,
          "volume_percent": 95, "is_restricted": False}
PLAYER = {"is_playing": True, "device": DEVICE, "progress_ms": 12000,
          "item": {"uri": TRACK, "name": "Song", "duration_ms": 180000, "artists": [{"name": "Artist"}],
                   "album": {"images": [{"url": "https://i.scdn.co/image/" + "a" * 40}]}}, "actions": {}}


class Response:
    def __init__(self, body=None, status=200, headers=None):
        self.body, self.status, self.headers = body, status, headers or {}
        self.released = False

    async def json(self):
        return self.body

    def release(self):
        self.released = True


class Transport:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    async def __call__(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def api(*responses):
    transport = Transport(*responses)
    return SpotifyAPI(transport), transport


async def test_player_and_no_content():
    client, tx = api(Response(PLAYER), Response(status=204))
    playing = await client.player()
    assert playing["state"] == "playing" and playing["cover"] == "a" * 40
    assert playing["duration"] == 180 and playing["position"] == 12
    assert (await client.player())["error"] == "no_device"
    assert all(x[2]["allow_redirects"] is False for x in tx.calls)


@pytest.mark.parametrize("status,code", [(401,"auth_required"),(403,"forbidden"),(404,"no_device"),(500,"network_error"),(302,"network_error")])
async def test_safe_errors(status, code):
    r = Response({"private": "must not appear"}, status)
    client, _ = api(r)
    with pytest.raises(SpotifyError, match=code):
        await client.player()
    assert r.released


async def test_rate_limit_prevents_every_endpoint_until_retry():
    now = [100]
    tx = Transport(Response(status=429, headers={"Retry-After": "5"}), Response(status=204))
    client = SpotifyAPI(tx, lambda: now[0])
    with pytest.raises(SpotifyError, match="rate_limited"):
        await client.player()
    with pytest.raises(SpotifyError, match="rate_limited"):
        await client.browse()
    assert len(tx.calls) == 1
    now[0] += 6
    await client.player()


@pytest.mark.parametrize("exception", [OSError("offline"), TimeoutError(), ValueError("bad JSON")])
async def test_network_errors(exception):
    client, _ = api(exception)
    with pytest.raises(SpotifyError, match="network_error"):
        await client.player()


async def test_search_pagination_and_nulls():
    client, tx = api(Response({"tracks": {"items": [None, {"uri": TRACK, "name": "Found"}], "next": "https://evil.test"}}))
    result = await client.browse("search", "Björk", "track", 3)
    assert len(result["items"]) == 1 and result["more"]
    assert tx.calls[0][2]["params"] == {"q": "Björk", "type": "track", "limit": 3, "offset": 3}
    assert len(tx.calls) == 1  # never follow an API-supplied URL


@pytest.mark.parametrize("category,body", [("playlists", {"items": [None]}),("albums", {"items": [{"album": None}]}),("recent", {"items": [{"track": None}]})])
async def test_empty_library(category, body):
    client, _ = api(Response(body))
    assert (await client.browse(category))["items"] == []


async def test_play_playlist_and_local_history():
    client, tx = api(Response(PLAYER), Response(status=204))
    await client.command("play_uri", PLAYLIST, "Favorites")
    assert tx.calls[-1][2]["json"] == {"context_uri": PLAYLIST}
    assert client.recent_playlists[0]["title"] == "Favorites"
    assert (await client.browse("local"))["items"] == client.recent_playlists


async def test_failed_play_not_recorded():
    client, _ = api(Response(PLAYER), Response(status=403))
    with pytest.raises(SpotifyError):
        await client.command("play_uri", PLAYLIST)
    assert not client.recent_playlists


async def test_track_uses_uris_and_targets_device():
    client, tx = api(Response(PLAYER), Response(status=204))
    await client.command("play_uri", TRACK)
    assert tx.calls[-1][2]["json"] == {"uris": [TRACK]}
    assert tx.calls[-1][2]["params"]["device_id"] == DEVICE["id"]


async def test_device_selection_short_handle_and_transfer():
    client, tx = api(Response({"devices": [DEVICE]}), Response({"devices": [DEVICE]}), Response(status=204))
    item = (await client.browse("devices"))["items"][0]
    assert len(item["uri"]) == 24 and DEVICE["id"] not in str(item)
    await client.command("device", item["uri"])
    assert tx.calls[-1][2]["json"] == {"device_ids": [DEVICE["id"]], "play": False}
    assert client.selected_device == DEVICE["id"]


async def test_volume_clamps_and_checks_capability():
    client, tx = api(Response(PLAYER), Response({"devices": [DEVICE]}), Response(status=204))
    await client.command("volume", "500")
    assert tx.calls[-1][2]["params"]["volume_percent"] == 100
    client, _ = api(Response(PLAYER), Response({"devices": [{**DEVICE, "supports_volume": False}]}))
    with pytest.raises(SpotifyError, match="volume_unavailable"):
        await client.command("volume_up")


async def test_restricted_and_no_device():
    client, _ = api(Response({**PLAYER, "device": {**DEVICE, "is_restricted": True}}))
    with pytest.raises(SpotifyError, match="restricted_device"):
        await client.command("toggle")
    client, _ = api(Response(status=204))
    with pytest.raises(SpotifyError, match="no_device"):
        await client.command("play")


async def test_restricted_action():
    client, _ = api(Response({**PLAYER, "actions": {"disallows": {"skipping_next": True}}}))
    with pytest.raises(SpotifyError, match="restricted_action"):
        await client.command("next")


@pytest.mark.parametrize("value", ["https://evil.test", "spotify:track:../secret", "spotify:local:" + "A"*22])
async def test_reject_bad_playback(value):
    client, tx = api(Response(PLAYER))
    with pytest.raises(SpotifyError, match="invalid_request"):
        await client.command("play_uri", value)
    assert len(tx.calls) == 1


async def test_recent_tracks_are_not_playlist_history():
    client, _ = api(Response({"items": [{"track": {"uri": TRACK, "name": "Recent"}, "context": {"uri": PLAYLIST}}]}))
    assert (await client.browse("recent"))["items"][0]["uri"] == TRACK
    assert not client.recent_playlists


async def test_home_recommends_playlists_from_recent_artist():
    recent = {"items": [{"track": {"uri": TRACK, "name": "Recent",
                               "artists": [{"name": "Björk"}]}}]}
    playlist = {"playlists": {"items": [None, {"uri": PLAYLIST,
                "name": "Björk Mix", "owner": {"display_name": "Spotify"}}]}}
    client, tx = api(Response(recent), Response(playlist))
    result = await client.browse("home")
    assert result["recent"][0]["uri"] == TRACK
    assert result["recommended"][0]["uri"] == PLAYLIST
    assert tx.calls[1][2]["params"] == {"q": "Björk", "type": "playlist", "limit": 5, "offset": 0}


async def test_home_without_recent_music_skips_recommendation_search():
    client, tx = api(Response({"items": []}))
    assert await client.browse("home") == {"recent": [], "recommended": []}
    assert len(tx.calls) == 1


async def test_seek_and_toggle():
    client, tx = api(Response(PLAYER), Response(status=204), Response(PLAYER), Response(status=204))
    await client.command("seek", "15.5")
    assert tx.calls[-1][2]["params"]["position_ms"] == 15500
    await client.command("toggle")
    assert tx.calls[-1][0:2] == ("PUT", "https://api.spotify.com/v1/me/player/pause")


def test_utf8_and_image_host_and_no_local_files():
    assert len(short("ñ"*50).encode()) == 48
    assert cover_id([{"url": "https://evil.test/image/"+"a"*40}]) == ""
    assert cover_id([{"url": "https://i.scdn.co/image/"+"a"*40}]) == "a"*40
    assert item_view(None) is None
    assert item_view({"uri": "spotify:local:music"}) is None
