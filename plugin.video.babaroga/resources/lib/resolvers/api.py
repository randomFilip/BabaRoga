"""Ask the same JSON endpoint the official player asks.

Channel entry example:
    "source": {"type": "api", "url": "https://example.tv/api/live/1",
               "path": ["data", "streamUrl"]}
"path" walks the JSON answer down to the link (keys, or numbers for lists).
Sign-in for services that need your own free account comes in a later
version; until then those channels stay marked "To test".
"""
from . import Stream, official_headers
from .. import net


def resolve(ch, source):
    headers = official_headers(ch)
    data = net.get(source["url"], headers=headers).json()
    for step in source.get("path", []):
        try:
            data = data[step]
        except (KeyError, IndexError, TypeError):
            raise net.NotFound("player API answer has no '{}'".format(step))
    if not isinstance(data, str) or not data.startswith("http"):
        raise net.NotFound("player API gave no link")
    return Stream(data, headers)
