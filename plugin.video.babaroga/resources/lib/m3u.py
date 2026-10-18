"""Read M3U / M3U8 channel lists (a web address or a file on the TV)."""
import re

TAG_ATTR = re.compile(r'([\w-]+)="([^"]*)"')


def parse(text):
    """Return a list of entries: name, url, logo, group, headers, props."""
    entries = []
    current = None
    headers = {}
    props = {}
    for raw in text.splitlines():
        line = raw.strip().lstrip("﻿")
        if not line:
            continue
        if line.startswith("#EXTINF"):
            attrs = dict(TAG_ATTR.findall(line))
            name = line.rsplit(",", 1)[1].strip() if "," in line else ""
            current = {
                "name": name or attrs.get("tvg-name") or "Channel",
                "logo": attrs.get("tvg-logo", ""),
                "group": attrs.get("group-title", ""),
            }
            ua = attrs.get("http-user-agent") or attrs.get("user-agent")
            ref = attrs.get("http-referrer") or attrs.get("referrer")
            if ua:
                headers["User-Agent"] = ua
            if ref:
                headers["Referer"] = ref
        elif line.startswith("#EXTVLCOPT:"):
            key, _, value = line[len("#EXTVLCOPT:"):].partition("=")
            key = key.strip().lower()
            if key == "http-user-agent":
                headers["User-Agent"] = value.strip()
            elif key in ("http-referrer", "http-referer"):
                headers["Referer"] = value.strip()
            elif key == "http-origin":
                headers["Origin"] = value.strip()
        elif line.startswith("#KODIPROP:"):
            key, _, value = line[len("#KODIPROP:"):].partition("=")
            props[key.strip()] = value.strip()
        elif line.startswith("#EXTGRP:") and current is not None:
            current["group"] = current["group"] or line[len("#EXTGRP:"):].strip()
        elif line.startswith("#"):
            continue
        else:
            url, headers_from_url = split_pipe(line)
            entry = current or {"name": url.rsplit("/", 1)[-1] or "Channel", "logo": "", "group": ""}
            entry["url"] = url
            entry["headers"] = dict(headers, **headers_from_url)
            entry["props"] = dict(props)
            entries.append(entry)
            current, headers, props = None, {}, {}
    return entries


def split_pipe(line):
    """Some lists add headers after a '|': url|User-Agent=...&Referer=..."""
    from urllib.parse import parse_qsl
    if "|" not in line:
        return line, {}
    url, _, extra = line.partition("|")
    return url.strip(), dict(parse_qsl(extra))


def groups(entries):
    seen = []
    for e in entries:
        if e["group"] and e["group"] not in seen:
            seen.append(e["group"])
    return seen
