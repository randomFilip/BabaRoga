"""Which country the TV is in. Only used to sort menus and mark locks."""
from . import common

TRACE_URL = "https://www.cloudflare.com/cdn-cgi/trace"
CACHE_SECONDS = 24 * 3600


def detect():
    cached = common.read_json("geo.json", {})
    if cached.get("country") and common.now() - cached.get("ts", 0) < CACHE_SECONDS:
        return cached["country"]
    try:
        from . import net
        text = net.get(TRACE_URL).text
        for line in text.splitlines():
            if line.startswith("loc="):
                country = line[4:].strip().upper()
                common.write_json("geo.json", {"country": country, "ts": common.now()})
                return country
    except Exception as exc:  # network trouble must never break the menus
        common.log("country detection failed: {}".format(exc))
    return cached.get("country", "")


def country():
    choice = common.setting("country")
    if choice and choice != "Auto":
        return choice
    return detect()
