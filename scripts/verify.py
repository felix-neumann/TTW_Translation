"""Compare a translated plugin with its source: same records in the same order,
same headers, and only null-terminated text fields may differ."""
import collections
import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from esm import iter_records, parse_subs  # noqa: E402


def verify(a, b):
    st, errs = collections.Counter(), []
    for ra, rb in itertools.zip_longest(iter_records(a), iter_records(b)):
        if ra is None or rb is None:
            errs.append('record count differs')
            break
        ta, fa, fla, da = ra
        tb, fb, flb, db = rb
        if (ta, fa, fla) != (tb, fb, flb):
            errs.append(('header', ta, hex(fa), tb, hex(fb)))
            continue
        st['records'] += 1
        if da == db:
            continue
        sa, sb = parse_subs(da), parse_subs(db)
        if [s for s, _ in sa] != [s for s, _ in sb]:
            errs.append(('subrecord list', ta, hex(fa)))
            continue
        for (s, x), (_, y) in zip(sa, sb):
            if x != y:
                st['changed_fields'] += 1
                if not (x.endswith(b'\0') and y.endswith(b'\0')):
                    errs.append(('non-text field changed', ta, hex(fa), s))
                try:
                    y[:-1].decode('cp1252')
                except UnicodeDecodeError:
                    errs.append(('encoding', ta, hex(fa), s))
    return st, errs


if __name__ == '__main__':
    st, errs = verify(sys.argv[1], sys.argv[2])
    print(os.path.basename(sys.argv[1]), dict(st), 'errors:', len(errs), errs[:5])
    sys.exit(1 if errs else 0)
