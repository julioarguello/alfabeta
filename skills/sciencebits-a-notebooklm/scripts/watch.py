#!/usr/bin/env python3
"""Watch DOWNLOADS_DIR, the student's `downloads.folder`, for capture zips (named sb_*.zip or the
Claude desktop app's temporary download files) and copy every finished capture into RAW_DIR as
sb_<tag>.zip.

Usage: python3 -u watch.py RAW_DIR DOWNLOADS_DIR
Runs on the Mac (start it with Desktop Commander start_process); stop it when the capture is done.
"""
import glob, json, os, shutil, sys, time, zipfile

if len(sys.argv) != 3:
    sys.exit('usage: watch.py RAW_DIR DOWNLOADS_DIR')
R = sys.argv[1]
D = os.path.expanduser(sys.argv[2])
os.makedirs(R, exist_ok=True)
seen = {}
for _ in range(20000):
    for f in glob.glob(os.path.join(D, '.*claudefordesktop*')) + glob.glob(os.path.join(D, 'sb_*.zip')):
        try:
            st = os.stat(f).st_size
            if seen.get(f) == st:
                continue
            m = json.loads(zipfile.ZipFile(f).read('meta.json'))
            seen[f] = st
            if 'menu' not in m or not m.get('items'):
                continue
            shutil.copyfile(f, os.path.join(R, 'sb_%s.zip' % m['tag']))
            print(time.strftime('%H:%M:%S'), 'collected', m['tag'], len(m['items']), flush=True)
        except Exception:
            pass
    time.sleep(1)
