"""Public contracts; credentials never cross this boundary."""
DOMAIN = "spotify_mini"
SCOPES = (
    "user-read-playback-state", "user-modify-playback-state",
    "playlist-read-private", "playlist-read-collaborative",
    "user-read-recently-played", "user-library-read",
)
PAGE_SIZE = 3
