"""Small Spotify Web API client, independent of Home Assistant for testing.

The injected request coroutine supplies OAuth, returns an aiohttp-like response,
and MUST disable redirects. No arbitrary URLs, credentials or audio leave here.
"""
from __future__ import annotations

import asyncio
import aiohttp
import hashlib
import re
import time
from typing import Any
from urllib.parse import urlparse

from .const import PAGE_SIZE

URI = re.compile(r"spotify:(track|album|artist|playlist):[A-Za-z0-9]{22}\Z")
COVER = re.compile(r"/image/([a-f0-9]{40})\Z")


class SpotifyError(Exception):
    def __init__(self, code: str, retry_after: int = 0):
        self.code, self.retry_after = code, retry_after
        super().__init__(code)


def short(value: Any, limit: int = 48) -> str:
    return str(value or "").encode("utf-8")[:limit].decode("utf-8", "ignore")


def cover_id(images: list | None) -> str:
    for image in images or []:
        url = urlparse(image.get("url", ""))
        match = COVER.fullmatch(url.path)
        if url.scheme == "https" and url.hostname == "i.scdn.co" and match:
            return match[1]
    return ""


def item_view(item: dict | None) -> dict | None:
    if not isinstance(item, dict) or not URI.fullmatch(item.get("uri", "")):
        return None  # local files, episodes and unavailable/null items are not music results
    album = item.get("album") or {}
    return {
        "uri": item["uri"], "title": short(item.get("name")),
        "artist": short(", ".join(x.get("name", "") for x in item.get("artists", []))
                        or (item.get("owner") or {}).get("display_name")),
        "cover": cover_id(item.get("images") or album.get("images")),
        "kind": item["uri"].split(":")[1],
    }


