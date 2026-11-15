"""Narasi suara sintetis (Edge TTS, id-ID-ArdiNeural) untuk video demo PERISAI-RESPON.

    video\\.venv\\Scripts\\python -I video\\suara.py          (dari folder KartikaCyber2026, sesudah susun.py)

Setiap baris subtitle di PERISAI-RESPON_demo.id.srt dibacakan oleh suara sintetis, diletakkan tepat di waktu
mulai barisnya, lalu digabung dengan PERISAI-RESPON_demo_subtitle.mp4 menjadi PERISAI-RESPON_demo_final.mp4.
Kalau suara lebih panjang dari ruang yang tersedia sampai baris berikutnya, suara dipercepat (maks 1,3x).
Teks narasi dikirim ke layanan suara Microsoft (Edge Read Aloud); isinya hanya naskah demo, tanpa data.
Narasi ini suara sintetis, dan hal itu dinyatakan di deskripsi YouTube dan bagian Deklarasi README.
"""
from __future__ import annotations

import asyncio
import hashlib
import re
import subprocess
import sys
import wave
from pathlib import Path

import edge_tts
import imageio_ffmpeg

HERE = Path(__file__).resolve().parent
SRT = HERE / "PERISAI-RESPON_demo.id.srt"
VIDEO_IN = HERE / "PERISAI-RESPON_demo_subtitle.mp4"
VIDEO_OUT = HERE / "PERISAI-RESPON_demo_final.mp4"
CACHE = HERE / "_suara"
VOICE = "id-ID-ArdiNeural"
RATE = "+0%"
SR = 24000
MAX_TEMPO = 1.3
FF = imageio_ffmpeg.get_ffmpeg_exe()


def ts(s: str) -> float:
    h, m, rest = s.split(":")
    sec, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000


def read_srt(p: Path) -> list[tuple[float, float, str]]:
    blocks = re.split(r"\r?\n\r?\n", p.read_text(encoding="utf-8").strip())
    cues = []
    for b in blocks:
        lines = b.splitlines()
        a, z = lines[1].split(" --> ")
        cues.append((ts(a.strip()), ts(z.strip()), " ".join(l.strip() for l in lines[2:])))
    return cues


def ff(*args: str) -> None:
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


async def tts(text: str, out: Path) -> None:
    await edge_tts.Communicate(text, VOICE, rate=RATE).save(str(out))


def wav_len(p: Path) -> float:
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


def video_len(p: Path) -> float:
    r = subprocess.run([FF, "-hide_banner", "-i", str(p)], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", r.stderr)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])


def main() -> int:
    CACHE.mkdir(exist_ok=True)
    cues = read_srt(SRT)
    total = video_len(VIDEO_IN)
    track = bytearray(int(total * SR) * 2)
    laporan = []
    for i, (a, z, text) in enumerate(cues):
        key = hashlib.sha256(f"{VOICE}|{RATE}|{text}".encode()).hexdigest()[:16]
        mp3, wav = CACHE / f"{key}.mp3", CACHE / f"{key}.wav"
        if not mp3.exists():
            asyncio.run(tts(text, mp3))
        ff("-i", str(mp3), "-ac", "1", "-ar", str(SR), "-sample_fmt", "s16", str(wav))
        dur = wav_len(wav)
        nxt = cues[i + 1][0] if i + 1 < len(cues) else total
        room = max(0.5, nxt - a - 0.08)
        tempo = 1.0
        if dur > room:
            tempo = min(MAX_TEMPO, dur / room)
            fast = CACHE / f"{key}_t{tempo:.3f}.wav"
            ff("-i", str(wav), "-filter:a", f"atempo={tempo:.4f}", "-ac", "1", "-ar", str(SR), "-sample_fmt", "s16", str(fast))
            wav, dur = fast, wav_len(fast)
        with wave.open(str(wav)) as w:
            pcm = w.readframes(w.getnframes())
        start = int(a * SR) * 2
        end = min(len(track), start + len(pcm))
        track[start:end] = pcm[: end - start]
        laporan.append((i + 1, a, dur, room, tempo, dur > room + 0.05))
    narasi = CACHE / "narasi.wav"
    with wave.open(str(narasi), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(track))
    ff("-i", str(VIDEO_IN), "-i", str(narasi), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
       "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
       "-movflags", "+faststart", "-shortest", str(VIDEO_OUT))
    dipercepat = [r for r in laporan if r[4] > 1.0]
    terpotong = [r for r in laporan if r[5]]
    print(f"{len(cues)} baris; dipercepat {len(dipercepat)} (maks {max([r[4] for r in laporan]):.2f}x); "
          f"masih melewati ruang {len(terpotong)}")
    for r in terpotong:
        print(f"  baris {r[0]} @ {r[1]:.1f}s: {r[2]:.2f}s > ruang {r[3]:.2f}s")
    print(f"video: {VIDEO_OUT.name} ({video_len(VIDEO_OUT):.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
