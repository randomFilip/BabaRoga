"""The verified channel list: loading, filtering and daily updates."""
import json
import os

from . import common

UPDATE_URL = ("https://raw.githubusercontent.com/randomFilip/BabaRoga/main/"
              "plugin.video.babaroga/resources/data/channels.json")

COUNTRIES = [
    ("MK", "North Macedonia"), ("AL", "Albania"), ("XK", "Kosovo"),
    ("RS", "Serbia"), ("ME", "Montenegro"), ("BA", "Bosnia and Herzegovina"),
    ("HR", "Croatia"), ("SI", "Slovenia"), ("BG", "Bulgaria"),
    ("GR", "Greece"), ("RO", "Romania"),
]
COUNTRY_NAMES = dict(COUNTRIES)

GENRES = [
    ("news", "News"), ("general", "General"), ("sports", "Sports"),
    ("music", "Music"), ("kids", "Kids"), ("movies", "Movies and Series"),
    ("documentary", "Documentary and Culture"), ("religious", "Religious"),
    ("regional", "Regional and Local"), ("parliament", "Parliament"),
]
GENRE_NAMES = dict(GENRES)

_cache = None


def _bundled_path():
    return os.path.join(common.ADDON_PATH, "resources", "data", "channels.json")


def _read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data.get("channels"), list):
            return data
    except (OSError, ValueError, AttributeError):
        pass
    return None


def load():
    """Newest valid list: the downloaded copy if newer, else the bundled one."""
    global _cache
    if _cache is not None:
        return _cache
    bundled = _read(_bundled_path()) or {"version": 0, "channels": []}
    downloaded = _read(common.profile_path("channels.json"))
    data = bundled
    if downloaded and downloaded.get("version", 0) > bundled.get("version", 0):
        data = downloaded
    _cache = data
    return data


def all_channels():
    return load()["channels"]


def by_id(channel_id):
    for ch in all_channels():
        if ch["id"] == channel_id:
            return ch
    return None


def is_locked_here(ch, country):
    geo = ch.get("geo_lock")
    return bool(geo) and bool(country) and country not in geo


def visible(country):
    """Channels that pass the user's settings."""
    show_untested = common.setting_bool("show_untested")
    hide_locked = common.setting_bool("hide_geolocked")
    out = []
    for ch in all_channels():
        status = ch.get("status", "to_test")
        if status == "failed":
            continue
        if status != "passed" and not show_untested:
            continue
        if hide_locked and is_locked_here(ch, country):
            continue
        out.append(ch)
    return out


def countries_with_channels(country):
    present = {ch["country"] for ch in visible(country)}
    return [(code, name) for code, name in COUNTRIES if code in present]


def genres_with_channels(country, in_country=None):
    present = set()
    for ch in visible(country):
        if in_country and ch["country"] != in_country:
            continue
        present.update(ch.get("genres", []))
    return [(key, name) for key, name in GENRES if key in present]


def update_from_github():
    """Download the published list; keep it only if it is valid and newer."""
    from . import net
    resp = net.get(UPDATE_URL)
    data = resp.json()
    if not isinstance(data.get("channels"), list) or not isinstance(data.get("version"), int):
        raise ValueError("unexpected channel list format")
    if data["version"] <= load().get("version", 0):
        return False
    common.write_json("channels.json", data)
    global _cache
    _cache = None
    return True
