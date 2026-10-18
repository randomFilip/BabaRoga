"""The My sources menu: add any address and BabaRoga works out what it is."""
import xbmc
import xbmcgui
import xbmcplugin
import xbmcvfs

from . import common, detect, mysources, net, player, resolvers
from .router import url

ONCE = "once"


def handle(action, params, menu):
    if action == "my":
        listing(menu)
    elif action == "my_add":
        add(params.get("t", "auto"))
    elif action == "my_once":
        once()
    elif action == "my_open":
        open_source(menu, params["s"], params.get("g"))
    elif action == "my_play":
        play(menu.handle, params["s"], int(params["i"]) if "i" in params else None, params.get("n"))
    elif action == "my_remove":
        if xbmcgui.Dialog().yesno(common.ADDON_NAME, "Remove this source?"):
            mysources.remove(params["s"])
            xbmc.executebuiltin("Container.Refresh")
    elif action == "my_rename":
        source = mysources.get(params["s"])
        if source:
            name = xbmcgui.Dialog().input("Name", source["name"])
            if name:
                mysources.rename(params["s"], name)
                xbmc.executebuiltin("Container.Refresh")


def _kind_of(source):
    return source.get("kind") or source["type"]


def listing(menu):
    menu.action("Add an address (type detected automatically)", "DefaultAddSource.png", action="my_add", t="auto")
    menu.action("Add a channel list file from this TV", "DefaultAddSource.png", action="my_add", t="file")
    menu.action("Open an address once (not saved)", "DefaultAddonsSearch.png", action="my_once")
    for s in mysources.load():
        kind = _kind_of(s)
        label = "{}  [COLOR grey]{}[/COLOR]".format(s["name"], detect.LABELS.get(kind, kind))
        li = xbmcgui.ListItem(label=label, offscreen=True)
        icon = "DefaultVideo.png" if s["type"] == "stream" else "DefaultNetwork.png"
        li.setArt({"icon": icon, "thumb": icon})
        li.addContextMenuItems([
            ("Rename", "RunPlugin({})".format(url(action="my_rename", s=s["id"]))),
            ("Remove", "RunPlugin({})".format(url(action="my_remove", s=s["id"]))),
        ])
        if s["type"] == "stream":
            li.getVideoInfoTag().setTitle(s["name"])
            li.setProperty("IsPlayable", "true")
            xbmcplugin.addDirectoryItem(menu.handle, url(action="my_play", s=s["id"]), li, isFolder=False)
        else:
            xbmcplugin.addDirectoryItem(menu.handle, url(action="my_open", s=s["id"]), li, isFolder=True)
    menu.end()


def _identify(address):
    """(type, kind, final address) or None if the person cancels."""
    xbmc.executebuiltin("ActivateWindow(busydialognocancel)")
    try:
        kind, final = detect.detect(address)
        error = None
    except (net.GeoBlocked, net.NotFound) as exc:
        kind, final, error = None, address, str(exc)
    except Exception as exc:
        kind, final, error = None, address, "could not connect ({})".format(exc.__class__.__name__)
    finally:
        xbmc.executebuiltin("Dialog.Close(busydialognocancel)")
    if error:
        if not xbmcgui.Dialog().yesno(common.ADDON_NAME, "Could not check this address: {}.[CR]Keep it as a web page anyway?".format(error)):
            return None
        kind = "page"
    if kind in ("page", "m3u"):
        return kind, kind, final
    return "stream", kind, final


def _ask_address():
    address = xbmcgui.Dialog().input("Address (https://...)", "https://")
    if address in ("", "https://", "http://"):
        return None
    if "://" not in address:
        address = "https://" + address
    return address.strip()


def add(how):
    dialog = xbmcgui.Dialog()
    if how == "file":
        address = dialog.browse(1, "Choose the channel list or stream file", "files", ".m3u|.m3u8|.txt")
        if not address:
            return
        f = xbmcvfs.File(address)
        try:
            text = f.read()
        finally:
            f.close()
        kind = detect.from_text(text) or "m3u"
        kind = "m3u" if kind == "page" else kind
        stype = "m3u" if kind == "m3u" else "stream"
    else:
        address = _ask_address()
        if not address:
            return
        found = _identify(address)
        if not found:
            return
        stype, kind, address = found
    default = address.replace("\\", "/").split("/")[-1] if how == "file" else address.split("//")[-1].split("/")[0]
    name = dialog.input("Name", default) or default
    mysources.add(stype, name, address, kind=kind)
    common.notify("Added {} as {}".format(name, detect.LABELS.get(kind, kind)))
    xbmc.executebuiltin("Container.Refresh")


