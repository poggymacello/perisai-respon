// Kontrol demo (peran Admin di demo publik), mengikuti pola Demo control PRAXIS:
// kirim log serangan, pindah akun, lab skenario, skrip demo, hak akses, dan atur ulang.
// Semua kasus dibuat dari log sintetis yang diproses parser + mesin yang sama dengan impor biasa.
import { api } from "../api.js";
import { card, clear, h, icon } from "../dom.js";

const UTAMA = [
  { id: "injeksi-inggris", judul: "Injeksi ke AI lewat log", isi: "Demo utama. Perintah 'isolasi DC01' diselipkan di CommandLine.", utama: true },
  { id: "dump-kredensial", judul: "Dump kredensial LSASS", isi: "Harapan: isolasi sah diusulkan dan menunggu Analis." },
  { id: "serangan-dc", judul: "Serangan ke controller domain", isi: "Harapan: aset terlindungi, tidak diisolasi otomatis." },
];
const HARAPAN = {
  "injeksi-inggris": "Injeksi terdeteksi, dieskalasi", "injeksi-indonesia": "Injeksi terdeteksi, dieskalasi",
  "injeksi-base64": "Disandikan, tetap terdeteksi", "klaim-izin": "Klaim izin ditandai", "karakter-tersembunyi": "Dinormalisasi, terdeteksi",
  "dump-kredensial": "Menunggu persetujuan Analis", "serangan-dc": "Aset terlindungi, dieskalasi",
};
const SKRIP = [
  { babak: "Babak 1: Ancaman", langkah: [
    "Halaman depan: di konsol serangan, ketik injeksi sendiri lalu matikan detektor pola. Putusan tetap DITOLAK.",
    "Sebagai Kapten Dimas (Admin), kirim 'Injeksi ke AI lewat log'. Kasusnya terbuka: CommandLine ditandai, kasus dieskalasi.",
    "Di kartu Uji usulan, coba 'isolasi DC01' dengan detektor dimatikan: policy menolak karena DC01 aset terlindungi."] },
  { babak: "Babak 2: Keputusan", langkah: [
    "Kirim 'Dump kredensial LSASS'. Sistem mengusulkan isolasi WS-LAB07 dan menunggu keputusan.",
    "Sebagai Admin, coba menyetujui: tidak bisa. Admin tidak boleh menyetujui aksi.",
    "Pindah ke Lettu Andi (Analis), setujui dengan catatan. Persetujuan masuk rantai audit, tidak dieksekusi ke jaringan."] },
  { babak: "Babak 3: Bukti", langkah: [
    "Jejak audit: Verifikasi integritas, lalu Uji deteksi perubahan. Salinan yang diubah gagal diverifikasi.",
    "Laporan CSIRT: sebagai Analis, isi kontak pelapor dan dampak (BSSN 1/2024 Pasal 15), lalu cetak.",
    "Kalau ditanya: Jalur OT (PLC tidak pernah diputus), lab skenario base64 dan karakter tersembunyi, aplikasi desktop offline."] },
];
const IZIN = [["lihat", "Melihat antrean, kasus, audit, laporan"], ["uji", "Menguji usulan dan injeksi"], ["tinjau", "Menyetujui, menolak, menutup kasus"],
  ["lapor", "Mengisi data pelaporan BSSN"], ["demo", "Kontrol demo"]];

function initials(n) { return n.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join(""); }

function scenarioButton({ judul, isi, utama }, onClick) {
  return h("button", { type: "button", class: `scn ${utama ? "scn-main" : ""}`, onclick: onClick },
    icon("play"), h("span", { class: "scn-t" }, h("b", null, judul), h("span", null, isi)), icon("arrow-right"));
}

function disclosure(title, summary, open, ...body) {
  return h("details", { class: "disc card", open: open || null },
    h("summary", null, h("span", { class: "disc-t" }, h("b", null, title), h("span", null, summary)), icon("chevron-down")),
    h("div", { class: "disc-b" }, ...body));
}

