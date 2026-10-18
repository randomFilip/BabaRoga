# BabaRoga

A Kodi add-on for free, official live TV from the Balkans. It works like a browser on the TV: it plays a channel exactly the way the broadcaster's own website does, sorted by country and genre.

Built for Kodi 21 "Omega" on Android TV (tested target: TCL C6K), and checked against Kodi 22 "Piers".

## Rules

Every channel must pass all of these, or it stays out:

1. **Official source.** The stream comes from the channel owner: its website player, its own streaming servers, or its official YouTube channel.
2. **Free the way a visitor gets it.** No login, or a free account you made yourself. No paid packages, no shared logins.
3. **Same requests as the browser.** The add-on loads the same page or player data the official site uses. It never forges tokens or skips a login.
4. **No DRM.** Widevine or PlayReady streams are skipped.
5. **No geo-unlocking.** A geo-locked channel plays only in its home country. No VPN or proxy tricks.
6. **Personal use.** Logos and ads stay as the broadcaster serves them. Nothing is recorded or shared.
7. **When in doubt, leave it out.**

Never added: links from telecom TV platforms, bare IP addresses, "free IPTV" lists or repositories that restream channels.

## Install on the TV

1. Kodi: Settings → System → Add-ons → turn on **Unknown sources**.
2. Settings → **File manager** → **Add source** → `<None>` → type `https://randomfilip.github.io/BabaRoga/` → name it `BabaRoga` → OK.
3. Settings → Add-ons → **Install from zip file** → `BabaRoga` → `repository.babaroga-1.0.0.zip`.
4. Add-ons → **Install from repository** → BabaRoga Repository → Video add-ons → BabaRoga → Install.
5. Open it from Add-ons → Video add-ons → BabaRoga.

Installed this way, Kodi updates the add-on by itself. The channel list also updates once a day from this repository, so new or fixed channels arrive without a new add-on version.

### Kodi's TV section (optional)

BabaRoga settings → **TV guide** → **Install IPTV Manager**, then turn on **Show channels in Kodi's TV section**. Your channels then appear under TV like normal channels: zap with channel up/down and open the guide.

- **Include my channel lists:** the channels of your My sources M3U lists go there too, grouped by list and by the list's own groups.
- **Load the TV guide named in my lists:** when a list names a guide in its first line (`#EXTM3U url-tvg="..."`), its programmes are shown for channels with a matching `tvg-id`. Plain and `.gz` guides work; only the next 36 hours are kept, to spare the TV's memory.

The guide for BabaRoga's official channels comes in a later version.

## My sources

BabaRoga → **My sources** → **Add an address**: type any address and BabaRoga works out what it is, first from the address and, when that is not enough, from what the server sends back (content type and the first bytes), the way a browser does.

| Detected as | What happens |
| --- | --- |
| HLS stream (`#EXTM3U` with `#EXT-X-` tags) | Plays directly |
| DASH stream (`<MPD`) | Plays directly |
| Video file (mp4, webm, mkv, MPEG-TS) | Plays directly |
| Channel list (`#EXTM3U` with channels) | Opens as a list; group titles become folders |
| YouTube video, live or channel | Plays through the YouTube add-on |
| Web page | Searched for videos (see below) |

Inside channel lists and web pages, links without a telling extension (for example `https://site/live?id=1`) are identified the same way when you press play.

On a **web page** BabaRoga lists every video it finds, best first:
- HLS (`.m3u8`) and DASH (`.mpd`) links, absolute or relative
- `<video>` and `<source>` tags, including `.mp4` and `.webm` files
- player settings (JW Player, Video.js, Clappr, Flowplayer and similar), including links with no extension
- schema.org video data, and links written in base64
- embedded players (iframes), two levels deep
- YouTube videos and YouTube channel live streams

Links are looked up again when you press play, so short-lived links stay fresh. Ad and tracking links are skipped.

Other options: **Add a channel list file from this TV** (USB stick or local storage) and **Open an address once** (plays or opens it without saving).

Every channel list keeps a copy on the TV: a list added from a file is copied when you add it (the USB stick can be removed afterwards), and a list from a web address is copied each time it loads, so it still opens when its server is down.

