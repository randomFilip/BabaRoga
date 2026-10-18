"""HTTP access that looks like an ordinary browser visit."""
from urllib.parse import urlparse

import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)
TIMEOUT = 12

_session = None


class GeoBlocked(Exception):
    """The broadcaster refuses viewers from this country."""


class Protected(Exception):
    """The stream needs a DRM licence, so it is left to the official site."""


class NotFound(Exception):
    """No stream link could be found where the official player keeps it."""


def session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept-Language": "mk,en;q=0.8",
        })
    return _session


def origin_of(url):
    p = urlparse(url)
    return "{}://{}".format(p.scheme, p.netloc)


def get(url, headers=None, allow_status=(200,)):
    resp = session().get(url, headers=headers or {}, timeout=TIMEOUT)
    if resp.status_code in (401, 403, 451):
        raise GeoBlocked("{} answered {}".format(urlparse(url).netloc, resp.status_code))
    if resp.status_code not in allow_status:
        raise NotFound("{} answered {}".format(urlparse(url).netloc, resp.status_code))
    return resp
