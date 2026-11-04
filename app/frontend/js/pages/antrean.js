// Beranda: antrean kasus (gaya incident queue).
import { api } from "../api.js";
import { banner, btn, clear, fmtNum, fmtTime, h, icon, setBusy } from "../dom.js";
import { actionText, reviewChip, sevChip, statusChip, warnChips } from "../labels.js";

const state = { q: "", sev: "", st: "", kat: "", tile: "", sort: "waktu", dir: -1 };

export async function loadSample(ctx, b) {
  if (b) setBusy(b, true, "Memuat data contoh");
  try {
    const r = await api.post("/api/sampel");
    ctx.toast(`Data contoh dimuat: ${r.n_event} event, ${r.n_kasus} kasus, ${r.n_kelompok_tanpa_temuan} kelompok tanpa temuan.`);
    ctx.refreshBadge();
    ctx.refreshStatus();
    return r;
  } catch (e) {
    ctx.toast(e.message, "bad");
    throw e;
  } finally {
    if (b) setBusy(b, false);
  }
}

function emptyState(ctx, rerender) {
  const st = ctx.status || {};
  const canUpload = !st.kemampuan || st.kemampuan.unggah;
  const sampleBtn = btn("Muat data contoh", { icon: "database", cls: canUpload ? "" : "primary" });
  sampleBtn.addEventListener("click", async () => { await loadSample(ctx, sampleBtn); rerender(); });
  return h("div", { class: "card" }, h("div", { class: "empty" },
    icon("inbox", "xl"),
    h("h2", null, "Belum ada kasus di sesi ini"),
    h("p", null, "Impor ekspor log Windows (XML wevtutil, JSON Winlogbeat, atau .evtx) atau muat data contoh sintetis. ",
      "Semua pemrosesan berjalan di perangkat ini."),
    h("div", { class: "actions" },
      canUpload ? h("a", { class: "btn primary", href: "#/impor" }, icon("upload"), "Impor log") : null,
      sampleBtn)));
}

function sortRows(rows) {
  const k = state.sort, d = state.dir;
  const val = (r) => k === "severity" ? r.severity_skor : k === "host" ? r.host : k === "id" ? r.id : (r.waktu || "");
  return rows.slice().sort((a, b) => (val(a) > val(b) ? 1 : val(a) < val(b) ? -1 : 0) * d);
}

function match(r) {
  if (state.q) {
    const q = state.q.toLowerCase();
    const hay = [r.id, r.host, r.kategori, r.kategori_id, r.attack.id, r.attack.nama, ...r.aturan, ...r.peringatan].join(" ").toLowerCase();
    if (!hay.includes(q)) return false;
  }
  if (state.sev && r.severity !== state.sev) return false;
  if (state.st && r.status_mesin !== state.st) return false;
  if (state.kat && r.kategori !== state.kat) return false;
  if (state.tile === "menunggu" && !(r.status_mesin === "MENUNGGU_PERSETUJUAN" && !r.status_tinjauan)) return false;
  if (state.tile === "dieskalasi" && r.status_mesin !== "DIESKALASI") return false;
  if (state.tile === "injeksi" && !r.peringatan.includes("INJEKSI_TERDETEKSI")) return false;
  if (state.tile === "tinggi" && r.severity !== "tinggi") return false;
  if (state.tile === "ditinjau" && !r.status_tinjauan) return false;
  return true;
}

