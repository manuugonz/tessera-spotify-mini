"""Use Home Assistant's credential storage and OAuth redirect handling."""
from homeassistant.components.application_credentials import AuthorizationServer


async def async_get_authorization_server(hass):
    return AuthorizationServer(
        authorize_url="https://accounts.spotify.com/authorize",
        token_url="https://accounts.spotify.com/api/token",
    )
