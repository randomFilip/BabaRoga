"""Your own sources: web pages and channel lists you add on the TV.

They are stored only on this TV (in the add-on's data folder) and are never
uploaded or added to the shared channel list.
"""
import re
from urllib.parse import urljoin

import xbmcvfs

from . import common, m3u, net
from .resolvers import page as page_resolver

FILE = "my_sources.json"
YOUTUBE = re.compile(r"""(?:youtube\.com/(?:embed/|watch\?v=|live/)|youtu\.be/)([\w-]{11})""")
MAX_FRAMES = 5


def load():
    return common.read_json(FILE, [])


def save(items):
    common.write_json(FILE, items)


def get(source_id):
    for s in load():
        if s["id"] == source_id:
            return s
    return None


def add(kind, name, address):
    items = load()
    new_id = str(max([int(s["id"]) for s in items] + [0]) + 1)
    items.append({"id": new_id, "type": kind, "name": name, "url": address})
    save(items)
    return new_id


def remove(source_id):
    save([s for s in load() if s["id"] != source_id])


def rename(source_id, name):
    items = load()
    for s in items:
        if s["id"] == source_id:
            s["name"] = name
    save(items)


# ---- channel lists ---------------------------------------------------------

def read_list(source):
    address = source["url"]
    if address.startswith(("http://", "https://")):
        text = net.get(address).text
    else:
        f = xbmcvfs.File(address)
        try:
            text = f.read()
        finally:
            f.close()
    return m3u.parse(text)


# ---- web pages -------------------------------------------------------------

def _links_in(text, base):
    """Stream links and YouTube videos found in one HTML page."""
    found = []
    clean = page_resolver._clean(text)
    for match in re.finditer(page_resolver.DEFAULT_PATTERN, clean):
        link = match.group(0)
        if link.startswith("//"):
            link = "https:" + link
        found.append({"url": urljoin(base, link), "referer": base})
    for vid in YOUTUBE.findall(clean):
        found.append({"url": "plugin://plugin.video.youtube/play/?video_id=" + vid, "referer": base})
    return found


def scan_page(address):
    """Everything playable the page (and its embedded players) points to."""
    text = net.get(address).text
    found = _links_in(text, address)
    for src in page_resolver.IFRAME.findall(text)[:MAX_FRAMES]:
        frame_url = urljoin(address, page_resolver._clean(src))
        if YOUTUBE.search(frame_url):
            found += _links_in(frame_url, address)
            continue
        try:
            found += _links_in(net.get(frame_url, headers={"Referer": address}).text, frame_url)
        except Exception as exc:
            common.log("embedded player {} skipped: {}".format(frame_url, exc))
    unique, seen = [], set()
    for item in found:
        key = item["url"].split("?")[0]
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def link_label(item, index):
    url = item["url"]
    if url.startswith("plugin://plugin.video.youtube"):
        return "YouTube video {}".format(index + 1)
    tail = url.split("?")[0].rstrip("/").rsplit("/", 2)
    host = net.origin_of(url).split("//")[-1]
    return "Stream {} ({}, {})".format(index + 1, host, "/".join(tail[-2:]))
