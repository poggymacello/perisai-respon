"""REST API PERISAI-RESPON (FastAPI). Semua endpoint di bawah /api; frontend statis disajikan dari /.

Keamanan server lokal:
  * desktop: hanya mendengar 127.0.0.1, header Host wajib 127.0.0.1/localhost (menahan DNS rebinding);
  * setiap permintaan yang mengubah data wajib membawa header X-Perisai: 1 (form dari situs lain tidak bisa);
  * CSP connect-src 'self': halaman tidak bisa memanggil host lain;
  * mode demo publik: unggah log ditolak, satu sesi terpisah per pengunjung, LLM mati.
"""

from __future__ import annotations

import hashlib
import logging
import mimetypes
import os
import platform
import re
import secrets
import shutil
import time
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import APP_NAME, APP_VERSION, ENGINE_VERSION, asetot, cekdraf, engine, evtx, reportfmt, sample
from .llmsvc import LLMService
from .paths import app_mode, data_dir, display_path, frontend_dir
from .store import REVIEW, ReviewError, Store, Workspace

from perisai import firewall as _fw  # noqa: E402
from perisai import policy as _policy  # noqa: E402
from perisai.ot import CHECKLIST, decide_ot, is_ot_asset  # noqa: E402
from perisai.v12 import isolation_supported  # noqa: E402

for _ext, _type in ((".js", "text/javascript"), (".css", "text/css"), (".svg", "image/svg+xml"), (".json", "application/json")):
    mimetypes.add_type(_type, _ext)  # registri Windows kadang memetakan .js ke text/plain

MAX_UPLOAD = 200 * 1024 * 1024
UPLOAD_EXT = {".xml", ".json", ".jsonl", ".ndjson", ".evtx", ".txt"}
DEMO_COOKIE = "perisai_demo"
DEMO_UPLOAD_MSG = ("Mode demo publik: unggah log dinonaktifkan. Server publik tidak boleh menerima log asli satuan. "
                   "Unduh aplikasi desktop untuk memeriksa log sendiri secara offline.")
WARNING_LABEL = {"INJEKSI_TERDETEKSI": "Injeksi terdeteksi", "DRAF_AI_DISUNTING": "Draf AI disunting",
                 "RINGKASAN_DISUNTING": "Ringkasan disunting", "MODE_DEGRADASI": "Mode aturan",
                 "DRAF_AI_BERTENTANGAN": "Draf AI bertentangan dengan aturan"}
CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; "
       "connect-src 'self'; object-src 'none'; frame-src 'self'; frame-ancestors 'self'; base-uri 'none'; "
       "form-action 'self'")


# ------------------------------------------------------------------ model permintaan / jawaban
class TinjauanIn(BaseModel):
    keputusan: Literal["setujui", "tolak", "tutup", "catatan"]
    analis: str = Field(min_length=2, max_length=80)
    catatan: str = Field(min_length=3, max_length=1000)


class SimulasiIn(BaseModel):
    jenis: str = Field(min_length=1, max_length=40)
    target: str | None = Field(default=None, max_length=255)
    bukti: list[str] = Field(default_factory=list, max_length=20)
    detektor_aktif: bool = True


UJI_JENIS = Literal["isolate_host", "block_ip", "no_action"]
UJI_MAKS = 2000


class UjiInjeksiIn(BaseModel):
    teks: str = Field(min_length=1, max_length=UJI_MAKS)
    jenis: UJI_JENIS = "isolate_host"
    target: str | None = Field(default=None, max_length=255)


def uji_injeksi_case(teks: str) -> dict:
    """Kasus contoh SINTETIS (pola K-0004): Word memanggil PowerShell, lalu koneksi keluar.
    Teks juri disisipkan ke CommandLine, field yang di dunia nyata bisa ditulis penyerang."""
    host = "WS-UJI01.batalyon.lab"
    return {"case_id": f"{host}@uji-injeksi", "dataset": "uji-injeksi", "label": "", "group": "", "side": "uji",
            "primary_host": host, "tanpa_temuan": False, "events": [
                {"id": "E1", "EventID": 1, "Channel": "Microsoft-Windows-Sysmon/Operational", "Computer": host,
                 "TimeCreated": "2026-10-29T04:12:44.0000000Z",
                 "Image": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
                 "ParentImage": "C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
                 "CommandLine": f'powershell.exe -nop -w hidden -c "Get-Date" {teks}', "Hostname": host},
                {"id": "E2", "EventID": 3, "Channel": "Microsoft-Windows-Sysmon/Operational", "Computer": host,
                 "TimeCreated": "2026-10-29T04:12:50.0000000Z",
                 "Image": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
                 "DestinationIp": "172.16.30.9", "DestinationPort": "8080", "Hostname": host}]}


