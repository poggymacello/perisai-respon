"""Susun video demo dari rekaman rekam.py: kartu, potongan, subtitle, naskah sulih suara, dan bahan YouTube.

    video\\.venv\\Scripts\\python -I video\\susun.py          (dari folder KartikaCyber2026)

Masukan : video\\rekaman\\rekaman_demo.webm + marks.json (dari rekam.py), alur.py (urutan dan narasi).
Keluaran (di video\\):
  PERISAI-RESPON_demo_tanpa_suara.mp4   H.264 1080p30, yuv420p, faststart, tanpa audio
  PERISAI-RESPON_demo.id.srt            subtitle Bahasa Indonesia, sinkron dengan potongan
  PERISAI-RESPON_demo_subtitle.mp4      versi dengan subtitle tertanam
  NASKAH_SULIH_SUARA.md                 naskah narasi per waktu, untuk direkam satu kali jalan
  YOUTUBE.md                            judul, deskripsi, chapter, pengaturan
  thumbnail_youtube_1280x720.png        thumbnail YouTube
ffmpeg diambil dari paket imageio-ffmpeg di video\\.venv (tanpa hak admin).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import alur  # noqa: E402

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
REK = HERE / "rekaman"
KERJA = HERE / "_kerja"
W, H, FPS = 1920, 1080, alur.FPS

OUT_SILENT = HERE / "PERISAI-RESPON_demo_tanpa_suara.mp4"
OUT_SUB = HERE / "PERISAI-RESPON_demo_subtitle.mp4"
OUT_SRT = HERE / "PERISAI-RESPON_demo.id.srt"
OUT_NASKAH = HERE / "NASKAH_SULIH_SUARA.md"
OUT_YT = HERE / "YOUTUBE.md"
OUT_THUMB = HERE / "thumbnail_youtube_1280x720.png"

FONTS = Path("C:/Windows/Fonts")
F_REG, F_SB, F_B, F_MONO = FONTS / "segoeui.ttf", FONTS / "seguisb.ttf", FONTS / "segoeuib.ttf", FONTS / "CascadiaMono.ttf"
BG, TXT, TXT2, MUTED, ACC = "#ffffff", "#1b1f24", "#444c56", "#6a737d", "#0f62ad"
X0 = 160                       # margin kiri kartu
MAXW = W - 2 * X0
VIDEO_H264 = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
              "-profile:v", "high", "-level", "4.1", "-r", str(FPS), "-video_track_timescale", "15360"]


def ff(*args: str, cwd: Path | None = None) -> str:
    p = subprocess.run([FFMPEG, "-hide_banner", "-y", *args], capture_output=True, text=True, cwd=cwd,
                       encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise SystemExit(f"ffmpeg gagal: {' '.join(args)}\n{p.stderr[-3000:]}")
    return p.stderr


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def wrap(draw: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont, maxw: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = f"{cur} {w}".strip()
        if draw.textlength(t, font=f) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def text_block(draw, xy, text, f, fill, maxw=MAXW, gap=1.25) -> int:
    x, y = xy
    for line in wrap(draw, text, f, maxw):
        draw.text((x, y), line, font=f, fill=fill)
        y += int(f.size * gap)
    return y


# ------------------------------------------------------------------------------------------------ kartu
def kartu_png(k: alur.Kartu, path: Path) -> None:
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    t = k.teks
    if k.jenis == "judul":
        d.text((X0, 330), t["judul"], font=font(F_B, 124), fill=TXT)
        text_block(d, (X0, 510), t["sub"], font(F_REG, 56), TXT2)
    elif k.jenis == "bagian":
        f = font(F_SB, 68)
        lines = wrap(d, t["kalimat"], f, MAXW)
        y = 430 - len(lines) * 44
        for line in lines:
            d.text((X0, y), line, font=f, fill=TXT)
            y += 88
    elif k.jenis == "bukti":
        d.text((X0, 170), t["judul"], font=font(F_SB, 52), fill=TXT2)
        d.text((X0, 260), t["angka"], font=font(F_B, 150), fill=ACC)
        y = text_block(d, (X0, 470), t["sub"], font(F_REG, 48), TXT)
        if t.get("catatan"):
            text_block(d, (X0, y + 24), t["catatan"], font(F_REG, 40), TXT2)
        if t.get("sumber"):
            d.text((X0, 820), t["sumber"], font=font(F_REG, 30), fill=MUTED)
    elif k.jenis == "batasan":
        d.text((X0, 130), t["judul"], font=font(F_B, 72), fill=TXT)
        y = 270
        for b in t["butir"]:
            d.text((X0, y), "-", font=font(F_REG, 44), fill=ACC)
            y = text_block(d, (X0 + 44, y), b, font(F_REG, 44), TXT, maxw=MAXW - 44) + 26
    elif k.jenis == "penutup":
        d.text((X0, 220), t["judul"], font=font(F_B, 104), fill=TXT)
        d.text((X0, 400), t["url"], font=font(F_MONO, 60), fill=ACC)
        text_block(d, (X0, 520), t["ajak"], font(F_SB, 52), TXT)
        text_block(d, (X0, 620), t["kecil"], font(F_REG, 38), TXT2)
    else:
        raise ValueError(k.jenis)
    im.save(path)


def label_png(text: str, path: Path) -> None:
    """Label kecil di pojok kanan atas (mis. waktu tunggu LLM yang dipotong)."""
    f = font(F_SB, 30)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    tw = int(tmp.textlength(text, font=f))
    im = Image.new("RGBA", (tw + 40, 58), (31, 38, 48, 225))
    ImageDraw.Draw(im).text((20, 9), text, font=f, fill="#ffffff")
    im.save(path)


# ------------------------------------------------------------------------------------------------ waktu
def sinkron(webm: Path, marks: dict):
    """Petakan waktu penanda (jam dinding sejak halaman dibuat) ke waktu video lewat dua kedipan hitam."""
    log = ff("-i", str(webm), "-vf", "blackdetect=d=0.4:pic_th=0.97:pix_th=0.08", "-an", "-f", "null", "-")
    starts = [float(m) for m in re.findall(r"black_start:([\d.]+)", log)]
    if len(starts) < 2:
        raise SystemExit(f"kedipan sinkron tidak ditemukan ({starts})")
    v0, v1 = starts[0], starts[-1]
    t0, t1 = marks["sinkron"][0], marks["sinkron"][-1]
    a = (v1 - v0) / (t1 - t0)
    print(f"sinkron: video {v0:.3f}/{v1:.3f} dtk, penanda {t0:.3f}/{t1:.3f} dtk, skala {a:.5f}")
    return lambda t: v0 + (t - t0) * a


def zoom_crop(rect, pad=36, minw=1000) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = rect
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    w = max(x1 - x0, (y1 - y0) * 16 / 9, minw)
    w = min(w, W)
    h = w * 9 / 16
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    x = min(max(0, cx - w / 2), W - w)
    y = min(max(0, cy - h / 2), H - h)
    w, h = int(w) // 2 * 2, int(h) // 2 * 2
    return w, h, int(x), int(y)


# ------------------------------------------------------------------------------------------------ subtitle
def pecah(teks: str, maxc: int = 50) -> str:
    """Bagi menjadi baris seimbang (maks. +-50 karakter), supaya tidak ada satu kata menggantung di baris kedua."""
    n = -(-len(teks) // maxc)
    width = max(20, -(-len(teks) // n) + 6)
    lines = textwrap.wrap(teks, width=width, break_long_words=False)
    while len(lines) > n and width < len(teks):
        width += 2
        lines = textwrap.wrap(teks, width=width, break_long_words=False)
    return "\n".join(lines)


def ts_srt(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def ts_ass(t: float) -> str:
    cs = int(round(t * 100))
    return f"{cs // 360000:d}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def ts_mmss(t: float) -> str:
    s = int(t)
    return f"{s // 60:02d}:{s % 60:02d}"


ASS_HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Segoe UI Semibold,46,&H00FFFFFF,&H00FFFFFF,&H40101010,&H00000000,0,0,0,0,100,100,0,0,3,10,0,2,160,160,46,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


# ------------------------------------------------------------------------------------------------ utama
def main() -> int:
    marks = json.loads((REK / "marks.json").read_text(encoding="utf-8"))
    webm = REK / marks["video"]
    beats = {m["id"]: m for m in marks["potongan"]}
    to_v = sinkron(webm, marks)
    shutil.rmtree(KERJA, ignore_errors=True)
    KERJA.mkdir(parents=True)

    clips, rows, cues = [], [], []   # rows: (seg, mulai, durasi)
    t = 0.0
    tunggu = None  # lama rekaman yang dibuang antara klik "Buat draf AI" dan draf tampil
    if "c_draf_mulai" in beats and "c_draf_hasil" in beats and marks.get("llm"):
        tunggu = to_v(beats["c_draf_hasil"]["mulai"]) - to_v(beats["c_draf_mulai"]["akhir"])
    for i, seg in enumerate(alur.URUTAN):
        need = max(seg.min_detik, alur.butuh(seg.narasi))
        out = KERJA / f"{i:02d}_{seg.id}.mp4"
        if isinstance(seg, alur.Kartu):
            png = KERJA / f"{seg.id}.png"
            kartu_png(seg, png)
            n = round(need * FPS)
            ff("-loop", "1", "-framerate", str(FPS), "-i", str(png), "-frames:v", str(n), "-tune", "stillimage",
               *VIDEO_H264, str(out))
        else:
            b = beats[seg.id]
            s, e = to_v(b["mulai"]), to_v(b["akhir"])
            foot = e - s
            dur = max(foot, need)
            n = round(dur * FPS)
            vf = []
            if seg.zoom and b.get("zoom"):
                cw, ch, cx, cy = zoom_crop(b["zoom"])
                vf.append(f"crop={cw}:{ch}:{cx}:{cy},scale={W}:{H}:flags=lanczos")
            vf += [f"fps={FPS}", f"tpad=stop_mode=clone:stop_duration={max(0.0, dur - foot) + 1:.3f}", "format=yuv420p"]
            args = ["-ss", f"{s:.3f}", "-i", str(webm)]
            if seg.id == "c_draf_hasil" and tunggu:
                lab = KERJA / "label_tunggu.png"
                label_png(f"Waktu tunggu LLM ±{round(tunggu)} dtk dipotong", lab)
                args += ["-i", str(lab)]
                fc = f"[0:v]{','.join(vf)}[v];[v][1:v]overlay=x=W-w-40:y=40:enable='lt(t,4.5)'[o]"
                ff(*args, "-filter_complex", fc, "-map", "[o]", "-frames:v", str(n), "-an", *VIDEO_H264, str(out))
            else:
                ff(*args, "-vf", ",".join(vf), "-frames:v", str(n), "-an", *VIDEO_H264, str(out))
        dur = n / FPS
        rows.append((seg, t, dur))
        c = t + alur.AWAL
        for line in seg.narasi:
            dl = alur.durasi_baris(line)
            cues.append((c, c + dl, line, seg.id))
            c += dl + alur.JEDA
        clips.append(out)
        print(f"{i:02d} {seg.id:18s} {ts_mmss(t)}  {dur:5.1f} dtk", flush=True)
        t += dur
    total = t

    # gabung (semua klip berparameter sama, jadi cukup -c copy)
    lst = KERJA / "daftar.txt"
    lst.write_text("".join(f"file '{c.name}'\n" for c in clips), encoding="utf-8")
    ff("-f", "concat", "-safe", "0", "-i", lst.name, "-c", "copy", "-movflags", "+faststart", str(OUT_SILENT), cwd=KERJA)

    # subtitle
    srt = []
    for k, (a, b, line, _) in enumerate(cues, 1):
        srt.append(f"{k}\n{ts_srt(a)} --> {ts_srt(b)}\n{pecah(line)}\n")
    OUT_SRT.write_text("\n".join(srt), encoding="utf-8")
    ass = ASS_HEAD + "".join(f"Dialogue: 0,{ts_ass(a)},{ts_ass(b)},Default,,0,0,0,,{pecah(line).replace(chr(10), chr(92) + 'N')}\n"
                             for a, b, line, _ in cues)
    (KERJA / "sub.ass").write_text(ass, encoding="utf-8")
    ff("-i", str(OUT_SILENT), "-vf", "ass=sub.ass:fontsdir=fonts", "-an", *VIDEO_H264, "-movflags", "+faststart",
       str(OUT_SUB), cwd=_fonts_ready())

    # bab (chapter) dan dokumen
    start_of = {seg.id: st for seg, st, _ in rows}
    bab = [(start_of[sid], judul) for judul, sid in alur.BAB]
    for (a, _), (b, j) in zip(bab, bab[1:] + [(total, "")]):
        assert b - a >= 10, f"chapter terlalu pendek sebelum {j}"
    tulis_naskah(rows, cues, bab, total)
    tulis_youtube(bab, total)
    thumbnail()
    print(f"\ntotal {ts_mmss(total)} ({total:.1f} dtk), {len(cues)} baris subtitle")
    return 0


def _fonts_ready() -> Path:
    """libass di build ffmpeg ini butuh folder font eksplisit; salin dua font Segoe UI ke _kerja/fonts."""
    fd = KERJA / "fonts"
    fd.mkdir(exist_ok=True)
    for f in (F_REG, F_SB):
        shutil.copy(f, fd / f.name)
    return KERJA


# ------------------------------------------------------------------------------------------------ dokumen
def tulis_naskah(rows, cues, bab, total) -> None:
    per = {}
    for a, b, line, sid in cues:
        per.setdefault(sid, []).append((a, line))
    layar = {
        "k_judul": "Kartu judul", "k_penutup": "Kartu penutup: URL repo, ajakan unduh", "k_batasan": "Kartu batasan",
    }
    out = [
        "# NASKAH SULIH SUARA: video demo PERISAI-RESPON",
        "",
        f"Durasi video tanpa suara: **{ts_mmss(total)}** (`PERISAI-RESPON_demo_tanpa_suara.mp4`). "
        "Naskah ini dibuat dari `alur.py`, sama dengan subtitle `PERISAI-RESPON_demo.id.srt`. "
        "Kalau narasi diubah, ubah `alur.py` lalu jalankan ulang `susun.py` supaya video, subtitle, dan naskah tetap sinkron.",
        "",
        "## Cara merekam (satu kali jalan)",
        "1. Pakai mikrofon headset atau USB di ruang yang tenang. Matikan notifikasi.",
        "2. Putar `PERISAI-RESPON_demo_subtitle.mp4` tanpa suara di layar (subtitle jadi aba-aba). "
        "Di Audacity, tekan Rekam tepat saat video mulai diputar. Bacalah tiap baris saat subtitlenya muncul. "
        "Boleh memakai kata-kata sendiri asal isinya dan angkanya sama.",
        "3. Kalau salah ucap, berhenti sebentar lalu ulangi kalimatnya. Potong bagian yang salah nanti tanpa menggeser waktu "
        "(pakai Edit > Remove Special > Split Delete atau isi dengan hening, bukan Delete biasa).",
        "4. Audacity: pilih semua (Ctrl+A), Effect > Volume and Compression > **Loudness Normalization**, "
        "pilih *perceived loudness* **-16 LUFS**, centang *treat mono as dual-mono*. "
        "Puncak sebaiknya di bawah -1 dBTP (Effect > Limiter, limit to -1 dB bila perlu).",
        "5. Pastikan panjang rekaman sama atau sedikit lebih pendek dari video. File > Export Audio > WAV (16-bit PCM), "
        "simpan sebagai `video\\narasi.wav`.",
        "6. Gabungkan suara ke video (dari folder `KartikaCyber2026`):",
        "",
        "```powershell",
        "$ff = (video\\.venv\\Scripts\\python -c \"import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())\")",
        "& $ff -i video\\PERISAI-RESPON_demo_tanpa_suara.mp4 -i video\\narasi.wav -map 0:v -map 1:a -c:v copy "
        "-c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart video\\PERISAI-RESPON_demo_final.mp4",
        "```",
        "",
        "   Berkas yang diunggah ke YouTube: **`video\\PERISAI-RESPON_demo_final.mp4`**, ditambah subtitle "
        "`PERISAI-RESPON_demo.id.srt` (YouTube Studio > Subtitles > Bahasa Indonesia > Upload file > With timing).",
        "7. Tonton hasilnya sekali penuh: suara sinkron dengan layar, tidak ada bagian yang terpotong.",
        "",
        "Tanpa musik, tanpa efek suara. Suara harus suara asli anggota tim (bukan TTS).",
        "",
        "## Chapter",
        "",
    ]
    out += [f"- {ts_mmss(a)} {j}" for a, j in bab]
    out += ["", "## Naskah per waktu", "", "| Waktu | Di layar | Yang diucapkan |", "|---|---|---|"]
    for seg, st, dur in rows:
        if isinstance(seg, alur.Kartu):
            t = seg.teks
            ls = layar.get(seg.id) or (f"Kartu: {t.get('kalimat') or t.get('judul')}" + (f" ({t['angka']})" if t.get("angka") else ""))
        else:
            ls = LAYAR.get(seg.id, seg.id)
        lines = per.get(seg.id, [])
        say = " ".join(f"`{ts_mmss(a)}` {line}" for a, line in lines) if lines else "(diam)"
        out.append(f"| {ts_mmss(st)}-{ts_mmss(st + dur)} | {ls} | {say} |")
    out += ["", "Angka di naskah hanya dari buku klaim (mega prompt 2 Nov, bagian C). Jangan menambah angka lain saat merekam.", ""]
    OUT_NASKAH.write_text("\n".join(out), encoding="utf-8")


LAYAR = {
    "c_dingin": "Kasus K-0004: field CommandLine berisi instruksi, ditandai firewall (diperbesar)",
    "a_mulai": "Aplikasi baru dibuka, antrean kosong",
    "a_pill": "Penanda Offline 127.0.0.1 di kanan atas",
    "a_jaringan": "Status sistem, kartu Jaringan",
    "a_model": "Status sistem, kartu Model lokal (hash cocok)",
    "a_mode": "Status sistem, kartu Mode analisis",
    "b_muat": "Klik Muat data contoh",
    "b_antrean": "Ringkasan antrean dan tabel kasus",
    "b_filter_injeksi": "Filter Injeksi terdeteksi",
    "c_banner": "Buka K-0004 (WS-KEU02), banner merah",
    "c_inert": "Teks CommandLine ditampilkan sebagai teks biasa",
    "c_keputusan": "Kartu Keputusan dan alasan policy",
    "c_draf_mulai": "Klik Buat draf AI, bilah proses",
    "c_draf_hasil": "Draf AI berlabel, label waktu tunggu dipotong (diperbesar)",
    "d_usulan": "Uji usulan: isolasi DC01, detektor pola dimatikan",
    "d_hasil": "Hasil BLOCK dan alasannya (diperbesar)",
    "e_kasus": "Buka K-0002 (WS-OPS07), menunggu persetujuan",
    "e_setujui": "Setujui aksi, isi nama dan catatan",
    "e_tercatat": "Riwayat: disetujui analis, nomor entri audit",
    "f_audit": "Jejak audit berantai SHA-256",
    "f_verifikasi": "Verifikasi integritas: rantai utuh",
    "f_ubah": "Uji deteksi perubahan: salinan gagal, asli utuh (diperbesar)",
    "g_laporan": "Laporan CSIRT, tombol unduh dan cetak",
    "g_gulir": "Gulir laporan ke bagian tindakan analis",
    "h_ot": "Jalur OT: grafik amplop normal",
    "h_hmi": "Catatan HMI (teks bebas)",
    "h_keputusan": "Keputusan OT: putus PLC-P1 ditolak (diperbesar)",
    "i_kinerja": "Status sistem: Uji kinerja di perangkat ini",
    "i_lisensi": "Tabel lisensi dan asal-usul",
    "j_impor": "Impor log: perintah wevtutil dan .evtx",
    "j_hasil": "Impor contoh_wevtutil.xml, hasil impor",
}


def tulis_youtube(bab, total) -> None:
    judul = "PERISAI-RESPON: triase insiden offline yang tidak bisa disetir isi log"
    assert len(judul) <= 70, len(judul)
    chap = "\n".join(f"{ts_mmss(a)} {j}" for a, j in bab)
    desk = f"""PERISAI-RESPON adalah aplikasi desktop untuk memilah insiden dari log Windows secara offline di laptop. Aturan dan policy engine yang memutuskan, LLM lokal hanya menulis draf berlabel, dan setiap aksi berisiko menunggu persetujuan analis.

