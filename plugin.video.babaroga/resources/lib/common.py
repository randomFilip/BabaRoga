"""Shared Kodi helpers: settings, storage paths, logging."""
import json
import os
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")
ADDON_NAME = ADDON.getAddonInfo("name")
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo("path"))
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))


def log(msg, level=xbmc.LOGINFO):
    xbmc.log("[{}] {}".format(ADDON_ID, msg), level)


def setting(key):
    return ADDON.getSetting(key)


def setting_bool(key):
    return ADDON.getSetting(key).lower() == "true"


def notify(message, seconds=4):
    xbmcgui.Dialog().notification(ADDON_NAME, message, xbmcgui.NOTIFICATION_INFO, seconds * 1000)


def kodi_major():
    build = xbmc.getInfoLabel("System.BuildVersion")
    try:
        return int(build.split(".")[0])
    except ValueError:
        return 21


def profile_path(name):
    if not os.path.isdir(PROFILE):
        os.makedirs(PROFILE, exist_ok=True)
    return os.path.join(PROFILE, name)


def read_json(name, default):
    path = profile_path(name)
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def write_json(name, data):
    path = profile_path(name)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def now():
    return int(time.time())
