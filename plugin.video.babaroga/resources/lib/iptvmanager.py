"""Channels and guide for IPTV Manager, which feeds Kodi's TV section.

IPTV Manager opens a socket on localhost and passes its port; we connect at
once (so it does not give up waiting) and then send JSON-STREAMS (channels)
or JSON-EPG (guide) data.

Sent:
  - BabaRoga's official channels
  - the channels of your My sources channel lists (setting), with the guide
    named in each list's header (url-tvg) when there is one (setting)
"""
import json
import socket
from urllib.parse import urlencode

from . import catalog, common, geo

PLUGIN = "plugin://plugin.video.babaroga/"


class _Socket(object):
    def __init__(self, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(("127.0.0.1", int(port)))

    def send(self, payload):
        try:
            self.sock.sendall(json.dumps(payload).encode("utf-8"))
        finally:
            self.sock.close()

    def close(self):
        self.sock.close()


def _include_my_lists():
    return common.setting("iptv.my_lists") != "false"


def _include_my_guides():
    return common.setting("iptv.my_guides") != "false"


def _my_lists():
    """[(source, entries, guide addresses)] for every channel list in My sources."""
    from . import mysources
    out = []
    for source in mysources.load():
        if source["type"] != "m3u":
            continue
        try:
            entries, guides = mysources.read_list_with_guide(source)
        except Exception as exc:
            common.log("TV section: list {} skipped: {}".format(source["name"], exc))
            continue
        out.append((source, entries, guides))
    return out


def _my_channel_id(source, index, entry):
    return "my{}-{}".format(source["id"], entry.get("tvg_id") or index)


def channels():
    country = geo.country()
    streams = []
    for ch in catalog.visible(country):
        if catalog.is_locked_here(ch, country):
            continue
        streams.append({
            "id": ch["id"],
            "name": ch["name"],
            "logo": ch.get("logo", ""),
            "group": [catalog.COUNTRY_NAMES.get(ch["country"], ch["country"])],
            "stream": PLUGIN + "?" + urlencode({"action": "play", "id": ch["id"]}),
        })
    if _include_my_lists():
        for source, entries, _ in _my_lists():
            for i, e in enumerate(entries):
                groups = [source["name"]] + ([e["group"]] if e["group"] else [])
                streams.append({
                    "id": _my_channel_id(source, i, e),
                    "name": e["name"],
                    "logo": e.get("logo", ""),
                    "group": groups,
                    "stream": PLUGIN + "?" + urlencode({"action": "my_play", "s": source["id"], "i": i, "n": e["name"]}),
                })
    return {"version": 1, "streams": streams}


def epg():
    guide = {}
    if _include_my_lists() and _include_my_guides():
        from . import xmltv
        for source, entries, guides in _my_lists():
            wanted = {}
            for i, e in enumerate(entries):
                if e.get("tvg_id"):
                    wanted.setdefault(e["tvg_id"], []).append(_my_channel_id(source, i, e))
            if not wanted or not guides:
                continue
            for address in guides:
                try:
                    found = xmltv.read(address, wanted)
                except Exception as exc:
                    common.log("TV section: guide {} skipped: {}".format(address, exc))
                    continue
                for tvg_id, programmes in found.items():
                    for channel_id in wanted[tvg_id]:
                        guide.setdefault(channel_id, []).extend(programmes)
    # Guide data for the official channels arrives in a later version.
    return {"version": 1, "epg": guide}


def send_channels(port):
    sock = _Socket(port)
    try:
        payload = channels()
    except Exception as exc:
        common.log("TV section channels failed: {}".format(exc))
        sock.close()
        return
    sock.send(payload)


def send_epg(port):
    sock = _Socket(port)
    try:
        payload = epg()
    except Exception as exc:
        common.log("TV section guide failed: {}".format(exc))
        sock.close()
        return
    sock.send(payload)
