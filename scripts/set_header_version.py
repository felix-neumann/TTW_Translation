"""Set the header version (TES4 HEDR) of plugins, e.g. 0.94 (Fallout 3) -> 1.34 (New Vegas).

TTW reports plugins with a header version below 1.3 as "unconverted Fallout 3 mods".
Converting a FO3 plugin with FNVEdit (add TTW masters, run the TTW conversion script)
does not change this value. Only the 4-byte float in the header is changed; file size,
records and the file modification time (load order!) stay the same.

Usage:
    python scripts/set_header_version.py [--version 1.34] [--backup <folder>] <plugin> [<plugin> ...]
"""
import argparse
import os
import shutil
import struct
import sys


def hedr_offset(data):
    if data[:4] != b'TES4':
        raise ValueError('kein TES4-Header')
    size = struct.unpack_from('<I', data, 4)[0]
    i = 24
    while i < 24 + size:
        sig, ln = data[i:i + 4], struct.unpack_from('<H', data, i + 4)[0]
        if sig == b'HEDR':
            return i + 6
        i += 6 + ln
    raise ValueError('kein HEDR-Feld')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plugins', nargs='+')
    ap.add_argument('--version', type=float, default=1.34)
    ap.add_argument('--backup', help='Ordner für Sicherungskopien')
    a = ap.parse_args()
    for p in a.plugins:
        with open(p, 'rb') as f:
            head = bytearray(f.read(4096))
        off = hedr_offset(head)
        old = struct.unpack_from('<f', head, off)[0]
        if abs(old - a.version) < 1e-4:
            print(f'  {p}: bereits {old:.2f}')
            continue
        if a.backup:
            dst = os.path.join(a.backup, os.path.basename(os.path.dirname(p)) + ' - ' + os.path.basename(p))
            os.makedirs(a.backup, exist_ok=True)
            shutil.copy2(p, dst)
        st = os.stat(p)
        with open(p, 'r+b') as f:
            f.seek(off)
            f.write(struct.pack('<f', a.version))
        os.utime(p, (st.st_atime, st.st_mtime))  # keep the date (load order)
        with open(p, 'rb') as f:
            chk = struct.unpack_from('<f', f.read(4096), off)[0]
        ok = abs(chk - a.version) < 1e-4 and os.path.getmtime(p) == st.st_mtime and os.path.getsize(p) == st.st_size
        print(f'  {p}: {old:.2f} -> {chk:.2f}  {"OK" if ok else "FEHLER"}')
        if not ok:
            sys.exit(1)


if __name__ == '__main__':
    main()
