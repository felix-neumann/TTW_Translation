"""Minimal reader/writer for Fallout 3 / New Vegas BSA archives (version 104 / 0x68)."""
import struct
import zlib

FLAG_DIRNAMES, FLAG_FILENAMES, FLAG_COMPRESSED, FLAG_EMBED_NAMES = 0x1, 0x2, 0x4, 0x100


class BSA:
    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            hdr = f.read(36)
            (magic, ver, off, self.flags, nfold, nfile,
             lfold, lfile, self.file_flags) = struct.unpack('<4sIIIIIIII', hdr)
            if magic != b'BSA\0' or ver != 0x68:
                raise ValueError(f'{path}: unsupported BSA (magic={magic!r}, version={ver:#x})')
            folders = [struct.unpack('<QII', f.read(16)) for _ in range(nfold)]
            recs = []
            for _, count, _ in folders:
                name = b''
                if self.flags & FLAG_DIRNAMES:
                    n = f.read(1)[0]
                    name = f.read(n)[:-1]
                for _ in range(count):
                    h, size, foff = struct.unpack('<QII', f.read(16))
                    recs.append((name, size, foff))
            names = f.read(lfile).split(b'\0')[:len(recs)] if self.flags & FLAG_FILENAMES else [b''] * len(recs)
        self.files = {}
        for (folder, size, foff), fname in zip(recs, names):
            path_ = (folder + b'/' + fname).decode('cp1252').lower().replace('\\', '/')
            compressed = bool(self.flags & FLAG_COMPRESSED) != bool(size & 0x40000000)
            self.files[path_] = (foff, size & 0x3FFFFFFF, compressed)

    def read(self, name):
        foff, size, compressed = self.files[name.lower().replace(chr(92), "/")]
        with open(self.path, 'rb') as f:
            f.seek(foff)
            data = f.read(size)
        if self.flags & FLAG_EMBED_NAMES:
            n = data[0]
            data = data[1 + n:]
        if compressed:
            data = zlib.decompress(data[4:])
        return data
