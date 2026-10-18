"""Open the official live page like a browser and find the player's link.

Without a "pattern" the shared link finder is used (see finder.py): it reads
the page and its embedded players and takes the best stream it finds.
With a "pattern" (a regular expression whose named group "url", or else
its whole match, is the link) only that is used, on the page and its
embedded players.
"""
import re
from urllib.parse import urljoin

from . import Stream, official_headers
from .. import finder, net

IFRAME = finder.IFRAME
MAX_IFRAMES = 3


def _clean(text):
    return finder.clean(text)


def _find(text, pattern, base):
    match = re.search(pattern, _clean(text))
    if not match:
        return None
    link = match.groupdict().get("url") or match.group(0)
    if link.startswith("//"):
        link = "https:" + link
    return urljoin(base, link)


def resolve(ch, source):
    page_url = source["url"]
    headers = official_headers(ch)
    referer = headers.get("Referer", page_url)

    pattern = source.get("pattern")
    if not pattern:
        streams = [s for s in finder.find(page_url, referer=referer) if s["kind"] in ("hls", "dash")]
        if not streams:
            raise net.NotFound("no stream link on the official page")
        return Stream(streams[0]["url"], official_headers(ch, page_url=streams[0]["referer"]))

    text = net.get(page_url, headers={"Referer": referer}).text
    link = _find(text, pattern, page_url)
    found_on = page_url
    if not link and source.get("follow_iframes", True):
        for src in IFRAME.findall(text)[:MAX_IFRAMES]:
            frame_url = urljoin(page_url, _clean(src))
            try:
                frame = net.get(frame_url, headers={"Referer": page_url}).text
            except (net.NotFound, net.GeoBlocked):
                continue
            link = _find(frame, pattern, frame_url)
            if link:
                found_on = frame_url
                break
    if not link:
        raise net.NotFound("no stream link on the official page")
    return Stream(link, official_headers(ch, page_url=found_on))
