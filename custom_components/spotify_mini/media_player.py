"""A normal HA media player, also used by TECHO5's existing media controls."""
from datetime import UTC, datetime
from homeassistant.components.media_player import MediaPlayerEntity, MediaPlayerEntityFeature as F, MediaPlayerState
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.exceptions import HomeAssistantError
from .api import SpotifyError


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([SpotifyMiniPlayer(entry)])


class SpotifyMiniPlayer(CoordinatorEntity, MediaPlayerEntity):
    _attr_name = "Spotify Mini"
    _attr_icon = "mdi:spotify"
    _attr_has_entity_name = True

    def __init__(self, entry):
        super().__init__(entry.runtime_data)
        self._attr_unique_id = entry.unique_id
        self._position_at = datetime.now(UTC)

    @property
    def data(self):
        return self.coordinator.data or {}

    @property
    def available(self):
        return self.data.get("state") != "unavailable"

    @property
    def state(self):
        return {"playing": MediaPlayerState.PLAYING, "paused": MediaPlayerState.PAUSED}.get(self.data.get("state"), MediaPlayerState.IDLE)

    @property
    def supported_features(self):
        features = F.PLAY_MEDIA | F.PLAY | F.PAUSE | F.NEXT_TRACK | F.PREVIOUS_TRACK | F.SEEK
        if self.data.get("volume_supported"):
            features |= F.VOLUME_SET | F.VOLUME_STEP
        return features

    @property
    def media_title(self):
        return self.data.get("title", "")

    @property
    def media_artist(self):
        return self.data.get("artist", "")

    @property
    def media_image_url(self):
        return "https://i.scdn.co/image/" + self.data["cover"] if self.data.get("cover") else None

    @property
    def media_duration(self):
        return self.data.get("duration", 0)

    @property
    def media_position(self):
        return self.data.get("position", 0)

    @property
    def media_position_updated_at(self):
        return self._position_at

    _position_at = None

    def _handle_coordinator_update(self):
        self._position_at = datetime.now(UTC)
        super()._handle_coordinator_update()

    @property
    def volume_level(self):
        value = self.data.get("volume")
        return value / 100 if value is not None else None

    @property
    def extra_state_attributes(self):
        return {"mini_cover": self.data.get("cover", ""), "mini_error": self.data.get("error", ""),
                "mini_device": self.data.get("device", ""), "mini_volume": self.data.get("volume_supported", False),
                "mini_position_at": self._position_at.timestamp() if self._position_at else 0}

    async def _command(self, op, value=""):
        try:
            await self.coordinator.command(op, value)
        except SpotifyError as exc:
            raise HomeAssistantError(exc.code) from exc

    async def async_media_play(self):
        await self._command("play")

    async def async_media_pause(self):
        await self._command("pause")

    async def async_media_play_pause(self):
        await self._command("toggle")

    async def async_media_next_track(self):
        await self._command("next")

    async def async_media_previous_track(self):
        await self._command("previous")

    async def async_set_volume_level(self, volume):
        await self._command("volume", str(round(volume * 100)))

    async def async_volume_up(self):
        await self._command("volume_up")

    async def async_volume_down(self):
        await self._command("volume_down")

    async def async_media_seek(self, position):
        await self._command("seek", str(position))

    async def async_play_media(self, media_type, media_id, **kwargs):
        await self._command("play_uri", media_id)
