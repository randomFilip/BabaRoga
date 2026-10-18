"""Find a channel's stream link the same way its official player does.

Every resolver returns a Stream. Links are resolved when you press play and
are never stored, because many broadcasters use short-lived tokens.
"""
from urllib.parse import urljoin

from .. import net


class Stream(object):
    def __init__(self, url, headers=None, kind=None):
        self.url = url
        self.headers = headers or {}
        self.kind = kind or guess_kind(url)


def guess_kind(url):
    low = url.lower().split("?")[0]
    if url.startswith("plugin://"):
        return "plugin"
    if low.endswith(".mpd"):
        return "dash"
    if ".m3u8" in low:
        return "hls"
    return "file"


def official_headers(ch, page_url=None):
    """Headers the official player sends: its page as Referer and Origin."""
    headers = dict(ch.get("headers") or {})
    ref = page_url or headers.get("Referer") or ch.get("website")
    if ref:
        headers.setdefault("Referer", ref)
        headers.setdefault("Origin", net.origin_of(ref))
    headers.setdefault("User-Agent", net.USER_AGENT)
    return headers


def resolve(ch):
    source = ch.get("source") or {}
    kind = source.get("type")
    if kind == "direct":
        from . import direct as mod
    elif kind == "page":
        from . import page as mod
    elif kind == "api":
        from . import api as mod
    elif kind == "youtube":
        from . import youtube as mod
    else:
        raise net.NotFound("unknown source type: {}".format(kind))
    stream = mod.resolve(ch, source)
    if stream.kind in ("hls", "dash"):
        check_not_protected(stream)
    return stream


# Widevine, PlayReady and FairPlay markers. Plain AES-128 HLS is not DRM:
# a browser plays it with no licence server, so it is allowed.
_DRM_MARKERS = (
    "edef8ba9-79d6-4ace-a3c8-27dcd51d21ed",  # Widevine
    "9a04f079-9840-4286-ab92-e65be0885f95",  # PlayReady
    "com.widevine", "com.microsoft.playready", "com.apple.streamingkeydelivery",
    "skd://",
)


def _has_drm(text):
    low = text.lower()
    return any(marker in low for marker in _DRM_MARKERS)


def check_not_protected(stream):
    text = net.get(stream.url, headers=stream.headers).text
    if _has_drm(text):
        raise net.Protected("DRM-protected stream")
    if stream.kind == "hls" and "#EXT-X-STREAM-INF" in text:
        # Keys sit in the media playlists, so look at the first variant too.
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                variant = urljoin(stream.url, line)
                if _has_drm(net.get(variant, headers=stream.headers).text):
                    raise net.Protected("DRM-protected stream")
                break
