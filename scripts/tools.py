"""Helpers for translating new strings.

    python scripts/tools.py glossary --work <work> "Regex" ["Regex" ...]
        Search official English->German terms (names, items, perks ...) from the game files.

    python scripts/tools.py check [--translations translations/claude_translations.json]
        Validate translations: cp1252-encodable, same format placeholders (%.0f, %g, %%).

    python scripts/tools.py merge <untranslated.json> [--translations ...]
        Append filled-in entries from untranslated.json to the translation file.
"""
import argparse
import glob
import json
import os
import pickle
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TR = os.path.join(HERE, '..', 'translations', 'claude_translations.json')
FMT = re.compile(r'%%|%[-+#0]*\d*(?:\.\d+)?[dsfgieuxX]\b')


def glossary(work, patterns, limit=15):
    ex = os.path.join(work, 'extract')
    g = {}
    for game in ('FNV', 'FO3'):
        for enp in sorted(glob.glob(os.path.join(ex, 'en', f'{game}_*.pkl'))):
            with open(enp, 'rb') as f:
                E = pickle.load(f)['entries']
            with open(os.path.join(ex, 'de', os.path.basename(enp)), 'rb') as f:
                dk = {(e[1], e[2], e[0], e[5], e[6]): e[7] for e in pickle.load(f)['entries']}
            for t, o, oid, fid, edid, s, i, txt in E:
                k = (o, oid, t, s, i)
                if k in dk and len(txt) <= 80 and t not in ('INFO', 'DIAL'):
                    g.setdefault(txt, {}).setdefault(dk[k], f'{game} {t}')
    for q in patterns:
        rx, n = re.compile(q, re.I), 0
        for en, des in g.items():
            if rx.search(en):
                print(f'{en!r:45} -> ' + ' | '.join(f'{d} ({v})' for d, v in list(des.items())[:3]))
                n += 1
                if n >= limit:
                    break


def check(path):
    with open(path, encoding='utf-8') as f:
        items = json.load(f)
    errors = 0
    for x in items:
        de = x.get('de')
        if de is None:
            continue
        try:
            de.encode('cp1252')
        except UnicodeEncodeError as e:
            print('Kodierung:', repr(x['en'][:50]), e)
            errors += 1
        if sorted(FMT.findall(x['en'])) != sorted(FMT.findall(de)):
            print('Platzhalter:', repr(x['en'][:50]), FMT.findall(x['en']), FMT.findall(de))
            errors += 1
    print(f'{len(items)} Einträge, {sum(1 for x in items if x.get("de") is None)} bleiben englisch, {errors} Fehler')
    return errors


def merge(untranslated, path):
    with open(path, encoding='utf-8') as f:
        items = json.load(f)
    known = {x['en'] for x in items}
    with open(untranslated, encoding='utf-8') as f:
        new = json.load(f)
    added = [x for x in new if x['en'] not in known]
    items.extend(added)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    print(f'{len(added)} Einträge hinzugefügt ({sum(1 for x in added if x.get("de") is None)} davon ohne "de" = bleiben englisch)')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    g = sub.add_parser('glossary')
    g.add_argument('--work', required=True)
    g.add_argument('patterns', nargs='+')
    c = sub.add_parser('check')
    c.add_argument('--translations', default=DEFAULT_TR)
    m = sub.add_parser('merge')
    m.add_argument('untranslated')
    m.add_argument('--translations', default=DEFAULT_TR)
    a = ap.parse_args()
    if a.cmd == 'glossary':
        glossary(a.work, a.patterns)
    elif a.cmd == 'check':
        sys.exit(1 if check(a.translations) else 0)
    else:
        merge(a.untranslated, a.translations)
