"""Menus and actions. URLs look like plugin://plugin.video.babaroga/?action=..."""
from urllib.parse import parse_qsl, urlencode

import xbmcgui
import xbmcplugin

from . import catalog, common, favourites, geo, health, net, player, resolvers

BASE = "plugin://{}/".format(common.ADDON_ID)


def url(**params):
    return BASE + "?" + urlencode(params)


class Menu(object):
    def __init__(self, handle):
        self.handle = handle

    def folder(self, label, icon="DefaultFolder.png", **params):
        li = xbmcgui.ListItem(label=label, offscreen=True)
        li.setArt({"icon": icon, "thumb": icon})
        xbmcplugin.addDirectoryItem(self.handle, url(**params), li, isFolder=True)

    def action(self, label, icon="DefaultAddonService.png", **params):
        li = xbmcgui.ListItem(label=label, offscreen=True)
        li.setArt({"icon": icon, "thumb": icon})
        xbmcplugin.addDirectoryItem(self.handle, url(**params), li, isFolder=False)

    def channel(self, ch, country, checks):
        tags = []
        state = health.status(ch["id"], checks)
        if catalog.is_locked_here(ch, country):
            tags.append("[COLOR orange]{} only[/COLOR]".format("/".join(ch["geo_lock"])))
        if state == health.OK:
            tags.append("[COLOR lime]OK[/COLOR]")
        elif state in (health.GEO, health.BROKEN):
            tags.append("[COLOR red]{}[/COLOR]".format("blocked here" if state == health.GEO else "not playing"))
        if ch.get("status") != "passed":
            tags.append("[COLOR grey]to test[/COLOR]")
        if ch.get("access") == "free_account":
            tags.append("[COLOR grey]account[/COLOR]")
        label = ch["name"] + ("  " + " ".join(tags) if tags else "")

        li = xbmcgui.ListItem(label=label, offscreen=True)
        logo = ch.get("logo") or "DefaultTVShows.png"
        li.setArt({"thumb": logo, "icon": logo, "poster": logo})
        genres = ", ".join(catalog.GENRE_NAMES.get(g, g) for g in ch.get("genres", []))
        tag = li.getVideoInfoTag()
        tag.setTitle(ch["name"])
        tag.setPlot("{}\n{}\n{}".format(
            catalog.COUNTRY_NAMES.get(ch["country"], ch["country"]), genres, ch.get("notes", "")).strip())
        tag.setMediaType("video")
        li.setProperty("IsPlayable", "true")
        if favourites.is_favourite(ch["id"]):
            li.addContextMenuItems([("Remove from favourites", "RunPlugin({})".format(url(action="fav_remove", id=ch["id"])))])
        else:
            li.addContextMenuItems([("Add to favourites", "RunPlugin({})".format(url(action="fav_add", id=ch["id"])))])
        xbmcplugin.addDirectoryItem(self.handle, url(action="play", id=ch["id"]), li, isFolder=False)

    def channels(self, items, country):
        checks = health.load()
        shown = 0
        for ch in items:
            if health.is_hidden(ch["id"], checks):
                continue
            self.channel(ch, country, checks)
            shown += 1
        xbmcplugin.setContent(self.handle, "videos")
        return shown

    def end(self, sort=False):
        if sort:
            xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.endOfDirectory(self.handle)


def home(menu, country):
    name = catalog.COUNTRY_NAMES.get(country)
    if name and any(ch["country"] == country for ch in catalog.visible(country)):
        menu.folder("My country: {}".format(name), "DefaultCountry.png", action="country", c=country)
    menu.folder("Balkans by country", "DefaultCountry.png", action="countries")
    menu.folder("By genre", "DefaultGenre.png", action="genres")
    menu.folder("Favourites", "DefaultFavourites.png", action="favourites")
    menu.folder("Recently watched", "DefaultRecentlyAddedEpisodes.png", action="recent")
    menu.folder("Search", "DefaultAddonsSearch.png", action="search")
    menu.folder("My sources", "DefaultNetwork.png", action="my")
    menu.folder("Tools", "DefaultAddonProgram.png", action="tools")
    menu.end()


# ---- My sources -------------------------------------------------------------

def my_menu(menu):
    from . import mysources
    menu.action("Add a web page", "DefaultAddSource.png", action="my_add", t="page")
    menu.action("Add a channel list (M3U) from a web address", "DefaultAddSource.png", action="my_add", t="m3u")
    menu.action("Add a channel list (M3U) from a file on this TV", "DefaultAddSource.png", action="my_add", t="m3u_file")
    for s in mysources.load():
        li = xbmcgui.ListItem(label="{}  [COLOR grey]{}[/COLOR]".format(s["name"], "web page" if s["type"] == "page" else "channel list"), offscreen=True)
        li.setArt({"icon": "DefaultNetwork.png", "thumb": "DefaultNetwork.png"})
        li.addContextMenuItems([
            ("Rename", "RunPlugin({})".format(url(action="my_rename", s=s["id"]))),
            ("Remove", "RunPlugin({})".format(url(action="my_remove", s=s["id"]))),
        ])
        xbmcplugin.addDirectoryItem(menu.handle, url(action="my_open", s=s["id"]), li, isFolder=True)
    menu.end()


