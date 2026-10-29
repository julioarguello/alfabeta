#!/usr/bin/env python3
"""Build a clickable PDF + a Markdown file per language from Science Bits capture zips.

Usage: build.py RAW_DIR OUT_DIR --config UNIT_JSON LANG [LANG ...]
RAW_DIR holds sb_<lang>_L<n>.zip files (one per lesson) produced by the capture job; OUT_DIR gets
TemaNN_<LANG>.pdf and .md. UNIT_JSON names the topic, which no default may do (constitution I):
{"prefix": "TemaNN", "langs": {"<lang>": {"unit": "<topic title>", "course": "<subject> · <grade level>"}}},
one entry per LANG. Without it, or without one of its keys, the build stops and names the key.

This file reads the configuration with the standard library only, and render.py, which loads the
PDF and HTML libraries and the fonts, runs only once it is complete.
"""
import json
import re
import sys

USAGE = 'usage: build.py RAW_DIR OUT_DIR --config UNIT_JSON LANG [LANG ...]'
PREFIX = re.compile(r'Tema\d{2}')
TEXTS = ('unit', 'course')


def missing(key):
    sys.exit('build.py: missing %s\n%s' % (key, USAGE))


def read_config(argv):
    """RAW_DIR, OUT_DIR, the prefix and each language's topic texts; exits naming the first key missing."""
    if len(argv) < 2 or argv[0] == '--config' or argv[1] == '--config':
        missing('RAW_DIR OUT_DIR')
    raw, out, rest = argv[0], argv[1], argv[2:]
    if len(rest) < 2 or rest[0] != '--config':
        missing('--config')
    path, langs = rest[1], rest[2:]
    if not langs:
        missing('LANG')
    try:
        with open(path, encoding='utf-8') as handle:
            unit = json.load(handle)
    except (OSError, ValueError):
        sys.exit('build.py: --config is not a readable JSON file\n%s' % USAGE)
    if not isinstance(unit, dict):
        missing('prefix')
    prefix = unit.get('prefix')
    if not isinstance(prefix, str) or not PREFIX.fullmatch(prefix):
        missing('prefix (TemaNN, two digits)')
    given = unit.get('langs') if isinstance(unit.get('langs'), dict) else {}
    texts = {}
    for lang in langs:
        entry = given.get(lang) if isinstance(given.get(lang), dict) else {}
        for key in TEXTS:
            value = entry.get(key)
            if not isinstance(value, str) or not value.strip():
                missing('langs.%s.%s' % (lang, key))
        texts[lang] = {key: entry[key] for key in TEXTS}
    return raw, out, prefix, texts


def main(argv):
    raw, out, prefix, texts = read_config(argv)
    import render  # only now: the libraries and the fonts it loads are not needed to report a key

    for lang in texts:
        if lang not in render.L10N:
            sys.exit('build.py: render.py has no interface texts for %s\n%s' % (lang, USAGE))
    for lang, own in texts.items():
        render.L10N[lang].update(own)
        render.build(raw, out, lang, prefix)


if __name__ == '__main__':
    main(sys.argv[1:])
