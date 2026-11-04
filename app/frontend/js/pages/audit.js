// Jejak audit berantai SHA-256: daftar entri, verifikasi, uji perubahan pada salinan, ekspor.
import { api, download } from "../api.js";
import { banner, btn, card, clear, fmtNum, fmtTime, h, icon, setBusy, short } from "../dom.js";
import { KIND } from "../labels.js";

function verifyBanner(v, when) {
  if (v.ok) {
    return banner("ok", "circle-check", h("b", null, "Rantai utuh. "),
      `${fmtNum(v.entries)} entri diverifikasi ulang dari berkas: setiap hash entri cocok dengan isi dan hash entri sebelumnya. Head `,
      h("span", { class: "hash" }, short(v.head, 20)), when ? h("span", { class: "muted" }, ` · ${when}`) : null);
  }
  return banner("bad", "triangle-alert", h("b", null, `Rantai RUSAK: ${v.problems.length} masalah. `),
    h("ul", { class: "reasons" }, v.problems.slice(0, 10).map((p) => h("li", { class: "mono" }, p))));
}

export async function render(page, _params, ctx) {
  const d = await api.get("/api/audit");
  clear(page);
  const status = h("div", { id: "audit-status" }, verifyBanner(d.verifikasi));
  const tamperOut = h("div", { id: "uji-perubahan" });
  const vBtn = btn("Verifikasi integritas", { icon: "refresh-cw", cls: "primary" });
  const tBtn = btn("Uji deteksi perubahan", { icon: "flask-conical", disabled: !d.jumlah });
  const eBtn = btn("Ekspor audit.jsonl", { icon: "download", disabled: !d.jumlah });
  vBtn.addEventListener("click", async () => {
    setBusy(vBtn, true, "Memverifikasi");
    try {
      const v = await api.post("/api/audit/verifikasi");
      clear(status).append(verifyBanner(v, `diverifikasi ${fmtTime(v.waktu)} UTC dalam ${fmtNum(v.ms, 1)} ms`));
    } catch (e) { ctx.toast(e.message, "bad"); } finally { setBusy(vBtn, false); }
  });
  tBtn.addEventListener("click", async () => {
    setBusy(tBtn, true, "Menguji");
    try {
      const r = await api.post("/api/audit/uji-perubahan");
      clear(tamperOut).append(card("Uji deteksi perubahan (pada salinan)", { icon: "flask-conical" },
        h("p", null, `Salinan audit.jsonl dibuat, lalu entri #${r.seq} (${KIND[r.jenis_entri] || r.jenis_entri}) diubah: `,
          h("span", { class: "mono" }, `${r.field}: ${JSON.stringify(r.sebelum)} → ${JSON.stringify(r.sesudah)}`), "."),
        r.hasil.ok ? banner("bad", "triangle-alert", "Perubahan TIDAK terdeteksi.")
          : banner("bad", "circle-x", h("b", null, "Perubahan terdeteksi pada salinan: "), h("ul", { class: "reasons" }, r.hasil.problems.map((p) => h("li", { class: "mono" }, p)))),
        r.asli.ok ? banner("ok", "circle-check", h("b", null, "Berkas asli tetap utuh "), `(${fmtNum(r.asli.entries)} entri). Salinan uji sudah dihapus.`)
          : banner("bad", "triangle-alert", "Berkas asli rusak.")));
    } catch (e) { ctx.toast(e.message, "bad"); } finally { setBusy(tBtn, false); }
  });
  eBtn.addEventListener("click", async () => {
    try { const m = await download("/api/audit/ekspor", `audit_${d.sesi.slice(0, 15)}.jsonl`); if (m) ctx.toast(m); } catch (e) { ctx.toast(e.message, "bad"); }
  });

  page.append(h("div", { class: "page-head" },
    h("div", { class: "titles" }, h("h1", null, "Jejak audit"),
      h("div", { class: "sub" }, `Sesi ${d.sesi} · ${fmtNum(d.jumlah)} entri · SHA-256 berantai (tiap entri memuat hash entri sebelumnya)`)),
    h("div", { class: "actions" }, vBtn, tBtn, eBtn)));
  page.append(status, tamperOut);
  if (!d.jumlah) {
    page.append(h("div", { class: "card" }, h("div", { class: "empty" }, icon("link-2", "xl"), h("h2", null, "Jejak audit masih kosong"),
      h("p", null, "Entri dibuat saat log diimpor, saat keputusan dibuat, dan saat analis menyetujui atau menolak aksi."),
      h("div", { class: "actions" }, h("a", { class: "btn primary", href: "#/impor" }, icon("upload"), "Impor log")))));
    return;
  }
  const kinds = [...new Set(d.entri.map((e) => e.kind))];
  let kindF = "";
  const sel = h("select", { class: "input", "aria-label": "Filter jenis entri", onchange: (e) => { kindF = e.target.value; draw(); } },
    h("option", { value: "" }, "Semua jenis"), kinds.map((k) => h("option", { value: k }, KIND[k] || k)));
  const tb = h("tbody");
  const count = h("span", { class: "count" });
  page.append(h("section", { class: "card" }, h("div", { class: "filters" }, sel, count),
    h("div", { class: "tbl-wrap" }, h("table", { class: "t" },
      h("thead", null, h("tr", null, h("th", null, "#"), h("th", null, "Waktu (UTC)"), h("th", null, "Jenis"), h("th", null, "Kasus"),
        h("th", null, "prev_hash"), h("th", null, "entry_hash"), h("th", null, "Isi"))), tb))));
  function draw() {
    clear(tb);
    const rows = d.entri.filter((e) => !kindF || e.kind === kindF).slice().reverse();
    for (const e of rows) {
      tb.append(h("tr", null, h("td", { class: "mono" }, e.seq), h("td", { class: "nowrap" }, fmtTime(e.ts)),
        h("td", null, e.kind === "tindakan_analis" ? h("b", null, KIND[e.kind]) : (KIND[e.kind] || e.kind)),
        h("td", null, e.kasus ? h("a", { href: `#/kasus/${e.kasus}` }, e.kasus) : h("span", { class: "mono small" }, e.case_id)),
        h("td", { class: "hash", title: e.prev_hash }, short(e.prev_hash, 12)),
        h("td", { class: "hash", title: e.entry_hash }, short(e.entry_hash, 12)),
        h("td", null, h("details", { class: "payload" }, h("summary", null, "payload"), h("pre", null, JSON.stringify(e.payload, null, 1))))));
    }
    count.textContent = `${rows.length} entri ditampilkan`;
  }
  draw();
}
