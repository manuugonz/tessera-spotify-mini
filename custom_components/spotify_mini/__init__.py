"""Spotify Mini backend: OAuth, bounded queries, media controls and local history."""
from __future__ import annotations
import logging
from datetime import timedelta

import aiohttp
from homeassistant.const import Platform
import voluptuous as vol
from homeassistant.core import SupportsResponse
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError, Unauthorized
from homeassistant.auth.permissions.const import POLICY_CONTROL, POLICY_READ
from homeassistant.helpers import config_entry_oauth2_flow, entity_registry as er
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .api import SpotifyAPI, SpotifyError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.MEDIA_PLAYER]


class Coordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, api):
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry, update_interval=timedelta(seconds=30))
        self.api = api
        self.store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.history")

    async def _async_update_data(self):
        try:
            return await self.api.player()
        except SpotifyError as exc:
            # Clear stale media on failure, exposing a safe error code to the screen.
            return {"state": "unavailable", "error": exc.code}

    async def command(self, operation, value="", title=""):
        result = await self.api.command(operation, value, title)
        if operation == "play_uri":
            await self.store.async_save({"playlists": self.api.recent_playlists})
        await self.async_request_refresh()
        return result


async def async_setup_entry(hass, entry):
    implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(hass, entry)
    session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)

    async def request(method, url, **kwargs):
        try:
            response = await session.async_request(method, url, **kwargs)
            if response.status == 401:
                entry.async_start_reauth(hass)
            return response
        except aiohttp.ClientResponseError as exc:
            if exc.status in (400, 401):
                entry.async_start_reauth(hass)
                raise ConfigEntryAuthFailed("Spotify authorization expired") from exc
            raise SpotifyError("network_error") from exc
        except aiohttp.ClientError as exc:
            raise SpotifyError("network_error") from exc

    coordinator = Coordinator(hass, entry, SpotifyAPI(request))
    saved = await coordinator.store.async_load() or {}
    coordinator.api.recent_playlists = [x for x in saved.get("playlists", []) if isinstance(x, dict)][:20]
    entry.runtime_data = coordinator
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, "browse"):
        async def handle(call):
            entity = call.data["entity_id"]
            registered = er.async_get(hass).async_get(entity)
            if not registered or registered.platform != DOMAIN:
                raise HomeAssistantError("Choose a Spotify Mini media player")
            coordinator = hass.data[DOMAIN].get(registered.config_entry_id)
            if coordinator is None:
                raise HomeAssistantError("Spotify Mini is not loaded")
            if call.context.user_id:
                user = await hass.auth.async_get_user(call.context.user_id)
                policy = POLICY_CONTROL if call.service == "command" else POLICY_READ
                if user is None or not user.permissions.check_entity(entity, policy):
                    raise Unauthorized(entity_id=entity)
            try:
                if call.service == "browse":
                    return await coordinator.api.browse(call.data["category"], call.data["query"],
                                                        call.data["kind"], call.data["offset"])
                return await coordinator.command(call.data["operation"], call.data["value"], call.data["title"])
            except ConfigEntryAuthFailed:
                return {"ok": False, "error": "auth_required", "items": []}
            except SpotifyError as exc:
                return {"ok": False, "error": exc.code, "retry_after": exc.retry_after, "items": []}

        hass.services.async_register(DOMAIN, "browse", handle, schema=vol.Schema({
            vol.Required("entity_id"): cv.entity_id,
            vol.Optional("category", default="playlists"): vol.In(["home", "playlists", "recent", "albums", "local", "devices", "search"]),
            vol.Optional("query", default=""): vol.All(str, vol.Length(max=48)),
            vol.Optional("kind", default="track"): vol.In(["track", "artist", "album", "playlist"]),
            vol.Optional("offset", default=0): vol.All(vol.Coerce(int), vol.Range(min=0, max=10000)),
        }), supports_response=SupportsResponse.ONLY)
        hass.services.async_register(DOMAIN, "command", handle, schema=vol.Schema({
            vol.Required("entity_id"): cv.entity_id,
            vol.Required("operation"): vol.In(["toggle", "play", "pause", "next", "previous", "volume", "volume_up", "volume_down", "seek", "device", "play_uri"]),
            vol.Optional("value", default=""): vol.All(str, vol.Length(max=96)),
            vol.Optional("title", default=""): vol.All(str, vol.Length(max=48)),
        }), supports_response=SupportsResponse.ONLY)
    return True


async def async_unload_entry(hass, entry):
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            for service in ("browse", "command"):
                hass.services.async_remove(DOMAIN, service)
        return True
    return False


async def async_remove_entry(hass, entry):
    await Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.history").async_remove()
