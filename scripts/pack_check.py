"""Check texture/mesh packs (MO2 mods) for conflicts and mixed mesh/texture sources.

For every file the winning source is determined like the game does it with MO2:
loose files of a mod beat loose files of lower mods; BSAs with a .override file beat
loose files; other BSAs lose against loose files. For every mesh shipped by a pack, the
texture paths inside the NIF are resolved to their winning source. Reported:
  - files shipped by several packs (and who wins)
  - pack meshes whose textures come from another pack although the own pack ships them
  - textures referenced by pack meshes that exist nowhere
  - NIFs with a non-FNV header

Usage:
    python scripts/pack_check.py --mo2 C:/Modding/MO2 --profile Default --data "<Spiel>/Data" --packs "WRP" "TTW Texture Merge" ...
"""
import argparse
import collections
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bsa import BSA  # noqa: E402

TEX_RE = re.compile(rb'([\x20-\x7e]{3,200}?\.dds)', re.I)


def norm(p):
    p = p.replace('\\', '/').lower().lstrip('/')
    return p


def nif_textures(b):
    out = set()
    for m in TEX_RE.finditer(b):
        s = m.group(1).decode('latin1')
        # strings in NIFs are length prefixed; take the part after the last control-ish garbage
        s = re.split(r'[^\w\\/.\- ]', s)[-1].strip()
        if not s.lower().endswith('.dds'):
            continue
        s = norm(s)
        if not s.startswith('textures/'):
            s = 'textures/' + s
        out.add(s)
    return out


