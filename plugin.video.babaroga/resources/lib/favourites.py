"""Favourites and recently watched, kept on the TV."""
from . import common

RECENT_MAX = 20


def favourites():
    return common.read_json("favourites.json", [])


def is_favourite(channel_id):
    return channel_id in favourites()


def add(channel_id):
    favs = favourites()
    if channel_id not in favs:
        favs.append(channel_id)
        common.write_json("favourites.json", favs)


def remove(channel_id):
    favs = [f for f in favourites() if f != channel_id]
    common.write_json("favourites.json", favs)


def recent():
    return common.read_json("recent.json", [])


def touch(channel_id):
    items = [channel_id] + [c for c in recent() if c != channel_id]
    common.write_json("recent.json", items[:RECENT_MAX])
