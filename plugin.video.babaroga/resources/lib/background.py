"""Background service: daily channel-list update and periodic health checks."""
import xbmc

from . import catalog, common, health

UPDATE_EVERY = 24 * 3600
CHECK_EVERY = 6 * 3600
TICK = 300  # seconds between looks at the clock


def run():
    monitor = xbmc.Monitor()
    if monitor.waitForAbort(60):  # let Kodi finish starting up
        return
    while not monitor.abortRequested():
        state = common.read_json("service.json", {})
        now = common.now()

        if common.setting_bool("auto_update") and now - state.get("updated", 0) > UPDATE_EVERY:
            try:
                catalog.update_from_github()
            except Exception as exc:
                common.log("channel list update failed: {}".format(exc))
            state["updated"] = now
            common.write_json("service.json", state)

        if (common.setting_bool("health_check") and now - state.get("checked", 0) > CHECK_EVERY
                and not xbmc.Player().isPlaying()):
            if health.run_all(monitor):
                state["checked"] = common.now()
                common.write_json("service.json", state)

        if monitor.waitForAbort(TICK):
            break
