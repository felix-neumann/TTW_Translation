"""Put German audio into a TTW sound archive.

Some German recordings are missed by voice-only tools, e.g. in Fallout 3 the intro
transitions ("10 years later" ..., sound\\fx\\qst\\qst_fadetowhite_*.wav), the radio
distress signals and Liberty Prime (sound\\fx\\voc\\...), or voice lines YUP replaced
with its own English files. This script compares German archives with one TTW archive,
takes every file that exists in both but differs (optionally filtered by regex), and
packs a new TTW archive with the German versions. All other files stay untouched and
the result is verified file by file.

Usage:
    python scripts/sound_fix.py --de "<DE>/Fallout - Sound.bsa" [--de ...]
                                --ttw "<TTW>/Fallout3 - Sound.bsa"
                                --bsarch "<path>/BSArch.exe" --out "<folder>"
                                [--include REGEX] [--exclude REGEX]

Paths in the regexes use forward slashes and lower case, e.g. --include "^sound/fx/voc/".
Find candidates first with scripts/sound_analyze.py.
"""
import argparse
import collections
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bsa import FLAG_COMPRESSED, BSA  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description='Deutsche Audiodateien in eine TTW-Sound-BSA übernehmen')
    ap.add_argument('--de', required=True, action='append', help='deutsche Quell-BSA (mehrfach möglich, erste gewinnt)')
    ap.add_argument('--ttw', required=True, help='TTW-BSA, die korrigiert werden soll')
    ap.add_argument('--bsarch', required=True, help='Pfad zu BSArch.exe')
    ap.add_argument('--out', required=True, help='Ausgabeordner für die neue BSA')
    ap.add_argument('--include', help='nur Pfade, die auf diesen regulären Ausdruck passen')
    ap.add_argument('--exclude', help='Pfade, die auf diesen regulären Ausdruck passen, auslassen')
    a = ap.parse_args()

    des = [BSA(p) for p in a.de]
    tt = BSA(a.ttw)
    if tt.flags & FLAG_COMPRESSED:
        sys.exit('Komprimierte Archive werden nicht unterstützt (Archiv-Flag 0x4 gesetzt).')
    inc = re.compile(a.include) if a.include else None
    exc = re.compile(a.exclude) if a.exclude else None

    def source(p):
        return next((d for d in des if p in d.files), None)

    diff = []
    for p in sorted(tt.files):
        if (inc and not inc.search(p)) or (exc and exc.search(p)):
            continue
        d = source(p)
        if d and d.read(p) != tt.read(p):
            diff.append((p, d))
    folders = collections.Counter(p.rsplit('/', 1)[0] for p, _ in diff)
    print(f'{os.path.basename(a.ttw)}: {len(diff)} Dateien werden durch die deutsche Fassung ersetzt:')
    for k, v in sorted(folders.items()):
        print(f'  {k}: {v}')
    if not diff:
        print('Nichts zu tun.')
        return

    os.makedirs(a.out, exist_ok=True)
    # BSArch detects the archive root by a folder named "sound" in the path, so the
    # staging folder must not contain such a folder name.
    staging = tempfile.mkdtemp(prefix='ttw_de_')
    out_bsa = os.path.join(os.path.abspath(a.out), os.path.basename(a.ttw))
    try:
        for p, d in diff:
            dst = os.path.join(staging, *p.split('/'))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as f:
                f.write(d.read(p))
        cmd = [a.bsarch, 'pack', f'{os.path.abspath(a.ttw)}+{staging}', out_bsa, '-fnv',
               f'-af:{tt.flags:#x}', f'-ff:{tt.file_flags:#x}']
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    nw = BSA(out_bsa)
    replaced = dict(diff)
    bad = [p for p in tt.files if nw.read(p) != (replaced[p].read(p) if p in replaced else tt.read(p))]
    if set(nw.files) != set(tt.files) or bad or (nw.flags, nw.file_flags) != (tt.flags, tt.file_flags):
        sys.exit(f'Prüfung fehlgeschlagen: {len(bad)} abweichende Dateien, Pfade gleich: {set(nw.files) == set(tt.files)}')
    list_path = os.path.join(a.out, os.path.splitext(os.path.basename(a.ttw))[0] + ' - ersetzte Dateien.txt')
    with open(list_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(f'{p.replace("/", chr(92))}  <-  {os.path.basename(d.path)}' for p, d in diff) + '\n')
    print(f'  -> {out_bsa} ({len(nw.files)} Dateien, {len(diff)} jetzt deutsch, Prüfung OK)')


if __name__ == '__main__':
    main()