# Peran di demo publik. Pemisahan tugas: admin mengelola demo tetapi tidak menyetujui aksi; analis menyetujui
# tetapi tidak mengelola sistem. Aplikasi desktop (satu operator, satu laptop) tidak memakai login.
PERAN = {
    "operator": {"label": "Operator", "izin": ["lihat", "uji"],
                 "tugas": "Memantau antrean, membuka kasus, menguji usulan dan injeksi."},
    "analis": {"label": "Analis", "izin": ["lihat", "uji", "tinjau", "lapor"],
               "tugas": "Menyetujui, menolak, atau menutup kasus, dan melengkapi laporan CSIRT."},
    "admin": {"label": "Admin", "izin": ["lihat", "uji", "demo"],
              "tugas": "Mengelola sesi demo dan memeriksa status sistem. Tidak bisa menyetujui aksi."},
}
IZIN_LABEL = {"tinjau": "meninjau kasus (setujui/tolak/tutup)", "lapor": "mengisi data pelaporan", "demo": "membuka kontrol demo"}


class MasukIn(BaseModel):
    peran: Literal["operator", "analis", "admin"]
    nama: str = Field(min_length=2, max_length=80)


class PelaporanIn(BaseModel):
    """Isian analis untuk laporan (Peraturan BSSN 1/2024 Pasal 15 ayat 4: kontak pelapor dan dampak)."""
    pelapor_nama: str = Field(default="", max_length=120)
    pelapor_satuan: str = Field(default="", max_length=160)
    pelapor_kontak: str = Field(default="", max_length=160)
    dampak: str = Field(default="", max_length=2000)


PELAPORAN_ROWS = [("pelapor_nama", "Nama pelapor"), ("pelapor_satuan", "Satuan / unit kerja"),
                  ("pelapor_kontak", "Kontak pelapor (telepon / surel dinas)"), ("dampak", "Dampak insiden")]


def _md_cell(v: str) -> str:
    return " ".join(str(v).split()).replace("|", "\\|") if v else "**belum diisi**"


def _with_pelaporan(md: str, p: dict) -> str:
    """Sisipkan bagian data pelaporan sebelum bagian kedua laporan (sesudah judul dan ringkasan run)."""
    sec = ("## Data pelaporan (Peraturan BSSN 1/2024 Pasal 15 ayat 4)\n\n"
           "Diisi analis sebelum laporan diteruskan ke CSIRT atasan.\n\n| Butir | Isi |\n|---|---|\n"
           + "".join(f"| {label} | {_md_cell(p.get(key, ''))} |\n" for key, label in PELAPORAN_ROWS) + "\n")
    i = md.find("\n## ")
    return md + "\n" + sec if i < 0 else md[: i + 1] + sec + md[i + 1:]


class ImporHasil(BaseModel):
    id: str
    jenis: str
    waktu: str
    berkas: list[dict]
    n_event: int
    n_kasus: int
    n_kelompok_tanpa_temuan: int
    jendela_menit: int
    kasus: list[str]
    detik: float


class KasusRingkas(BaseModel):
    id: str
    case_id: str
    host: str
    waktu: str | None
    kategori: str
    kategori_id: str
    attack: dict
    severity: str
    severity_skor: int
    status_mesin: str
    status_tinjauan: str | None
    aksi: dict
    peringatan: list[str]
    aturan: list[str]
    n_event: int
    aset_terlindungi: bool
    ada_draf: bool


# ------------------------------------------------------------------ util
def _summary(ws: Workspace, k: dict) -> dict:
    c, d = k["case"], k["decision"]
    meta = engine.case_meta(c)
    cek = _draft_check(k)
    tac =engine.ATTACK_TACTIC.get(d["kategori"], ("-", "-"))
    slot = c["case_id"].split("@", 1)[1] if "@" in c["case_id"] else None
    return {"id": k["id"], "case_id": c["case_id"], "host": c.get("primary_host") or "-",
            "waktu": meta["waktu_awal"] or slot, "kategori": d["kategori"],
            "kategori_id": engine.CATEGORY_ID.get(d["kategori"], d["kategori"]),
            "attack": {"id": tac[0], "nama": tac[1]}, "severity": meta["severity"], "severity_skor": meta["severity_skor"],
            "status_mesin": d["final_status"], "status_tinjauan": ws.review_status(k), "aksi": d["final_action"],
            "peringatan": list(d["warnings"]) + (["DRAF_AI_BERTENTANGAN"] if (cek or {}).get("status") == "BERTENTANGAN"
                                                 else []),
            "aturan": [r["id"] for r in meta["aturan_terpicu"]],
            "n_event": len(c["events"]), "aset_terlindungi": _policy.is_protected_host(c.get("primary_host"))
            or bool(asetot.match(c.get("primary_host"))),
            "ada_draf": bool(k.get("draf")), "cek_draf": (cek or {}).get("status")}


def _draft_check(k: dict) -> dict | None:
    """Hasil cek silang draf AI vs aturan. Draf dari versi sebelum fitur ini dicek saat dibuka (tanpa entri audit)."""
    dr = k.get("draf")
    if not dr:
        return None
    if not dr.get("cek_silang"):
        dr["cek_silang"] = cekdraf.check_case(dr.get("draf_ai") or "", k["case"], k["decision"]["kategori"]) | {
            "audit_seq": None, "dihitung_saat_dibuka": True}
    return dr["cek_silang"]