def nif_ok(b):
    nl = b.find(b'\n')
    if nl < 0 or not b.startswith(b'Gamebryo File Format'):
        return 'kein Gamebryo-Header'
    ver = struct.unpack_from('<I', b, nl + 1)[0]
    uv = struct.unpack_from('<I', b, nl + 6)[0]
    uv2 = struct.unpack_from('<I', b, nl + 14)[0] if uv >= 10 else None
    if (ver, uv, uv2) != (0x14020007, 11, 34):
        return f'Version {ver:#x} user={uv} user2={uv2}'
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mo2', required=True)
    ap.add_argument('--profile', default='Default')
    ap.add_argument('--data', required=True, help='Data-Ordner (für Spiel-BSAs)')
    ap.add_argument('--packs', nargs='+', required=True, help='MO2-Mod-Namen der zu prüfenden Packs')
    a = ap.parse_args()

    mods_dir = os.path.join(a.mo2, 'mods')
    modlist = [l.rstrip('\n')[1:] for l in open(os.path.join(a.mo2, 'profiles', a.profile, 'modlist.txt'), encoding='utf-8')
               if l.startswith('+')]  # highest priority first

    # loose files: first (highest) mod wins
    loose = {}
    by_mod = collections.defaultdict(set)
    for mod in modlist:
        d = os.path.join(mods_dir, mod)
        if not os.path.isdir(d):
            continue
        for r, _, fs in os.walk(d):
            for f in fs:
                rel = norm(os.path.relpath(os.path.join(r, f), d))
                if rel.startswith(('meshes/', 'textures/')):
                    by_mod[mod].add(rel)
                    loose.setdefault(rel, (mod, os.path.join(r, f)))

    # BSAs in the game Data folder (as deployed); .override BSAs beat loose files
    bsa_files = {}
    override = {}
    for n in sorted(os.listdir(a.data)):
        if not n.lower().endswith('.bsa'):
            continue
        try:
            b = BSA(os.path.join(a.data, n))
        except Exception:
            continue
        ov = os.path.exists(os.path.join(a.data, n[:-4] + '.override'))
        for p in b.files:
            if p.startswith(('meshes/', 'textures/')):
                if ov:
                    override.setdefault(p, (n, b))
                else:
                    bsa_files.setdefault(p, (n, b))

    def winner(p):
        if p in override:
            return 'BSA ' + override[p][0] + ' (.override)'
        if p in loose:
            return loose[p][0]
        if p in bsa_files:
            return 'BSA ' + bsa_files[p][0]
        return None

    def read(p):
        if p in override:
            return override[p][1].read(p)
        if p in loose:
            return open(loose[p][1], 'rb').read()
        if p in bsa_files:
            return bsa_files[p][1].read(p)
        return None

    # 1) overlaps between packs
    print('== 1) Dateien, die mehrere Packs liefern ==')
    owners = collections.defaultdict(list)
    for mod in a.packs:
        for p in by_mod.get(mod, ()):
            owners[p].append(mod)
    multi = {p: m for p, m in owners.items() if len(m) > 1}
    per = collections.Counter((tuple(m), p.split('/')[0]) for p, m in multi.items())
    for (m, kind), n in sorted(per.items()):
        print(f'  {n:5} {kind:8} in {" + ".join(m)}  -> gewinnt {m[0]}')
    if not multi:
        print('  keine')
    # pack files that are overridden by a .override BSA (pack loses although it ships the file)
    print('\n== 1b) Pack-Dateien, die gegen ein .override-Archiv verlieren ==')
    lost = collections.Counter()
    ex = collections.defaultdict(list)
    for mod in a.packs:
        for p in by_mod.get(mod, ()):
            if p in override:
                lost[(mod, override[p][0])] += 1
                ex[(mod, override[p][0])].append(p)
    for (mod, b), n in sorted(lost.items()):
        print(f'  {n:5} aus {mod} verlieren gegen {b}, z. B. {ex[(mod, b)][:3]}')
    if not lost:
        print('  keine')

    # 2+3) meshes of packs: textures resolved
    print('\n== 2) Pack-Meshes mit Texturen aus anderer Quelle (obwohl das eigene Pack sie liefert) ==')
    mixed, missing, badnif = [], [], []
    for mod in a.packs:
        for p in sorted(by_mod.get(mod, ())):
            if not p.endswith('.nif'):
                continue
            if winner(p) != mod:
                continue  # mesh of this pack is not used in game
            data = open(loose[p][1], 'rb').read()
            bad = nif_ok(data)
            if bad:
                badnif.append((mod, p, bad))
            for t in nif_textures(data):
                w = winner(t)
                if w is None:
                    missing.append((mod, p, t))
                elif t in by_mod.get(mod, ()) and w != mod:
                    mixed.append((mod, p, t, w))
    for mod, p, t, w in mixed[:60]:
        print(f'  {mod}: {p}\n      Textur {t} gewinnt aus {w}')
    print(f'  insgesamt: {len(mixed)}')
    print('\n== 3) Von Pack-Meshes benutzte Texturen, die es nirgends gibt ==')
    for mod, p, t in missing[:60]:
        print(f'  {mod}: {p}\n      fehlt: {t}')
    print(f'  insgesamt: {len(missing)}')
    print('\n== 3b) Pack-Meshes mit ungültigem/fremdem NIF-Header ==')
    for mod, p, bad in badnif[:60]:
        print(f'  {mod}: {p}  {bad}')
    print(f'  insgesamt: {len(badnif)}')

    print('\n== 4) Alles mit grenade/40mm im Pfad ==')
    allp = set(loose) | set(override) | set(bsa_files)
    for p in sorted(x for x in allp if re.search(r'grenade|40mm', x)):
        w = winner(p)
        if any(p in by_mod.get(m, ()) for m in a.packs) or 'override' in w:
            extra = ''
            if p.endswith('.nif'):
                d = read(p)
                extra = nif_ok(d) or 'NIF ok'
                ts = nif_textures(d)
                miss = [t for t in ts if winner(t) is None]
                extra += f', {len(ts)} Texturen' + (f', FEHLEN: {miss}' if miss else '')
            print(f'  {p:80} gewinnt: {w}  {extra}')


if __name__ == '__main__':
    main()
