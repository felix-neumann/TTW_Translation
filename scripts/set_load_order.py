"""Set plugin file dates so that Fallout 3 / New Vegas load plugins in the given order.

These games ignore the order in plugins.txt / loadorder.txt and sort plugins by file
modification time (masters before plugins). MO2 does the same as this script for its
virtual Data folder: 2000-01-01 00:00 UTC plus one day per position. Use it for a
manually maintained game folder (e.g. one copied to a Steam Deck); it works on Windows
and Linux and only changes file dates, never contents.

Usage:
    python scripts/set_load_order.py --loadorder "<MO2>/profiles/<Profil>/loadorder.txt" --data "<Spiel>/Data"
    python scripts/set_load_order.py ... --check     (only report, change nothing)
"""
import argparse
import datetime
import os
import sys

BASE = 946684800  # 2000-01-01 00:00:00 UTC, as used by MO2
DAY = 86400


def read_order(path):
    with open(path, encoding='utf-8-sig') as f:
        return [l.strip().lstrip('*') for l in f if l.strip() and not l.startswith('#')]


def files_by_name(data):
    return {n.lower(): os.path.join(data, n) for n in os.listdir(data) if n.lower().endswith(('.esm', '.esp'))}


def current_order(found):
    """Order the game would use: masters first, then by modification time."""
    def key(item):
        name, path = item
        return (not name.lower().endswith('.esm'), os.path.getmtime(path))
    return [n for n, _ in sorted(found, key=key)]


def main():
    ap = argparse.ArgumentParser(description='Plugin-Zeitstempel gemäß Ladereihenfolge setzen')
    ap.add_argument('--loadorder', required=True, help='loadorder.txt (z. B. aus dem MO2-Profil)')
    ap.add_argument('--data', required=True, help='Data-Ordner des Spiels')
    ap.add_argument('--check', action='store_true', help='nur prüfen, nichts ändern')
    a = ap.parse_args()

    order = read_order(a.loadorder)
    files = files_by_name(a.data)
    found = [(n, files[n.lower()]) for n in order if n.lower() in files]
    missing = [n for n in order if n.lower() not in files]
    extra = sorted(os.path.basename(p) for k, p in files.items() if k not in {n.lower() for n in order})
    if missing:
        print('Nicht im Data-Ordner (übersprungen):', ', '.join(missing))
    if extra:
        print('Im Data-Ordner, aber nicht in der Ladereihenfolge (unverändert):', ', '.join(extra))

    wanted = [n for n, _ in found]
    if current_order(found) == wanted:
        print(f'Ladereihenfolge stimmt bereits ({len(wanted)} Plugins).')
        if a.check:
            return
    elif a.check:
        print('Ladereihenfolge stimmt NICHT. Aktuell (nach Datum):')
        for i, n in enumerate(current_order(found)):
            print(f'  {i:3} {n}' + ('' if n == wanted[i] else f'   <- sollte sein: {wanted[i]}'))
        sys.exit(1)

    for i, (name, path) in enumerate(found):
        t = BASE + i * DAY
        os.utime(path, (t, t))
    result = current_order(found)
    ok = result == wanted
    for i, (name, path) in enumerate(found):
        d = datetime.datetime.fromtimestamp(os.path.getmtime(path))
        print(f'  {i:3} {d:%Y-%m-%d %H:%M}  {name}')
    print('Ladereihenfolge gesetzt und geprüft: ' + ('OK' if ok else 'FEHLER'))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
