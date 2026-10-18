"""Build the Kodi repository served by GitHub Pages from the docs/ folder.

Usage: python tools/build_repo.py

Writes:
  docs/index.html                         page Kodi's file manager can browse
  docs/repository.babaroga-<v>.zip        install this first (updates come through it)
  docs/plugin.video.babaroga-<v>.zip      the add-on itself, for a one-off install
  docs/repo/addons.xml (+ .md5)           what Kodi reads to find updates
  docs/repo/<addon id>/<addon id>-<v>.zip

Zips are built with fixed timestamps, so the same files always give the
same zip and the check workflow can tell when docs/ is out of date.
"""
import hashlib
import os
import re
import shutil
import zipfile

ADDONS = ["plugin.video.babaroga", "repository.babaroga"]
OUT = "docs"
SKIP_DIRS = {"__pycache__"}
SKIP_EXT = {".pyc", ".pyo", ".tmp"}
FIXED_TIME = (2020, 1, 1, 0, 0, 0)


def addon_xml(addon):
    with open(os.path.join(addon, "addon.xml"), encoding="utf-8") as fh:
        return fh.read()


def version(addon):
    return re.search(r'<addon[^>]+version="([^"]+)"', addon_xml(addon)).group(1)


def build_zip(addon, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    out = os.path.join(dest_dir, "{}-{}.zip".format(addon, version(addon)))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(addon):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for name in sorted(files):
                if os.path.splitext(name)[1] in SKIP_EXT:
                    continue
                path = os.path.join(root, name)
                info = zipfile.ZipInfo(path.replace(os.sep, "/"), FIXED_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                with open(path, "rb") as fh:
                    zf.writestr(info, fh.read())
    return out


def main():
    repo_dir = os.path.join(OUT, "repo")
    if os.path.isdir(repo_dir):
        shutil.rmtree(repo_dir)
    for old in os.listdir(OUT) if os.path.isdir(OUT) else []:
        if old.endswith(".zip"):
            os.remove(os.path.join(OUT, old))
    os.makedirs(repo_dir, exist_ok=True)

    parts = []
    for addon in ADDONS:
        build_zip(addon, os.path.join(repo_dir, addon))
        body = re.sub(r"^<\?xml[^>]*\?>\s*", "", addon_xml(addon).strip())
        parts.append(body)
    addons = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n{}\n</addons>\n'.format("\n".join(parts))
    with open(os.path.join(repo_dir, "addons.xml"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(addons)
    with open(os.path.join(repo_dir, "addons.xml.md5"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(hashlib.md5(addons.encode("utf-8")).hexdigest())

    # Top-level copies, so Kodi's file manager shows both zips in one list.
    links = [os.path.basename(build_zip(addon, OUT)) for addon in ("repository.babaroga", "plugin.video.babaroga")]
    html = "<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\"><title>BabaRoga</title></head><body>\n"
    html += "".join('<a href="{0}">{0}</a><br>\n'.format(link) for link in links)
    html += "</body></html>\n"
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    for link in links:
        print(os.path.join(OUT, link))


if __name__ == "__main__":
    main()
