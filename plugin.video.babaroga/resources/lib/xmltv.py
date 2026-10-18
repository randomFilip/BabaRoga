"""Read an XMLTV guide (plain or .gz) for the channels in your lists.

The guide is streamed and read piece by piece, so even a large guide file
does not fill the TV's memory. Only programmes from 3 hours ago to 36 hours
ahead are kept, and only for the channels you have.
"""
import gzip
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from . import common, net

PAST = timedelta(hours=3)
AHEAD = timedelta(hours=36)
XMLTV_TIME = re.compile(r"^(\d{14})(?:\s*([+-]\d{4}))?")


def parse_time(value):
    m = XMLTV_TIME.match(value or "")
    if not m:
        return None
    moment = datetime.strptime(m.group(1), "%Y%m%d%H%M%S")
    offset = m.group(2)
    if offset:
        sign = 1 if offset[0] == "+" else -1
        delta = timedelta(hours=int(offset[1:3]), minutes=int(offset[3:5]))
        moment = moment.replace(tzinfo=timezone(sign * delta))
    else:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


def _open(address):
    resp = net.session().get(address, timeout=60, stream=True)
    if resp.status_code != 200:
        resp.close()
        raise net.NotFound("guide answered {}".format(resp.status_code))
    resp.raw.decode_content = True
    stream = _Rewound(resp.raw)
    if stream.head[:2] == b"\x1f\x8b":  # a .gz file, whatever its name
        return resp, gzip.GzipFile(fileobj=stream)
    return resp, stream


class _Rewound(object):
    """A stream whose first bytes were looked at, given back unread."""

    def __init__(self, raw):
        self.raw = raw
        self.head = raw.read(2)
        self._pending = self.head

    def read(self, size=-1):
        pending, self._pending = self._pending, b""
        if size is None or size < 0:
            return pending + self.raw.read()
        if len(pending) >= size:
            self._pending = pending[size:]
            return pending[:size]
        return pending + self.raw.read(size - len(pending))


def _text(el, tag):
    child = el.find(tag)
    return (child.text or "").strip() if child is not None and child.text else ""


def read(address, wanted):
    """{guide channel id: [programme, ...]} for the ids in `wanted`."""
    now = datetime.now(timezone.utc)
    lo, hi = now - PAST, now + AHEAD
    out = {}
    resp, stream = _open(address)
    try:
        for _, el in ET.iterparse(stream, events=("end",)):
            if el.tag != "programme":
                if el.tag == "channel":
                    el.clear()
                continue
            channel = el.get("channel")
            if channel in wanted:
                start, stop = parse_time(el.get("start")), parse_time(el.get("stop"))
                if start and stop and stop > lo and start < hi:
                    prog = {"start": start.isoformat(), "stop": stop.isoformat(),
                            "title": _text(el, "title") or "?"}
                    desc = _text(el, "desc")
                    if desc:
                        prog["description"] = desc
                    sub = _text(el, "sub-title")
                    if sub:
                        prog["subtitle"] = sub
                    cat = _text(el, "category")
                    if cat:
                        prog["genre"] = cat
                    icon = el.find("icon")
                    if icon is not None and icon.get("src"):
                        prog["image"] = icon.get("src")
                    out.setdefault(channel, []).append(prog)
            el.clear()
    except ET.ParseError as exc:
        common.log("guide {} stopped early: {}".format(address, exc))
    finally:
        resp.close()
    return out
