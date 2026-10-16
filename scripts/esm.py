"""Minimal reader/writer for Fallout 3 / Fallout New Vegas plugin files (.esm/.esp).

The format is the same for both games: a TES4 header record followed by nested
GRUPs. Records have a 24 byte header (type, data size, flags, FormID, vc info),
subrecords a 6 byte header (signature, uint16 size). Strings are stored inline
(no string tables) as null-terminated cp1252 text.
"""
import collections
import mmap
import struct
import zlib

COMPRESSED = 0x00040000


def _inflate(raw):
    # Some records in FalloutNV.esm have broken zlib checksums, so the stream is
    # inflated raw (skipping the 4 byte size + 2 byte zlib header) without checking.
    return zlib.decompressobj(-15).decompress(raw[6:])


def iter_records(path):
    """Yield (type, formid, flags, data) for every record, data decompressed."""
    with open(path, 'rb') as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

    def walk(pos, end):
        while pos < end:
            typ = mm[pos:pos + 4]
            size, = struct.unpack_from('<I', mm, pos + 4)
            if typ == b'GRUP':
                yield from walk(pos + 24, pos + size)
                pos += size
                continue
            flags, fid = struct.unpack_from('<II', mm, pos + 8)
            data = mm[pos + 24:pos + 24 + size]
            if flags & COMPRESSED:
                data = _inflate(data)
            yield typ.decode(), fid, flags, data
            pos += 24 + size

    yield from walk(0, len(mm))


def parse_subs(data):
    """Return a list of [signature(bytes), payload(bytes)]; handles XXXX big fields."""
    i, out, big = 0, [], None
    while i < len(data):
        sig = bytes(data[i:i + 4])
        l, = struct.unpack_from('<H', data, i + 4)
        i += 6
        if sig == b'XXXX':
            big, = struct.unpack_from('<I', data, i)
            i += l
            continue
        if big is not None:
            l, big = big, None
        out.append([sig, bytes(data[i:i + l])])
        i += l
    return out


def build_subs(subs):
    out = bytearray()
    for sig, b in subs:
        if len(b) > 0xFFFF:
            out += b'XXXX' + struct.pack('<HI', 4, len(b)) + sig + struct.pack('<H', 0)
        else:
            out += sig + struct.pack('<H', len(b))
        out += b
    return bytes(out)


def rewrite(src, dst, repl):
    """Copy src to dst, replacing subrecord payloads.

    repl: {raw FormID: {(signature str, occurrence index): new text bytes without null}}
    Unchanged records are copied byte for byte; GRUP sizes are patched as needed.
    Returns a Counter with the number of changed records and fields.
    """
    st = collections.Counter()
    with open(src, 'rb') as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    out = open(dst, 'wb')

    def walk(pos, end):
        while pos < end:
            typ = mm[pos:pos + 4]
            size, = struct.unpack_from('<I', mm, pos + 4)
            if typ == b'GRUP':
                hdr_at = out.tell()
                out.write(mm[pos:pos + 24])
                walk(pos + 24, pos + size)
                new_size = out.tell() - hdr_at
                if new_size != size:
                    cur = out.tell()
                    out.seek(hdr_at + 4)
                    out.write(struct.pack('<I', new_size))
                    out.seek(cur)
                pos += size
                continue
            flags, fid = struct.unpack_from('<II', mm, pos + 8)
            rec_end = pos + 24 + size
            r = repl.get(fid) if typ != b'TES4' else None
            if not r:
                out.write(mm[pos:rec_end])
                pos = rec_end
                continue
            raw = mm[pos + 24:rec_end]
            comp = bool(flags & COMPRESSED)
            subs = parse_subs(_inflate(raw) if comp else raw)
            occ = collections.Counter()
            changed = 0
            for s in subs:
                sig = s[0].decode('latin1')
                i = occ[sig]
                occ[sig] += 1
                nb = r.get((sig, i))
                if nb is None:
                    continue
                # Audio holotapes store a FormID (4 bytes) in NOTE:TNAM, not text.
                if typ == b'NOTE' and sig == 'TNAM' and len(s[1]) == 4:
                    continue
                if s[1] != nb + b'\0':
                    s[1] = nb + b'\0'
                    changed += 1
            if not changed:
                out.write(mm[pos:rec_end])
                pos = rec_end
                continue
            st['records'] += 1
            st['fields'] += changed
            nd = build_subs(subs)
            if comp:
                nd = struct.pack('<I', len(nd)) + zlib.compress(nd, 6)
            out.write(typ + struct.pack('<I', len(nd)) + mm[pos + 8:pos + 24] + nd)
            pos = rec_end

    walk(0, len(mm))
    out.close()
    mm.close()
    return st
