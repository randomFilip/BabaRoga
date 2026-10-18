"""Your own sources: web pages and channel lists you add on the TV.

They are stored only on this TV (in the add-on's data folder) and are never
uploaded or added to the shared channel list.
"""
import xbmcvfs

from . import common, m3u, net

FILE = "my_sources.json"


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

def scan_page(address):
    """Everything playable the page (and its embedded players) points to."""
    from . import finder
    return finder.find(address)


def link_label(item, index):
    from . import finder
    return finder.label(item, index)
