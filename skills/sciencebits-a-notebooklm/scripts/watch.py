#!/usr/bin/env python3
"""Watch DOWNLOADS_DIR, the student's `downloads.folder`, for capture zips (sb_*.zip) and copy every
finished capture downloaded since it started into RAW_DIR as sb_<tag>.zip.

Usage: python3 -u watch.py RAW_DIR DOWNLOADS_DIR
Runs on the Mac, in the background, one per unit; stop it when that unit's capture is done. A zip
already in the folder when it starts belongs to an earlier capture and is never collected, however
it is named: Chrome keeps it and names the new one «sb_<tag> (1).zip», and the tag comes from inside.
"""
import glob
import json
import os
import shutil
import sys
import time
import zipfile

USAGE = 'usage: watch.py RAW_DIR DOWNLOADS_DIR'
POLLS = 20000


def collect(raw, downloads, since, seen):
    """Copy each finished capture newer than `since` into `raw`; the tags it copied.

    `seen` holds path → size of what was read already. A zip still being written fails to open, stays
    out of `seen` and is read again on the next poll.
    """
    collected = []
    for path in glob.glob(os.path.join(downloads, 'sb_*.zip')):
        try:
            stat = os.stat(path)
            if stat.st_mtime < since or seen.get(path) == stat.st_size:
                continue
            with zipfile.ZipFile(path) as capture:
                meta = json.loads(capture.read('meta.json'))
            seen[path] = stat.st_size
            if not isinstance(meta, dict) or 'menu' not in meta or not meta.get('items'):
                continue
            shutil.copyfile(path, os.path.join(raw, 'sb_%s.zip' % meta['tag']))
            collected.append((meta['tag'], len(meta['items'])))
        except (OSError, KeyError, ValueError, zipfile.BadZipFile):
            continue
    return collected


def main(argv):
    if len(argv) != 2:
        sys.exit(USAGE)
    raw = os.path.expanduser(argv[0])
    downloads = os.path.expanduser(argv[1])
    os.makedirs(raw, exist_ok=True)
    since = time.time()
    seen = {}
    for _ in range(POLLS):
        for tag, items in collect(raw, downloads, since, seen):
            print(time.strftime('%H:%M:%S'), 'collected', tag, items, flush=True)
        time.sleep(1)


if __name__ == '__main__':
    main(sys.argv[1:])
