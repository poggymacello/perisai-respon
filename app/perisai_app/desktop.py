"""Titik masuk aplikasi desktop: server lokal di 127.0.0.1 (port bebas) + jendela native (pywebview/WebView2).

    PERISAI-RESPON.exe                 jendela aplikasi
    PERISAI-RESPON.exe --browser       buka di browser bawaan (bila WebView2 bermasalah)
    PERISAI-RESPON.exe --headless      server saja (untuk uji otomatis); port ditulis ke instance.json
    PERISAI-RESPON.exe --data-dir D    folder data lain (bawaan %LOCALAPPDATA%\\PERISAI-RESPON)
"""

from __future__ import annotations

import argparse
import json
import logging
import logging.handlers
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

from . import APP_NAME, APP_VERSION

WEBVIEW2_GUID = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
IDLE_EXIT_S = 300  # mode browser: keluar bila tidak ada ping dari halaman selama 5 menit


def _msgbox(text: str) -> None:
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, text, APP_NAME, 0x40)
            return
        except Exception:
            pass
    print(text, file=sys.stderr)


def webview2_version() -> str | None:
    if os.name != "nt":
        return None
    import winreg
    keys = [(winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{WEBVIEW2_GUID}"),
            (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{WEBVIEW2_GUID}"),
            (winreg.HKEY_CURRENT_USER, rf"Software\Microsoft\EdgeUpdate\Clients\{WEBVIEW2_GUID}")]
    for hive, path in keys:
        try:
            with winreg.OpenKey(hive, path) as k:
                v = str(winreg.QueryValueEx(k, "pv")[0])
                if v and v != "0.0.0.0":
                    return v
        except OSError:
            continue
    return None


def _setup_logging(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    log = folder / "app.log"
    if sys.stdout is None or sys.stderr is None:  # build berjendela (tanpa konsol)
        fh = open(log, "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        sys.stdout = sys.stdout or fh
        sys.stderr = sys.stderr or fh
    h = logging.handlers.RotatingFileHandler(log, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers[:] = [h]
    root.setLevel(logging.INFO)
    return log


class _SingleInstance:
    def __init__(self, path: Path):
        self.path = path
        self.fh = None

    def acquire(self) -> bool:
        self.fh = open(self.path, "a+")  # noqa: SIM115
        try:
            if os.name == "nt":
                import msvcrt
                self.fh.seek(0)
                msvcrt.locking(self.fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            return False


class JsApi:
    """Dipanggil dari halaman lewat window.pywebview.api (hanya di jendela desktop)."""

    def __init__(self, base: str):
        self.base = base
        self._window = None  # garis bawah: pywebview tidak menelusuri atribut privat saat mengekspos API

    def simpan(self, path: str, nama: str) -> dict:
        import webview
        if not path.startswith("/api/"):
            return {"ok": False, "galat": "path tidak sah"}
        with urllib.request.urlopen(self.base + path.lstrip("/"), timeout=60) as r:  # server lokal sendiri
            data = r.read()
        res = self._window.create_file_dialog(webview.SAVE_DIALOG, save_filename=nama)
        if not res:
            return {"ok": False, "batal": True}
        dest = Path(res[0] if isinstance(res, (list, tuple)) else res)
        dest.write_bytes(data)
        from .paths import display_path
        return {"ok": True, "path": display_path(dest), "ukuran": len(data)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog=APP_NAME)
    ap.add_argument("--browser", action="store_true")
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--data-dir")
    args, _ = ap.parse_known_args(argv)
    if args.data_dir:
        os.environ["PERISAI_DATA_DIR"] = str(Path(args.data_dir).resolve())
    os.environ["PERISAI_MODE"] = "desktop"

    from .paths import data_dir
    root = data_dir()
    _setup_logging(root / "log")
    log = logging.getLogger("perisai.desktop")
    log.info("%s %s mulai, data=%s", APP_NAME, APP_VERSION, root)

    lock = _SingleInstance(root / "app.lock")
    if not lock.acquire():
        info = root / "instance.json"
        port = None
        try:
            port = json.loads(info.read_text(encoding="utf-8"))["port"]
        except (OSError, ValueError, KeyError):
            pass
        if port and args.browser:
            webbrowser.open(f"http://127.0.0.1:{port}/")
        else:
            _msgbox(f"{APP_NAME} sudah berjalan. Tutup jendela yang lama dulu, atau buka "
                    f"http://127.0.0.1:{port}/ di browser." if port else f"{APP_NAME} sudah berjalan.")
        return 0

    import uvicorn

    from .api import create_app

    app = create_app(mode="desktop", root=root, bind="127.0.0.1")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", args.port))
    port = sock.getsockname()[1]
    app.state.port = port
    server = uvicorn.Server(uvicorn.Config(app, log_config=None, access_log=False, lifespan="off",
                                           timeout_graceful_shutdown=2))
    th = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True, name="perisai-server")
    th.start()
    t0 = time.time()
    while not server.started and th.is_alive() and time.time() - t0 < 30:
        time.sleep(0.05)
    if not server.started:
        _msgbox("Server lokal gagal berjalan. Lihat log di folder data aplikasi (log\\app.log).")
        return 1
    url = f"http://127.0.0.1:{port}/"
    info = root / "instance.json"
    info.write_text(json.dumps({"pid": os.getpid(), "port": port, "versi": APP_VERSION}), encoding="utf-8")
    log.info("server di %s", url)
    stop = threading.Event()
    window_ref: dict = {}

    def shutdown():
        stop.set()
        w = window_ref.get("w")
        if w is not None:
            threading.Thread(target=w.destroy, daemon=True).start()

    app.state.shutdown = shutdown
    try:
        wv2 = webview2_version()
        if args.headless:
            app.state.ui = "headless"
            log.info("mode headless")
            while not stop.wait(1):
                pass
        elif args.browser or (os.name == "nt" and not wv2):
            app.state.ui = "browser"
            log.info("mode browser (WebView2=%s)", wv2)
            webbrowser.open(url)
            app.state.last_ping = time.time()
            while not stop.wait(5):
                if time.time() - app.state.last_ping > IDLE_EXIT_S:
                    log.info("tidak ada halaman terbuka selama %s detik: keluar", IDLE_EXIT_S)
                    break
        else:
            import webview
            app.state.ui = "jendela"
            api = JsApi(url)
            w = webview.create_window(f"{APP_NAME} {APP_VERSION}", url, js_api=api, width=1440, height=900,
                                      min_size=(1100, 680), text_select=True, background_color="#F4F5F7")
            api._window = w
            window_ref["w"] = w
            try:
                webview.start(gui="edgechromium" if os.name == "nt" else None, private_mode=True, debug=False)
            except Exception:
                log.exception("jendela WebView2 gagal; pindah ke browser")
                app.state.ui = "browser"
                webbrowser.open(url)
                app.state.last_ping = time.time()
                while not stop.wait(5):
                    if time.time() - app.state.last_ping > IDLE_EXIT_S:
                        break
    finally:
        server.should_exit = True
        th.join(timeout=5)
        try:
            info.unlink()
        except OSError:
            pass
        log.info("selesai")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