def once():
    address = _ask_address()
    if not address:
        return
    found = _identify(address)
    if not found:
        return
    stype, kind, address = found
    mysources.set_once({"id": ONCE, "type": stype, "kind": kind, "name": address, "url": address})
    if stype == "stream":
        try:
            stream = _stream_for(mysources.get(ONCE))
        except Exception as exc:
            common.notify("Not playing: {}".format(exc))
            return
        li = player.list_item(stream, {"name": address})
        xbmc.Player().play(li.getPath(), li)
    else:
        xbmc.executebuiltin("Container.Update({})".format(url(action="my_open", s=ONCE)))


def _item(menu, label, logo, params):
    li = xbmcgui.ListItem(label=label, offscreen=True)
    art = logo or "DefaultVideo.png"
    li.setArt({"icon": art, "thumb": art})
    li.getVideoInfoTag().setTitle(label)
    li.setProperty("IsPlayable", "true")
    xbmcplugin.addDirectoryItem(menu.handle, url(**params), li, isFolder=False)


def open_source(menu, source_id, group=None):
    from . import m3u
    source = mysources.get(source_id)
    if not source:
        return menu.end()
    try:
        if source["type"] == "page":
            links = mysources.scan_page(source["url"])
            if not links:
                common.notify("No video links found on this page")
            for i, item in enumerate(links):
                _item(menu, mysources.link_label(item, i), "", dict(action="my_play", s=source_id, i=i))
        elif source["type"] == "m3u":
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
                        _item(menu, e["name"], e["logo"], dict(action="my_play", s=source_id, i=i))
        else:
            _item(menu, source["name"], "", dict(action="my_play", s=source_id))
    except net.GeoBlocked:
        common.notify("This address is not available from your country")
    except Exception as exc:
        common.log("open source {} failed: {}".format(source_id, exc))
        common.notify("Could not open: {}".format(exc))
    xbmcplugin.setContent(menu.handle, "videos")
    menu.end()


def _kind_for_entry(address, headers):
    """Stream type of one link; asks the server when the address does not say."""
    kind = resolvers.guess_kind(address)
    if kind == "file" and not detect.from_address(address) and address.startswith("http"):
        try:
            found, _ = detect.detect(address, headers=headers)
            if found in ("hls", "dash", "file"):
                return found
        except Exception as exc:
            common.log("could not identify {}: {}".format(address, exc))
    return kind


def _entry(source, index, name=None):
    """The list entry to play. The name is checked because a list that
    changes on its server can move channels to other positions."""
    entries = mysources.read_list(source)
    if name and not (0 <= index < len(entries) and entries[index]["name"] == name):
        for e in entries:
            if e["name"] == name:
                return e
    return entries[index]


def _stream_for(source, index=None, name=None):
    headers = {"User-Agent": net.USER_AGENT}
    props = {}
    if source["type"] == "page":
        # Search again at play time so short-lived links are fresh.
        item = mysources.scan_page(source["url"])[index]
        headers.update({"Referer": item["referer"], "Origin": net.origin_of(item["referer"])})
        address, kind = item["url"], item["kind"]
    elif source["type"] == "m3u":
        entry = _entry(source, index, name)
        headers.update(entry["headers"])
        props = entry.get("props", {})
        address = entry["url"]
        kind = _kind_for_entry(address, headers)
    else:
        address, kind = source["url"], source.get("kind")
    if any("license" in k for k in props):
        raise net.Protected("licence required")
    if kind == "youtube":
        if not address.startswith("plugin://"):
            address = detect.youtube_plugin_url(address)
        return resolvers.Stream(address, kind="plugin")
    stream = resolvers.Stream(address, headers, kind=kind if kind in ("hls", "dash", "file") else None)
    if stream.kind in ("hls", "dash"):
        resolvers.check_not_protected(stream)
    return stream


def play(handle, source_id, index=None, name=None):
    source = mysources.get(source_id)
    if not source:
        return player.fail(handle, "Source not found")
    try:
        stream = _stream_for(source, index, name)
    except net.GeoBlocked:
        return player.fail(handle, "Not available from your country")
    except net.Protected:
        return player.fail(handle, "Protected stream: BabaRoga does not play DRM")
    except Exception as exc:
        common.log("my_play {}/{} failed: {}".format(source_id, index, exc))
        return player.fail(handle, "This link is not playing right now")
    player.play(handle, stream, {"name": source["name"]})