export async function render(page, _params, ctx) {
  const data = await api.get("/api/kasus");
  const rerender = () => render(page, _params, ctx);
  clear(page);
  const imp = data.impor || [];
  const nEmpty = imp.reduce((a, i) => a + i.n_kelompok_tanpa_temuan, 0);
  const nFiles = new Set(imp.flatMap((i) => i.berkas.map((b) => b.nama))).size;
  const canUpload = !ctx.status || ctx.status.kemampuan.unggah;
  const sampleBtn = btn("Muat data contoh", { icon: "database" });
  sampleBtn.addEventListener("click", async () => { await loadSample(ctx, sampleBtn); rerender(); });
  page.append(h("div", { class: "page-head" },
    h("div", { class: "titles" }, h("h1", null, "Antrean kasus"),
      h("div", { class: "sub" }, data.kasus.length
        ? `${fmtNum(data.kasus.length)} kasus dari ${fmtNum(nFiles)} berkas log · sesi ${data.sesi}`
        : `Sesi ${data.sesi}`)),
    h("div", { class: "actions" },
      canUpload ? h("a", { class: "btn primary", href: "#/impor" }, icon("upload"), "Impor log") : null,
      data.kasus.length ? null : sampleBtn)));
  if (ctx.status && ctx.status.mode === "demo") {
    page.append(banner("warn", "info", h("b", null, "Demo publik. "),
      "Kasus di bawah dibuat dari log contoh sintetis (host fiktif *.batalyon.lab). Unggah log dimatikan di server publik; ",
      "unduh aplikasi desktop untuk memeriksa log sendiri secara offline."));
  }
  if (!data.kasus.length) {
    page.append(emptyState(ctx, rerender));
    return;
  }

  const c = data.hitung;
  const tiles = [["", "Total kasus", c.total], ["menunggu", "Perlu keputusan analis", c.menunggu], ["dieskalasi", "Dieskalasi ke analis", c.dieskalasi],
    ["injeksi", "Injeksi terdeteksi", c.injeksi, true], ["tinggi", "Severity tinggi", c.tinggi], ["ditinjau", "Sudah ditinjau analis", c.ditinjau]];
  const statsEl = h("div", { class: "stats", role: "group", "aria-label": "Ringkasan antrean" });
  page.append(statsEl);

  const body = h("tbody");
  const countEl = h("span", { class: "count", "aria-live": "polite" });
  const head = h("thead");
  const sevSel = h("select", { class: "input", "aria-label": "Filter severity", onchange: (e) => { state.sev = e.target.value; draw(); } },
    h("option", { value: "" }, "Semua severity"), ...["tinggi", "sedang", "rendah", "info"].map((v) => h("option", { value: v }, v[0].toUpperCase() + v.slice(1))));
  const stSel = h("select", { class: "input", "aria-label": "Filter status", onchange: (e) => { state.st = e.target.value; draw(); } },
    h("option", { value: "" }, "Semua status"), h("option", { value: "MENUNGGU_PERSETUJUAN" }, "Menunggu persetujuan"), h("option", { value: "DIESKALASI" }, "Dieskalasi"));
  const cats = [...new Map(data.kasus.map((r) => [r.kategori, r])).values()];
  const katSel = h("select", { class: "input", "aria-label": "Filter kategori", onchange: (e) => { state.kat = e.target.value; draw(); } },
    h("option", { value: "" }, "Semua kategori"), ...cats.map((r) => h("option", { value: r.kategori }, `${r.attack.id} ${r.kategori_id}`)));
  sevSel.value = state.sev; stSel.value = state.st; katSel.value = state.kat;
  const q = h("input", { class: "input", type: "search", placeholder: "Cari host, ID, aturan, ATT&CK", value: state.q, "aria-label": "Cari kasus",
    oninput: (e) => { state.q = e.target.value; draw(); } });

  page.append(h("section", { class: "card", "aria-label": "Daftar kasus" },
    h("div", { class: "filters" }, h("div", { class: "search" }, icon("search"), q), sevSel, stSel, katSel,
      h("button", { type: "button", class: "linkbtn small", onclick: () => { Object.assign(state, { q: "", sev: "", st: "", kat: "", tile: "" }); rerender(); } }, "Reset filter"),
      countEl),
    h("div", { class: "tbl-wrap" }, h("table", { class: "t" }, head, body))));
  page.append(h("p", { class: "muted small" },
    `${fmtNum(nEmpty)} kelompok event tanpa temuan aturan tidak dibuat kasus. Waktu dalam UTC. `,
    "Aksi yang disetujui hanya dicatat di jejak audit; PERISAI tidak menjalankan aksi ke sistem."));

  function sortBtn(key, label) {
    const active = state.sort === key;
    return h("button", { type: "button", "aria-sort": active ? (state.dir > 0 ? "ascending" : "descending") : null,
      onclick: () => { state.dir = state.sort === key ? -state.dir : (key === "severity" || key === "waktu" ? -1 : 1); state.sort = key; draw(); } },
      label, active ? (state.dir > 0 ? " ▲" : " ▼") : "");
  }

  function draw() {
    clear(statsEl);
    for (const [key, label, n, alert] of tiles) {
      statsEl.append(h("button", { type: "button", class: `stat ${alert && n ? "alert" : ""}`, "aria-pressed": state.tile === key ? "true" : "false",
        onclick: () => { state.tile = state.tile === key ? "" : key; draw(); } },
        h("div", { class: "n" }, fmtNum(n)), h("div", { class: "l" }, label)));
    }
    clear(head).append(h("tr", null,
      h("th", null, sortBtn("id", "ID")), h("th", null, sortBtn("waktu", "Waktu (UTC)")), h("th", null, sortBtn("host", "Host")),
      h("th", null, "Kategori (ATT&CK)"), h("th", null, sortBtn("severity", "Severity")), h("th", null, "Status mesin"),
      h("th", null, "Tindakan analis"), h("th", null, "Peringatan"), h("th", null, "Aksi diusulkan")));
    const rows = sortRows(data.kasus.filter(match));
    clear(body);
    for (const r of rows) {
      const link = h("a", { href: `#/kasus/${r.id}` }, r.id);
      const tr = h("tr", { class: "click", onclick: (e) => { if (e.target.tagName !== "A") ctx.go(`#/kasus/${r.id}`); } },
        h("td", { class: "nowrap" }, h("span", { class: `sev-bar ${r.severity}`, "aria-hidden": "true" }), link),
        h("td", { class: "nowrap" }, fmtTime(r.waktu)),
        h("td", null, r.host, r.aset_terlindungi ? h("div", { class: "small muted" }, "aset terlindungi") : null),
        h("td", null, h("span", { class: "tag" }, r.attack.id), " ", r.attack.nama, h("div", { class: "small muted" }, r.kategori_id)),
        h("td", null, sevChip(r.severity)),
        h("td", null, statusChip(r.status_mesin)),
        h("td", null, reviewChip(r.status_tinjauan)),
        h("td", null, r.peringatan.length ? warnChips(r.peringatan) : h("span", { class: "muted" }, "-")),
        h("td", null, actionText(r.aksi)));
      body.append(tr);
    }
    if (!rows.length) body.append(h("tr", null, h("td", { colspan: "9", class: "muted" }, "Tidak ada kasus yang cocok dengan filter.")));
    countEl.textContent = `Menampilkan ${rows.length} dari ${data.kasus.length}`;
  }
  draw();
}
