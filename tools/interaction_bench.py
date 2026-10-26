#!/usr/bin/env python3
"""Drive the real LVGL plugin via the official bench and simulated Spotify answers.

Usage: TESSERA_TREE=/path/to/tessera python tools/interaction_bench.py /path/to/tessera-plugins . --board guition --strict
Only the temporary host build gets the label-location probe; shipped firmware is unchanged.
"""
import asyncio
import json
from pathlib import Path
import re
import sys

sdk = Path(sys.argv.pop(1)).resolve()
sys.path.insert(0, str(sdk / "tools"))
import bench  # noqa: E402

bench.host.PROBES += '''    - action: spotify_probe_label
      variables:
        needle: string
        occurrence: int
      then:
        - lambda: |-
            int seen = 0;
            std::function<void(lv_obj_t *)> walk = [&](lv_obj_t *o) {
              if (!lv_obj_is_visible(o)) return;
              if (lv_obj_check_type(o, &lv_label_class) && needle == lv_label_get_text(o)) {
                if (seen++ == occurrence) {
                  lv_area_t b; lv_obj_get_coords(o, &b);
                  ESP_LOGI("render", "spotify target %d %d", (b.x1+b.x2)/2, (b.y1+b.y2)/2);
                }
              }
              for (uint32_t i=0; i<lv_obj_get_child_count(o); ++i) walk(lv_obj_get_child(o,i));
            };
            walk(lv_screen_active());
'''
original_answer = bench.Bench.answer
original_cards = bench.Bench.cards


async def answer(self, data):
    body = json.loads(data.get("body") or "{}")
    self.spotify_requests = getattr(self, "spotify_requests", []) + [body]
    if body.get("ask") == "call_service:spotify_mini.browse":
        category = body.get("data", {}).get("category")
        if category == "devices":
            items = [{"uri": "test-device-handle", "title": "Echo Show 8", "kind": "device"}]
        elif category == "home":
            self.spec["commands"][body["ask"]] = {
                "recent": [{"uri": "spotify:track:0000000000000000000001", "title": "Recent song",
                            "artist": "Example", "cover": "0" * 40, "kind": "track"}],
                "recommended": [{"uri": "spotify:playlist:0000000000000000000001", "title": "Suggested mix",
                                 "artist": "Example", "cover": "0" * 40, "kind": "playlist"}]}
            return await original_answer(self, data)
        else:
            kind = body.get("data", {}).get("kind", "playlist") if category == "search" else "playlist"
            items = [{"uri": f"spotify:{kind}:0000000000000000000001", "title": "Test music",
                      "artist": "Example", "cover": "0" * 40, "kind": kind}]
        self.spec["commands"][body["ask"]] = {"items": items, "more": False}
    return await original_answer(self, data)


async def tap_label(self, text, occurrence=0):
    start = len(self.lines)
    await self.call("spotify_probe_label", needle=text, occurrence=occurrence)
    line = await self.until(lambda line: "spotify target " in line, 4, "label " + text, start)
    x, y = map(int, re.search(r"spotify target (\d+) (\d+)", line).groups())
    await self.tap(x, y)
    await asyncio.sleep(.8)


async def cards(self, out, view):
    await original_cards(self, out, view)
    for dark in (False, True):
        await self.dark(dark)
        await self.call("render_close_cards")
        await self.call("render_page", page=0)
        await self.page_done(0)
        centre, area = await self.box(0)
        assert area, "first tile must be visible"
        await self.tap(*centre)
        await asyncio.sleep(.6)
        theme = "dark" if dark else "light"
        await self.pictures_settled()
        (await self.render("interaction-player-" + theme, keep=False)).save(out / ("interaction-player-" + theme + ".png"))
        self.faults(await self.audit(card=True), "interactive player " + theme)
        await self.tap(61, 114)
        await asyncio.sleep(.8)
        assert self.spotify_requests[-1]["data"]["category"] == "devices"
        self.faults(await self.audit(card=True), "interactive devices " + theme)
        await self.tap(45, 45)
        await asyncio.sleep(.3)
        await self.tap(414, 114)
        await asyncio.sleep(.8)
        assert self.spotify_requests[-1]["data"]["category"] == "home"
        await self.pictures_settled()
        (await self.render("interaction-menu-" + theme, keep=False)).save(out / ("interaction-menu-" + theme + ".png"))
        self.faults(await self.audit(card=True), "interactive menu " + theme)
        await tap_label(self, "Library")
        assert self.spotify_requests[-1]["data"]["category"] == "playlists"
        self.faults(await self.audit(card=True), "interactive library " + theme)
        await self.tap(45, 45)
        await asyncio.sleep(.3)
        await self.tap(45, 45)
        await asyncio.sleep(.3)
        await self.tap(414, 114)
        await asyncio.sleep(.8)
        await tap_label(self, "Search music")
        await tap_label(self, "a")
        await tap_label(self, "b")
        (await self.render("interaction-keyboard-" + theme, keep=False)).save(out / ("interaction-keyboard-" + theme + ".png"))
        self.faults(await self.audit(card=True), "interactive keyboard " + theme)
        await tap_label(self, "Search")
        assert self.spotify_requests[-1]["data"]["query"] == "ab"
        assert self.spotify_requests[-1]["data"]["category"] == "search"
        await self.pictures_settled()
        self.faults(await self.audit(card=True), "interactive search " + theme)
        await tap_label(self, "Test music")
        assert self.spotify_requests[-1]["ask"] == "call_service:spotify_mini.command"
        assert self.spotify_requests[-1]["data"]["operation"] == "play_uri"
        assert self.spotify_requests[-1]["data"]["value"].startswith("spotify:track:")
        # After successful selection, the now-playing title is back on the card.
        start = len(self.lines)
        await self.call("spotify_probe_label", needle="Evening Walk", occurrence=0)
        await self.until(lambda line: "spotify target " in line, 4, "automatic return to player", start)
        await self.call("render_close_cards")
    (out / "interaction-requests.json").write_text(json.dumps(self.spotify_requests, indent=2))


bench.Bench.answer = answer
bench.Bench.cards = cards
raise SystemExit(bench.main())
