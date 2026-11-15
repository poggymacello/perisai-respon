"""Build Windows: PyInstaller onedir -> app/dist/PERISAI-RESPON-<APP_VERSION>-win64.zip

    app\\.venv\\Scripts\\python -I app\\tools\\build.py            # dengan llama_cpp (mode LLM bisa aktif bila model ada)
    set PERISAI_BUNDLE_LLM=0 && app\\.venv\\Scripts\\python -I app\\tools\\build.py   # aturan saja, lebih kecil

Langkah: cek hash mesin vs prototype/frozen -> manifes build -> ikon -> PyInstaller -> berkas pendamping -> zip.
Model GGUF (0,92 GB) TIDAK dibundel.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
PROTO = APP.parent / "prototype"
BUILD = APP / "build"
DIST = APP / "dist"
sys.path.insert(0, str(APP))
from perisai_app import APP_VERSION  # noqa: E402

NAME = f"PERISAI-RESPON-{APP_VERSION}-win64"
CORE = ["__init__.py", "audit.py", "cases.py", "detector.py", "firewall.py", "llm.py", "logs.py", "pipeline.py",
        "policy.py", "v11.py", "v12.py"]

README_TXT = """PERISAI-RESPON {ver} (Windows 10/11, 64-bit)
=============================================

Cara menjalankan
1. Ekstrak seluruh isi zip ke satu folder (jangan dijalankan dari dalam zip).
2. Klik dua kali PERISAI-RESPON.exe.
3. Bila muncul "Windows protected your PC" (SmartScreen): klik "More info" lalu "Run anyway".
   Berkas exe ini belum ditandatangani sertifikat penerbit.
4. Di layar Antrean kasus, klik "Muat data contoh", lalu buka kasus berlabel "Injeksi terdeteksi".

Yang perlu diketahui
- Aplikasi berjalan offline. Server lokal hanya mendengar di 127.0.0.1; tidak ada data yang dikirim keluar.
- Persetujuan analis hanya DICATAT di jejak audit. Aplikasi tidak menjalankan aksi apa pun ke sistem.
- Data sesi disimpan di %LOCALAPPDATA%\\PERISAI-RESPON.
- Mode LLM (opsional): salin qwen2.5-1.5b-instruct-q3_k_m.gguf ke folder "models" di samping exe ini,
  lalu buka ulang aplikasi. SHA-256 model dicek dulu; bila tidak cocok, aplikasi tetap di mode aturan.
  Tautan unduh dan hash ada di README repo (prototype/DATA.md).
- Bila jendela tidak muncul (WebView2 tidak ada): jalankan  PERISAI-RESPON.exe --browser
- Log aplikasi: %LOCALAPPDATA%\\PERISAI-RESPON\\log\\app.log

Lisensi: MIT (LICENSE.txt). Komponen pihak ketiga: THIRD_PARTY.txt.
"""

MODELS_TXT = """Taruh berkas model di folder ini untuk mengaktifkan mode LLM lokal (opsional):

  qwen2.5-1.5b-instruct-q3_k_m.gguf   (0,92 GB, Apache-2.0)
  SHA-256 58cb5c05ecef48e82961f1a2be6544145ea26136f69dddda4bbbd092f0e4b993

Sumber: Hugging Face Qwen/Qwen2.5-1.5B-Instruct-GGUF (lihat prototype/DATA.md di repo).
Tanpa model, aplikasi berjalan di mode aturan dengan fitur triase lengkap.
"""

THIRD_PARTY = """Komponen pihak ketiga yang dibundel di PERISAI-RESPON {ver}
- Python 3.11 (PSF License)
- FastAPI, Starlette, Pydantic, Uvicorn, h11, anyio, python-multipart (MIT / BSD-3-Clause)
- pywebview (BSD-3-Clause), pythonnet / clr-loader (MIT), bottle (MIT), proxy_tools (MIT)
- NumPy, pandas (BSD-3-Clause), python-dateutil (Apache-2.0/BSD), tzdata (Apache-2.0)
- llama-cpp-python, llama.cpp / ggml (MIT), diskcache (Apache-2.0), Jinja2, MarkupSafe (BSD-3-Clause)  [bila dibundel]
- Ikon Lucide 0.460.0 (ISC; bagian dari Feather: MIT), lisensi lengkap di _internal/frontend/vendor/lucide/LICENSE
- Kendali (MIT, Poggy Macello Gultom & Mohammad Ari Alexander Aziz): pola policy engine, pola injeksi, audit berantai
Tidak dibundel: model Qwen2.5-1.5B-Instruct (Apache-2.0), data OTRF (MIT), data HAI 21.03 (CC BY-SA 4.0).
"""


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def engine_manifest() -> None:
    expected = {}
    for f in ("CODE_EVAL.sha256", "CODE_V11_posthoc.sha256", "CODE_V12_posthoc.sha256"):
        for line in (PROTO / "frozen" / f).read_text(encoding="utf-8").splitlines():
            m = re.match(r"^([0-9a-f]{64}) \*perisai/(\S+\.py)$", line.strip())
            if m:
                expected[m.group(2)] = m.group(1)
    got = {f: sha(PROTO / "perisai" / f) for f in CORE}
    bad = [f for f in CORE if f in expected and expected[f] != got[f]]
    if bad:
        raise SystemExit(f"kode mesin tidak cocok dengan hash beku: {bad}")
    out = BUILD / "engine_meta" / "build_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(got, indent=1), encoding="utf-8")
    print(f"manifes mesin: {len(got)} berkas cocok dengan prototype/frozen")


def main() -> None:
    engine_manifest()
    subprocess.run([sys.executable, "-I", str(APP / "tools" / "make_icon.py"), str(BUILD / "perisai.ico")], check=True)
    shutil.rmtree(DIST / "PERISAI-RESPON", ignore_errors=True)
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--distpath", str(DIST),
                    "--workpath", str(BUILD / "pyi"), str(APP / "packaging" / "perisai.spec")], check=True, cwd=str(APP))
    out = DIST / NAME
    shutil.rmtree(out, ignore_errors=True)
    shutil.move(str(DIST / "PERISAI-RESPON"), str(out))
    (out / "BACA_DULU.txt").write_text(README_TXT.format(ver=APP_VERSION), encoding="utf-8")
    (out / "THIRD_PARTY.txt").write_text(THIRD_PARTY.format(ver=APP_VERSION), encoding="utf-8")
    shutil.copy(APP.parent / "LICENSE", out / "LICENSE.txt")
    (out / "models").mkdir(exist_ok=True)
    (out / "models" / "BACA.txt").write_text(MODELS_TXT, encoding="utf-8")
    z = DIST / f"{NAME}.zip"
    z.unlink(missing_ok=True)
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(out.rglob("*")):
            if p.is_file():
                zf.write(p, f"{NAME}/{p.relative_to(out).as_posix()}")
    size = z.stat().st_size
    total = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"zip: {z} ({size / 1e6:.1f} MB; terekstrak {total / 1e6:.1f} MB)")
    print(f"SHA-256 zip: {sha(z)}")
    (DIST / f"{NAME}.zip.sha256").write_text(f"{sha(z)}  {z.name}\n", encoding="utf-8")


if __name__ == "__main__":
    os.environ.setdefault("PERISAI_BUNDLE_LLM", "1")
    main()
