package tessera

import (
 "encoding/json"
 "slices"
 "testing"
)

func TestSpotifyProbeIsNotSupportedUpstream(t *testing.T) {
 c := capabilities(gridFor(true, false))
 if slices.Contains(c.Features, "plugins") { t.Fatal("upstream now advertises plugins: reassess adapter") }
 tile := placedTile(0, 0, "square", "plugin:spotify_mini.player", "", `{}`)
 tile.Name = "Spotify probe"
 tile.X = json.RawMessage(`{"state":"playing","attributes":{"media_title":"Touch test"}}`)
 p := describe(tile, tileOptions(tile))
 if p.Taps { t.Fatal("upstream unexpectedly supports a plugin tap") }
 if p.Value == "Touch test" { t.Fatal("upstream unexpectedly consumes plugin payload") }
 t.Log("Echo Show 8 capabilities lack plugins; the plugin probe has no tap handler or plugin data renderer")
}
