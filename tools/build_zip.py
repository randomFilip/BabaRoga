"""Build the installable add-on zip: dist/plugin.video.babaroga-<version>.zip

Usage: python tools/build_zip.py
"""
import os
import re
import zipfile

ADDON = "plugin.video.babaroga"
SKIP_DIRS = {"__pycache__"}
SKIP_EXT = {".pyc", ".pyo", ".tmp"}


def version():
    with open(os.path.join(ADDON, "addon.xml"), encoding="utf-8") as fh:
        text = fh.read()
    return re.search(r'<addon[^>]+version="([^"]+)"', text).group(1)


def main():
    os.makedirs("dist", exist_ok=True)
    out = os.path.join("dist", "{}-{}.zip".format(ADDON, version()))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(ADDON):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for name in sorted(files):
                if os.path.splitext(name)[1] in SKIP_EXT:
                    continue
                path = os.path.join(root, name)
                zf.write(path, path.replace(os.sep, "/"))
    print(out)


if __name__ == "__main__":
    main()