export async function render(page, _params, ctx) {
  const [peran, lab] = await Promise.all([api.get("/api/peran"), api.get("/api/demo/skenario").catch(() => ({ skenario: [] }))]);
  clear(page);
  page.append(h("div", { class: "page-head" },
    h("div", { class: "titles" },
      h("h1", { class: "with-chip" }, "Kontrol demo", h("span", { class: "sim" }, "Simulator")),
      h("div", { class: "sub" }, "Memainkan peran penyerang dan sumber log, supaya alur lengkap bisa ditunjukkan dalam beberapa menit."))));
  if (peran.wajib && !(peran.masuk && peran.masuk.izin.includes("demo"))) {
    page.append(card("Untuk Analis dan Admin", { icon: "lock" },
      h("p", null, "Halaman ini untuk yang menjalankan demo: Lettu Andi (Analis) dan Kapten Dimas (Admin). Operator bekerja dari antrean kasus."),
      h("div", { class: "actions" }, h("a", { class: "btn", href: "#/antrean" }, "Kembali ke antrean"), h("a", { class: "btn primary", href: "#/masuk" }, icon("user"), "Ganti akun"))));
    return;
  }

  const result = h("div", { "aria-live": "polite" });
  let busy = false;
  async function run(fn) {
    if (busy) return;
    busy = true; page.classList.add("is-busy");
    try { const r = await fn(); if (r) clear(result).append(r); }
    catch (e) { clear(result).append(h("div", { class: "banner bad" }, icon("triangle-alert"), h("div", null, e.message || String(e)))); }
    finally { busy = false; page.classList.remove("is-busy"); }
  }
  const send = (id) => run(async () => {
    const r = await api.post(`/api/demo/skenario/${id}`);
    ctx.refreshBadge();
    const k = r.kasus[0];
    if (!k) return h("div", { class: "banner warn" }, icon("info"), h("div", null, "Log terkirim, tetapi tidak ada aturan yang terpicu."));
    ctx.toast(`${k.id} dibuka dari log sintetis ${k.host}.`);
    ctx.go(`#/kasus/${k.id}`);
    return null;
  });
  const switchTo = (a) => run(async () => {
    const m = await api.post("/api/masuk", { email: a.email, sandi: peran.sandi_demo });
    await ctx.refreshPeran();
    ctx.toast(`Sekarang masuk sebagai ${m.nama} (${m.label}).`);
    ctx.go(m.izin.includes("demo") ? "#/demo" : "#/antrean");
    return null;
  });

  // kartu atas: kirim log + pindah akun
  const sendCard = card("Kirim log serangan", { icon: "send" },
    h("p", { class: "hint card-hint" }, "Ke host fiktif WS-LAB*.lab.batalyon.lab. Kasus baru langsung dibuka."),
    h("div", { class: "scn-list" }, UTAMA.map((s) => scenarioButton(s, () => send(s.id)))));
  const me = peran.masuk || {};
  const switchCard = card("Pindah akun", { icon: "user" },
    h("p", { class: "hint card-hint" }, "Seperti berganti orang di posko. Setiap masuk tercatat di jejak audit."),
    h("ul", { class: "acc-list" }, (peran.akun || []).map((a) => {
      const self = a.email === me.email;
      return h("li", null, h("button", { type: "button", class: "acc acc-sm", disabled: self || null, onclick: () => switchTo(a) },
        h("span", { class: "acc-av" }, initials(a.nama)),
        h("span", { class: "acc-t" }, h("span", { class: "acc-name" }, a.nama, self ? h("span", { class: "acc-you" }, "Anda") : null),
          h("span", { class: "acc-sub" }, `${a.label}: ${a.tugas}`)),
        self ? null : icon("arrow-right")));
    })));

  // lab skenario dengan filter grup
  const groups = [{ id: "semua", label: "Semua" }, ...[...new Map(lab.skenario.map((s) => [s.grup, s.grup_label])).entries()].map(([id, label]) => ({ id, label }))];
  let group = "semua";
  const chips = h("div", { class: "chips", role: "group", "aria-label": "Saring skenario" });
  const grid = h("div", { class: "lab-grid" });
  function drawLab() {
    clear(chips).append(...groups.map((g) => {
      const n = g.id === "semua" ? lab.skenario.length : lab.skenario.filter((s) => s.grup === g.id).length;
      return h("button", { type: "button", class: "chip-btn", "aria-pressed": String(group === g.id), onclick: () => { group = g.id; drawLab(); } },
        g.label, h("span", null, String(n)));
    }));
    clear(grid).append(...lab.skenario.filter((s) => group === "semua" || s.grup === group).map((s) =>
      h("button", { type: "button", class: "lab-item", onclick: () => send(s.id) },
        h("span", { class: "lab-h" }, h("b", null, s.judul), h("span", { class: "tag" }, s.grup_label),
          h("span", { class: `pill-s ${s.grup === "serangan" ? "wait" : "bad"}` }, HARAPAN[s.id] || "")),
        h("span", { class: "lab-d" }, s.ringkas))));
  }
  drawLab();

  const script = h("div", { class: "script" }, SKRIP.map((s) => h("div", null, h("h3", null, s.babak),
    h("ol", null, s.langkah.map((t, i) => h("li", null, h("span", { class: "n" }, String(i + 1)), h("span", null, t)))))));

  const roles = peran.peran;
  const matrix = h("table", { class: "t" },
    h("thead", null, h("tr", null, h("th", null, "Hak"), ...roles.map((r) => h("th", { class: "num" }, r.label)))),
    h("tbody", null, IZIN.map(([k, label]) => h("tr", null, h("td", null, label),
      ...roles.map((r) => h("td", { class: "num" }, r.izin.includes(k)
        ? h("span", { class: "chip st-ok" }, icon("check"), "boleh") : h("span", { class: "chip st-esc" }, "tidak")))))));

  const resetBtn = h("button", { type: "button", class: "btn danger", onclick: () => {
    if (!window.confirm("Atur ulang data demo? Kasus kiriman lab, tinjauan, dan isian laporan di sesi ini tidak dibawa.")) return;
    run(async () => { await api.post("/api/sesi/baru"); ctx.refreshBadge(); ctx.toast("Data demo diatur ulang. Akun Anda tetap masuk.");
      return h("div", { class: "banner ok" }, icon("circle-check"), h("div", null, "Kembali ke 10 kasus contoh awal.")); });
  } }, icon("rotate-ccw"), "Atur ulang data demo");

  page.append(result,
    h("div", { class: "grid-2eq" }, sendCard, switchCard),
    disclosure("Lab skenario", `${lab.skenario.length} log serangan sintetis. Masing-masing membuat kasus baru di sesi Anda.`, true, chips, grid),
    disclosure("Skrip demo", "Urutan yang dipakai saat presentasi, dengan siapa mengerjakan apa.", false, script),
    disclosure("Pembagian hak akses", "Pemisahan tugas yang ditegakkan server.", false, h("div", { class: "tbl-wrap" }, matrix),
      h("p", { class: "small muted" }, "Admin tidak bisa menyetujui aksi, dan analis tidak bisa mengubah sistem. Ini dicek di server pada setiap permintaan, bukan hanya disembunyikan di tampilan.")),
    h("div", { class: "card row-card" },
      h("div", null, h("h2", null, "Atur ulang demo"), h("p", { class: "small muted" }, "Kembali ke titik awal: 10 kasus contoh. Kasus kiriman lab dihapus dari sesi ini.")),
      resetBtn));
}