def my_add(kind):
    from . import mysources
    dialog = xbmcgui.Dialog()
    if kind == "m3u_file":
        address = dialog.browse(1, "Choose the channel list", "files", ".m3u|.m3u8")
        kind = "m3u"
    else:
        address = dialog.input("Web address (https://...)", "https://")
        if address in ("", "https://", "http://"):
            return
    if not address:
        return
    name = dialog.input("Name", address.split("//")[-1].split("/")[0])
    mysources.add(kind, name or address, address)
    common.notify("Added: {}".format(name or address))
    import xbmc
    xbmc.executebuiltin("Container.Refresh")


def _my_item(menu, label, logo, play_params):
    li = xbmcgui.ListItem(label=label, offscreen=True)
    art = logo or "DefaultVideo.png"
    li.setArt({"icon": art, "thumb": art})
    li.getVideoInfoTag().setTitle(label)
    li.setProperty("IsPlayable", "true")
    xbmcplugin.addDirectoryItem(menu.handle, url(**play_params), li, isFolder=False)


def my_open(menu, source_id, group=None):
    from . import mysources
    source = mysources.get(source_id)
    if not source:
        return menu.end()
    try:
        if source["type"] == "page":
            links = mysources.scan_page(source["url"])
            if not links:
                common.notify("No video links found on this page")
            for i, item in enumerate(links):
                _my_item(menu, mysources.link_label(item, i), "", dict(action="my_play", s=source_id, i=i))
        else:
            from . import m3u
            entries = mysources.read_list(source)
            groups = m3u.groups(entries)
            if group is None and len(groups) > 1:
                for g in groups:
                    menu.folder(g, "DefaultGenre.png", action="my_open", s=source_id, g=g)
                if any(not e["group"] for e in entries):
                    menu.folder("Other", "DefaultGenre.png", action="my_open", s=source_id, g="")
            else:
                for i, e in enumerate(entries):
                    if group is None or e["group"] == group:
                        _my_item(menu, e["name"], e["logo"], dict(action="my_play", s=source_id, i=i))
    except net.GeoBlocked:
        common.notify("This address is not available from your country")
    except Exception as exc:
        common.log("open source {} failed: {}".format(source_id, exc))
        common.notify("Could not open: {}".format(exc))
    xbmcplugin.setContent(menu.handle, "videos")
    menu.end()


def my_play(handle, source_id, index):
    from . import mysources
    source = mysources.get(source_id)
    if not source:
        return player.fail(handle, "Source not found")
    try:
        if source["type"] == "page":
            # Scan again at play time so short-lived links are fresh.
            item = mysources.scan_page(source["url"])[index]
            headers = {"User-Agent": net.USER_AGENT, "Referer": item["referer"],
                       "Origin": net.origin_of(item["referer"])}
            entry = {"name": source["name"], "url": item["url"], "headers": headers, "props": {}, "logo": ""}
        else:
            entry = mysources.read_list(source)[index]
            entry["headers"].setdefault("User-Agent", net.USER_AGENT)
        if any("license" in k for k in entry.get("props", {})):
            raise net.Protected("licence required")
        stream = resolvers.Stream(entry["url"], entry["headers"])
        if stream.kind in ("hls", "dash"):
            resolvers.check_not_protected(stream)
    except net.GeoBlocked:
        return player.fail(handle, "Not available from your country")
    except net.Protected:
        return player.fail(handle, "Protected stream: BabaRoga does not play DRM")
    except Exception as exc:
        common.log("my_play {}/{} failed: {}".format(source_id, index, exc))
        return player.fail(handle, "This link is not playing right now")
    player.play(handle, stream, entry)


def country_menu(menu, country, code, genre=None):
    items = [ch for ch in catalog.visible(country) if ch["country"] == code]
    if genre:
        items = [ch for ch in items if genre in ch.get("genres", [])]
        menu.channels(items, country)
        return menu.end(sort=True)
    genres = catalog.genres_with_channels(country, in_country=code)
    if len(genres) > 1:
        for key, name in genres:
            menu.folder(name, "DefaultGenre.png", action="country", c=code, g=key)
        menu.folder("All channels", "DefaultTVShows.png", action="country", c=code, g="")
        return menu.end()
    menu.channels(items, country)
    menu.end(sort=True)