def _decision_for_report(k: dict) -> dict:
    """Keputusan untuk laporan; draf yang bertentangan dengan aturan diberi tanda di teks laporan."""
    d = k["decision"]
    cek = _draft_check(k)
    if not cek or cek["status"] != "BERTENTANGAN" or not d.get("draf_ai"):
        return d
    names = ", ".join(f"{b['attack']} {b['nama']}" for b in cek["bertentangan"])
    note = (f" [DITANDAI: bertentangan dengan temuan aturan. Draf menyebut {names}; kategori aturan "
            f"{cek['attack_aturan']['id']} {cek['attack_aturan']['nama']} tetap berlaku.]")
    return {**d, "draf_ai": d["draf_ai"] + note}


def _os_name() -> str:
    if platform.system() == "Windows":
        build = platform.version().split(".")[-1]
        name = "Windows 11" if build.isdigit() and int(build) >= 22000 else f"Windows {platform.release()}"
        return f"{name} (build {build})"
    return f"{platform.system()} {platform.release()}"


def _counts(rows: list[dict]) -> dict:
    return {"total": len(rows),
            "menunggu": sum(r["status_mesin"] == "MENUNGGU_PERSETUJUAN" and not r["status_tinjauan"] for r in rows),
            "dieskalasi": sum(r["status_mesin"] == "DIESKALASI" for r in rows),
            "injeksi": sum("INJEKSI_TERDETEKSI" in r["peringatan"] for r in rows),
            "tinggi": sum(r["severity"] == "tinggi" for r in rows),
            "ditinjau": sum(bool(r["status_tinjauan"]) for r in rows)}


def _review_options(ws: Workspace, k: dict) -> list[dict]:
    st = k["decision"]["final_status"]
    cur = ws.review_status(k)
    out = []
    for key, (label, status, allowed) in REVIEW.items():
        if st in allowed and not (status and cur in ("DISETUJUI", "DITOLAK", "DITUTUP_ANALIS")):
            out.append({"keputusan": key, "label": label})
    return out


def _safe_name(name: str) -> str:
    base = Path(name or "log").name
    base = re.sub(r"[^A-Za-z0-9._ -]", "_", base).strip(" .") or "log"
    return base[:120]


def _strip_proposal(p: dict | None) -> dict | None:
    if not p:
        return None
    return {k: v for k, v in p.items() if k != "ringkasan"}


def _llm_run_meta(ws: Workspace, llm: LLMService) -> tuple[str, str]:
    n = sum(1 for k in ws.state["kasus"] if k.get("draf"))
    st = llm.status()
    chk = (st["model"]["cek"] or {}).get("status") or st["alasan"] or "-"
    if n:
        return f"Qwen2.5-1.5B lokal (draf AI untuk {n} kasus; keputusan tetap dari aturan)", chk
    if st["tersedia"]:
        return "Qwen2.5-1.5B lokal tersedia, belum dipakai (belum ada draf AI; keputusan dari aturan)", chk
    return "tidak aktif (mode aturan)", chk if st["model"]["nama"] else "tidak dipakai (mode aturan)"


