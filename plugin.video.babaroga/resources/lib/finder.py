"""Find the video a web page plays, the way a browser's player gets it.

Looks in the page and in its embedded players (iframes, two levels deep) for:
  - HLS (.m3u8) and DASH (.mpd) links, absolute or relative
  - <video src> and <source src> tags, including .mp4 / .webm files
  - player settings: JW Player, Video.js, Clappr, Flowplayer and similar
    ("file", "src", "source", "hls", "dash", "streamUrl" ... values)
  - schema.org VideoObject data (contentUrl, embedUrl)
  - links written in base64 inside the page (atob("...") and similar)
  - YouTube embeds: single videos and a channel's live stream
Player links without a telling extension are identified by asking the
server what it sends (see detect.py).
"""
import base64
import html
import json
import re
from urllib.parse import urljoin, urlparse

from . import common, net

MAX_FRAMES = 8
MAX_DEPTH = 2
MAX_PROBES = 5

STREAM_EXT = r"(?:m3u8|mpd)"
FILE_EXT = r"(?:mp4|webm|m4v)"
URL_CHARS = r"""[^\s"'<>\\()]"""

ABSOLUTE = re.compile(r"(?:https?:)?//" + URL_CHARS + r"+?\." + STREAM_EXT + r"(?:\?" + URL_CHARS + r"*)?", re.I)
QUOTED_RELATIVE = re.compile(r"""["'](/?""" + URL_CHARS + r"+?\." + STREAM_EXT + r"(?:\?[^\s\"'<>]*)?)[\"']", re.I)
VIDEO_TAG = re.compile(r"""<(?:video|source)\b[^>]*?\bsrc\s*=\s*["']([^"']+)["']""", re.I)
PLAYER_KEY = re.compile(
    r"""["']?(?:file|src|source|hls|hlsUrl|hls_url|dash|dashUrl|streamUrl|stream_url|videoUrl|video_url|contentUrl|mp4)["']?\s*[:=]\s*["']([^"']+)["']""",
    re.I)
B64 = re.compile(r"""["']((?:aHR0c|Ly9)[A-Za-z0-9+/=]{16,})["']""")
IFRAME = re.compile(r"""<iframe\b[^>]*?\b(?:data-src|src)\s*=\s*["']([^"']+)["']""", re.I)
YOUTUBE_VIDEO = re.compile(r"""(?:youtube(?:-nocookie)?\.com/(?:embed/|watch\?v=|live/|shorts/)|youtu\.be/)([\w-]{11})""")
YOUTUBE_LIVE = re.compile(r"""youtube(?:-nocookie)?\.com/embed/live_stream\?channel=(UC[\w-]{22})""")
JSON_LD = re.compile(r"""<script[^>]+application/ld\+json[^>]*>(.*?)</script>""", re.I | re.S)

SKIP = ("doubleclick", "googlesyndication", "/ads/", "vast", "preroll", "imasdk", "adservice")


def clean(text):
    text = text.replace("\\/", "/").replace("\\u002F", "/").replace("\\u002f", "/")
    text = text.replace("\\u0026", "&").replace("\\u003D", "=").replace("\\u003d", "=")
    return html.unescape(text)


def _kind(url):
    low = url.lower().split("?")[0]
    if url.startswith("plugin://"):
        return "youtube"
    if low.endswith(".mpd"):
        return "dash"
    if ".m3u8" in low:
        return "hls"
    if re.search(r"\." + FILE_EXT + r"$", low):
        return "file"
    return None


STATIC = (".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
          ".woff", ".woff2", ".ttf", ".html", ".htm", ".php", ".json", ".xml", ".vtt", ".srt")


def _static(url):
    return url.split("?")[0].split("#")[0].lower().endswith(STATIC)


def _absolute(link, base):
    link = link.strip()
    if link.startswith("//"):
        return "https:" + link
    return urljoin(base, link)


