"""Hand an official YouTube live over to the YouTube add-on."""
import xbmc

from . import Stream
from .. import net


def resolve(ch, source):
    if not xbmc.getCondVisibility("System.HasAddon(plugin.video.youtube)"):
        raise net.NotFound("install the YouTube add-on to watch this channel")
    if source.get("video_id"):
        url = "plugin://plugin.video.youtube/play/?video_id={}".format(source["video_id"])
    else:
        url = "plugin://plugin.video.youtube/play/?channel_id={}&live=1".format(source["channel_id"])
    return Stream(url, kind="plugin")
