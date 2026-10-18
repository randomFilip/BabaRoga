"""Open the official live page like a browser and find the player's link.

The channel entry may give a "pattern": a regular expression whose named
group "url", or else its whole match, is the link. Without one, the first .m3u8 or .mpd
address on the page is used. Embedded players (iframes) on the page are
followed, at most three, so a page that loads its player from the
broadcaster's video host still works.
"""
import html
import re
from urllib.parse import urljoin

from . import Stream, official_headers
from .. import net

DEFAULT_PATTERN = r"""(?:https?:)?//[^\s"'<>\\]+?\.(?:m3u8|mpd)(?:\?[^\s"'<>\\]*)?"""
IFRAME = re.compile(r"""<iframe[^>]+src\s*=\s*["']([^"']+)["']""", re.I)
MAX_IFRAMES = 3


def _clean(text):
    return html.unescape(text.replace("\\/", "/").replace("\\u0026", "&"))


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
    pattern = source.get("pattern") or DEFAULT_PATTERN
    headers = official_headers(ch)
    text = net.get(page_url, headers={"Referer": headers.get("Referer", page_url)}).text

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
