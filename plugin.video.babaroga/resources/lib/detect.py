"""Work out what an address is: a stream, a channel list, a web page or YouTube.

Decided first from the address itself, and when that is not enough, from
what the server sends back (its content type and the first bytes), the same
way a browser decides what to do with a link.

Kinds:
  hls      HLS live stream or video (.m3u8 that is a stream playlist)
  dash     DASH stream (.mpd)
  file     a plain video file (mp4, webm, mkv, ts ...)
  m3u      a channel list (#EXTM3U list of channels)
  youtube  a YouTube video, live stream or channel
  page     an ordinary web page (search it for videos)
"""
import re

from . import net

YT_VIDEO = re.compile(r"(?:youtube(?:-nocookie)?\.com/(?:watch\?(?:.*&)?v=|embed/|live/|shorts/)|youtu\.be/)([\w-]{11})")
YT_CHANNEL = re.compile(r"youtube\.com/(?:channel/|embed/live_stream\?channel=)(UC[\w-]{22})")

VIDEO_EXT = (".mp4", ".m4v", ".webm", ".mkv", ".mov", ".ts", ".avi", ".flv")
SNIFF_BYTES = 65536


def youtube_plugin_url(address):
    m = YT_CHANNEL.search(address)
    if m:
        return "plugin://plugin.video.youtube/play/?channel_id={}&live=1".format(m.group(1))
    m = YT_VIDEO.search(address)
    if m and m.group(1) != "live_stream":
        return "plugin://plugin.video.youtube/play/?video_id={}".format(m.group(1))
    return None


def from_text(text):
    """Kind from the start of a file's content, or None."""
    head = text.lstrip("﻿ \r\n\t")[:SNIFF_BYTES]
    if head.startswith("#EXTM3U") or head.startswith("#EXTINF"):
        # Stream playlists carry #EXT-X- tags; channel lists do not.
        return "hls" if "#EXT-X-" in head else "m3u"
    if "<MPD" in head[:4096]:
        return "dash"
    low = head[:2048].lower()
    if "<html" in low or "<!doctype html" in low or "<head" in low or "<body" in low:
        return "page"
    return None


def from_address(address):
    """Kind from the address alone, or None when it cannot tell."""
    if youtube_plugin_url(address):
        return "youtube"
    path = address.split("?")[0].split("#")[0].lower()
    if path.endswith(".mpd"):
        return "dash"
    if path.endswith(VIDEO_EXT):
        return "file"
    return None  # .m3u8 can be a stream or a channel list, so look inside


def from_response(content_type, first_bytes):
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct.startswith(("video/", "audio/")) and "mpegurl" not in ct:
        return "file"
    if ct == "application/dash+xml":
        return "dash"
    if first_bytes[4:8] == b"ftyp":  # MP4 / M4V
        return "file"
    if len(first_bytes) > 376 and first_bytes[0] == 0x47 and first_bytes[188] == 0x47 and first_bytes[376] == 0x47:
        return "file"  # MPEG-TS: a sync byte every 188 bytes
    if first_bytes[:4] == b"\x1a\x45\xdf\xa3":  # Matroska / WebM
        return "file"
    text = first_bytes.decode("utf-8", "ignore")
    kind = from_text(text)
    if kind:
        return kind
    if "mpegurl" in ct:
        return "hls"
    if ct in ("text/html", "application/xhtml+xml"):
        return "page"
    return None


def detect(address, headers=None):
    """(kind, final_address). Raises net.GeoBlocked / net.NotFound."""
    kind = from_address(address)
    if kind:
        return kind, address
    resp = net.session().get(address, headers=headers or {}, timeout=net.TIMEOUT,
                             stream=True, allow_redirects=True)
    try:
        if resp.status_code in (401, 403, 451):
            raise net.GeoBlocked("{} answered {}".format(address, resp.status_code))
        if resp.status_code >= 400:
            raise net.NotFound("{} answered {}".format(address, resp.status_code))
        first = b""
        for chunk in resp.iter_content(4096):
            first += chunk
            if len(first) >= SNIFF_BYTES:
                break
        kind = from_response(resp.headers.get("Content-Type"), first) or "page"
        return kind, resp.url
    finally:
        resp.close()


LABELS = {
    "hls": "HLS stream", "dash": "DASH stream", "file": "video file",
    "m3u": "channel list", "youtube": "YouTube", "page": "web page",
}
