// Kontrol demo (peran Admin di demo publik): alur terpandu, reset sesi, matriks hak akses.
import { api } from "../api.js";
import { btn, card, clear, h, icon, setBusy } from "../dom.js";

const ALUR = [
  ["Antrean kasus", "10 kasus dari 22 event sintetis; 3 bertanda injeksi.", "#/antrean", "inbox"],
  ["Kasus injeksi K-0004", "Kalimat injeksi di CommandLine ditandai, kasus dieskalasi.", "#/kasus/K-0004", "triangle-alert"],
  ["Uji usulan isolasi DC01", "Di kartu Uji usulan: matikan detektor pola, policy tetap menolak.", "#/kasus/K-0004", "flask-conical"],
  ["Uji injeksi bebas", "Tulis injeksi sendiri; lihat hasil dengan dan tanpa detektor.", "#/uji/jalan", "crosshair"],
  ["Persetujuan analis K-0002", "Masuk sebagai Analis untuk menyetujui isolasi WS-OPS07.", "#/kasus/K-0002", "user-check"],
  ["Jejak audit", "Verifikasi rantai, lalu uji deteksi perubahan.", "#/audit", "link-2"],
  ["Laporan CSIRT", "Lengkapi data pelaporan BSSN, lalu cetak.", "#/laporan", "file-text"],
];
const IZIN = [["lihat", "Melihat antrean, kasus, audit, laporan"], ["uji", "Menguji usulan dan injeksi"], ["tinjau", "Menyetujui / menolak / menutup kasus"],
  ["lapor", "Mengisi data pelaporan BSSN"], ["demo", "Kontrol demo"]];

export async function render(page, _params, ctx) {
  const peran = await api.get("/api/peran");
  clear(page);
  page.append(h("div", { class: "page-head" },
    h("div", { class: "titles" }, h("div", { class: "eyebrow" }, "Admin"), h("h1", null, "Kontrol demo"),
      h("div", { class: "sub" }, "Jalankan alur demonstrasi langkah demi langkah, atur ulang sesi, dan lihat pembagian hak akses."))));
  if (peran.wajib && !(peran.masuk && peran.masuk.izin.includes("demo"))) {
    page.append(card("Hanya untuk Admin", { icon: "lock" }, h("p", null, "Masuk sebagai Admin untuk membuka kontrol demo."),
      h("a", { class: "btn primary", href: "#/masuk" }, icon("user"), "Ganti peran")));
    return;
  }
  const reset = btn("Atur ulang sesi demo", { icon: "refresh-cw", cls: "danger" });
  reset.addEventListener("click", async () => {
    if (!window.confirm("Mulai sesi baru dengan 10 kasus contoh? Tinjauan dan isian laporan di sesi ini tidak dibawa.")) return;
    setBusy(reset, true, "Mengatur ulang");
    try { await api.post("/api/sesi/baru"); ctx.toast("Sesi demo diatur ulang. Peran Anda tetap."); ctx.refreshBadge(); render(page, _params, ctx); }
    catch (e) { ctx.toast(e.message, "bad"); setBusy(reset, false); }
  });
  const steps = h("ol", { class: "guide" }, ALUR.map(([t, d, href, ic], i) => h("li", null,
    h("span", { class: "guide-n" }, String(i + 1)),
    h("div", { class: "guide-t" }, h("b", null, t), h("span", { class: "small muted" }, d)),
    h("a", { class: "btn sm", href }, icon(ic), "Buka"))));
  const roles = peran.peran;
  const matrix = h("table", { class: "t" },
    h("thead", null, h("tr", null, h("th", null, "Hak"), ...roles.map((r) => h("th", { class: "num" }, r.label)))),
    h("tbody", null, IZIN.map(([k, label]) => h("tr", null, h("td", null, label),
      ...roles.map((r) => h("td", { class: "num" }, r.izin.includes(k)
        ? h("span", { class: "chip st-ok", title: "boleh" }, icon("check"), "boleh")
        : h("span", { class: "chip st-esc", title: "tidak" }, "tidak")))))));
  page.append(h("div", { class: "grid2" },
    card("Alur demonstrasi", { icon: "list-checks" }, steps),
    card("Sesi", { icon: "database" }, h("p", { class: "small muted" }, "Tiap pengunjung punya sesi sendiri lewat cookie. Mengatur ulang hanya memengaruhi sesi Anda."), reset)),
    card("Pembagian hak akses", { icon: "lock", flush: true }, h("div", { class: "tbl-wrap" }, matrix),
      h("p", { class: "small muted pad" }, "Admin tidak bisa menyetujui aksi, dan analis tidak bisa mengubah sistem. Batas ini ditegakkan di server, bukan hanya disembunyikan di tampilan.")));
}
