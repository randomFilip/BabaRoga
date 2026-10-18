"""Channel list for IPTV Manager, which feeds Kodi's TV section.

IPTV Manager opens a socket on localhost and passes its port; we answer
with JSON-STREAMS (channels) and JSON-EPG (guide) data.
"""
import json
import socket

from . import catalog, geo


def _send(port, payload):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("127.0.0.1", int(port)))
    try:
        sock.sendall(json.dumps(payload).encode("utf-8"))
    finally:
        sock.close()


def send_channels(port):
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
            "stream": "plugin://plugin.video.babaroga/?action=play&id={}".format(ch["id"]),
        })
    _send(port, {"version": 1, "streams": streams})


def send_epg(port):
    # Guide data arrives in phase 2; an empty guide keeps IPTV Manager happy.
    _send(port, {"version": 1, "epg": {}})