My sources are stored only on the TV and never go into the shared channel list. DRM-protected streams are not played. Long-press (context menu) a source to rename or remove it.

## Adding or checking a channel (browser test)

1. Find the official site from the broadcaster itself, never from a channel list.
2. Open its live page in Chrome on a PC, press F12, open **Network**, filter by `m3u8` (or `mpd`) and press play.
3. The stream host must be the broadcaster's own domain or the delivery network its official player uses.
4. It must play without signing in, or with a free account.
5. A licence request in the Network tab, or Widevine/PlayReady in the manifest, means exclude.
6. Note whether the page says it only works in its country, and whether it plays from North Macedonia.
7. Update the channel in `plugin.video.babaroga/resources/data/channels.json`:
   - `status`: `"passed"` (or `"failed"`)
   - `verified`: the test date, for example `"2026-10-20"`
   - `evidence`: what you saw, for example `"Plays without login; Network tab shows live.mrt.com.mk .m3u8"`
   - `source.pattern`: only if the default search does not find the link on the page
8. Raise `version` at the top of the file (for example `2026102001`), then run `python tools/validate_channels.py`.
9. Re-test every three months, and at once when a channel breaks.

### Channel entry

```json
{
  "id": "MRT1.mk",
  "name": "MRT 1",
  "country": "MK",
  "genres": ["general"],
  "logo": "https://...",
  "website": "https://www.mrt.com.mk/",
  "source": {"type": "page", "url": "https://play.mrt.com.mk/live/mrt1"},
  "headers": {"Referer": "https://play.mrt.com.mk/"},
  "access": "free",
  "geo_lock": null,
  "drm": false,
  "status": "to_test",
  "verified": null,
  "evidence": ""
}
```

- **Source types:** `direct` (fixed link on the broadcaster's server), `page` (find the link on the official live page), `api` (ask the official player's JSON endpoint; set `path`), `youtube` (`channel_id` or `video_id`).
- **Genres:** `news`, `general`, `sports`, `music`, `kids`, `movies`, `documentary`, `religious`, `regional`, `parliament`.
- **geo_lock:** `null` when unknown or none, or a list such as `["MK"]`.
- **access:** `free` or `free_account`.

Names, ids and logos start from the public-domain [iptv-org database](https://github.com/iptv-org/database). Stream sources come only from the browser test.

## Releasing

1. Raise `version` in `plugin.video.babaroga/addon.xml` and add a line to `<news>`.
2. Run `python tools/build_repo.py` and commit everything, including `docs/`.
3. Push. GitHub Pages serves `docs/`, and every TV with the BabaRoga Repository picks up the new version.

The Check workflow fails if `docs/` was not rebuilt after a change to an add-on.

Changes to `channels.json` alone need no release: the add-on picks them up within a day.

## Layout

```text
plugin.video.babaroga/
├── addon.xml
├── main.py                 menus and playback
├── service.py              background: daily list update, channel checks
└── resources/
    ├── settings.xml
    ├── data/channels.json  the verified channel list
    └── lib/
        ├── router.py       menus and actions
        ├── catalog.py      channel list, countries, genres, updates
        ├── geo.py          country detection
        ├── resolvers/      direct, page, api, youtube
        ├── player.py       hands the stream to inputstream.adaptive
        ├── health.py       channel checks
        ├── favourites.py   favourites and recently watched
        ├── detect.py       works out what an address is
        ├── finder.py       finds the videos on a web page
        ├── m3u.py          reads channel lists
        ├── mysources.py    your own sources (stored on the TV)
        ├── mymenu.py       the My sources menu
        ├── xmltv.py        reads TV guides for your lists
        └── iptvmanager.py  channels for Kodi's TV section
repository.babaroga/        Kodi repository add-on (points at GitHub Pages)
docs/                       generated by tools/build_repo.py, served by GitHub Pages
tools/
├── validate_channels.py
└── build_repo.py
```

## Roadmap

- **Phase 1:** North Macedonia first, then neighbouring countries. Menus, geolocation, favourites, search.
- **Phase 2:** all 11 countries, sign-in for free-account services (RTS Planeta, HRTi, ERTFLIX, TVR+), TV guide, sports today.
- **Phase 3:** catch-up and free on-demand from broadcasters' own archives.
