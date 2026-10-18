"""A fixed link the broadcaster publishes on its own server."""
from . import Stream, official_headers


def resolve(ch, source):
    return Stream(source["url"], official_headers(ch))