class SpotifyAPI:
    def __init__(self, request, clock=time.monotonic):
        self.request, self.clock = request, clock
        self.lock = asyncio.Lock()
        self.blocked_until = 0.0
        self.selected_device: str | None = None
        self.recent_playlists: list[dict] = []  # only selections through this integration
        self.state: dict = {}

    async def call(self, method: str, path: str, **kwargs) -> dict:
        # Paths are entirely from this module, never an API-provided next URL.
        async with self.lock:
            if self.clock() < self.blocked_until:
                raise SpotifyError("rate_limited", max(1, int(self.blocked_until - self.clock())))
            try:
                async with asyncio.timeout(12):
                    response = await self.request(method, "https://api.spotify.com/v1/" + path,
                                                  allow_redirects=False, **kwargs)
                    try:
                        status = response.status
                        if status == 204:
                            return {}
                        if status == 429:
                            try:
                                delay = max(1, min(86400, int(response.headers.get("Retry-After", "30"))))
                            except (ValueError, TypeError):
                                delay = 30
                            self.blocked_until = self.clock() + delay
                            raise SpotifyError("rate_limited", delay)
                        if status >= 300:
                            raise SpotifyError({401: "auth_required", 403: "forbidden",
                                                404: "no_device"}.get(status, "network_error"))
                        body = await response.json()
                        if not isinstance(body, dict):
                            raise SpotifyError("invalid_response")
                        return body
                    finally:
                        response.release()
            except SpotifyError:
                raise
            except (OSError, TimeoutError, ValueError, aiohttp.ClientError) as exc:
                raise SpotifyError("network_error") from exc

    async def player(self) -> dict:
        body = await self.call("GET", "me/player")
        device = body.get("device") or {}
        item = body.get("item") or {}
        view = item_view(item) or {}
        self.state = {
            **view, "state": "playing" if body.get("is_playing") else "paused" if body else "idle",
            "position": max(0, (body.get("progress_ms") or 0) / 1000),
            "duration": max(0, (item.get("duration_ms") or 0) / 1000),
            "volume": device.get("volume_percent"), "device": short(device.get("name")),
            "device_id": device.get("id"), "restricted": device.get("is_restricted", False),
            "volume_supported": device.get("supports_volume", False),
            "disallows": (body.get("actions") or {}).get("disallows") or {},
            "error": "" if device else "no_device",
        }
        return self.state

    async def devices(self) -> list[dict]:
        body = await self.call("GET", "me/player/devices")
        return [d for d in body.get("devices", []) if d.get("id") and not d.get("is_restricted")]

    @staticmethod
    def device_key(device: dict) -> str:
        # Opaque IDs need not fit Tessera's 48-byte limit. Resolve a short handle server-side.
        return hashlib.sha256(device["id"].encode()).hexdigest()[:24]

    async def browse(self, category="playlists", query="", kind="track", offset=0) -> dict:
        if not isinstance(offset, int) or not 0 <= offset <= 10000:
            raise SpotifyError("invalid_request")
        params = {"limit": PAGE_SIZE, "offset": offset}
        if category == "home":
            # The menu pairs recent tracks with playlists matching a recently
            # heard artist. Search is supported; featured playlists is deprecated.
            body = await self.call("GET", "me/player/recently-played", params={"limit": 10})
            recent = [v for entry in body.get("items") or []
                      if (v := item_view((entry or {}).get("track"))) is not None][:2]
            artist = next((entry["artist"].split(", ")[0] for entry in recent
                           if entry["artist"]), "")
            recommended = []
            if artist:
                found = await self.call("GET", "search", params={"q": artist,
                                  "type": "playlist", "limit": 5, "offset": 0})
                recommended = [v for raw in (found.get("playlists") or {}).get("items") or []
                               if (v := item_view(raw)) is not None][:2]
            return {"recent": recent, "recommended": recommended}
        if category == "devices":
            items = [{"uri": self.device_key(d), "title": short(d.get("name")),
                      "kind": "device", "cover": "", "artist": ""} for d in await self.devices()]
            return {"items": items[offset:offset + PAGE_SIZE], "more": len(items) > offset + PAGE_SIZE}
        if category == "local":
            return {"items": self.recent_playlists[offset:offset + PAGE_SIZE],
                    "more": len(self.recent_playlists) > offset + PAGE_SIZE}
        if category == "search":
            if kind not in {"track", "artist", "album", "playlist"} or not query.strip() or len(query) > 48:
                raise SpotifyError("invalid_request")
            body = await self.call("GET", "search", params={**params, "q": query.strip(), "type": kind})
            body = body.get(kind + "s") or {}
            raw = body.get("items") or []
        elif category == "playlists":
            body = await self.call("GET", "me/playlists", params=params)
            raw = body.get("items") or []
        elif category == "albums":
            body = await self.call("GET", "me/albums", params=params)
            raw = [x.get("album") for x in body.get("items") or []]
        elif category == "recent":
            # Cursor endpoint: fetch at most Spotify's last 50 tracks, then paginate locally.
            body = await self.call("GET", "me/player/recently-played", params={"limit": 50})
            all_items = body.get("items") or []
            raw = [x.get("track") for x in all_items[offset:offset + PAGE_SIZE]]
            body = {"next": len(all_items) > offset + PAGE_SIZE}
        else:
            raise SpotifyError("invalid_request")
        items = [v for x in raw if (v := item_view(x)) is not None]
        return {"items": items, "more": bool(body.get("next"))}

    async def command(self, operation: str, value: str = "", title: str = "") -> dict:
        if operation == "device":
            devices = await self.devices()
            found = next((d for d in devices if self.device_key(d) == value), None)
            if found is None:
                raise SpotifyError("no_device")
            await self.call("PUT", "me/player", json={"device_ids": [found["id"]], "play": False})
            self.selected_device = found["id"]  # change only after successful transfer
            return {"ok": True}
        state = await self.player()
        target = self.selected_device or state.get("device_id")
        if not target:
            raise SpotifyError("no_device")
        if state.get("restricted") and target == state.get("device_id"):
            raise SpotifyError("restricted_device")
        params = {"device_id": target}
        if operation == "play_uri":
            if not URI.fullmatch(value):
                raise SpotifyError("invalid_request")
            payload = {"uris": [value]} if value.startswith("spotify:track:") else {"context_uri": value}
            await self.call("PUT", "me/player/play", params=params, json=payload)
            if value.startswith("spotify:playlist:"):
                record = {"uri": value, "title": short(title) or value, "artist": "", "cover": "", "kind": "playlist"}
                self.recent_playlists = [record] + [x for x in self.recent_playlists if x["uri"] != value][:19]
        elif operation in {"toggle", "play", "pause", "next", "previous"}:
            op = ("pause" if state["state"] == "playing" else "play") if operation == "toggle" else operation
            disallow = {"pause": "pausing", "play": "resuming", "next": "skipping_next", "previous": "skipping_prev"}[op]
            if target == state.get("device_id") and state["disallows"].get(disallow):
                raise SpotifyError("restricted_action")
            await self.call("POST" if op in {"next", "previous"} else "PUT", "me/player/" + op, params=params)
        elif operation in {"volume", "volume_up", "volume_down"}:
            # Query the selected device, not another currently active device's capabilities.
            device = next((d for d in await self.devices() if d["id"] == target), None)
            if not device or not device.get("supports_volume") or device.get("volume_percent") is None:
                raise SpotifyError("volume_unavailable")
            try:
                percent = int(value) if operation == "volume" else device["volume_percent"] + (5 if operation == "volume_up" else -5)
            except ValueError as exc:
                raise SpotifyError("invalid_request") from exc
            await self.call("PUT", "me/player/volume", params={**params, "volume_percent": max(0, min(100, percent))})
        elif operation == "seek":
            try:
                position = float(value)
                if not 0 <= position <= state["duration"] or state["disallows"].get("seeking"):
                    raise ValueError
            except ValueError as exc:
                raise SpotifyError("invalid_request") from exc
            await self.call("PUT", "me/player/seek", params={**params, "position_ms": round(position * 1000)})
        else:
            raise SpotifyError("invalid_request")
        return {"ok": True}
