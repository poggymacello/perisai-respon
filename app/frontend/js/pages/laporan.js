// Laporan CSIRT (Markdown dari perisai.laporan), tampilan + unduh + cetak.
import { api, download } from "../api.js";
import { banner, btn, clear, h, icon, setBusy } from "../dom.js";

export async function render(page, _params, ctx) {
  let d;
  try {
    d = await api.get("/api/laporan");
  } catch (e) {
    clear(page);
    page.append(h("div", { class: "page-head" }, h("div", { class: "titles" }, h("h1", null, "Laporan CSIRT"))));
    if (e.status === 409) {
      page.append(h("div", { class: "card" }, h("div", { class: "empty" }, icon("file-text", "xl"), h("h2", null, "Belum ada yang dilaporkan"),
        h("p", null, "Laporan dibuat dari kasus di sesi ini. Impor log atau muat data contoh dulu."),
        h("div", { class: "actions" }, h("a", { class: "btn primary", href: "#/impor" }, icon("upload"), "Impor log")))));
      return;
    }
    throw e;
  }
  clear(page);
  const paper = h("article", { class: "paper", id: "laporan" });
  paper.innerHTML = d.html; // HTML dibuat server dari Markdown yang SUDAH di-escape (perisai_app/reportfmt.py)
  const dl = (fmt) => async () => {
    try { const m = await download(`/api/laporan/unduh?format=${fmt}`, `${d.nama}.${fmt}`); if (m) ctx.toast(m); } catch (e) { ctx.toast(e.message, "bad"); }
  };
  const refresh = btn("Buat ulang", { icon: "refresh-cw" });
  refresh.addEventListener("click", async () => { setBusy(refresh, true, "Membuat"); await render(page, _params, ctx); });
  page.append(h("div", { class: "page-head" },
    h("div", { class: "titles" }, h("h1", null, "Laporan CSIRT"),
      h("div", { class: "sub" }, "Dibuat dari kasus, keputusan, dan jejak audit sesi ini. Teks bebas log tidak disalin ke laporan.")),
    h("div", { class: "actions" }, refresh,
      btn("Unduh Markdown", { icon: "file-down", onclick: dl("md") }),
      btn("Unduh HTML", { icon: "file-down", onclick: dl("html") }),
      btn("Cetak / simpan PDF", { icon: "printer", cls: "primary", onclick: () => window.print() }))));
  if (ctx.status && ctx.status.mode === "demo") page.append(banner("warn", "info", "Laporan dari data contoh sintetis."));
  page.append(paper);
}