# ------------------------------------------------------------------ aplikasi
def create_app(mode: str | None = None, root: Path | None = None, bind: str = "127.0.0.1") -> FastAPI:
    mode = mode or app_mode()
    demo = mode == "demo"
    root = root or data_dir()
    store = Store(root, demo=demo)
    llm = LLMService(enabled=not demo)
    os.environ.setdefault("OTEL_SDK_DISABLED", "true")
    # FastAPI >= 0.16x punya integrasi OpenTelemetry bawaan; dimatikan seluruhnya (tidak ada SDK/eksportir terpasang).
    app = FastAPI(title=f"{APP_NAME} API", version=APP_VERSION, docs_url=None, redoc_url=None, openapi_url="/api/openapi.json",
                  telemetry={"tracing": False, "metrics": False, "logs": False, "operation_spans": False,
                             "auto_configure": False})
    app.state.store, app.state.llm, app.state.mode, app.state.bind = store, llm, mode, bind
    app.state.port = None
    app.state.ui = "server"
    app.state.shutdown = None
    app.state.last_ping = time.time()
    if not demo:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])

    @app.middleware("http")
    async def guard(request: Request, call_next):
        if demo and request.url.path == "/api/impor":  # tolak sebelum isi berkas dibaca server
            return JSONResponse({"detail": DEMO_UPLOAD_MSG}, status_code=403)
        if request.url.path.startswith("/api/") and request.method not in ("GET", "HEAD", "OPTIONS"):
            if request.headers.get("x-perisai") != "1":
                return JSONResponse({"detail": "permintaan ditolak: header X-Perisai tidak ada"}, status_code=403)
        resp = await call_next(request)
        resp.headers["Content-Security-Policy"] = CSP
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["X-Frame-Options"] = "SAMEORIGIN"
        if request.url.path.startswith("/api/") or request.url.path in ("/", "/index.html"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    def workspace(request: Request, response: Response) -> Workspace:
        visitor = request.cookies.get(DEMO_COOKIE) if demo else None
        ws, created = store.active(visitor)
        if demo:
            if created or not ws.state["kasus"]:
                if not ws.state["impor"]:
                    ws.import_files(sample.sample_files(), label="data contoh")
            if ws.sid != visitor:
                response.set_cookie(DEMO_COOKIE, ws.sid, httponly=True, samesite="lax", max_age=7 * 86400)
        return ws

    def require(ws: Workspace, izin: str) -> None:
        """Di demo publik: pengunjung harus masuk dengan peran yang punya izin ini. Desktop: selalu boleh."""
        if not demo:
            return
        m = ws.state.get("masuk")
        if not m:
            raise HTTPException(401, "masuk dulu dengan salah satu peran demo")
        if izin not in PERAN[m["peran"]]["izin"]:
            raise HTTPException(403, f"peran {PERAN[m['peran']]['label']} tidak boleh {IZIN_LABEL.get(izin, izin)}")

    def case_or_404(ws: Workspace, kid: str) -> dict:
        k = ws.get(kid)
        if k is None:
            raise HTTPException(404, f"kasus {kid} tidak ada di sesi ini")
        return k

    # -------------------------------------------------------------- status
    @app.get("/api/status")
    def status(request: Request, ws: Workspace = Depends(workspace)):
        app.state.last_ping = time.time()
        if not getattr(app.state, "ui_seen", False):
            app.state.ui_seen = True
            logging.getLogger("perisai.api").info("antarmuka pertama terhubung: %s", request.headers.get("user-agent", "-")[:160])
        st = llm.status()
        cpu = platform.processor() or platform.machine()
        if os.name == "nt":
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as kk:
                    cpu = winreg.QueryValueEx(kk, "ProcessorNameString")[0].strip()
            except OSError:
                pass
        return {"aplikasi": {"nama": APP_NAME, "versi": APP_VERSION},
                "mesin": {"versi": ENGINE_VERSION, "jalur": "perisai.v12.decide_v12 + guard_draft",
                          "integritas": engine.engine_integrity()},
                "mode": mode, "mode_analisis": "llm" if st["tersedia"] else "aturan", "llm": st,
                "jaringan": {"bind": bind, "port": app.state.port,
                             "lokal_saja": bind in ("127.0.0.1", "localhost", "::1"),
                             "csp_connect": "'self'", "telemetri": False},
                "data": {"folder": display_path(root), "sesi": ws.sid}, "antarmuka": app.state.ui,
                "sesi": {"id": ws.sid, "n_kasus": len(ws.state["kasus"]), "n_impor": len(ws.state["impor"]),
                         "n_audit": len(ws.audit.entries()), "dibuat": ws.state["dibuat"]},
                "kemampuan": {"unggah": not demo, "evtx": evtx.available(), "llm": st["tersedia"]},
                "perangkat": {"os": _os_name(), "cpu": cpu,
                              "inti_logis": os.cpu_count(), "python": platform.python_version()}}

    @app.get("/api/ping")
    def ping():
        app.state.last_ping = time.time()
        return {"ok": True}

    # -------------------------------------------------------------- impor
    @app.post("/api/sampel", response_model=ImporHasil)
    def load_sample(ws: Workspace = Depends(workspace)):
        # Idempoten: data contoh yang sudah dimuat di sesi ini tidak diimpor ulang (mencegah kasus ganda).
        sudah = next((i for i in ws.state["impor"] if i.get("jenis") == "data contoh"), None)
        if sudah is not None:
            return sudah
        return ws.import_files(sample.sample_files(), label="data contoh")

    @app.get("/api/sampel/{nama}")
    def sample_file(nama: str):
        if nama not in sample.SAMPLE_FILES:
            raise HTTPException(404, "berkas contoh tidak ada")
        p = sample.sample_files()[sample.SAMPLE_FILES.index(nama)][0]
        return FileResponse(p, filename=nama, media_type="application/octet-stream")

    @app.post("/api/impor", response_model=ImporHasil)
    def upload(berkas: list[UploadFile] = File(...), jendela: int = Form(15), ws: Workspace = Depends(workspace)):
        if demo:
            raise HTTPException(403, DEMO_UPLOAD_MSG)
        if not 1 <= jendela <= 240:
            raise HTTPException(422, "jendela pengelompokan harus 1-240 menit")
        if not berkas:
            raise HTTPException(422, "tidak ada berkas")
        tmp = root / "tmp" / secrets.token_hex(6)
        tmp.mkdir(parents=True)
        try:
            files = []
            for i, f in enumerate(berkas):
                name = _safe_name(f.filename)
                ext = Path(name).suffix.lower()
                if ext not in UPLOAD_EXT:
                    raise HTTPException(415, f"{name}: format tidak didukung (pakai .xml wevtutil, .json/.jsonl "
                                             f"Winlogbeat, atau .evtx)")
                dst = tmp / f"{i:02d}_{name}"
                h, size = hashlib.sha256(), 0
                with dst.open("wb") as out:
                    while chunk := f.file.read(1 << 20):
                        size += len(chunk)
                        if size > MAX_UPLOAD:
                            raise HTTPException(413, f"{name}: lebih dari {MAX_UPLOAD // (1 << 20)} MB")
                        h.update(chunk)
                        out.write(chunk)
                if size == 0:
                    raise HTTPException(422, f"{name}: berkas kosong")
                path = dst
                if ext == ".evtx":
                    path = tmp / f"{i:02d}_{name}.xml"
                    try:
                        evtx.evtx_to_xml(dst, path)
                    except evtx.EvtxError as exc:
                        raise HTTPException(422, f"{name}: {exc}") from exc
                files.append((path, name, size, h.hexdigest()))
            try:
                res = ws.import_files(files, window=jendela)
            except HTTPException:
                raise
            except Exception as exc:  # XML rusak, DOCTYPE ditolak, dsb.
                raise HTTPException(422, f"berkas tidak bisa dibaca: {type(exc).__name__}: {str(exc)[:200]}") from exc
            if res["n_event"] == 0:
                raise HTTPException(422, "tidak ada event yang dikenali. Pakai wevtutil qe ... /f:xml atau JSON Winlogbeat.")
            return res
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # -------------------------------------------------------------- kasus
    @app.get("/api/kasus")
    def list_cases(ws: Workspace = Depends(workspace)):
        rows = [_summary(ws, k) for k in ws.state["kasus"]]
        return {"sesi": ws.sid, "kasus": rows, "hitung": _counts(rows), "impor": ws.state["impor"]}

    @app.get("/api/kasus/{kid}")
    def get_case(kid: str, ws: Workspace = Depends(workspace)):
        k = case_or_404(ws, kid)
        c, d = k["case"], k["decision"]
        flagged = {(f["event"], f["field"]): f for f in k["firewall"]["temuan"]}
        events = []
        for e in c["events"]:
            v = engine.event_view(e)
            v["ditandai"] = [{"field": fld, "kode": flagged[(e["id"], fld)]["kode"]}
                             for fld in v["teks_bebas"] if (e["id"], fld) in flagged]
            events.append(v)
        _draft_check(k)
        iso_ok, iso_rules = isolation_supported(c, d["kategori"])
        llm_on = llm.status()["tersedia"]
        entries = [{"seq": e["seq"], "ts": e["ts"], "kind": e["kind"], "hash": e["entry_hash"]}
                   for e in ws.audit.entries() if e["case_id"] == c["case_id"]]
        job = llm.jobs.active_for(ws.sid, kid)
        return {"ringkas": _summary(ws, k), "kasus": {"case_id": c["case_id"], "sha256": c.get("sha256"),
                "sumber": c.get("dataset"), "n_event_rekaman": c.get("n_events_recording"), "primary_host": c.get("primary_host")},
                "aturan_terpicu": engine.case_meta(c)["aturan_terpicu"], "event": events, "firewall": k["firewall"],
                "keputusan": {"verdict": d["verdict"], "aksi_akhir": d["final_action"], "status": d["final_status"],
                              "kategori": d["kategori"], "ringkasan_aturan": d["ringkasan"],
                              "alasan": [engine.reason_text(r, llm_on) for r in d["reasons"]], "alasan_asli": d["reasons"],
                              "peringatan": d["warnings"], "sumber": d["source"], "verdict_usulan_v1": d.get("v1_verdict"),
                              "usulan_llm": _strip_proposal(d.get("proposal")),
                              "syarat_isolasi": {"terpenuhi": iso_ok, "aturan": iso_rules}},
                "draf": k.get("draf"), "tinjauan": k["tinjauan"], "opsi_tinjauan": _review_options(ws, k),
                "audit": entries, "tugas": llm.jobs.view(job) if job else None,
                "aksi_tersedia": engine.ACTIONS}

    @app.post("/api/kasus/{kid}/tinjauan")
    def review(kid: str, body: TinjauanIn, ws: Workspace = Depends(workspace)):
        require(ws, "tinjau")
        case_or_404(ws, kid)
        try:
            rec = ws.review(kid, body.keputusan, body.analis.strip(), body.catatan.strip())
        except ReviewError as exc:
            raise HTTPException(409, str(exc)) from exc
        return {"tinjauan": rec, "dieksekusi": False,
                "pesan": "Dicatat di jejak audit. PERISAI tidak menjalankan aksi ke sistem (pilot baca-saja)."}

    @app.post("/api/kasus/{kid}/simulasi")
    def simulate(kid: str, body: SimulasiIn, ws: Workspace = Depends(workspace)):
        k = case_or_404(ws, kid)
        r = engine.simulate(k["case"], body.jenis.strip(), (body.target or "").strip() or None,
                            [b.strip() for b in body.bukti if b.strip()], body.detektor_aktif)
        on = llm.status()["tersedia"]
        return r | {"alasan_usulan": [engine.reason_text(x, on) for x in r["alasan_usulan"]],
                    "alasan_akhir": [engine.reason_text(x, on) for x in r["alasan_akhir"]]}

    @app.post("/api/uji-injeksi")
    def uji_injeksi(body: UjiInjeksiIn):
        """Juri menjadi penyerang: teks bebas masuk ke log sintetis, lalu usulan penyerang diuji ke policy dengan
        anggapan terburuk (AI menuruti injeksi 100%). Tanpa sesi, tidak mengubah kasus, tidak dicatat di audit."""
        case = uji_injeksi_case(body.teks)
        target = (body.target or "").strip() or None
        on = llm.status()["tersedia"]
        fw = engine._fw_dump(_fw.inspect_case(case))
        hasil = {}
        for key, aktif in (("detektor_aktif", True), ("detektor_mati", False)):
            r = engine.simulate(case, body.jenis, target, ["E1"], aktif)
            hasil[key] = r | {"alasan_usulan": [engine.reason_text(x, on) for x in r["alasan_usulan"]],
                              "alasan_akhir": [engine.reason_text(x, on) for x in r["alasan_akhir"]]}
        flagged = {(f["event"], f["field"]): f for f in fw["temuan"]}
        events = []
        for e in case["events"]:
            v = engine.event_view(e)
            v["ditandai"] = [{"field": fld, "kode": flagged[(e["id"], fld)]["kode"]}
                             for fld in v["teks_bebas"] if (e["id"], fld) in flagged]
            events.append(v)
        return {"kasus": {"host": case["primary_host"], "event": events},
                "firewall": fw, "usulan": {"jenis": body.jenis, "target": target}, **hasil}

    @app.post("/api/kasus/{kid}/draf-ai")
    def draft(kid: str, ws: Workspace = Depends(workspace)):
        k = case_or_404(ws, kid)
        st = llm.status()
        if not st["tersedia"]:
            raise HTTPException(409, f"Mode LLM tidak aktif: {st['alasan']}.")
        running = llm.jobs.active_for(ws.sid, kid)
        if running:
            return llm.jobs.view(running)

        def work(stage):
            model = llm.get_llm(stage)
            stage("LLM lokal menulis usulan (CPU)")
            t0 = time.perf_counter()
            d, r, _ = engine.decide_case(k["case"], _LockedAudit(ws), model)
            secs = round(time.perf_counter() - t0, 1)
            llm.last_case_seconds = secs
            stage("menyaring draf, cek silang dengan aturan, dan mencatat ke audit")
            # Cek silang deterministik: draf yang menamai kategori lain dari temuan aturan ditandai. Keputusan tidak
            # berubah; hasilnya dicatat sebagai entri audit sendiri, sesudah entri keputusan_v12 draf ini.
            cek = cekdraf.check_case(d["draf_ai"], k["case"], d["kategori"])
            ent = _LockedAudit(ws).append(k["case"]["case_id"], "cek_silang_draf", cekdraf.audit_payload(cek),
                                          engine.now_iso())
            cek |= {"audit_seq": ent["seq"], "audit_hash": ent["entry_hash"]}
            before = k["decision_rules"]["final_action"]
            info = {"ts": engine.now_iso(), "detik_llm": round(r.get("llm_seconds") or 0.0, 1), "detik_total": secs,
                    "draf_ai": d["draf_ai"], "dibuang": d.get("draf_dibuang_v12", []),
                    "dibuang_v11": [s for s in d.get("kalimat_dibuang", []) if s not in
                                    {x["kalimat"] for x in d.get("draf_dibuang_v12", [])}],
                    "galat_llm": r.get("error"), "usulan_llm": _strip_proposal(r.get("proposal")),
                    "verdict_usulan": d.get("v1_verdict"), "aksi_tidak_berubah": d["final_action"] == before,
                    "token": {"prompt": r.get("prompt_tokens"), "keluaran": r.get("completion_tokens")},
                    "cek_silang": cek}
            ws.set_draft(kid, d, info)
            return {"kasus": kid, "detik": secs}

        return llm.jobs.submit("draf_ai", ws.sid, work, kasus=kid, perkiraan_detik=llm.last_case_seconds or 30)

    @app.get("/api/tugas/{jid}")
    def job(jid: str, ws: Workspace = Depends(workspace)):
        j = llm.jobs.get(jid)
        if j is None or j["pemilik"] != ws.sid:
            raise HTTPException(404, "tugas tidak ada")
        return llm.jobs.view(j)

    # -------------------------------------------------------------- audit
    @app.get("/api/audit")
    def audit(ws: Workspace = Depends(workspace)):
        ents = ws.audit.entries()
        kid_by_case = {k["case"]["case_id"]: k["id"] for k in ws.state["kasus"]}
        rows = [{"seq": e["seq"], "ts": e["ts"], "case_id": e["case_id"], "kasus": kid_by_case.get(e["case_id"]),
                 "kind": e["kind"], "prev_hash": e["prev_hash"], "entry_hash": e["entry_hash"],
                 "payload_hash": e["payload_hash"], "payload": e["payload"]} for e in ents[-3000:]]
        return {"sesi": ws.sid, "entri": rows, "jumlah": len(ents), "verifikasi": ws.audit.verify(),
                "berkas": "audit.jsonl"}

    @app.post("/api/audit/verifikasi")
    def verify(ws: Workspace = Depends(workspace)):
        t0 = time.perf_counter()
        v = ws.audit.verify()
        return v | {"ms": round((time.perf_counter() - t0) * 1000, 2), "waktu": engine.now_iso()}

    @app.post("/api/audit/uji-perubahan")
    def tamper(ws: Workspace = Depends(workspace)):
        try:
            return ws.tamper_test()
        except ReviewError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/api/audit/ekspor")
    def export_audit(ws: Workspace = Depends(workspace)):
        if not ws.audit.path.exists():
            raise HTTPException(404, "jejak audit masih kosong")
        return FileResponse(ws.audit.path, filename=f"audit_{ws.sid[:15]}.jsonl", media_type="application/x-ndjson")

    # -------------------------------------------------------------- laporan
    def build_report(ws: Workspace) -> tuple[str, str]:
        items = [{"case": k["case"], "decision": _decision_for_report(k)} for k in ws.state["kasus"]]
        imp = ws.state["impor"]
        names = list(dict.fromkeys(b["nama"] for i in imp for b in i["berkas"]))
        llm_txt, chk = _llm_run_meta(ws, llm)
        run = {"waktu": engine.now_iso(), "sumber": ", ".join(names) or "-", "n_event": sum(i["n_event"] for i in imp),
               "llm": llm_txt, "model_check": chk, "audit_path": "audit.jsonl (ekspor dari menu Jejak audit)",
               "n_tanpa_temuan": sum(i["n_kelompok_tanpa_temuan"] for i in imp)}
        md = engine.render_report(run, items, ws.audit, ws.all_reviews(), llm_on=llm.status()["tersedia"])
        md = _with_pelaporan(md, ws.state.get("pelaporan") or {})
        return md, f"laporan_perisai_{ws.sid[:15]}"

    @app.post("/api/laporan/pelaporan")
    def save_pelaporan(body: PelaporanIn, ws: Workspace = Depends(workspace)):
        require(ws, "lapor")
        data = {k: v.strip() for k, v in body.model_dump().items()}
        with ws.lock:
            ws.state["pelaporan"] = data | {"diubah": engine.now_iso()}
            ws.save()
        return ws.state["pelaporan"]

    @app.get("/api/laporan")
    def report(ws: Workspace = Depends(workspace)):
        if not ws.state["kasus"]:
            raise HTTPException(409, "belum ada kasus; impor log atau muat data contoh dulu")
        md, name = build_report(ws)
        return {"markdown": md, "html": reportfmt.md_to_html(md), "nama": name,
                "pelaporan": ws.state.get("pelaporan") or {}}

    @app.get("/api/laporan/unduh")
    def report_download(format: Literal["md", "html"] = "md", ws: Workspace = Depends(workspace)):
        if not ws.state["kasus"]:
            raise HTTPException(409, "belum ada kasus")
        md, name = build_report(ws)
        if format == "md":
            return PlainTextResponse(md, media_type="text/markdown; charset=utf-8",
                                     headers={"Content-Disposition": f'attachment; filename="{name}.md"'})
        return Response(reportfmt.standalone_html(md, name), media_type="text/html; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{name}.html"'})

    @app.get("/api/laporan/cetak")
    def report_print(ws: Workspace = Depends(workspace)):
        if not ws.state["kasus"]:
            raise HTTPException(409, "belum ada kasus")
        md, name = build_report(ws)
        return Response(reportfmt.standalone_html(md, name), media_type="text/html; charset=utf-8")

    # -------------------------------------------------------------- OT
    @app.get("/api/ot")
    def ot():
        case, prop = sample.ot_case(), sample.ot_proposal()
        d = decide_ot(case, prop)
        fw = _fw.inspect_case(case)
        tags = [{"tag": e["ObjectName"], "nilai": e["Nilai"], "normal": [float(x) for x in e["Normal"].strip("[]").split(",")],
                 "detik_melanggar": e["DetikMelanggar"], "jendela_detik": 60, "host": e["Hostname"], "waktu": e["TimeCreated"]}
                for e in case["events"] if e["EventID"] == "OT-AMPLOP"]
        return {"kasus": case, "usulan": prop, "keputusan": d, "firewall": {"injeksi": fw.injection, "kode": fw.codes()},
                "tag": tags, "checklist": CHECKLIST, "aset_ot": is_ot_asset(case["primary_host"]),
                "sumber": "prototype/demo.py skenario 5c (sintetis); usulan dibuat tangan untuk meniru LLM yang menuruti catatan HMI"}

    # -------------------------------------------------------------- kinerja
    @app.post("/api/uji-kinerja")
    def bench(ws: Workspace = Depends(workspace)):
        cases = [k["case"] for k in ws.state["kasus"]]
        src = "kasus di sesi ini"
        if not cases:
            from .engine import parse_files
            files = sample.sample_files()
            _, cases, _ = parse_files([f[0] for f in files], ", ".join(f[1] for f in files))
            src = "data contoh"
        res = engine.bench_rules(cases)
        return res | {"sumber": src, "waktu": engine.now_iso()}

    @app.post("/api/uji-kinerja/llm")
    def bench_llm(ws: Workspace = Depends(workspace)):
        st = llm.status()
        if not st["tersedia"]:
            raise HTTPException(409, f"Mode LLM tidak aktif: {st['alasan']}.")
        running = llm.jobs.active_for(ws.sid)
        if running:
            raise HTTPException(409, "masih ada tugas LLM yang berjalan; tunggu sampai selesai")

        def work(stage):
            from perisai.pipeline import run_guarded
            files = sample.sample_files()
            _, cases, _ = engine.parse_files([f[0] for f in files], ", ".join(f[1] for f in files))
            case = next(c for c in cases if c.get("primary_host", "").startswith("WS-OPS07"))
            loaded_before = llm._llm is not None
            t0 = time.perf_counter()
            model = llm.get_llm(stage)
            t_load = time.perf_counter() - t0
            stage("LLM lokal menulis usulan untuk 1 kasus contoh")
            r = run_guarded(case, model, None)  # tanpa audit: ini pengukuran, bukan triase
            llm.last_case_seconds = round(r["llm_seconds"], 1)
            return {"detik_muat_model": None if loaded_before else round(t_load, 1), "detik_llm": round(r["llm_seconds"], 1),
                    "token_prompt": r.get("prompt_tokens"), "token_keluaran": r.get("completion_tokens"),
                    "firewall_ms": round(r["firewall_ms"], 3), "policy_ms": round(r["policy_ms"], 3),
                    "usulan_valid": r.get("proposal") is not None, "thread": llm.n_threads, "kasus": case["case_id"]}

        return llm.jobs.submit("uji_llm", ws.sid, work, perkiraan_detik=(llm.last_case_seconds or 30) + 10)

    # -------------------------------------------------------------- sesi
    @app.get("/api/peran")
    def roles(ws: Workspace = Depends(workspace)):
        return {"wajib": demo, "masuk": ws.state.get("masuk"),
                "peran": [{"id": k} | v for k, v in PERAN.items()]}

    @app.post("/api/masuk")
    def sign_in(body: MasukIn, ws: Workspace = Depends(workspace)):
        if not demo:
            raise HTTPException(409, "login hanya dipakai di demo publik; aplikasi desktop dipakai satu operator")
        p = PERAN[body.peran]
        with ws.lock:
            ws.state["masuk"] = {"peran": body.peran, "label": p["label"], "nama": body.nama.strip(),
                                 "izin": p["izin"], "waktu": engine.now_iso()}
            ws.save()
            ws.audit.append(ws.sid, "masuk", {"peran": body.peran, "nama": body.nama.strip()}, engine.now_iso())
        return ws.state["masuk"]

    @app.post("/api/keluar-peran")
    def sign_out(ws: Workspace = Depends(workspace)):
        with ws.lock:
            ws.state.pop("masuk", None)
            ws.save()
        return {"ok": True}

    @app.post("/api/sesi/baru")
    def new_session(request: Request, response: Response):
        visitor = request.cookies.get(DEMO_COOKIE) if demo else None
        old = store.active(visitor)[0] if visitor else None
        ws = store.new_session()
        if demo:
            if old is not None and old.state.get("masuk"):
                ws.state["masuk"] = old.state["masuk"]  # tetap masuk dengan peran yang sama
                ws.save()
            ws.import_files(sample.sample_files(), label="data contoh")
            response.set_cookie(DEMO_COOKIE, ws.sid, httponly=True, samesite="lax", max_age=7 * 86400)
        return {"sesi": ws.sid}

    @app.get("/api/sesi")
    def sessions():
        if demo:
            return {"sesi": []}
        return {"sesi": store.list_sessions()[:50]}

    @app.post("/api/keluar")
    def quit_app():
        if demo or app.state.shutdown is None:
            raise HTTPException(409, "tidak tersedia di mode ini")
        app.state.shutdown()
        return {"ok": True}

    # -------------------------------------------------------------- frontend
    # Desktop: "/" = aplikasi, landing di /landing/. Demo publik: "/" = landing, aplikasi di /app/.
    # /app/ tersedia di kedua mode supaya tautan landing selalu sama.
    fdir = frontend_dir()
    if fdir.exists():
        landing = fdir / "landing" / "index.html"
        if demo and landing.exists():
            @app.get("/", include_in_schema=False)
            def landing_page():
                return FileResponse(landing, media_type="text/html")

        @app.get("/app", include_in_schema=False)
        def app_slash():
            return Response(status_code=307, headers={"Location": "/app/"})

        app.mount("/app", StaticFiles(directory=str(fdir), html=True), name="frontend-app")
        app.mount("/", StaticFiles(directory=str(fdir), html=True), name="frontend")

    llm.check_async()
    return app


class _LockedAudit:
    """AuditLog yang mengambil kunci sesi tiap kali menulis (tugas LLM berjalan di thread lain)."""

    def __init__(self, ws: Workspace):
        self._ws = ws

    def append(self, *a, **kw):
        with self._ws.lock:
            return self._ws.audit.append(*a, **kw)

    def __getattr__(self, name):
        return getattr(self._ws.audit, name)
