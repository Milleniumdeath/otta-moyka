"""Pure-stdlib PWA icon generator (no Pillow). Draws an OTTA water-drop emblem.

Run:  python scripts/gen_pwa_icons.py
Outputs PNGs into core/static/pwa/.
"""
import math
import os
import struct
import zlib

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "core", "static", "pwa")

# Brand palette (from templates [data-theme=dark])
BG_TOP = (8, 18, 28)
BG_BOT = (4, 9, 14)
DROP_A = (0, 200, 255)   # --cyan
DROP_B = (84, 131, 179)  # --accent
WHITE = (255, 255, 255)


def _lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def _blend(dst, src, alpha):
    return tuple(int(round(dst[i] * (1 - alpha) + src[i] * alpha)) for i in range(3))


def _draw_pixel(S, x, y, emblem_scale):
    """Return RGB for the given pixel center using 2x2 supersampling."""
    acc = [0, 0, 0]
    for sx in (0.25, 0.75):
        for sy in (0.25, 0.75):
            px = (x + sx) / S
            py = (y + sy) / S
            acc_c = _sample(px, py, emblem_scale)
            for i in range(3):
                acc[i] += acc_c[i]
    return tuple(c // 4 for c in acc)


def _sample(px, py, scale):
    """px, py in [0,1]. Returns RGB."""
    # vertical gradient background
    color = _lerp(BG_TOP, BG_BOT, py)

    # subtle radial glow behind the drop
    gx, gy = 0.5, 0.46
    gd = math.hypot(px - gx, py - gy)
    glow = max(0.0, 1.0 - gd / 0.55)
    color = _blend(color, (16, 40, 58), 0.35 * glow * glow)

    # --- water drop, centred, sized by `scale` (1.0 = fills icon, <1 for maskable) ---
    cx = 0.5
    disk_cy = 0.40
    R = 0.215 * scale
    apex_y = disk_cy + 0.40 * scale

    in_drop = False
    # round top
    if math.hypot(px - cx, py - disk_cy) <= R:
        in_drop = True
    # tapering bottom triangle
    elif disk_cy <= py <= apex_y:
        half_w = R * (apex_y - py) / (apex_y - disk_cy)
        if abs(px - cx) <= half_w:
            in_drop = True

    if in_drop:
        # diagonal gradient fill cyan -> accent
        t = max(0.0, min(1.0, ((px - cx) / (2 * R) + (py - disk_cy) / (apex_y - disk_cy)) * 0.6 + 0.4))
        color = _lerp(DROP_A, DROP_B, t)
        # glossy highlight
        hl = math.hypot(px - (cx - 0.06 * scale), py - (disk_cy - 0.06 * scale))
        if hl <= 0.07 * scale:
            color = _blend(color, WHITE, 0.55 * (1 - hl / (0.07 * scale)))

    return color


def _write_png(path, S, emblem_scale):
    rows = []
    for y in range(S):
        row = bytearray()
        row.append(0)  # filter type 0
        for x in range(S):
            r, g, b = _draw_pixel(S, x, y, emblem_scale)
            row += bytes((r, g, b, 255))
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(typ, data):
        return (struct.pack(">I", len(data)) + typ + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xffffffff))

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", S, S, 8, 6, 0, 0, 0)
    idat = zlib.compress(raw, 9)
    with open(path, "wb") as f:
        f.write(sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b""))
    print("wrote", path, f"({S}x{S})")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    targets = [
        ("icon-192.png", 192, 1.0),
        ("icon-512.png", 512, 1.0),
        ("icon-512-maskable.png", 512, 0.66),
        ("apple-touch-icon.png", 180, 1.0),
        ("favicon.png", 64, 1.0),
    ]
    for name, size, scale in targets:
        _write_png(os.path.join(OUT_DIR, name), size, scale)


if __name__ == "__main__":
    main()
