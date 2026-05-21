"""Generate a minimal 512×512 placeholder PNG icon — stdlib only, no Pillow needed."""
import struct, zlib, sys

def make_solid_png(path, w, h, color):
    r, g, b = color
    row = bytes([0]) + bytes([r, g, b] * w)  # filter byte + w pixels RGB
    raw = row * h
    def chunk(tag, data):
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', crc)
    png  = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(raw, 9))
    png += chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(png)

out = sys.argv[1] if len(sys.argv) > 1 else 'icon_placeholder.png'
make_solid_png(out, 512, 512, (15, 17, 23))   # couleur fond de l'app
print(f'Icône placeholder : {out}')
