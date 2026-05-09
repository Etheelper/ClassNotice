import struct
import os


def create_ico(filepath, size=48):
    w = size
    h = size
    bpp = 32

    with open(filepath, 'wb') as f:
        f.write(b'\x00\x00\x01\x00\x01\x00')

        f.write(struct.pack('B', w if w < 256 else 0))
        f.write(struct.pack('B', h if h < 256 else 0))
        f.write(b'\x00\x00\x00\x00\x00\x00')
        f.write(struct.pack('<H', bpp))

        bmp_header_size = 40
        pixel_data_size = w * h * 4
        and_mask_size = ((w + 31) // 32) * 4 * h
        image_size = bmp_header_size + pixel_data_size + and_mask_size
        f.write(struct.pack('<I', image_size))
        f.write(struct.pack('<I', 22))

        f.write(struct.pack('<I', bmp_header_size))
        f.write(struct.pack('<i', w))
        f.write(struct.pack('<i', h * 2))
        f.write(struct.pack('<H', 1))
        f.write(struct.pack('<H', bpp))
        f.write(struct.pack('<I', 0))
        f.write(struct.pack('<I', pixel_data_size + and_mask_size))
        f.write(struct.pack('<i', 0))
        f.write(struct.pack('<i', 0))
        f.write(struct.pack('<I', 0))
        f.write(struct.pack('<I', 0))

        cx, cy = w // 2, h // 2
        r = min(cx, cy) - 2

        for y in range(h):
            row = bytearray()
            for x in range(w):
                dx = x - cx
                dy = y - cy
                dist = (dx * dx + dy * dy) ** 0.5

                if dist <= r:
                    if dist <= r * 0.85:
                        row.extend(struct.pack('BBBB', 255, 144, 24, 255))
                    else:
                        t = (dist - r * 0.85) / (r * 0.15)
                        a = int(255 * (1 - t))
                        row.extend(struct.pack('BBBB', 255, 144, 24, a))
                else:
                    row.extend(b'\x00\x00\x00\x00')
            f.write(row)

        for _ in range(and_mask_size):
            f.write(b'\x00')


server_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server')
client_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'client')

for d in [server_dir, client_dir]:
    ico_path = os.path.join(d, 'icon.ico')
    create_ico(ico_path, 48)
    print("Generated: " + ico_path)
