"""Ikon aplikasi (kotak biru + huruf P), digambar dengan kode: tanpa gambar generatif, tanpa pustaka gambar.

    app\\.venv\\Scripts\\python -I app\\tools\\make_icon.py <keluaran.ico>
"""

from __future__ import annotations

import math
import struct
import sys
import zlib
from pathlib import Path

BLUE = (0x0F, 0x62, 0xAD)


def _inside_bg(x: float, y: float) -> bool:
    r = 4.0
    cx = min(max(x, r), 32 - r)
    cy = min(max(y, r), 32 - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r and 0 <= x <= 32 and 0 <= y <= 32


def _inside_p(x: float, y: float) -> bool:
    outer = (10 <= x <= 18.5 and 7 <= y <= 20) or (x >= 18.5 and math.hypot(x - 18.5, y - 13.5) <= 6.5)
    outer = outer or (10 <= x <= 14 and 7 <= y <= 25)
    hole = (14 <= x <= 18.5 and 11 <= y <= 16) or (x >= 18.5 and math.hypot(x - 18.5, y - 13.5) <= 2.5)
    return outer and not hole


def render(size: int, ss: int = 4) -> bytes:
    rows = []
    for py in range(size):
        row = bytearray([0])
        for px in range(size):
            bg = fg = 0
            for sy in range(ss):
                for sx in range(ss):
                    x = (px + (sx + 0.5) / ss) * 32 / size
                    y = (py + (sy + 0.5) / ss) * 32 / size
                    if _inside_bg(x, y):
                        bg += 1
                        if _inside_p(x, y):
                            fg += 1
            n = ss * ss
            a = bg / n
            t = fg / bg if bg else 0
            col = [round(c * (1 - t) + 255 * t) for c in BLUE]
            row += bytes(col + [round(255 * a)])
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def main(out: Path) -> None:
    sizes = [16, 24, 32, 48, 64, 128, 256]
    pngs = [render(s) for s in sizes]
    head = struct.pack("<HHH", 0, 1, len(sizes))
    offset = 6 + 16 * len(sizes)
    entries = b""
    for s, png in zip(sizes, pngs):
        entries += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(png), offset)
        offset += len(png)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(head + entries + b"".join(pngs))
    print(f"ikon {out} ({out.stat().st_size} byte)")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
