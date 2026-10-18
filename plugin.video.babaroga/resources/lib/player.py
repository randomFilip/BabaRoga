"""Turn a resolved Stream into something Kodi plays."""
from urllib.parse import quote

import xbmcgui
import xbmcplugin

from . import common


def header_string(headers):
    return "&".join("{}={}".format(k, quote(v, safe="")) for k, v in headers.items())


def list_item(stream, ch):
    li = xbmcgui.ListItem(label=ch["name"], path=stream.url, offscreen=True)
    if ch.get("logo"):
        li.setArt({"thumb": ch["logo"], "icon": ch["logo"]})
    if stream.kind in ("hls", "dash"):
        headers = header_string(stream.headers)
        li.setProperty("inputstream", "inputstream.adaptive")
        if common.kodi_major() >= 22:
            li.setProperty("inputstream.adaptive.common_headers", headers)
        else:
            li.setProperty("inputstream.adaptive.manifest_headers", headers)
            li.setProperty("inputstream.adaptive.stream_headers", headers)
        li.setMimeType("application/vnd.apple.mpegurl" if stream.kind == "hls" else "application/dash+xml")
        li.setContentLookup(False)
    return li


def play(handle, stream, ch):
    xbmcplugin.setResolvedUrl(handle, True, list_item(stream, ch))


def fail(handle, message):
    common.notify(message)
    xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
