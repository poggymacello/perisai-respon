"""Mengendarai aplikasi yang sedang berjalan dengan browser headless (Playwright + Edge/Chrome terpasang),
memeriksa alur utama, mencatat galat konsol, dan menyimpan tangkapan layar 1920x1080.

    app\\.venv\\Scripts\\python -I app\\tools\\shoot.py --data-dir <folder data aplikasi> --out app\\screenshots [--llm]

Port dibaca dari <data-dir>\\instance.json (ditulis PERISAI-RESPON.exe / run_desktop.py --headless).
--llm: buat draf AI untuk kasus injeksi (butuh mode LLM aktif, ±30-60 dtk).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--llm", action="store_true")
    ap.add_argument("--channel", default="msedge")
    args = ap.parse_args()
    port = json.loads((Path(args.data_dir) / "instance.json").read_text(encoding="utf-8"))["port"]
    base = f"http://127.0.0.1:{port}/"
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    checks: list[str] = []

    def check(cond: bool, what: str) -> None:
        checks.append(("OK   " if cond else "GAGAL ") + what)
        if not cond:
            errors.append("cek gagal: " + what)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1, locale="id-ID")
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.on("requestfailed", lambda r: errors.append(f"requestfailed: {r.url}") if "127.0.0.1" in r.url else None)
        outbound: list[str] = []
        page.on("request", lambda r: outbound.append(r.url) if not r.url.startswith(base) and not r.url.startswith("data:") else None)

        def shot(name: str, full: bool = False) -> None:
            page.evaluate("document.getElementById('toasts').replaceChildren()")  # notifikasi sementara tidak ikut difoto
            page.wait_for_timeout(250)
            page.screenshot(path=str(out / name), full_page=full)

        def go(hash_: str, sel: str) -> None:
            page.goto(base + hash_)
            page.wait_for_selector(sel, timeout=20000)

        # 1. antrean kosong -> muat data contoh
        go("#/antrean", "h1")
        if page.locator(".empty").count():
            page.get_by_role("button", name="Muat data contoh").first.click()
            page.wait_for_selector("table.t tbody tr.click", timeout=20000)
        rows = page.locator("table.t tbody tr.click").count()
        check(rows >= 10, f"antrean berisi {rows} kasus")

        # 2. setujui satu aksi isolasi (WS-OPS07) lewat UI
        page.get_by_role("link", name="K-0002").click()
        page.wait_for_selector("text=Setujui aksi")
        page.get_by_role("button", name="Setujui aksi").click()
        page.fill("#analis", "Lettu Inf. A. Pratama")
        page.fill("#catatan", "Proses svc-update.exe dari C:\\Users\\Public mengakses LSASS; isolasi disetujui menunggu verifikasi operator.")
        page.get_by_role("button", name="Catat ke jejak audit").click()
        page.wait_for_selector("text=Disetujui analis", timeout=10000)
        check(page.locator(".review-item").count() >= 1, "persetujuan tercatat di riwayat")
        go("#/antrean", "table.t tbody tr.click")
        shot("01_antrean.png")

        # 3. detail kasus injeksi (WS-KEU02, instruksi "isolate_host DC01")
        go("#/kasus/K-0004", "#ringkasan-aturan")
        check(page.locator(".banner.bad").count() >= 1, "banner injeksi tampil di K-0004")
        check(page.locator(".inert.flagged").count() >= 1, "field yang ditandai tampil inert")
        al = page.inner_text("#alasan-policy")
        check(al.startswith("Keputusan diambil dari aturan"), "alasan pertama dipetakan (bukan 'LLM dimatikan')")
        check("teks asli mesin" in al, "teks asli mesin tetap terlihat")
        if args.llm:
            btn = page.get_by_role("button", name="Buat draf AI")
            if btn.is_enabled():
                btn.click()
                page.wait_for_selector("#draf-ai", timeout=240000)
                check(True, "draf AI selesai untuk K-0004")
            else:
                check(False, "tombol Buat draf AI aktif (mode LLM)")
        shot("02_detail_injeksi.png")

        # 4. uji usulan penyerang terhadap policy: isolasi DC01, detektor pola dimatikan
        page.get_by_role("button", name="isolasi DC01").click()
        page.uncheck("#sim-det")
        page.get_by_role("button", name="Uji usulan").click()
        page.wait_for_selector("#sim-hasil", timeout=10000)
        txt = page.inner_text("#sim-hasil")
        check("BLOCK" in txt and "terlindungi" in txt, "policy menolak isolasi DC01 walau detektor dimatikan")
        page.locator("#sim-hasil").scroll_into_view_if_needed()
        page.evaluate("document.getElementById('sim-hasil').closest('section').scrollIntoView({block: 'center'})")
        shot("03_policy_menolak.png")

        # 5. audit: verifikasi + uji perubahan
        go("#/audit", "#audit-status")
        page.get_by_role("button", name="Verifikasi integritas").click()
        page.wait_for_selector("#audit-status >> text=diverifikasi", timeout=10000)
        page.get_by_role("button", name="Uji deteksi perubahan").click()
        page.wait_for_selector("#uji-perubahan >> text=Perubahan terdeteksi", timeout=10000)
        check("Rantai utuh" in page.inner_text("#audit-status"), "rantai audit utuh")
        shot("04_audit.png")

        # 6. laporan
        go("#/laporan", "#laporan h1")
        check("Laporan Insiden PERISAI-RESPON" in page.inner_text("#laporan"), "laporan CSIRT tampil")
        check("Tindakan analis" in page.inner_text("#laporan"), "laporan memuat tindakan analis")
        shot("05_laporan.png")

        # 7. OT
        go("#/ot", "#ringkasan-ot")
        check("DITOLAK" in page.inner_text("main"), "usulan putus PLC ditolak")
        shot("06_ot.png")

        # 8. status + uji kinerja
        go("#/status", "text=Integritas kode mesin")
        page.get_by_role("button", name="Uji kinerja di perangkat ini").click()
        page.wait_for_selector("#hasil-kinerja .stats", timeout=20000)
        body = page.inner_text("main")
        check("POGGY" not in body and "Users\\" not in body, "tidak ada path pribadi di layar status")
        shot("07_status.png")

        # 9. impor (tidak dipakai di paket screenshot utama, untuk pemeriksaan)
        go("#/impor", "#dropzone")
        page.set_input_files("#file-input", [str(Path(__file__).resolve().parents[1] / "perisai_app" / "sampel" / "contoh_wevtutil.xml")])
        page.get_by_role("button", name="Impor dan triase").click()
        page.wait_for_selector("text=Hasil impor", timeout=20000)
        check(True, "unggah berkas lewat halaman Impor")
        shot("08_impor.png")

        for name in ("01_antrean.png", "02_detail_injeksi.png", "03_policy_menolak.png", "04_audit.png", "05_laporan.png", "06_ot.png", "07_status.png"):
            check((out / name).stat().st_size > 20000, f"{name} tersimpan")
        check(not outbound, f"tidak ada permintaan ke host lain ({len(outbound)})")
        browser.close()

    print("\n".join(checks))
    if errors:
        print("\nGALAT:")
        print("\n".join(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