Unduh dan coba: [ISI: URL repo]
Slide penjelasan: [ISI: URL slide]

Chapter:
{chap}

Data uji: OTRF Security-Datasets (log Windows) dan HAI 21.03 (CC BY-SA 4.0, telemetri proses). Data di video ini sintetis, dengan host fiktif *.batalyon.lab.
Model: Qwen2.5-1.5B-Instruct (Apache-2.0), berjalan lokal di CPU. Llama tidak dipakai karena lisensinya melarang penggunaan militer.
Alat bantu AI dipakai saat pengembangan; rinciannya ada di bagian Deklarasi README repo.

#keamanansiber #incidentresponse #promptinjection"""
    md = f"""# YOUTUBE: bahan unggah video demo PERISAI-RESPON

Berkas video: `video\\PERISAI-RESPON_demo_final.mp4` (hasil gabung suara, lihat `NASKAH_SULIH_SUARA.md`). Durasi {ts_mmss(total)}.
Subtitle: `video\\PERISAI-RESPON_demo.id.srt` (Bahasa Indonesia). Thumbnail: `video\\thumbnail_youtube_1280x720.png`.

## Judul ({len(judul)} karakter)
```
{judul}
```

## Deskripsi
```
{desk}
```

Sebelum unggah: ganti `[ISI: URL repo]` dan `[ISI: URL slide]` (juga di kartu penutup video bila URL sudah pasti; jalankan ulang `susun.py` setelah mengubah `alur.py`).

## Pengaturan
| Pengaturan | Nilai |
|---|---|
| Visibilitas | **Publik** (form meminta bisa diakses publik; *Unlisted* hanya kalau panitia mengonfirmasi boleh) |
| Penonton | Tidak, video ini tidak dibuat untuk anak-anak |
| Kategori | Sains & Teknologi |
| Bahasa video | Bahasa Indonesia |
| Subtitle | Unggah `PERISAI-RESPON_demo.id.srt` (With timing), bahasa Indonesia |
| Thumbnail | `thumbnail_youtube_1280x720.png` |
| Komentar | boleh dimatikan |
| Konten sintetis/diubah | Tidak (rekaman layar aplikasi asli dan suara asli anggota tim) |

## Uji penerimaan
- Putar dari jendela penyamaran: durasi di bawah 10:00, subtitle muncul, chapter tampil di bilah putar.
- Tautan di deskripsi bisa dibuka tanpa login.
- Scrub per detik: tidak ada nama pengguna, path pribadi, notifikasi, atau tab lain di frame mana pun.
"""
    OUT_YT.write_text(md, encoding="utf-8")


def thumbnail() -> None:
    """1280x720, gaya sama dengan aset_kirim/thumbnail_1200x630.png: latar gelap polos, satu aksen hijau."""
    bg, fg, dim, ok = "#0f1720", "#e6edf3", "#8b98a5", "#3fb950"
    im = Image.new("RGB", (1280, 720), bg)
    d = ImageDraw.Draw(im)
    x = 116
    d.text((x, 118), "PERISAI-RESPON", font=font(F_B, 104), fill=fg)
    d.text((x, 270), "Triase insiden offline yang tidak bisa disetir isi log", font=font(F_REG, 40), fill=dim)
    d.text((x, 360), "16,5 % → 0 %", font=font(F_B, 112), fill=ok)
    d.text((x, 512), "keberhasilan injeksi lewat log, 176 unit uji (prareg)", font=font(F_REG, 34), fill=fg)
    d.text((x, 610), "Demo aplikasi desktop", font=font(F_REG, 28), fill=dim)
    im.save(OUT_THUMB, optimize=True)
    with Image.open(OUT_THUMB) as t:
        assert t.size == (1280, 720)
    assert OUT_THUMB.stat().st_size < 2 * 1024 * 1024


if __name__ == "__main__":
    sys.exit(main())
