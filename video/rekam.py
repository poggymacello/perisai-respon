"""Rekam layar demo PERISAI-RESPON dari aplikasi asli (exe hasil build), otomatis dan bisa diulang.

    video\\.venv\\Scripts\\python -I video\\rekam.py            (dari folder KartikaCyber2026)

Langkah:
  1. Membuat folder data BARU di %TEMP% (bukan %LOCALAPPDATA%\\PERISAI-RESPON), lalu menautkan model GGUF
     ke <data>\\models\\ (hard link; berkas model tidak diubah). Tanpa --model, aplikasi jalan di mode aturan.
  2. Menjalankan PERISAI-RESPON.exe --headless --data-dir <data>, menunggu cek SHA-256 model, lalu memanaskan
     model sekali lewat /api/uji-kinerja/llm (pengukuran ini tidak masuk jejak audit).
  3. Membuka aplikasi di Edge headless (Playwright, record_video 1920x1080) dengan zoom 125 % (setara skala
     tampilan Windows 125 %), lalu menjalankan alur demo dengan jeda yang cukup untuk dibaca. Elemen yang
     sedang dibahas diberi garis tepi oranye lewat CSSOM (kode aplikasi tidak diubah).
  4. Menyimpan rekaman (.webm) dan penanda waktu tiap potongan (marks.json) ke video\\rekaman\\.
     susun.py memakai penanda itu untuk memotong, mengurutkan, dan memberi subtitle.

Lama tiap potongan diambil dari narasi di alur.py, jadi layar tidak berpindah sebelum narasinya selesai.
Data yang dipakai hanya log contoh sintetis bawaan aplikasi (host fiktif *.batalyon.lab).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import alur  # noqa: E402

KC = HERE.parent
EXE = KC / "app" / "dist" / "PERISAI-RESPON-1.0.0-win64" / "PERISAI-RESPON.exe"
MODEL = KC / "prototype" / "models" / "qwen2.5-1.5b-instruct-q3_k_m.gguf"
SAMPEL_XML = KC / "app" / "perisai_app" / "sampel" / "contoh_wevtutil.xml"
PRIBADI = ("POGGY", "poggy", "arialexander")  # "Users\Public" di log contoh bukan data pribadi

ANALIS = "Analis Piket (contoh)"
CATATAN = ("Proses svc-update.exe dari C:\\Users\\Public mengakses LSASS. "
           "Isolasi disetujui, menunggu konfirmasi operator.")

# Bantuan di halaman: sorotan, gulir halus, kotak elemen. Semua lewat CSSOM (CSP halaman melarang <style> inline).
JS = r"""
(() => {
  if (window.__rk) return;
  const lit = [];
  const main = () => document.getElementById('main');
  window.__rk = {
    zoom(z) {
      document.documentElement.style.zoom = String(z);
      document.querySelector('.app').style.height = `calc(100vh / ${z})`;
    },
    hl(el) {
      lit.push([el, el.style.outline, el.style.outlineOffset, el.style.boxShadow, el.style.borderRadius]);
      el.style.outline = '3px solid #e8590c';
      el.style.outlineOffset = '3px';
      el.style.boxShadow = '0 0 0 7px rgba(232, 89, 12, 0.18)';
      if (!el.style.borderRadius) el.style.borderRadius = '4px';
    },
    clear() {
      while (lit.length) { const [el, o, oo, bs, br] = lit.pop(); el.style.outline = o; el.style.outlineOffset = oo; el.style.boxShadow = bs; el.style.borderRadius = br; }
    },
    lit() { return lit.map(([el]) => el); },
    box(els) {
      let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
      for (const el of els) { const r = el.getBoundingClientRect(); x0 = Math.min(x0, r.left); y0 = Math.min(y0, r.top); x1 = Math.max(x1, r.right); y1 = Math.max(y1, r.bottom); }
      return [x0, y0, x1, y1];
    },
    // berapa piksel layar bergeser per 1 unit scrollTop (zoom CSS membuat keduanya bisa berbeda)
    k() {
      const m = main(); const st = m.scrollTop; const probe = m.firstElementChild;
      const a = probe.getBoundingClientRect().top;
      for (const step of [50, -50]) {
        m.scrollTop = st + step;
        const d = m.scrollTop - st; const b = probe.getBoundingClientRect().top;
        m.scrollTop = st;
        if (Math.abs(d) >= 1) return (a - b) / d;
      }
      return 1;
    },
    scrollTo(el, offset, ms) {
      const m = main(); const k = this.k();
      const mt = m.getBoundingClientRect().top; const r = el.getBoundingClientRect();
      const max = m.scrollHeight - m.clientHeight;
      const from = m.scrollTop; const to = Math.max(0, Math.min(max, from + (r.top - mt - offset) / k));
      const dur = ms || Math.max(500, Math.min(1600, Math.abs(to - from) * k * 0.9));
      return new Promise((res) => {
        if (Math.abs(to - from) < 2) { res(0); return; }
        const t0 = performance.now();
        const step = (now) => { const p = Math.min(1, (now - t0) / dur); m.scrollTop = from + (to - from) * (0.5 - Math.cos(Math.PI * p) / 2); p < 1 ? requestAnimationFrame(step) : res(dur); };
        requestAnimationFrame(step);
      });
    },
    flash(on) {
      let d = document.getElementById('__rk_sync');
      if (on && !d) { d = document.createElement('div'); d.id = '__rk_sync'; Object.assign(d.style, {position: 'fixed', inset: '0', background: '#000', zIndex: '99999'}); document.body.appendChild(d); }
      if (!on && d) d.remove();
    },
  };
})();
"""


def http(base: str, method: str, path: str, timeout: float = 30) -> dict:
    req = urllib.request.Request(base + path.lstrip("/"), method=method, data=b"{}" if method == "POST" else None,
                                 headers={"X-Perisai": "1", "Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # server lokal sendiri (127.0.0.1)
        return json.loads(r.read() or b"{}")


def start_app(exe: Path, data: Path) -> tuple[subprocess.Popen, str]:
    proc = subprocess.Popen([str(exe), "--headless", "--data-dir", str(data)], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, cwd=str(exe.parent))
    info = data / "instance.json"
    t0 = time.time()
    while time.time() - t0 < 60:
        if info.exists():
            try:
                port = json.loads(info.read_text(encoding="utf-8"))["port"]
                return proc, f"http://127.0.0.1:{port}/"
            except (ValueError, KeyError):
                pass
        if proc.poll() is not None:
            raise SystemExit(f"aplikasi berhenti saat mulai (kode {proc.returncode})")
        time.sleep(0.3)
    proc.kill()
    raise SystemExit("instance.json tidak muncul dalam 60 dtk")


def wait_llm(base: str, want_llm: bool) -> dict:
    t0 = time.time()
    while True:
        st = http(base, "GET", "/api/status")
        if not st["llm"]["memeriksa"]:
            break
        if time.time() - t0 > 180:
            raise SystemExit("cek SHA-256 model tidak selesai dalam 180 dtk")
        time.sleep(1)
    if want_llm and st["mode_analisis"] != "llm":
        raise SystemExit(f"mode LLM tidak aktif: {st['llm'].get('alasan')}")
    if want_llm:
        job = http(base, "POST", "/api/uji-kinerja/llm")
        print("pemanasan model ...", flush=True)
        while True:
            j = http(base, "GET", f"/api/tugas/{job['id']}")
            if j["status"] in ("selesai", "gagal"):
                print(f"pemanasan: {j['status']} {j.get('hasil') or j.get('galat')}", flush=True)
                break
            time.sleep(1)
    return st


class Rekaman:
    def __init__(self, page, need: dict[str, float], zoom: float):
        self.page = page
        self.need = need
        self.zoom = zoom
        self.t0 = time.monotonic()
        self.marks: list[dict] = []
        self.sync: list[float] = []
        self.warn: list[str] = []
        self.info: dict = {}

    def now(self) -> float:
        return time.monotonic() - self.t0

    def wait(self, s: float) -> None:
        self.page.wait_for_timeout(int(s * 1000))

    def helpers(self) -> None:
        self.page.evaluate(JS)

    # ----- sorotan dan gulir
    def hl(self, target) -> None:
        loc = self.page.locator(target) if isinstance(target, str) else target
        loc.first.evaluate("el => window.__rk.hl(el)")

    def clear(self) -> None:
        self.page.evaluate("window.__rk.clear()")

    def scroll(self, target, offset: int = 90, ms: int | None = None) -> None:
        loc = self.page.locator(target) if isinstance(target, str) else target
        loc.first.evaluate(f"el => window.__rk.scrollTo(el, {offset}, {ms or 0})")
        self.wait(0.25)

    def click(self, target, pause: float = 0.9) -> None:
        """Sorot dulu supaya penonton tahu apa yang diklik (kursor tidak terekam), lalu klik."""
        loc = self.page.locator(target) if isinstance(target, str) else target
        loc = loc.first
        loc.scroll_into_view_if_needed()
        loc.evaluate("el => window.__rk.hl(el)")
        self.wait(pause)
        loc.click()
        self.wait(0.3)

    def nav(self, label: str, wait_sel: str) -> None:
        self.click(self.page.locator("#nav a", has_text=label), pause=0.7)
        self.page.wait_for_selector(wait_sel, timeout=30000)
        self.helpers()
        self.clear()
        self.wait(0.4)

    def flash(self) -> None:
        self.page.evaluate("window.__rk.flash(true)")
        self.sync.append(self.now())
        self.wait(1.2)
        self.page.evaluate("window.__rk.flash(false)")
        self.wait(0.6)

    def privacy(self, where: str) -> None:
        txt = self.page.inner_text("body")
        for s in PRIBADI:
            if s in txt:
                self.warn.append(f"{where}: teks pribadi '{s}' terlihat")

    @contextmanager
    def beat(self, bid: str, zoom_sel: list | None = None):
        if bid not in self.need:
            raise KeyError(f"potongan {bid} tidak ada di alur.py")
        self.clear()
        start = self.now()
        yield
        rect = None
        if zoom_sel is not None:
            els = []
            for sel in zoom_sel:
                loc = self.page.locator(sel) if isinstance(sel, str) else sel
                els.append(loc.first.element_handle())
            rect = self.page.evaluate("els => window.__rk.box(els)", els)
        left = self.need[bid] - (self.now() - start)
        if left > 0:
            self.wait(left)
        end = self.now()
        self.privacy(bid)
        self.marks.append({"id": bid, "mulai": round(start, 3), "akhir": round(end, 3), "zoom": rect})
        print(f"  {bid:20s} {start:7.2f} -> {end:7.2f}  ({end - start:5.2f} dtk)", flush=True)


def demo(r: Rekaman, base: str, llm_on: bool) -> None:
    p = r.page
    p.goto(base + "#/antrean")
    p.wait_for_selector(".empty", timeout=30000)
    r.helpers()
    p.evaluate(f"window.__rk.zoom({r.zoom})")
    p.evaluate("document.getElementById('toasts').replaceChildren()")
    r.wait(1.0)
    r.flash()

    # ---------------- A. mulai, offline, status
    with r.beat("a_mulai"):
        r.wait(1.0)
        r.hl(".empty")
    with r.beat("a_pill"):
        r.hl("#top-pills .pill >> nth=-1")
    with r.beat("a_jaringan"):
        r.nav("Status sistem", "text=Integritas kode mesin")
        sec = p.locator("section[aria-label='Jaringan']")
        r.scroll(sec, offset=120)
        r.wait(0.3)
        r.hl(sec)
    with r.beat("a_model"):
        sec = p.locator("section[aria-label='Model lokal']")
        r.scroll(sec, offset=120)
        r.wait(0.3)
        r.hl(sec)
    with r.beat("a_mode"):
        sec = p.locator("section[aria-label='Mode analisis']")
        r.scroll(sec, offset=120)
        r.wait(0.3)
        r.hl(sec)

    # ---------------- B. data contoh dan antrean
    with r.beat("b_muat"):
        r.nav("Antrean kasus", ".empty")
        r.click(p.locator(".empty button", has_text="Muat data contoh"), pause=1.2)
        p.wait_for_selector("table.t tbody tr.click", timeout=30000)
        r.wait(0.5)
    with r.beat("b_antrean"):
        r.hl(".stats")
        r.wait(3.5)
        r.clear()
        r.hl("section[aria-label='Daftar kasus']")
    with r.beat("b_filter_injeksi"):
        r.click(p.locator("button.stat", has_text="Injeksi terdeteksi"), pause=1.0)
        r.clear()
        r.hl(p.locator("button.stat", has_text="Injeksi terdeteksi"))
        r.hl("section[aria-label='Daftar kasus'] table")

    # ---------------- C. kasus injeksi K-0004 (WS-KEU02)
    with r.beat("c_banner"):
        r.click(p.get_by_role("link", name="K-0004"), pause=1.0)
        p.wait_for_selector("#ringkasan-aturan", timeout=30000)
        r.helpers()
        r.clear()
        r.wait(0.8)
        r.hl(".banner.bad")
    flagged = p.locator(".inert.flagged").first
    row = p.locator("tr.sel").first
    label = p.locator(".inert-label").first
    with r.beat("c_dingin", zoom_sel=[row, label, flagged]):
        r.hl(flagged)
    with r.beat("c_inert"):
        r.hl(flagged)
    with r.beat("c_keputusan"):
        r.hl(p.locator("section[aria-label='Keputusan'] ol.reasons"))
    ai = p.locator("section.ai-panel")
    with r.beat("c_draf_mulai"):
        r.scroll(ai, offset=110)
        r.wait(0.4)
        r.hl(ai)
        r.wait(1.5)
        if llm_on:
            r.click(p.get_by_role("button", name="Buat draf AI"), pause=1.0)
    if llm_on:
        t = time.time()
        p.wait_for_selector("#draf-ai", timeout=300000)
        r.info["draf_detik_tunggu"] = round(time.time() - t, 1)
        r.info["draf_ai"] = p.inner_text("#draf-ai")
        r.wait(0.8)
        p.evaluate("document.getElementById('toasts').replaceChildren()")
        r.scroll(p.locator("section.ai-panel"), offset=70, ms=300)
        r.wait(0.5)
    with r.beat("c_draf_hasil", zoom_sel=["section.ai-panel"]):
        r.hl("section.ai-panel")

    # ---------------- D. uji usulan: isolasi DC01, detektor pola mati
    sim = p.locator("section[aria-label='Uji usulan terhadap policy']")
    with r.beat("d_usulan"):
        r.scroll(sim, offset=90)
        r.wait(0.5)
        r.click(p.get_by_role("button", name="isolasi DC01"), pause=1.0)
        r.clear()
        r.hl("#sim-target")
        r.wait(2.0)
        r.clear()
        det_label = p.locator("label.check", has=p.locator("#sim-det"))
        r.hl(det_label)
        r.wait(0.8)
        p.uncheck("#sim-det")
    r.click(p.get_by_role("button", name="Uji usulan"), pause=0.3)
    p.wait_for_selector("#sim-hasil", timeout=15000)
    r.info["sim_hasil"] = p.inner_text("#sim-hasil")
    r.scroll("#sim-hasil", offset=260, ms=300)
    r.wait(0.4)
    with r.beat("d_hasil", zoom_sel=["#sim-hasil"]):
        r.hl("#sim-hasil")

    # ---------------- E. setujui isolasi WS-OPS07 (K-0002)
    with r.beat("e_kasus"):
        r.nav("Antrean kasus", "table.t tbody tr.click")
        r.click(p.locator("button.stat", has_text="Perlu keputusan analis"), pause=0.8)
        r.click(p.get_by_role("link", name="K-0002"), pause=0.9)
        p.wait_for_selector("text=Setujui aksi", timeout=30000)
        r.helpers()
        r.clear()
        r.wait(0.6)
        r.hl(p.locator("section[aria-label='Keputusan']"))
    with r.beat("e_setujui"):
        sec = p.locator("section[aria-label='Tindakan analis']")
        r.scroll(sec, offset=110)
        r.click(p.get_by_role("button", name="Setujui aksi"), pause=1.0)
        r.clear()
        p.locator("#analis").click()
        p.locator("#analis").press_sequentially(ANALIS, delay=55)
        r.wait(0.4)
        p.locator("#catatan").click()
        p.locator("#catatan").press_sequentially(CATATAN, delay=28)
        r.wait(0.6)
        r.click(p.get_by_role("button", name="Catat ke jejak audit"), pause=0.9)
        p.wait_for_selector(".review-item", timeout=15000)
        r.wait(0.5)
    with r.beat("e_tercatat"):
        r.scroll(".review-item", offset=200, ms=500)
        r.hl(".review-item")

    # ---------------- F. jejak audit
    with r.beat("f_audit"):
        r.nav("Jejak audit", "#audit-status")
        r.hl("section.card table.t")
    with r.beat("f_verifikasi"):
        r.scroll(".page-head", offset=10, ms=600)
        r.click(p.get_by_role("button", name="Verifikasi integritas"), pause=0.9)
        p.wait_for_selector("#audit-status >> text=diverifikasi", timeout=15000)
        r.hl("#audit-status")
    r.click(p.get_by_role("button", name="Uji deteksi perubahan"), pause=0.3)
    p.wait_for_selector("#uji-perubahan >> text=Perubahan terdeteksi", timeout=15000)
    r.info["uji_perubahan"] = p.inner_text("#uji-perubahan")
    p.evaluate("document.getElementById('toasts').replaceChildren()")
    r.wait(0.4)
    with r.beat("f_ubah", zoom_sel=["#uji-perubahan section"]):
        r.hl("#uji-perubahan section")

    # ---------------- G. laporan CSIRT
    with r.beat("g_laporan"):
        r.nav("Laporan CSIRT", "#laporan h1")
        r.hl(p.locator(".page-head .actions"))
    with r.beat("g_gulir"):
        target = p.locator("#laporan :is(h2,h3)", has_text="Tindakan analis")
        if target.count() == 0:
            target = p.locator("#laporan :is(h2,h3)").nth(2)
        r.scroll(target, offset=120, ms=2600)
        r.wait(0.3)
        r.hl(target)

    # ---------------- H. jalur OT
    with r.beat("h_ot"):
        r.nav("Jalur OT", "#ringkasan-ot")
        r.hl("section[aria-label='Anomali tag']")
    with r.beat("h_hmi"):
        sec = p.locator("section[aria-label='Catatan HMI (teks bebas)']")
        r.scroll(sec, offset=140)
        r.hl(sec)
    r.scroll(".page-head", offset=10, ms=500)
    r.wait(0.3)
    with r.beat("h_keputusan", zoom_sel=["section[aria-label='Keputusan OT']"]):
        r.hl("section[aria-label='Keputusan OT']")

    # ---------------- I. status: uji kinerja dan lisensi
    with r.beat("i_kinerja"):
        r.nav("Status sistem", "text=Integritas kode mesin")
        r.click(p.get_by_role("button", name="Uji kinerja di perangkat ini"), pause=1.0)
        p.wait_for_selector("#hasil-kinerja .stats", timeout=30000)
        r.clear()
        r.hl("#hasil-kinerja")
    with r.beat("i_lisensi"):
        sec = p.locator("section[aria-label='Lisensi dan asal-usul']")
        r.scroll(sec, offset=110)
        r.hl(sec)

    # ---------------- J. impor log (XML wevtutil; .evtx dikonversi lokal)
    with r.beat("j_impor"):
        r.nav("Impor log", "#dropzone")
        r.hl("section[aria-label='Ekspor log dari Windows']")
    with r.beat("j_hasil"):
        p.set_input_files("#file-input", [str(SAMPEL_XML)])
        r.wait(1.0)
        r.click(p.get_by_role("button", name="Impor dan triase"), pause=1.0)
        p.wait_for_selector("text=Hasil impor", timeout=30000)
        r.wait(0.4)
        res = p.locator("section[aria-label='Hasil impor']")
        r.scroll(res, offset=110)
        r.hl(res)
    r.wait(0.5)
    r.flash()
    missing = set(r.need) - {m["id"] for m in r.marks}
    if missing:
        r.warn.append(f"potongan di alur.py yang tidak terekam: {sorted(missing)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=str(EXE))
    ap.add_argument("--model", default=str(MODEL), help="berkas GGUF; kosongkan (--model '') untuk mode aturan")
    ap.add_argument("--data-dir", default="", help="folder data baru (bawaan %%TEMP%%\\perisai-rekam-<waktu>)")
    ap.add_argument("--out", default=str(HERE / "rekaman"))
    ap.add_argument("--channel", default="msedge")
    ap.add_argument("--zoom", type=float, default=1.25)
    ap.add_argument("--simpan-data", action="store_true", help="jangan hapus folder data sesudah merekam")
    args = ap.parse_args()

    stamp = time.strftime("%Y%m%d-%H%M%S")
    data = Path(args.data_dir) if args.data_dir else Path(os.environ.get("TEMP", "/tmp")) / f"perisai-rekam-{stamp}"
    if data.exists() and any(data.iterdir()):
        raise SystemExit(f"folder data harus baru dan kosong: {data}")
    (data / "models").mkdir(parents=True, exist_ok=True)
    llm_on = bool(args.model)
    if llm_on:
        src = Path(args.model)
        dst = data / "models" / src.name
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / "_mentah"
    shutil.rmtree(tmp, ignore_errors=True)

    proc, base = start_app(Path(args.exe), data)
    print(f"aplikasi: {base}  data: {data}", flush=True)
    try:
        wait_llm(base, llm_on)
        need = alur.kebutuhan_rekam()
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel=args.channel, headless=True)
            ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1, locale="id-ID",
                                      record_video_dir=str(tmp), record_video_size={"width": 1920, "height": 1080})
            page = ctx.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
            page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
            outbound: list[str] = []
            page.on("request", lambda q: outbound.append(q.url) if not q.url.startswith(base) and not q.url.startswith("data:") else None)
            r = Rekaman(page, need, args.zoom)
            demo(r, base, llm_on)
            video = page.video
            ctx.close()
            browser.close()
            src = Path(video.path())
        dst = out / "rekaman_demo.webm"
        shutil.move(str(src), dst)
        shutil.rmtree(tmp, ignore_errors=True)
        meta = {"video": dst.name, "dibuat": stamp, "zoom": args.zoom, "llm": llm_on, "sinkron": r.sync,
                "potongan": r.marks, "info": r.info, "peringatan": r.warn + errors,
                "permintaan_ke_host_lain": outbound}
        (out / "marks.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"rekaman: {dst} ({dst.stat().st_size / 1e6:.1f} MB)")
        print("peringatan:", meta["peringatan"] or "tidak ada")
        print("permintaan ke host lain:", len(outbound))
    finally:
        try:
            http(base, "POST", "/api/keluar", timeout=5)
        except Exception:
            pass
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        if not args.simpan_data:
            shutil.rmtree(data, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
