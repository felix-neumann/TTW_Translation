"""Check a manually maintained (non-MO2) game folder before playing or copying it to e.g. a Steam Deck.

Checks:
  1. INIs (Fallout.ini, FalloutPrefs.ini): archive invalidation set up like MO2 does it
     (bInvalidateOlderFiles=1, empty SInvalidationFile, an invalidation BSA first in
     SArchiveList that exists in Data), sLanguage, read-only flag. Without the invalidation
     BSA, loose files only win against an archive if they are newer than it - copied archives
     are usually newer than mod files, so mods silently stop working.
  2. Templates in the install folder (Fallout_default.ini, low/medium/high/VeryHigh.ini) that
     the game/launcher use to recreate the INIs.
  3. Load order: plugin file dates must follow loadorder.txt (see set_load_order.py).
  4. Plugin header versions: TTW reports plugins below 1.3 as unconverted Fallout 3 mods.
  5. Loose files that would lose against an archive if invalidation were missing.

Usage:
    python scripts/check_gamedir.py --game "<...>/Fallout New Vegas" --inis "<...>/My Games/FalloutNV"
                                    [--loadorder "<MO2>/profiles/Default/loadorder.txt"] [--language GERMAN]
Exit code 1 if a problem was found.
"""
import argparse
import os
import stat
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bsa import BSA  # noqa: E402
from set_load_order import current_order, files_by_name, read_order  # noqa: E402

problems = []


def problem(msg):
    problems.append(msg)
    print('  PROBLEM:', msg)


def ok(msg):
    print('  ok:', msg)