def run(argv):
    handle = int(argv[1])
    params = dict(parse_qsl(argv[2].lstrip("?")))
    action = params.get("action", "home")
    country = geo.country()
    menu = Menu(handle)

    if action == "home":
        home(menu, country)
    elif action == "countries":
        for code, name in catalog.countries_with_channels(country):
            menu.folder(name, "DefaultCountry.png", action="country", c=code)
        menu.end()
    elif action == "country":
        code = params["c"]
        genre = params.get("g")
        if genre == "":
            menu.channels([ch for ch in catalog.visible(country) if ch["country"] == code], country)
            menu.end(sort=True)
        else:
            country_menu(menu, country, code, genre)
    elif action == "genres":
        for key, name in catalog.genres_with_channels(country):
            menu.folder(name, "DefaultGenre.png", action="genre", g=key)
        menu.end()
    elif action == "genre":
        key = params["g"]
        items = [ch for ch in catalog.visible(country) if key in ch.get("genres", [])]
        # Your own country's channels first, then the rest by country order.
        order = {code: i for i, (code, _) in enumerate(catalog.COUNTRIES)}
        items.sort(key=lambda ch: (ch["country"] != country, order.get(ch["country"], 99), ch["name"]))
        menu.channels(items, country)
        menu.end()
    elif action == "favourites":
        menu.channels([c for c in (catalog.by_id(i) for i in favourites.favourites()) if c], country)
        menu.end()
    elif action == "recent":
        menu.channels([c for c in (catalog.by_id(i) for i in favourites.recent()) if c], country)
        menu.end()
    elif action == "search":
        text = xbmcgui.Dialog().input("Channel name")
        if text:
            low = text.lower()
            menu.channels([ch for ch in catalog.visible(country) if low in ch["name"].lower()], country)
        menu.end(sort=True)
    elif action == "my":
        my_menu(menu)
    elif action == "my_add":
        my_add(params.get("t", "page"))
    elif action == "my_open":
        my_open(menu, params["s"], params.get("g"))
    elif action == "my_play":
        my_play(handle, params["s"], int(params["i"]))
    elif action == "my_remove":
        from . import mysources
        if xbmcgui.Dialog().yesno(common.ADDON_NAME, "Remove this source?"):
            mysources.remove(params["s"])
            import xbmc
            xbmc.executebuiltin("Container.Refresh")
    elif action == "my_rename":
        from . import mysources
        source = mysources.get(params["s"])
        if source:
            name = xbmcgui.Dialog().input("Name", source["name"])
            if name:
                mysources.rename(params["s"], name)
                import xbmc
                xbmc.executebuiltin("Container.Refresh")
    elif action == "tools":
        menu.action("Update the channel list now", action="update_now")
        menu.action("Check all channels now", action="check_now")
        menu.action("Settings", "DefaultAddonProgram.png", action="settings")
        menu.end()
    elif action == "play":
        play(handle, params["id"])
    elif action == "fav_add":
        favourites.add(params["id"])
        common.notify("Added to favourites")
    elif action == "fav_remove":
        favourites.remove(params["id"])
        common.notify("Removed from favourites")
        import xbmc
        xbmc.executebuiltin("Container.Refresh")
    elif action == "update_now":
        try:
            changed = catalog.update_from_github()
            common.notify("Channel list updated" if changed else "Channel list is already up to date")
        except Exception as exc:
            common.notify("Update failed: {}".format(exc))
    elif action == "check_now":
        progress = xbmcgui.DialogProgress()
        progress.create(common.ADDON_NAME, "Checking channels")
        items = catalog.all_channels()
        for i, ch in enumerate(items):
            if progress.iscanceled():
                break
            progress.update(int(i * 100 / max(len(items), 1)), ch["name"])
            if (ch.get("source") or {}).get("type") != "youtube" and ch.get("status") != "failed":
                health.record(ch["id"], health.check(ch))
        progress.close()
    elif action == "settings":
        common.ADDON.openSettings()
    elif action == "iptv_channels":
        from . import iptvmanager
        iptvmanager.send_channels(params["port"])
    elif action == "iptv_epg":
        from . import iptvmanager
        iptvmanager.send_epg(params["port"])


def play(handle, channel_id):
    ch = catalog.by_id(channel_id)
    if not ch:
        return player.fail(handle, "Channel not found")
    try:
        stream = resolvers.resolve(ch)
    except net.GeoBlocked:
        health.record(ch["id"], health.GEO)
        return player.fail(handle, "{} is not available from your country".format(ch["name"]))
    except net.Protected:
        health.record(ch["id"], health.PROTECTED)
        return player.fail(handle, "Protected stream: watch it on the official site")
    except Exception as exc:
        common.log("play {} failed: {}".format(channel_id, exc))
        return player.fail(handle, "{} is not playing right now".format(ch["name"]))
    favourites.touch(ch["id"])
    player.play(handle, stream, ch)
