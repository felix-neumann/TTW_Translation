"""Extract all translatable text fields from a plugin.

Each entry is a tuple:
    (record type, origin plugin, object id, raw FormID, EditorID, field, occurrence, text)

"origin plugin" + "object id" identify a record independent of the load order:
TTW prepends the New Vegas masters to the Fallout 3 files, so raw FormIDs of
the same record differ between the original game files and the TTW files.
"""
import collections
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from esm import iter_records, parse_subs  # noqa: E402

# Fields found (by diffing the English and German game files) to hold translated text.
ANY_RECORD = {'FULL', 'DESC'}
SPECIFIC = {
    ('INFO', 'NAM1'), ('INFO', 'RNAM'), ('QUST', 'CNAM'), ('QUST', 'NNAM'), ('MESG', 'ITXT'),
    ('TERM', 'ITXT'), ('TERM', 'RNAM'), ('NOTE', 'TNAM'), ('AMMO', 'ONAM'), ('AMMO', 'QNAM'),
    ('AVIF', 'ANAM'), ('FACT', 'MNAM'), ('FACT', 'FNAM'), ('BPTD', 'BPTN'), ('REGN', 'RDMP'),
    ('GMST', 'DATA'), ('REFR', 'XATO'), ('ACHR', 'XATO'), ('ACRE', 'XATO'), ('ACTI', 'XATO'),
    ('DIAL', 'TDUM'), ('PERK', 'EPF2'),
}


def is_text(b):
    if not b.endswith(b'\0') or len(b) < 2:
        return False
    return not any(c < 9 or 13 < c < 32 and c != 27 for c in b[:-1]) and b'\0' not in b[:-1]


def extract(path):
    name = os.path.basename(path).lower()
    masters, out = [], []
    for t, fid, fl, data in iter_records(path):
        subs = parse_subs(data)
        if t == 'TES4':
            masters = [b.rstrip(b'\0').decode('cp1252').lower() for s, b in subs if s == b'MAST']
            continue
        idx = fid >> 24
        origin = masters[idx] if idx < len(masters) else name
        edid = next((b[:-1].decode('cp1252') for s, b in subs if s == b'EDID'), '')
        occ = collections.Counter()
        for s, b in subs:
            s = s.decode('latin1')
            k = (t, s)
            i = occ[k]
            occ[k] += 1
            if (s in ANY_RECORD or k in SPECIFIC) and is_text(b):
                if t == 'GMST' and not edid.startswith('s'):
                    continue  # only string game settings
                try:
                    txt = b[:-1].decode('cp1252')
                except UnicodeDecodeError:
                    continue
                out.append((t, origin, fid & 0xFFFFFF, fid, edid, s, i, txt))
    return dict(name=name, masters=masters, entries=out)


def extract_to(src, dst):
    r = extract(src)
    with open(dst, 'wb') as f:
        pickle.dump(r, f)
    return os.path.basename(src), len(r['entries'])


if __name__ == '__main__':
    print(*extract_to(sys.argv[1], sys.argv[2]))
