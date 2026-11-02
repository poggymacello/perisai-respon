"""Buat thumbnail (1200x630, <=500 KB) dan 5 screenshot untuk submission Kartika Cyber Hackathon 2026.

Screenshot 1-4 adalah render teks keluaran ASLI demo.py / triase.py (tidak diubah, hanya dipilih dan dipotong
baris panjangnya). Screenshot 5 adalah grafik hasil evaluasi yang sudah ada. Jalankan dari folder KartikaCyber2026:
    prototype\\.venv\\Scripts\\python -I aset_kirim\\buat_aset.py
"""
import shutil
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "aset_kirim"
DEMO = ROOT / "prototype" / "results" / "demo" / "demo_output.txt"
LAPORAN = ROOT / "prototype" / "results" / "contoh_laporan" / "laporan.md"
FIG = ROOT / "prototype" / "results" / "fig_endpoints.png"

MONO = ["Consolas", "DejaVu Sans Mono"]
SANS = ["Segoe UI", "Calibri", "DejaVu Sans"]
BG, FG, DIM, OK, BAD, ACC = "#0f1720", "#e6edf3", "#8b98a5", "#3fb950", "#f85149", "#58a6ff"


def section(lines, tag):
    """Baris-baris satu skenario demo, dari '[tag]' sampai pemisah '====' berikutnya."""
    start = next(i for i, l in enumerate(lines) if l.startswith(f"[{tag}]"))
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("====")), len(lines))
    return lines[start:end]


def colour(line):
    low = line.lower()
    if "draf ai (disaring)" in low:
        return OK
    if any(k in low for k in ("injeksi terdeteksi", "block", "utuh=false", "dibuang", "ditolak")):
        return BAD
    if any(k in low for k in ("utuh=true", "menunggu_persetujuan", "dieskalasi", "draf ai (disaring)")):
        return OK
    if line.startswith("[") or line.startswith("#"):
        return ACC
    return FG


def render(lines, title, path, width=150):
    wrapped = []
    for l in lines:
        parts = textwrap.wrap(l, width=width, subsequent_indent="      ") or [""]
        wrapped += [(p, colour(l)) for p in parts]
    h = 1.0 + 0.215 * len(wrapped)
    fig = plt.figure(figsize=(16, h), dpi=100)
    fig.patch.set_facecolor(BG)
    fig.text(0.012, 1 - 0.32 / h, title, color=DIM, family=SANS, fontsize=12, va="top")
    for i, (txt, c) in enumerate(wrapped):
        fig.text(0.012, 1 - (0.75 + 0.215 * i) / h, txt, color=c, family=MONO, fontsize=10.5, va="top")
    fig.savefig(path, facecolor=BG)
    plt.close(fig)


def thumbnail(path):
    fig = plt.figure(figsize=(12, 6.3), dpi=100)
    fig.patch.set_facecolor(BG)
    # Standar gambar pratinjau 1,91:1: teks di zona aman tengah, satu bukti, terbaca saat diperkecil ke lebar 300 px.
    fig.text(0.09, 0.74, "PERISAI-RESPON", color=FG, family=SANS, fontsize=64, weight="bold", va="center")
    fig.text(0.09, 0.58, "Triase insiden offline yang tidak bisa disetir isi log",
             color=DIM, family=SANS, fontsize=27, va="center")
    fig.text(0.09, 0.36, "16,5 % → 0 %", color=OK, family=SANS, fontsize=54, weight="bold", va="center")
    fig.text(0.09, 0.22, "keberhasilan injeksi lewat log, 176 unit uji", color=FG, family=SANS, fontsize=20, va="center")
    fig.text(0.09, 0.10, "Kategori Penangkalan", color=DIM, family=SANS, fontsize=16, va="center")
    fig.savefig(path, facecolor=BG)
    plt.close(fig)


def main():
    lines = DEMO.read_text(encoding="utf-8").splitlines()
    src = "keluaran asli demo.py (render teks; baris panjang dibungkus)"
    s3 = [l for l in section(lines, "3") if not l.lstrip().startswith("[E") or l.lstrip().startswith("[E1]")]
    render(s3, f"1/5 · Injeksi 'isolasi DC01' di field CommandLine tertangkap, kasus dieskalasi ke manusia · {src}",
           OUT / "screenshot_1_injeksi_dieskalasi.png")
    render(section(lines, "4") + [""] + section(lines, "5c"),
           f"2/5 · Detektor pola dibuat buta: policy tetap menolak isolasi DC01 dan pemutusan PLC · {src}",
           OUT / "screenshot_2_policy_menahan.png")
    s6 = section(lines, "6")
    render(s6[:5] + ["   ..."] + s6[-2:],
           f"3/5 · Audit berantai SHA-256: satu entri diubah langsung ketahuan · {src}",
           OUT / "screenshot_3_audit_hash_chain.png")
    rep = LAPORAN.read_text(encoding="utf-8").splitlines()
    render(rep[:26], "4/5 · Laporan CSIRT dari log Windows (wevtutil XML) · keluaran asli triase.py, laporan.md",
           OUT / "screenshot_4_laporan_csirt.png")
    shutil.copyfile(FIG, OUT / "screenshot_5_hasil_evaluasi.png")

    thumb = OUT / "thumbnail_1200x630.png"
    thumbnail(thumb)
    with Image.open(thumb) as im:
        assert im.size == (1200, 630), im.size
    assert thumb.stat().st_size <= 500 * 1024, thumb.stat().st_size
    for p in sorted(OUT.glob("*.png")):
        with Image.open(p) as im:
            print(f"{p.name}: {im.size[0]}x{im.size[1]}, {p.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
