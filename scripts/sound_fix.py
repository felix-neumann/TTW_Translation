"""Put German sound effects with speech into the TTW sound archive.

The German Fallout 3 "Fallout - Sound.bsa" contains localized recordings outside of
sound\\voice\\ that voice-only tools miss: the intro transitions ("10 years later" ...,
sound\\fx\\qst\\qst_fadetowhite_*.wav), the radio distress signals and Liberty Prime
(sound\\fx\\voc\\...). This script compares the German archive with the TTW archive,
takes every file that exists in both but differs, and packs a new TTW archive with
the German versions (all other files stay untouched).

Usage:
    python scripts/sound_fix.py --de "<DE FO3>/Data/Fallout - Sound.bsa"
                                --ttw "<TTW>/Fallout3 - Sound.bsa"
                                --bsarch "<path>/BSArch.exe"
                                --out "<folder>"
"""
import argparse
import collections
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bsa import BSA  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description='Deutsche Sprach-Effekte in die TTW-Sound-BSA übernehmen')
    ap.add_argument('--de', required=True, help='deutsche "Fallout - Sound.bsa" (Fallout 3)')
    ap.add_argument('--ttw', required=True, help='aktuelle TTW-"Fallout3 - Sound.bsa"')
    ap.add_argument('--bsarch', required=True, help='Pfad zu BSArch.exe')
    ap.add_argument('--out', required=True, help='Ausgabeordner für die neue BSA')
    a = ap.parse_args()

    de, tt = BSA(a.de), BSA(a.ttw)
    diff = sorted(p for p in tt.files if p in de.files and de.read(p) != tt.read(p))
    folders = collections.Counter(p.rsplit('/', 1)[0] for p in diff)
    print(f'{len(diff)} Dateien unterscheiden sich:')
    for k, v in sorted(folders.items()):
        print(f'  {k}: {v}')
    if not diff:
        print('Nichts zu tun.')
        return

    os.makedirs(a.out, exist_ok=True)
    # BSArch detects the archive root by a folder named "sound" in the path, so the
    # staging folder must not contain such a folder name.
    staging = tempfile.mkdtemp(prefix='ttw_de_')
    try:
        for p in diff:
            dst = os.path.join(staging, *p.split('/'))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as f:
                f.write(de.read(p))
        out_bsa = os.path.join(os.path.abspath(a.out), os.path.basename(a.ttw))
        cmd = [a.bsarch, 'pack', f'{os.path.abspath(a.ttw)}+{staging}', out_bsa, '-fnv',
               f'-af:{tt.flags:#x}', f'-ff:{tt.file_flags:#x}']
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    nw = BSA(out_bsa)
    bad = [p for p in tt.files if nw.read(p) != (de.read(p) if p in diff else tt.read(p))]
    if set(nw.files) != set(tt.files) or bad:
        sys.exit(f'Prüfung fehlgeschlagen: {len(bad)} abweichende Dateien, Pfade gleich: {set(nw.files) == set(tt.files)}')
    with open(os.path.join(a.out, 'ersetzte_dateien.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(p.replace('/', '\\') for p in diff) + '\n')
    print(f'Fertig: {out_bsa} ({len(nw.files)} Dateien, {len(diff)} jetzt deutsch, Prüfung OK)')


if __name__ == '__main__':
    main()
