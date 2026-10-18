"""Compare TTW sound/voice archives with the German original game archives.

For every file under sound\\ in a TTW archive, the same path is looked up in the German
archives of the game the TTW archive is based on (both games for TTW's own archives).
Result per TTW archive: identical to German / different from German / not in German.
"Different" files are candidates for still-English audio; they are listed per folder
and written to a JSON file for sound_fix.py-style repacking.

Usage:
    python scripts/sound_analyze.py --de <folder with German BSAs> --ttw <folder with TTW BSAs> --out report.json
"""
import argparse
import collections
import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bsa import BSA  # noqa: E402

FO3_DE = ['fallout - sound.bsa', 'fallout - voices.bsa', 'fallout - menuvoices.bsa', 'anchorage - sounds.bsa',
          'brokensteel - sounds.bsa', 'pointlookout - sounds.bsa', 'thepitt - sounds.bsa', 'zeta - sounds.bsa']
FNV_DE = ['fallout - voices1.bsa', 'deadmoney - sounds.bsa', 'honesthearts - sounds.bsa',
          'oldworldblues - sounds.bsa', 'lonesomeroad - sounds.bsa', 'gunrunnersarsenal - sounds.bsa']
FO3_TTW_PREFIX = ('fallout3 - ', 'anchorage - ', 'brokensteel - ', 'pointlookout - ', 'thepitt - ', 'zeta - ')
FNV_TTW_PREFIX = ('fallout - ', 'deadmoney - ', 'honesthearts - ', 'oldworldblues - ', 'lonesomeroad - ',
                  'gunrunnersarsenal - ')


def digest(b, p):
    return hashlib.md5(b.read(p)).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--de', required=True)
    ap.add_argument('--ttw', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    def open_all(folder):
        return {n.lower(): BSA(os.path.join(folder, n)) for n in sorted(os.listdir(folder)) if n.lower().endswith('.bsa')}

    de, ttw = open_all(a.de), open_all(a.ttw)
    pools = {'FO3': [de[n] for n in FO3_DE if n in de], 'FNV': [de[n] for n in FNV_DE if n in de]}
    print('Deutsche Archive:', {k: [os.path.basename(b.path) for b in v] for k, v in pools.items()})

    def lookup(game, path):
        for b in pools[game]:
            if path in b.files:
                return b
        return None

    report = {}
    for name, tb in ttw.items():
        games = ['FO3'] if name.startswith(FO3_TTW_PREFIX) else ['FNV'] if name.startswith(FNV_TTW_PREFIX) else ['FNV', 'FO3']
        files = [p for p in tb.files if p.startswith('sound/')]
        stat = collections.Counter()
        diff = collections.defaultdict(list)

        def check(p):
            hits = [(g, lookup(g, p)) for g in games]
            hits = [(g, b) for g, b in hits if b]
            if not hits:
                return p, 'nicht in DE', None
            t = digest(tb, p)
            for g, b in hits:
                if digest(b, p) == t:
                    return p, 'identisch', g
            g, b = hits[0]
            return p, 'unterschiedlich', f'{g}:{os.path.basename(b.path)}'

        with ThreadPoolExecutor(8) as ex:
            for p, res, src in ex.map(check, files):
                stat[res] += 1
                if res == 'unterschiedlich':
                    diff[p.rsplit('/', 1)[0]].append((p, src))
        report[name] = dict(stats=dict(stat), different={k: v for k, v in sorted(diff.items())})
        print(f'\n== {os.path.basename(tb.path)} ({"/".join(games)}): {len(files)} Sound-Dateien, {dict(stat)}')
        top = collections.Counter()
        for k, v in diff.items():
            top['/'.join(k.split('/')[:4])] += len(v)
        for k, v in top.most_common(15):
            print(f'     {v:6}  {k}')
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=1)


if __name__ == '__main__':
    main()
