"""Exercise the real HA 2026.10 runtime, not fake modules with matching names."""
import time
from types import MappingProxyType
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry, ConfigEntries, ConfigEntryState
from homeassistant.helpers import config_entry_oauth2_flow as oauth, entity_registry as er, device_registry as dr
from homeassistant.exceptions import HomeAssistantError
from custom_components import spotify_mini as integration
from custom_components.spotify_mini.api import SpotifyAPI
from custom_components.spotify_mini.media_player import SpotifyMiniPlayer
from test_api import Response, PLAYER


def make_entry():
    return ConfigEntry(domain="spotify_mini", title="Test", unique_id="account-1", version=1,
                       minor_version=1, source="user", state=ConfigEntryState.SETUP_IN_PROGRESS, options={}, discovery_keys=MappingProxyType({}),
                       subentries_data=None, data={"auth_implementation": "spotify_mini", "token": {
                           "access_token": "fake-test-token", "refresh_token": "fake-test-refresh", "expires_at": 0}})


@pytest.fixture
async def hass(tmp_path):
    instance = HomeAssistant(str(tmp_path))
    instance.config_entries = ConfigEntries(instance, {})
    instance.config.components.add("spotify_mini")
    yield instance
    await instance.async_stop()


async def test_real_oauth_refresh_and_persistence(hass, monkeypatch):
    entry = make_entry()
    implementation = Mock()
    implementation.async_refresh_token = AsyncMock(return_value={"access_token": "refreshed-test-token",
                                                               "refresh_token": "rotated-test-refresh",
                                                               "expires_at": time.time() + 3600})
    persisted = []
    def update(entry, **kwargs):
        persisted.append(kwargs["data"])
        object.__setattr__(entry, "data", MappingProxyType(kwargs["data"]))
    monkeypatch.setattr(hass.config_entries, "async_update_entry", update)
    session = oauth.OAuth2Session(hass, entry, implementation)
    await session.async_ensure_token_valid()
    await session.async_ensure_token_valid()
    assert implementation.async_refresh_token.await_count == 1
    assert persisted[0]["token"]["refresh_token"] == "rotated-test-refresh"


async def test_coordinator_entity_real_ha(hass):
    entry = make_entry()
    request = AsyncMock(return_value=Response(PLAYER))
    coordinator = integration.Coordinator(hass, entry, SpotifyAPI(request))
    coordinator.async_set_updated_data(await coordinator._async_update_data())
    entry.runtime_data = coordinator
    player = SpotifyMiniPlayer(entry)
    assert player.media_title == "Song" and player.state == "playing"
    assert player.media_image_url.endswith("a"*40)
    assert player.volume_level == .95
    assert "access_token" not in str(player.extra_state_attributes)
    request.return_value = Response(status=500)
    coordinator.async_set_updated_data(await coordinator._async_update_data())
    assert not player.available
    assert player.extra_state_attributes["mini_error"] == "network_error"


async def test_setup_browse_command_unload_services(hass, monkeypatch):
    entry = make_entry()
    monkeypatch.setattr(oauth, "async_get_config_entry_implementation", AsyncMock(return_value=Mock()))
    request = AsyncMock(return_value=Response(PLAYER))
    monkeypatch.setattr(oauth.OAuth2Session, "async_request", request)
    monkeypatch.setattr(hass.config_entries, "async_forward_entry_setups", AsyncMock())
    monkeypatch.setattr(hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True))
    hass.config_entries._entries[entry.entry_id] = entry
    await integration.async_setup_entry(hass, entry)
    registry = er.async_get(hass)
    dr.async_setup(hass)
    await dr.async_load(hass, load_empty=True)
    await registry.async_load()
    entity = registry.async_get_or_create("media_player", "spotify_mini", "account-1", config_entry=entry)
    request.return_value = Response({"items": [{"uri": "spotify:playlist:"+"B"*22, "name": "Mine"}]})
    result = await hass.services.async_call("spotify_mini", "browse", {"entity_id": entity.entity_id},
                                            blocking=True, return_response=True)
    assert result["items"][0]["title"] == "Mine"
    request.return_value = Response(status=403)
    result = await hass.services.async_call("spotify_mini", "command", {"entity_id": entity.entity_id, "operation": "toggle"},
                                            blocking=True, return_response=True)
    assert result["error"] == "forbidden"
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call("spotify_mini", "browse", {"entity_id": "media_player.unrelated"},
                                      blocking=True, return_response=True)
    await integration.async_unload_entry(hass, entry)
    assert not hass.services.has_service("spotify_mini", "browse")
    assert not hass.services.has_service("spotify_mini", "command")