def _from_text(text, base):
    """(url, kind) pairs found in one page's text."""
    out = []
    raw = text
    text = clean(text)

    def add(link, probe=False):
        if not link or link.startswith(("data:", "blob:", "javascript:")):
            return
        url = _absolute(link, base)
        kind = _kind(url)
        if any(s in url.lower() for s in SKIP):
            return
        if kind:
            out.append((url, kind))
        elif probe and url.startswith("http") and url != base and not _static(url):
            out.append((url, "unknown"))

    for m in ABSOLUTE.finditer(text):
        add(m.group(0))
    for m in QUOTED_RELATIVE.finditer(text):
        add(m.group(1))
    for m in VIDEO_TAG.finditer(text):
        add(m.group(1))
    for m in PLAYER_KEY.finditer(text):
        add(m.group(1), probe=True)  # player settings may point at a link without an extension
    for block in JSON_LD.findall(raw):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        for obj in data if isinstance(data, list) else [data]:
            if isinstance(obj, dict):
                for key in ("contentUrl", "embedUrl"):
                    if isinstance(obj.get(key), str):
                        add(obj[key])
                        out.extend(_youtube(obj[key]))
    for m in B64.finditer(text):
        try:
            decoded = base64.b64decode(m.group(1) + "===").decode("utf-8", "ignore")
        except (ValueError, UnicodeError):
            continue
        if decoded.startswith(("http", "//")):
            add(decoded)
    out.extend(_youtube(text))
    return out


def _youtube(text):
    out = []
    for cid in YOUTUBE_LIVE.findall(text):
        out.append(("plugin://plugin.video.youtube/play/?channel_id={}&live=1".format(cid), "youtube"))
    for vid in YOUTUBE_VIDEO.findall(text):
        if vid != "live_stream":
            out.append(("plugin://plugin.video.youtube/play/?video_id=" + vid, "youtube"))
    return out


def find(address, referer=None):
    """Every playable link on the page, best first.

    Each result: {"url", "kind", "referer"} where referer is the page or
    embedded player the link was found on (sent back when playing).
    """
    results = []
    visited = set()

    def visit(url, ref, depth):
        if url in visited or len(visited) > MAX_FRAMES:
            return
        visited.add(url)
        try:
            text = net.get(url, headers={"Referer": ref} if ref else None).text
        except Exception as exc:
            common.log("finder skipped {}: {}".format(url, exc))
            return
        for link, kind in _from_text(text, url):
            results.append({"url": link, "kind": kind, "referer": url})
        if depth >= MAX_DEPTH:
            return
        for src in IFRAME.findall(text):
            frame = _absolute(clean(src), url)
            if not frame.startswith("http"):
                continue
            if YOUTUBE_VIDEO.search(frame) or YOUTUBE_LIVE.search(frame):
                for link, kind in _youtube(frame):
                    results.append({"url": link, "kind": kind, "referer": url})
                continue
            visit(frame, url, depth + 1)

    visit(address, referer, 0)

    # Links from player settings with no telling extension: ask the server.
    from . import detect
    probed = 0
    unknown, seen_unknown = [], set()
    for r in results:
        if r["kind"] == "unknown" and r["url"] not in seen_unknown:
            seen_unknown.add(r["url"])
            unknown.append(r)
    results[:] = [r for r in results if r["kind"] != "unknown"]
    for item in unknown:
        if probed >= MAX_PROBES:
            continue
        probed += 1
        try:
            kind, final = detect.detect(item["url"], headers={"Referer": item["referer"]})
        except Exception as exc:
            common.log("finder could not identify {}: {}".format(item["url"], exc))
            continue
        if kind in ("hls", "dash", "file"):
            results.append({"url": item["url"], "kind": kind, "referer": item["referer"]})

    rank = {"hls": 0, "dash": 1, "youtube": 2, "file": 3}
    unique, seen = [], set()
    for item in sorted(results, key=lambda r: rank.get(r["kind"], 9)):
        key = item["url"].split("?")[0] if item["kind"] != "youtube" else item["url"]
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def label(item, index):
    if item["kind"] == "youtube":
        return "YouTube {} {}".format("live" if "live=1" in item["url"] else "video", index + 1)
    host = urlparse(item["url"]).netloc
    tail = "/".join(item["url"].split("?")[0].rstrip("/").rsplit("/", 2)[-2:])
    kind = {"hls": "HLS", "dash": "DASH", "file": "file"}[item["kind"]]
    return "Stream {}  [COLOR grey]{} · {} · {}[/COLOR]".format(index + 1, kind, host, tail)
