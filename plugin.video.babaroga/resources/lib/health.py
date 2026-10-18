"""Background checks: does each channel still play from this TV?"""
from . import catalog, common, net, resolvers

OK, GEO, PROTECTED, BROKEN = "ok", "geo", "protected", "broken"
HIDE_AFTER = 3  # failed checks in a row before a channel is hidden


def load():
    return common.read_json("health.json", {})


def status(channel_id, data=None):
    entry = (data if data is not None else load()).get(channel_id) or {}
    return entry.get("status")


def is_hidden(channel_id, data=None):
    entry = (data if data is not None else load()).get(channel_id) or {}
    return entry.get("fails", 0) >= HIDE_AFTER


def check(ch):
    try:
        stream = resolvers.resolve(ch)
        if stream.kind in ("hls", "dash"):
            net.get(stream.url, headers=stream.headers)
        return OK
    except net.GeoBlocked:
        return GEO
    except net.Protected:
        return PROTECTED
    except Exception as exc:
        common.log("check {} failed: {}".format(ch["id"], exc))
        return BROKEN


def record(channel_id, result):
    data = load()
    entry = data.get(channel_id) or {}
    entry["status"] = result
    entry["ts"] = common.now()
    entry["fails"] = 0 if result == OK else entry.get("fails", 0) + 1
    data[channel_id] = entry
    common.write_json("health.json", data)


def run_all(monitor=None, pause=2):
    """Check every channel, one at a time, stopping if Kodi starts playing."""
    import xbmc
    for ch in catalog.all_channels():
        if ch.get("status") == "failed" or (ch.get("source") or {}).get("type") == "youtube":
            continue
        if monitor and (monitor.abortRequested() or xbmc.Player().isPlaying()):
            return False
        record(ch["id"], check(ch))
        if monitor and monitor.waitForAbort(pause):
            return False
    return True
