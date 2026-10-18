"""Duration of WAV / OGG Vorbis data (bytes) - used to tell re-encoded German audio from English audio."""
import struct


def duration(b):
    if b[:4] == b'RIFF':
        i, fmt, dl = 12, None, 0
        while i < len(b) - 8:
            cid, cl = b[i:i + 4], struct.unpack('<I', b[i + 4:i + 8])[0]
            if cid == b'fmt ':
                fmt = struct.unpack('<HHIIHH', b[i + 8:i + 24])
            if cid == b'data':
                dl = cl
            i += 8 + cl + (cl & 1)
        return dl / fmt[3] if fmt and fmt[3] else None
    if b[:4] == b'OggS':
        # sample rate from the Vorbis identification header, length from the last page's granule position
        k = b.find(b'\x01vorbis')
        if k < 0:
            return None
        rate = struct.unpack('<I', b[k + 12:k + 16])[0]
        last = b.rfind(b'OggS')
        gran = struct.unpack('<q', b[last + 6:last + 14])[0]
        return gran / rate if rate else None
    if b[:3] == b'ID3' or b[:2] in (b'\xff\xfb', b'\xff\xf3', b'\xff\xf2'):
        return None  # mp3: not needed here
    return None
