"""Entrypoint Vercel (Python serverless) untuk demo publik PERISAI-RESPON.

Sama seperti image Docker: PERISAI_MODE=demo, data contoh sintetis saja, unggah log ditolak, LLM mati.
Sesi pengunjung disimpan di /tmp instance dan bisa hilang saat instance berganti. Itu sesuai untuk demo.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ["PERISAI_MODE"] = "demo"
os.environ.setdefault("PERISAI_DATA_DIR", "/tmp/perisai-demo")
os.environ.setdefault("PERISAI_ENGINE_DIR", str(ROOT / "prototype"))
os.environ.setdefault("PERISAI_FRONTEND_DIR", str(ROOT / "app" / "frontend"))
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.path.insert(0, str(ROOT / "app"))

from perisai_app.api import create_app  # noqa: E402

app = create_app(mode="demo", bind="0.0.0.0")
