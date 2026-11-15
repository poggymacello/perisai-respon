// Laporan CSIRT (Markdown dari perisai.laporan), tampilan + unduh + cetak.
import { api, download } from "../api.js";
import { banner, btn, card, clear, h, icon, setBusy } from "../dom.js";

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
  if (ctx.can("lapor")) page.append(pelaporanForm(d.pelaporan || {}, ctx, () => render(page, _params, ctx)));
  else page.append(banner("info", "lock", h("b", null, "Data pelaporan diisi Analis. "), "Masuk sebagai Analis untuk melengkapi kontak pelapor dan dampak. ",
    h("a", { href: "#/masuk" }, "Ganti peran")));
  page.append(paper);
}

// Isian Peraturan BSSN 1/2024 Pasal 15 ayat 4 (kontak pelapor dan dampak). Disimpan per sesi, masuk ke laporan.
function pelaporanForm(p, ctx, rerender) {
  const f = (name, label, ph, max) => h("label", { class: "field" }, h("span", null, label),
    h("input", { class: "input", name, value: p[name] || "", placeholder: ph, maxlength: String(max) }));
  const dampak = h("textarea", { class: "input", name: "dampak", rows: "3", maxlength: "2000",
    placeholder: "mis. 1 workstation keuangan tidak bisa dipakai ±2 jam; tidak ada data keluar yang terkonfirmasi", value: p.dampak || "" });
  const filled = ["pelapor_nama", "pelapor_kontak", "dampak"].every((k) => (p[k] || "").trim());
  const save = btn("Simpan ke laporan", { icon: "check", cls: "primary", type: "submit" });
  const form = h("form", { class: "no-print", onsubmit: async (e) => {
    e.preventDefault();
    const body = Object.fromEntries(new FormData(form).entries());
    setBusy(save, true, "Menyimpan");
    try { await api.post("/api/laporan/pelaporan", body); ctx.toast("Data pelaporan disimpan ke laporan."); rerender(); }
    catch (err) { ctx.toast(err.message, "bad"); setBusy(save, false); }
  } },
    h("div", { class: "grid-form" }, f("pelapor_nama", "Nama pelapor", "mis. Lettu Inf. A. Pratama", 120),
      f("pelapor_satuan", "Satuan / unit kerja", "mis. Posko Siber Yon-X", 160)),
    f("pelapor_kontak", "Kontak pelapor", "telepon atau surel dinas", 160),
    h("label", { class: "field" }, h("span", null, "Dampak insiden"), dampak),
    h("div", { class: "actions" }, save, h("span", { class: "small muted" }, "Kolom kosong tercetak sebagai \"belum diisi\".")));
  return card("Data pelaporan (BSSN 1/2024 Pasal 15 ayat 4)", { icon: "user-check", cls: "no-print",
    right: filled ? h("span", { class: "chip st-ok" }, icon("check"), "Lengkap") : h("span", { class: "chip chip-warn-soft" }, "Belum lengkap") }, form);
}
