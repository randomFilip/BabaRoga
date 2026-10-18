"""Check channels.json against the project rules before anything is published.

Usage: python tools/validate_channels.py [path/to/channels.json]
Exits with an error if any rule is broken.
"""
import ipaddress
import json
import re
import sys
from urllib.parse import urlparse

DEFAULT = "plugin.video.babaroga/resources/data/channels.json"
COUNTRIES = {"MK", "AL", "XK", "RS", "ME", "BA", "HR", "SI", "BG", "GR", "RO"}
GENRES = {"news", "general", "sports", "music", "kids", "movies",
          "documentary", "religious", "regional", "parliament"}
SOURCES = {"direct", "page", "api", "youtube"}
STATUSES = {"to_test", "passed", "failed"}
ACCESS = {"free", "free_account"}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def is_ip(host):
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def check_url(errors, where, value):
    p = urlparse(value or "")
    if p.scheme not in ("http", "https") or not p.hostname:
        errors.append("{}: not a web address: {!r}".format(where, value))
    elif is_ip(p.hostname):
        errors.append("{}: bare IP addresses are not allowed: {}".format(where, value))


def validate(data):
    errors = []
    if not isinstance(data.get("version"), int):
        errors.append("version must be a whole number (raise it on every change)")
    seen = set()
    for i, ch in enumerate(data.get("channels", [])):
        where = ch.get("id") or "channel #{}".format(i + 1)
        for key in ("id", "name", "country", "genres", "source", "access", "status"):
            if key not in ch:
                errors.append("{}: missing '{}'".format(where, key))
        if ch.get("id") in seen:
            errors.append("{}: duplicate id".format(where))
        seen.add(ch.get("id"))
        if ch.get("country") not in COUNTRIES:
            errors.append("{}: unknown country {!r}".format(where, ch.get("country")))
        for g in ch.get("genres", []):
            if g not in GENRES:
                errors.append("{}: unknown genre {!r}".format(where, g))
        if ch.get("access") not in ACCESS:
            errors.append("{}: access must be one of {}".format(where, sorted(ACCESS)))
        if ch.get("drm") is not False:
            errors.append("{}: DRM streams are never included (drm must be false)".format(where))
        geo = ch.get("geo_lock")
        if geo is not None and (not isinstance(geo, list) or any(c not in COUNTRIES for c in geo)):
            errors.append("{}: geo_lock must be null or a list of country codes".format(where))
        if ch.get("website"):
            check_url(errors, where + " website", ch["website"])
        if ch.get("logo"):
            check_url(errors, where + " logo", ch["logo"])

        src = ch.get("source") or {}
        if src.get("type") not in SOURCES:
            errors.append("{}: source type must be one of {}".format(where, sorted(SOURCES)))
        elif src["type"] == "youtube":
            if not (src.get("channel_id") or src.get("video_id")):
                errors.append("{}: youtube source needs channel_id or video_id".format(where))
        else:
            check_url(errors, where + " source", src.get("url"))
            if src.get("pattern"):
                try:
                    re.compile(src["pattern"])
                except re.error as exc:
                    errors.append("{}: bad pattern: {}".format(where, exc))

        status = ch.get("status")
        if status not in STATUSES:
            errors.append("{}: status must be one of {}".format(where, sorted(STATUSES)))
        if status == "passed":
            if not DATE.match(ch.get("verified") or ""):
                errors.append("{}: a passed channel needs the test date in 'verified'".format(where))
            if len(ch.get("evidence", "")) < 20:
                errors.append("{}: a passed channel needs evidence from the browser test".format(where))
    return errors


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    errors = validate(data)
    total = len(data.get("channels", []))
    passed = sum(1 for c in data.get("channels", []) if c.get("status") == "passed")
    if errors:
        print("\n".join(errors))
        print("{} problem(s) in {} channels".format(len(errors), total))
        sys.exit(1)
    print("OK: {} channels, {} passed the browser test".format(total, passed))


if __name__ == "__main__":
    main()
