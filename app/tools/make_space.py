"""Susun folder siap-unggah untuk Hugging Face Space (SDK Docker): app/dist/space/

    app\\.venv\\Scripts\\python -I app\\tools\\make_space.py

Isi folder = Dockerfile di akar + README.md berisi metadata Space + kode mesin (salinan prototype/perisai, tidak diubah)
+ aplikasi. Folder ini yang di-push manusia ke repo git Space (lihat app/DEPLOY.md). Skrip ini tidak mengunggah apa pun.
"""

from __future__ import annotations

import shutil
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parent
OUT = APP / "dist" / "space"

README = """---
title: PERISAI-RESPON demo
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Triase insiden offline; demo publik dengan data sintetis
---

# PERISAI-RESPON 1.1.0, demo publik

Demo ini hanya memuat log contoh SINTETIS (host fiktif *.batalyon.lab). Unggah log dimatikan: server publik tidak boleh
menerima log asli. Untuk memeriksa log sendiri secara offline, unduh aplikasi desktop Windows dari halaman rilis repo.

Tiap pengunjung mendapat sesi terpisah. Persetujuan analis hanya dicatat di jejak audit, tidak dieksekusi.
"""

DOCKERFILE = (APP / "Dockerfile").read_text(encoding="utf-8")
DOCKERFILE = (DOCKERFILE.replace("COPY app/requirements.txt", "COPY requirements.txt")
              .replace("COPY prototype/perisai ", "COPY prototype/perisai ")
              .replace("COPY app/perisai_app ", "COPY app/perisai_app ")
              .replace("COPY app/frontend ", "COPY app/frontend "))
DOCKERFILE = DOCKERFILE.replace("# Build dari AKAR repo (butuh prototype/perisai):\n#   docker build -f app/Dockerfile",
                                "# Folder Space: Dockerfile di akar.\n#   docker build")


def main() -> None:
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    ign = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(ROOT / "prototype" / "perisai", OUT / "prototype" / "perisai", ignore=ign)
    shutil.copytree(APP / "perisai_app", OUT / "app" / "perisai_app", ignore=ign)
    shutil.copytree(APP / "frontend", OUT / "app" / "frontend", ignore=ign)
    shutil.copy(APP / "requirements.txt", OUT / "requirements.txt")
    shutil.copy(ROOT / "LICENSE", OUT / "LICENSE")
    (OUT / "Dockerfile").write_text(DOCKERFILE.replace("-f app/Dockerfile ", ""), encoding="utf-8")
    (OUT / "README.md").write_text(README, encoding="utf-8")
    n = sum(1 for p in OUT.rglob("*") if p.is_file())
    print(f"{n} berkas -> {OUT}")


if __name__ == "__main__":
    main()
