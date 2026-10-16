"""Decide the German text for every text field of the files in "To Translate".

Priority per field:
  1. Same origin record exists in the original game files with identical English
     text -> its official German text (FO3 or FNV, whichever game the record is from).
  2. Same English string translated anywhere else: FNV before FO3 (same record
     type + field first, then any field, then whitespace/case-insensitive).
  3. Origin record exists but TTW/YUP changed the English text slightly
     (>= 80 % similar and the same numbers) -> official German text of the original.
  4. Otherwise "new": needs a translation from translations/claude_translations.json.

GMSTs are matched by EditorID instead of FormID.
"""
import collections
import difflib
import glob
import json
import os
import pickle
import re


def _load(p):
    with open(p, 'rb') as f:
        return pickle.load(f)


def _digits(x):
    return re.findall(r'\d+', x)


def similar(a, b):
    return _digits(a) == _digits(b) and difflib.SequenceMatcher(None, a, b).ratio() >= 0.8


def norm(s):
    return re.sub(r'\s+', ' ', s.replace('\r\n', '\n')).strip().lower()


def best(c):
    return c.most_common(1)[0][0]


class Sources:
    """Official English/German pairs from the original game files."""

    def __init__(self, exdir):
        self.src = {}
        self.gm = {'FO3': {}, 'FNV': {}}
        self.ctx = {'FO3': {}, 'FNV': {}}
        self.anyd = {'FO3': {}, 'FNV': {}}
        self.nd = {'FO3': {}, 'FNV': {}}
        for game in ('FO3', 'FNV'):
            for enp in sorted(glob.glob(os.path.join(exdir, 'en', f'{game}_*.pkl'))):
                dep = os.path.join(exdir, 'de', os.path.basename(enp))
                D = _load(dep)['entries']
                E = _load(enp)['entries']
                dk = {(e[1], e[2], e[0], e[5], e[6]): e[7] for e in D}
                dg = {e[4]: e[7] for e in D if e[0] == 'GMST'}
                for t, o, oid, fid, edid, s, i, txt in E:
                    if t == 'GMST':
                        if edid in dg:
                            self.gm[game][edid] = (txt, dg[edid])
                        continue
                    k = (o, oid, t, s, i)
                    if k not in dk:
                        continue
                    de = dk[k]
                    self.src[k] = (txt, de, game)
                    self.ctx[game].setdefault((t, s, txt), collections.Counter())[de] += 1
                    self.anyd[game].setdefault(txt, collections.Counter())[de] += 1
                    self.nd[game].setdefault(norm(txt), collections.Counter())[de] += 1

    def lookup(self, t, s, txt):
        for g in ('FNV', 'FO3'):
            if (t, s, txt) in self.ctx[g]:
                return best(self.ctx[g][(t, s, txt)]), 'dict_' + g
            if txt in self.anyd[g]:
                return best(self.anyd[g][txt]), 'dict_' + g
        n = norm(txt)
        for g in ('FNV', 'FO3'):
            if n in self.nd[g]:
                return best(self.nd[g][n]), 'norm_' + g
        return None, None


def build(exdir):
    """Returns (results, new): results[plugin] = {masters, res: [(entry, german|None, method)]},
    new = {english text: {'refs': [...], 'old_en': ..., 'old_de': ...}} for strings needing a translation."""
    S = Sources(exdir)
    results, new, ref = {}, collections.OrderedDict(), {}
    for p in sorted(glob.glob(os.path.join(exdir, 'ttw', '*.pkl'))):
        r = _load(p)
        res = []
        for e in r['entries']:
            t, o, oid, fid, edid, s, i, txt = e
            de = m = None
            if t == 'GMST':
                for g in ('FNV', 'FO3'):
                    v = S.gm[g].get(edid)
                    if v and v[0] == txt:
                        de, m = v[1], 'gmst_' + g
                        break
                if not de:
                    de, m = S.lookup(t, s, txt)
                if not de:
                    for g in ('FNV', 'FO3'):
                        if edid in S.gm[g]:
                            ref[txt] = S.gm[g][edid]
                            if similar(S.gm[g][edid][0], txt):
                                de, m = S.gm[g][edid][1], 'gmst_changed_' + g
                            break
            else:
                k = (o, oid, t, s, i)
                if k in S.src and S.src[k][0] == txt:
                    de, m = S.src[k][1], 'record_' + S.src[k][2]
                else:
                    de, m = S.lookup(t, s, txt)
                    if not de and k in S.src:
                        ref[txt] = S.src[k][:2]
                        if similar(S.src[k][0], txt):
                            de, m = S.src[k][1], 'changed_' + S.src[k][2]
            if not de:
                m = 'new'
                if re.search('[A-Za-z]', txt):
                    new.setdefault(txt, {'refs': []})['refs'].append((r['name'], t, s, edid))
            res.append((e, de, m))
        results[r['name']] = dict(masters=r['masters'], res=res)
    for txt, v in new.items():
        rf = ref.get(txt)
        v['old_en'], v['old_de'] = (rf[0], rf[1]) if rf else (None, None)
    return results, new
