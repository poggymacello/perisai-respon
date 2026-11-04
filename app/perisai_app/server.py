"""Mode server (Docker / demo publik / pengembangan).

    PERISAI_MODE=demo python -m perisai_app.server          # 0.0.0.0:7860, data contoh saja, unggah ditolak
    python -m perisai_app.server --port 8765                 # mode desktop di 127.0.0.1 tanpa jendela (dev)

Mode desktop TIDAK pernah mendengar di alamat selain 127.0.0.1: server dengan log asli tidak boleh terbuka ke jaringan.
"""

from __future__ import annotations

import argparse
import os

import uvicorn

from .api import create_app
from .paths import app_mode


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", "7860")))
    args = ap.parse_args()
    mode = app_mode()
    host = "0.0.0.0" if mode == "demo" else "127.0.0.1"
    app = create_app(mode=mode, bind=host)
    app.state.port = args.port
    uvicorn.run(app, host=host, port=args.port, proxy_headers=mode == "demo", forwarded_allow_ips="*",
                access_log=False, log_level="info")


if __name__ == "__main__":
    main()
