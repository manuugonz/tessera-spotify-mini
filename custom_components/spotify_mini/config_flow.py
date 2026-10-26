"""Spotify OAuth authorization and reauthorization in Home Assistant only."""
import logging
import asyncio
import aiohttp
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN, SCOPES


class ConfigFlow(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    DOMAIN = DOMAIN
    VERSION = 1

    @property
    def logger(self):
        return logging.getLogger(__name__)

    @property
    def extra_authorize_data(self):
        return {"scope": " ".join(SCOPES), "show_dialog": "true"}

    async def async_oauth_create_entry(self, data):
        session = async_get_clientsession(self.hass)
        try:
            async with asyncio.timeout(15), session.get("https://api.spotify.com/v1/me", headers={
                "Authorization": "Bearer " + data["token"]["access_token"]
            }, allow_redirects=False) as response:
                if response.status != 200:
                    return self.async_abort(reason="cannot_connect")
                profile = await response.json()
        except (OSError, TimeoutError, ValueError, aiohttp.ClientError):
            return self.async_abort(reason="cannot_connect")
        if not profile.get("id"):
            return self.async_abort(reason="cannot_connect")
        await self.async_set_unique_id(profile["id"])
        if self.source == "reauth":
            self._abort_if_unique_id_mismatch()
            return self.async_update_reload_and_abort(self._get_reauth_entry(), data_updates=data)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=profile.get("display_name") or "Spotify Mini", data=data)

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        return await self.async_step_pick_implementation(user_input={
            "implementation": self._get_reauth_entry().data["auth_implementation"]
        })
