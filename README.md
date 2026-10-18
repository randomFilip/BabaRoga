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

1. Download the latest `plugin.video.babaroga-x.y.z.zip` from [Releases](https://github.com/randomFilip/BabaRoga/releases) onto a USB stick, or note its link.
2. In Kodi: Settings → System → Add-ons → turn on **Unknown sources**.
3. Settings → Add-ons → **Install from zip file** → pick the zip.
4. Open it from Add-ons → Video add-ons → BabaRoga.

The channel list updates itself once a day from this repository, so new or fixed channels arrive without reinstalling.

Optional: install **IPTV Manager** and turn it on in BabaRoga's settings to see the channels in Kodi's TV section.

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
2. Commit, then tag: `git tag v0.1.1 && git push --tags`.
3. GitHub Actions checks the channel list and publishes the zip on the Releases page.

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
        └── iptvmanager.py  channels for Kodi's TV section
tools/
├── validate_channels.py
└── build_zip.py
```

## Roadmap

- **Phase 1:** North Macedonia first, then neighbouring countries. Menus, geolocation, favourites, search.
- **Phase 2:** all 11 countries, sign-in for free-account services (RTS Planeta, HRTi, ERTFLIX, TVR+), TV guide, sports today.
- **Phase 3:** catch-up and free on-demand from broadcasters' own archives.
