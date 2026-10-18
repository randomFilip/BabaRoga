"""Your own sources: web pages and channel lists you add on the TV.

They are stored only on this TV (in the add-on's data folder) and are never
uploaded or added to the shared channel list.

Every channel list also keeps a copy in the add-on's data folder:
  - a list added from a file (USB stick, Downloads) is copied when added,
    so it keeps working after the stick is removed;
  - a list from a web address is copied each time it loads, so it still
    opens when that server is down.
"""
import os

import xbmcvfs

from . import common, m3u, net

FILE = "my_sources.json"


def load():
    return common.read_json(FILE, [])


def save(items):
    common.write_json(FILE, items)


def get(source_id):
    if source_id == "once":
        return common.read_json("once.json", None)
    for s in load():
        if s["id"] == source_id:
            return s
    return None


def set_once(source):
    """An address opened once: kept only until the next one."""
    common.write_json("once.json", source)


def add(stype, name, address, kind=None, text=None):
    """stype: page, m3u or stream; kind: what detect.py found (hls, dash ...).
    text: the list's contents, for a list added from a file."""
    items = load()
    new_id = str(max([int(s["id"]) for s in items] + [0]) + 1)
    items.append({"id": new_id, "type": stype, "kind": kind or stype, "name": name, "url": address})
    save(items)
    if text is not None:
        _save_copy(new_id, text)
    return new_id


def _copy_path(source_id):
    folder = common.profile_path("lists")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "{}.m3u".format(source_id))


def _save_copy(source_id, text):
    try:
        with open(_copy_path(source_id), "w", encoding="utf-8") as fh:
            fh.write(text)
    except OSError as exc:
        common.log("could not keep a copy of list {}: {}".format(source_id, exc))


def _read_copy(source_id):
    try:
        with open(_copy_path(source_id), encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def remove(source_id):
    save([s for s in load() if s["id"] != source_id])
    try:
        os.remove(_copy_path(source_id))
    except OSError:
        pass


def rename(source_id, name):
    items = load()
    for s in items:
        if s["id"] == source_id:
            s["name"] = name
    save(items)


# ---- channel lists ---------------------------------------------------------

def read_list(source):
    return read_list_with_guide(source)[0]


def read_list_with_guide(source):
    """(entries, guide addresses) of a channel list."""
    text = None
    try:
        text = _read_original(source["url"])
    except Exception as exc:
        common.log("list {} not reachable, using the kept copy: {}".format(source["name"], exc))
    if text and m3u.parse(text):
        if source.get("id") != "once":
            _save_copy(source["id"], text)
    else:
        text = _read_copy(source.get("id")) or text
        if text is None:
            raise net.NotFound("the list is not reachable and no copy is kept yet")
    return m3u.parse(text), m3u.guide_urls(text)


def _read_original(address):
    if address.startswith(("http://", "https://")):
        return net.get(address).text
    if not xbmcvfs.exists(address):
        raise net.NotFound("file not found: {}".format(address))
    f = xbmcvfs.File(address)
    try:
        return f.read()
    finally:
        f.close()


# ---- web pages -------------------------------------------------------------

def scan_page(address):
    """Everything playable the page (and its embedded players) points to."""
    from . import finder
    return finder.find(address)


def link_label(item, index):
    from . import finder
    return finder.label(item, index)
