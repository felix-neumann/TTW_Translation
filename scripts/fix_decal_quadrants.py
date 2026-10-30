"""Copy the top-left quadrant of a DXT1/DXT5 decal texture into the other three quadrants.

Decals whose impact data lacks the "NoSubtextures" flag are treated as a 2x2 atlas: the
game picks one quadrant at random per hit. Enhanced Blood Textures' impactbullet.dds only
has the wound in the top-left quadrant; the rest is transparent and hides the text
"You're looking in the wrong place", which can show up on hit actors. After this fix every
quadrant holds the same wound. Blocks are copied as-is (no recompression), on every mip level;
mips smaller than 8x8 are fixed by copying pixel indices inside the 4x4 block.

Usage:
    python scripts/fix_decal_quadrants.py <in.dds> <out.dds>
"""
import argparse
import struct


def fix(data):
    if data[:4] != b'DDS ':
        raise ValueError('not a DDS file')
    h, w = struct.unpack('<II', data[12:20])
    mips = max(1, struct.unpack('<I', data[28:32])[0])
    fourcc = data[84:88]
    if fourcc not in (b'DXT1', b'DXT5'):
        raise ValueError(f'unsupported format {fourcc!r}')
    bs = 8 if fourcc == b'DXT1' else 16
    out = bytearray(data)
    off = 128
    for lvl in range(mips):
        mw, mh = max(1, w >> lvl), max(1, h >> lvl)
        bw, bh = (mw + 3) // 4, (mh + 3) // 4
        if mw >= 8 and mh >= 8:
            qw, qh = bw // 2, bh // 2
            for by in range(bh):
                for bx in range(bw):
                    if bx < qw and by < qh:
                        continue
                    src = off + ((by % qh) * bw + (bx % qw)) * bs
                    dst = off + (by * bw + bx) * bs
                    out[dst:dst + bs] = data[src:src + bs]
        elif mw >= 2 and mh >= 2:
            fix_small_block(out, off, bs, mw // 2, mh // 2)
        off += bw * bh * bs
    return bytes(out)


def fix_small_block(out, off, bs, qw, qh):
    """Single 4x4 block, mip smaller than 8x8: pixel (x, y) takes the indices of (x % qw, y % qh)."""
    col = off + bs - 4  # 2-bit color indices (last 4 bytes of the block)
    ci = int.from_bytes(out[col:col + 4], 'little')
    new_ci = 0
    for y in range(4):
        for x in range(4):
            s = (y % qh) * 4 + (x % qw)
            new_ci |= ((ci >> (2 * s)) & 3) << (2 * (y * 4 + x))
    out[col:col + 4] = new_ci.to_bytes(4, 'little')
    if bs == 16:  # DXT5: 3-bit alpha indices in bytes 2..7
        ai = int.from_bytes(out[off + 2:off + 8], 'little')
        new_ai = 0
        for y in range(4):
            for x in range(4):
                s = (y % qh) * 4 + (x % qw)
                new_ai |= ((ai >> (3 * s)) & 7) << (3 * (y * 4 + x))
        out[off + 2:off + 8] = new_ai.to_bytes(6, 'little')


def main():
    ap = argparse.ArgumentParser(description='Oberes linkes Viertel einer Decal-Textur in alle Viertel kopieren')
    ap.add_argument('src')
    ap.add_argument('dst')
    a = ap.parse_args()
    with open(a.src, 'rb') as f:
        data = f.read()
    with open(a.dst, 'wb') as f:
        f.write(fix(data))
    print(f'{a.dst}: fertig')


if __name__ == '__main__':
    main()