def read_ini(path):
    """Tolerant INI reader: Bethesda INIs contain free text lines; later values win."""
    values, section = {}, ''
    with open(path, encoding='cp1252', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith((';', '#')):
                continue
            if line.startswith('[') and line.endswith(']'):
                section = line[1:-1].strip().lower()
            elif '=' in line:
                k, v = line.split('=', 1)
                values[(section, k.strip().lower())] = v.strip()
    return values


def get(values, section, key):
    return values.get((section.lower(), key.lower()))


def check_archive(cp, name, data, language, required):
    inv = get(cp, 'Archive', 'bInvalidateOlderFiles')
    sinv = get(cp, 'Archive', 'SInvalidationFile')
    alist = get(cp, 'Archive', 'SArchiveList')
    if inv is None and alist is None and not required:
        ok(f'{name}: kein [Archive]-Abschnitt (wird aus anderer INI genommen)')
        return
    if inv != '1':
        problem(f'{name}: bInvalidateOlderFiles={inv} (soll 1)')
    if sinv not in ('', None):
        problem(f'{name}: SInvalidationFile={sinv} (soll leer sein)')
    first = (alist or '').split(',')[0].strip()
    if not first.lower().startswith('fallout - invalidation') and 'aii' not in first.lower() and 'ai!' not in first.lower():
        problem(f'{name}: SArchiveList beginnt nicht mit einer Invalidierungs-BSA ({first!r})')
    elif not os.path.exists(os.path.join(data, first)):
        problem(f'{name}: Invalidierungs-BSA {first!r} fehlt im Data-Ordner')
    else:
        ok(f'{name}: Archiv-Invalidierung über {first}')
    lang = get(cp, 'General', 'sLanguage')
    if language and lang and lang.upper() != language.upper():
        problem(f'{name}: sLanguage={lang} (erwartet {language})')


def main():
    ap = argparse.ArgumentParser(description='Manuell gepflegtes Spielverzeichnis prüfen')
    ap.add_argument('--game', required=True, help='Spielordner (mit FalloutNV.exe und Data)')
    ap.add_argument('--inis', help='Ordner mit Fallout.ini/FalloutPrefs.ini (z. B. Dokumente/My Games/FalloutNV)')
    ap.add_argument('--loadorder', help='loadorder.txt (z. B. aus dem MO2-Profil)')
    ap.add_argument('--language', default='GERMAN')
    a = ap.parse_args()
    data = os.path.join(a.game, 'Data')

    print('== 1) INIs ==')
    if a.inis:
        for n in ('Fallout.ini', 'FalloutPrefs.ini'):
            p = os.path.join(a.inis, n)
            if not os.path.exists(p):
                problem(f'{n} fehlt in {a.inis}')
                continue
            if not os.stat(p).st_mode & stat.S_IWRITE:
                problem(f'{n} ist schreibgeschützt (Kopieren/Überschreiben schlägt still fehl)')
            check_archive(read_ini(p), n, data, a.language, required=(n == 'Fallout.ini'))
    else:
        print('  übersprungen (--inis nicht angegeben)')

    print('== 2) Vorlagen im Installationsordner ==')
    for n, req in (('Fallout_default.ini', True), ('low.ini', False), ('medium.ini', False), ('high.ini', False), ('VeryHigh.ini', False)):
        p = os.path.join(a.game, n)
        if os.path.exists(p):
            cp = read_ini(p)
            check_archive(cp, n, data, a.language if n == 'Fallout_default.ini' else None, req)
            mip = get(cp, 'Display', 'iTexMipMapSkip')
            if mip not in (None, '0'):
                problem(f'{n}: iTexMipMapSkip={mip} (Texturen werden verkleinert geladen)')

    print('== 3) Ladereihenfolge ==')
    if a.loadorder:
        order = read_order(a.loadorder)
        files = files_by_name(data)
        found = [(n, files[n.lower()]) for n in order if n.lower() in files]
        if current_order(found) == [n for n, _ in found]:
            ok(f'Datumsreihenfolge entspricht loadorder.txt ({len(found)} Plugins)')
        else:
            problem('Plugin-Daten entsprechen nicht loadorder.txt -> set_load_order.py ausführen')
        extra = sorted(os.path.basename(p) for k, p in files.items() if k not in {n.lower() for n in order})
        if extra:
            problem('Plugins im Data-Ordner, die nicht in loadorder.txt stehen: ' + ', '.join(extra))
    else:
        print('  übersprungen (--loadorder nicht angegeben)')

    print('== 4) Plugin-Header ==')
    low = []
    for n in sorted(os.listdir(data)):
        if n.lower().endswith(('.esm', '.esp')):
            head = open(os.path.join(data, n), 'rb').read(4096)
            i = head.find(b'HEDR')
            if i >= 0 and struct.unpack_from('<f', head, i + 6)[0] < 1.3:
                low.append(n)
    if low:
        problem('Header-Version < 1.3 (TTW: "nicht konvertiert") -> set_header_version.py: ' + ', '.join(low))
    else:
        ok('alle Plugins haben Header-Version >= 1.3')

    print('== 5) Lose Dateien, die ohne Invalidierung gegen ein neueres Archiv verlieren würden ==')
    times, override = {}, set()
    for n in os.listdir(data):
        if n.lower().endswith('.bsa'):
            try:
                b = BSA(os.path.join(data, n))
            except Exception:
                continue
            ov = os.path.exists(os.path.join(data, n[:-4] + '.override'))
            t = os.path.getmtime(os.path.join(data, n))
            for p in b.files:
                if ov:
                    override.add(p)
                else:
                    times[p] = max(times.get(p, 0), t)
    count = 0
    for r, _, fs in os.walk(data):
        for f in fs:
            full = os.path.join(r, f)
            rel = os.path.relpath(full, data).lower().replace('\\', '/')
            if rel in times and rel not in override and os.path.getmtime(full) < times[rel]:
                count += 1
    print(f'  {count} lose Dateien wären ohne Invalidierungs-BSA wirkungslos'
          + (' (unkritisch, solange Punkt 1 in Ordnung ist)' if count else ''))

    print('\nErgebnis:', 'alles in Ordnung' if not problems else f'{len(problems)} Problem(e)')
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
