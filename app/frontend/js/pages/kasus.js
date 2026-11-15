// Detail kasus: bukti, injeksi, keputusan + alasan policy, persetujuan analis, simulasi usulan, DRAF AI.
import { api } from "../api.js";
import { banner, btn, card, clear, fmtNum, fmtTime, h, icon, kv, setBusy, short } from "../dom.js";
import { ACTION, KIND, VERDICT, actionText, codeLabel, reviewChip, sevChip, statusChip, warnChips } from "../labels.js";

const NAME_KEY = "perisai.analis";
const SHOW_FIELDS = ["TimeCreated", "@timestamp", "Channel", "Hostname", "Image", "ParentImage", "SourceImage", "TargetImage",
  "GrantedAccess", "TargetUserName", "SubjectUserName", "LogonType", "IpAddress", "SourceIp", "DestinationIp", "DestinationPort",
  "ServiceName", "ShareName", "RelativeTargetName", "TargetObject", "TargetFilename", "ObjectName"];

function getName() { try { return localStorage.getItem(NAME_KEY) || ""; } catch { return ""; } }
function setName(v) { try { localStorage.setItem(NAME_KEY, v); } catch { /* */ } }

function evidenceTable(d) {
  const tb = h("tbody");
  for (const e of d.event) {
    const st = e.terstruktur;
    const pairs = SHOW_FIELDS.filter((f) => f in st && f !== "TimeCreated" && f !== "@timestamp" && f !== "Channel" && f !== "Hostname")
      .map((f) => [f, String(st[f])]);
    const flagged = new Map(e.ditandai.map((x) => [x.field, x.kode]));
    tb.append(h("tr", { class: flagged.size ? "sel" : null },
      h("td", { class: "mono nowrap" }, e.id),
      h("td", { class: "mono" }, String(st.EventID)),
      h("td", { class: "nowrap small" }, fmtTime(st.TimeCreated || st["@timestamp"]), h("div", { class: "muted" }, st.Channel || "")),
      h("td", null, kv(pairs.length ? pairs : [["-", "tidak ada field terstruktur lain"]])),
      h("td", null, e.aturan.length ? e.aturan.map((r) => h("div", null, h("span", { class: "tag" }, r.id), " ", r.judul, " ", h("span", { class: `chip sev-${r.severity === "high" ? "tinggi" : r.severity === "medium" ? "sedang" : "rendah"}` }, r.severity)))
        : h("span", { class: "muted" }, "tidak memicu aturan"))));
    const free = Object.entries(e.teks_bebas);
    if (free.length) {
      tb.append(h("tr", { class: "sub-row" }, h("td", null), h("td", { colspan: "4" },
        free.map(([f, v]) => {
          const codes = flagged.get(f);
          return h("div", null,
            h("div", { class: "inert-label" }, h("span", { class: "field-name" }, `${e.id}.${f}`), "teks bebas, bisa ditulis penyerang; ditampilkan sebagai teks biasa",
              codes ? h("span", { class: "chip chip-warn" }, icon("triangle-alert"), "ditandai firewall: ", codes.map(codeLabel).join(", ")) : null),
            h("div", { class: `inert ${codes ? "flagged" : ""}` }, String(v)));
        }))));
    }
  }
  return h("div", { class: "tbl-wrap" }, h("table", { class: "t" },
    h("thead", null, h("tr", null, h("th", null, "Event"), h("th", null, "EventID"), h("th", null, "Waktu (UTC) / channel"),
      h("th", null, "Field terstruktur (dipakai sebagai bukti)"), h("th", null, "Aturan detektor"))), tb));
}

function decisionCard(d) {
  const k = d.keputusan;
  const iso = k.syarat_isolasi;
  const kids = [
    h("div", { class: "muted small" }, "Aksi akhir yang diajukan sistem"),
    h("div", { class: "decision-action" }, icon(k.aksi_akhir.jenis === "escalate" ? "user" : "ban", "lg"), actionText(k.aksi_akhir)),
    h("div", { class: "actions" }, statusChip(k.status), ...warnChips(k.peringatan)),
    h("hr", { class: "sep" }),
    kv([["Kategori", `${d.ringkas.attack.id} ${d.ringkas.attack.nama} (${d.ringkas.kategori_id})`],
      ["Severity", sevChip(d.ringkas.severity)],
      ["Sumber keputusan", k.sumber === "rules_v12" ? "aturan v1.2.2 (bukan LLM)" : k.sumber],
      ["Syarat bukti isolasi", iso.terpenuhi ? `terpenuhi (${iso.aturan.join(", ")})` : `tidak terpenuhi (${iso.aturan.join(", ") || "tanpa aturan"})`],
      d.ringkas.aset_terlindungi ? ["Aset", "terlindungi (DC/SIEM/DNS/gateway, aset OT HMI/PLC/SCADA/RTU/EWS, atau daftar satuan): tidak pernah diisolasi otomatis"] : null,
      k.usulan_llm ? ["Usulan LLM", `${actionText(k.usulan_llm.aksi)} · putusan policy: ${VERDICT[k.verdict_usulan_v1] || k.verdict_usulan_v1}`] : null,
    ].filter(Boolean), "kv wide"),
    h("h3", { class: "mt" }, "Alasan policy"),
    h("ol", { class: "reasons", id: "alasan-policy" }, k.alasan.map((r, i) => {
      const raw = (k.alasan_asli || [])[i];
      return raw && raw !== r
        ? h("li", { title: `Teks asli mesin: ${raw}` }, r, h("div", { class: "small muted" }, "teks asli mesin: ", h("span", { class: "mono" }, raw)))
        : h("li", null, r);
    })),
  ];
  return card("Keputusan", { icon: "list-checks" }, ...kids);
}

function reviewCard(d, ctx, rerender) {
  const body = h("div");
  const opts = d.opsi_tinjauan;
  const form = h("form", { hidden: true, novalidate: true });
  const nameIn = h("input", { class: "input", id: "analis", maxlength: "80", autocomplete: "name", value: getName(), required: true });
  const noteIn = h("textarea", { class: "input", id: "catatan", maxlength: "1000", rows: "3", required: true,
    placeholder: "Contoh: hash berkas dicek di sandbox lokal; host sudah dikonfirmasi ke operator." });
  const err = h("div", { class: "err-text", role: "alert" });
  const submit = btn("Catat ke jejak audit", { type: "submit", cls: "primary", icon: "check" });
  const cancel = btn("Batal", { onclick: () => { form.hidden = true; } });
  const title = h("h3");
  let chosen = null;
  form.append(title,
    h("label", { class: "field" }, h("span", null, "Nama / NRP analis"), nameIn),
    h("label", { class: "field" }, h("span", null, "Catatan (wajib)"), noteIn),
    err, h("div", { class: "actions" }, submit, cancel),
    h("p", { class: "hint" }, "Dicatat, tidak dieksekusi. PERISAI tidak menjalankan aksi ke sistem (pilot baca-saja)."));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    err.textContent = "";
    const analis = nameIn.value.trim(), catatan = noteIn.value.trim();
    if (analis.length < 2) { err.textContent = "Isi nama analis (min. 2 karakter)."; nameIn.focus(); return; }
    if (catatan.length < 3) { err.textContent = "Isi catatan (min. 3 karakter)."; noteIn.focus(); return; }
    setBusy(submit, true, "Mencatat");
    try {
      const r = await api.post(`/api/kasus/${d.ringkas.id}/tinjauan`, { keputusan: chosen.keputusan, analis, catatan });
      setName(analis);
      ctx.toast(`${r.tinjauan.label}: tercatat sebagai entri audit #${r.tinjauan.seq}. Tidak ada aksi yang dijalankan.`);
      ctx.refreshBadge();
      rerender();
    } catch (ex) {
      err.textContent = ex.message;
      setBusy(submit, false);
    }
  });
  const btns = h("div", { class: "actions" });
  const STY = { setujui: ["ok", "circle-check", "Setujui aksi"], tolak: ["danger", "circle-x", "Tolak aksi"],
    tutup: ["", "archive", "Tutup kasus"], catatan: ["", "square-pen", "Tambah catatan"] };
  for (const o of opts) {
    const [cls, ic, lab] = STY[o.keputusan];
    btns.append(btn(lab, { cls, icon: ic, onclick: () => {
      chosen = o;
      title.textContent = o.keputusan === "setujui" ? `Setujui: ${actionText(d.keputusan.aksi_akhir)}`
        : o.keputusan === "tolak" ? `Tolak: ${actionText(d.keputusan.aksi_akhir)}` : o.label;
      form.hidden = false;
      (nameIn.value ? noteIn : nameIn).focus();
    } }));
  }
  if (d.keputusan.status === "MENUNGGU_PERSETUJUAN") {
    body.append(h("p", null, "Aksi berisiko ini butuh keputusan analis. Persetujuan dicatat di rantai audit dan ",
      h("b", null, "tidak dieksekusi"), " oleh aplikasi."));
  } else {
    body.append(h("p", null, "Sistem tidak mengusulkan aksi berisiko. Kasus diserahkan ke analis untuk ditinjau."));
  }
  const m = ctx.peran && ctx.peran.masuk;
  if (m && !nameIn.value) nameIn.value = m.nama;
  if (ctx.can("tinjau")) body.append(btns, form);
  else body.append(h("div", { class: "banner info" }, icon("lock"), h("div", null,
    h("b", null, `Peran ${m ? m.label : "ini"} tidak bisa meninjau kasus. `),
    "Hanya Analis yang boleh menyetujui, menolak, atau menutup kasus. Pembatasan ini juga ditegakkan di server. ",
    h("a", { href: "#/masuk" }, "Ganti peran"))));
  if (d.tinjauan.length) {
    body.append(h("h3", { class: "mt" }, "Riwayat"), ...d.tinjauan.slice().reverse().map((r) => h("div", { class: "review-item" },
      h("div", { class: "actions" }, r.status ? reviewChip(r.status) : h("span", { class: "chip st-esc" }, r.label), h("span", { class: "muted small" }, fmtTime(r.ts))),
      h("div", null, h("b", null, r.analis), ": ", r.catatan),
      h("div", { class: "small muted" }, `audit #${r.seq} · `, h("span", { class: "hash" }, short(r.hash, 16))))));
  }
  return card("Tindakan analis", { icon: "user", right: reviewChip(d.ringkas.status_tinjauan) }, body);
}

function simulationCard(d) {
  const ids = d.event.map((e) => e.id);
  const sel = h("select", { class: "input", id: "sim-jenis" }, ...d.aksi_tersedia.map((a) => h("option", { value: a }, `${a} (${ACTION[a]})`)),
    h("option", { value: "hapus_berkas" }, "hapus_berkas (di luar daftar)"));
  const target = h("input", { class: "input", id: "sim-target", placeholder: "mis. DC01 atau 10.10.0.53" });
  const bukti = h("div", { class: "actions" }, ids.map((id, i) => h("label", { class: "check" },
    h("input", { type: "checkbox", value: id, checked: i === 0 }), id)));
  const det = h("input", { type: "checkbox", id: "sim-det", checked: true });
  const out = h("div", { "aria-live": "polite" });
  const run = btn("Uji usulan", { icon: "flask-conical", cls: "primary" });
  const presets = h("div", { class: "actions" }, h("span", { class: "muted small" }, "Contoh usulan penyerang:"),
    btn("isolasi DC01", { cls: "sm", onclick: () => { sel.value = "isolate_host"; target.value = "DC01"; } }),
    btn("blokir 10.10.0.53", { cls: "sm", onclick: () => { sel.value = "block_ip"; target.value = "10.10.0.53"; } }),
    btn("tutup kasus", { cls: "sm", onclick: () => { sel.value = "no_action"; target.value = ""; } }));
  run.addEventListener("click", async () => {
    setBusy(run, true, "Menguji");
    clear(out);
    try {
      const r = await api.post(`/api/kasus/${d.ringkas.id}/simulasi`, {
        jenis: sel.value, target: target.value || null, detektor_aktif: det.checked,
        bukti: Array.from(bukti.querySelectorAll("input:checked")).map((x) => x.value) });
      out.append(h("div", { class: `banner ${r.putusan_usulan === "BLOCK" ? "bad" : "info"}`, id: "sim-hasil" },
        icon(r.putusan_usulan === "BLOCK" ? "ban" : "info"),
        h("div", null,
          h("div", null, "Usulan ", h("b", null, actionText(r.usulan)), r.usulan.bukti.length ? ` (bukti ${r.usulan.bukti.join(", ")})` : "",
            ": ", h("span", { class: `verdict ${r.putusan_usulan}` }, VERDICT[r.putusan_usulan] || r.putusan_usulan)),
          h("ul", { class: "reasons" }, r.alasan_usulan.map((x) => h("li", null, x))),
          h("div", { class: "small" }, "Aksi akhir yang tetap diajukan sistem: ", h("b", null, actionText(r.aksi_akhir)), ` · ${r.status_akhir}`),
          !r.detektor_aktif ? h("div", { class: "small muted" }, "Detektor pola dimatikan untuk uji ini: hanya aturan struktural policy yang bekerja.") : null)));
    } catch (e) {
      out.append(banner("bad", "triangle-alert", e.message));
    } finally { setBusy(run, false); }
  });
  return card("Uji usulan terhadap policy", { icon: "flask-conical" },
    h("p", { class: "muted small" }, "Masukkan usulan seperti yang akan dikirim LLM (atau penyerang yang menyetir LLM). ",
      "Hasilnya hanya ditampilkan; kasus tidak berubah dan tidak dicatat sebagai keputusan."),
    presets,
    h("div", { class: "grid-form" },
      h("label", { class: "field" }, h("span", null, "Aksi"), sel),
      h("label", { class: "field" }, h("span", null, "Target"), target)),
    h("div", { class: "field" }, h("span", { class: "small", style: null }, h("b", null, "Bukti (id event)")), bukti),
    h("div", { class: "actions" }, h("label", { class: "check" }, det, "Detektor pola injeksi aktif"), h("div", { class: "spacer" }), run),
    out);
}

// Cek silang draf AI vs kategori aturan (perisai_app/cekdraf.py). Hanya tampilan; keputusan tetap dari aturan.
function crossCheckLabel(cek) {
  if (!cek) return "";
  if (cek.status === "BERTENTANGAN") {
    return h("div", { class: "actions xcheck", id: "cek-silang" },
      h("span", { class: "chip chip-warn" }, icon("triangle-alert"), cek.label),
      h("span", { class: "small muted" }, `kategori yang berlaku: ${cek.attack_aturan.id} ${cek.attack_aturan.nama} (dari aturan)`));
  }
  const ok = cek.status === "SESUAI";
  return h("div", { class: "actions xcheck", id: "cek-silang" },
    h("span", { class: `chip ${ok ? "st-ok" : "st-esc"}` }, ok ? icon("circle-check") : null, cek.label),
    h("span", { class: "small muted" }, ok ? `cek silang dengan ${cek.attack_aturan.id} ${cek.attack_aturan.nama}` : "cek silang: tidak ada kategori untuk dibandingkan"));
}

function crossCheckDetail(cek) {
  if (!cek || cek.status !== "BERTENTANGAN") return "";
  return banner("bad", "triangle-alert", h("div", null, h("b", null, "Draf dikesampingkan untuk kategori. "), cek.alasan,
    cek.audit_seq != null ? h("div", { class: "small muted" }, `Dicatat di jejak audit #${cek.audit_seq}.`) : null));
}

function aiCard(d, ctx, rerender) {
  const st = ctx.status;
  const llmOn = st && st.mode_analisis === "llm";
  const dr = d.draf;
  const body = h("div");
  const right = h("span", { class: "ai-label" }, "DRAF AI · bukan dasar keputusan");
  if (dr) {
    body.append(
      h("p", { class: "muted small" }, `Dibuat ${fmtTime(dr.ts)} oleh Qwen2.5-1.5B lokal (${fmtNum(dr.detik_llm, 1)} dtk di CPU). `,
        "Disaring per kalimat oleh guard_draft v1.2.2: kalimat harus menyebut bukti terstruktur, dan tidak boleh menyarankan aksi, ",
        "membenarkan penutupan, mengklaim keputusan atasan, atau menyalin teks log."),
      dr.draf_ai ? crossCheckLabel(dr.cek_silang) : "",
      dr.draf_ai ? h("blockquote", { class: `inert${dr.cek_silang && dr.cek_silang.status === "BERTENTANGAN" ? " conflict" : ""}`, id: "draf-ai" }, dr.draf_ai)
        : h("p", { id: "draf-ai" }, h("i", null, "Tidak ada kalimat yang lolos penyaring.")),
      dr.draf_ai ? crossCheckDetail(dr.cek_silang) : "",
      dr.galat_llm ? banner("warn", "triangle-alert", `LLM: ${dr.galat_llm}`) : "",
      kv([["Usulan LLM", dr.usulan_llm ? actionText(dr.usulan_llm.aksi) : "tidak valid / kosong"],
        ["Putusan policy atas usulan", VERDICT[dr.verdict_usulan] || dr.verdict_usulan || "-"],
        ["Aksi akhir", dr.aksi_tidak_berubah ? "tidak berubah (tetap dari aturan)" : "berubah"]], "kv wide"));
    const dropped = (dr.dibuang || []).map((x) => ({ s: x.kalimat, why: x.alasan })).concat((dr.dibuang_v11 || []).map((s) => ({ s, why: ["KLAIM_TIDAK_DIDUKUNG"] })));
    body.append(h("h3", { class: "mt" }, `Kalimat yang dibuang (${dropped.length})`));
    if (dropped.length) {
      body.append(h("ul", { class: "dropped" }, dropped.map((x) => h("li", null,
        h("div", { class: "s inert" }, x.s), h("div", { class: "actions" }, x.why.map((w) => h("span", { class: "tag" }, w)))))));
    } else body.append(h("p", { class: "muted" }, "Tidak ada."));
  } else {
    body.append(h("p", { class: "muted" }, llmOn
      ? "Belum ada draf. LLM lokal menulis 2-3 kalimat ringkasan; keputusan dan aksi tetap dari aturan."
      : `Mode LLM tidak aktif (${(st && st.llm.alasan) || "model tidak ada"}). Draf AI opsional; triase tetap lengkap tanpa LLM. Lihat Status sistem untuk cara mengaktifkan.`));
  }
  const prog = h("div", { hidden: true }, h("div", { class: "progress" }, h("div")), h("div", { class: "small muted", "aria-live": "polite" }));
  const go = btn(dr ? "Buat ulang draf AI" : "Buat draf AI", { icon: "sparkles", disabled: !llmOn });
  let timer = null;
  async function poll(job) {
    prog.hidden = false;
    go.disabled = true;
    const bar = prog.querySelector(".progress > div");
    const txt = prog.querySelector(".small");
    const tick = async () => {
      try {
        const j = await api.get(`/api/tugas/${job.id}`);
        const est = j.perkiraan_detik || 30;
        bar.style.width = `${Math.min(95, (j.detik_berjalan / est) * 100)}%`;
        txt.textContent = `${j.status === "antre" ? "Menunggu giliran" : j.tahap} · ${fmtNum(j.detik_berjalan, 0)} dtk (perkiraan ±${fmtNum(est, 0)} dtk di CPU)`;
        if (j.status === "selesai") { bar.style.width = "100%"; ctx.toast(`Draf AI ${d.ringkas.id} selesai (${fmtNum(j.hasil.detik, 1)} dtk).`); rerender(); return; }
        if (j.status === "gagal") { prog.hidden = true; go.disabled = false; body.append(banner("bad", "triangle-alert", `Draf AI gagal: ${j.galat}`)); return; }
        timer = setTimeout(tick, 1000);
      } catch (e) { timer = setTimeout(tick, 2000); }
    };
    tick();
  }
  go.addEventListener("click", async () => {
    try { poll(await api.post(`/api/kasus/${d.ringkas.id}/draf-ai`)); } catch (e) { ctx.toast(e.message, "bad"); }
  });
  if (d.tugas) poll(d.tugas);
  const c = card("Ringkasan AI", { icon: "sparkles", cls: "ai-panel", right }, body, prog, h("div", { class: "actions" }, go,
    h("span", { class: "muted small" }, "Berjalan di latar belakang; halaman lain tetap bisa dipakai.")));
  c._cleanup = () => clearTimeout(timer);
  return c;
}

export async function render(page, params, ctx) {
  const kid = params[0];
  const d = await api.get(`/api/kasus/${encodeURIComponent(kid)}`);
  const rerender = async () => {
    const y = document.getElementById("main").scrollTop;
    if (cleanups) cleanups();
    const c2 = await render(page, params, ctx);
    cleanups = c2;
    document.getElementById("main").scrollTop = y;
  };
  let cleanups = null;
  clear(page);
  const r = d.ringkas;
  page.append(h("div", { class: "crumbs" }, h("a", { href: "#/antrean" }, "Antrean kasus"), " / ", r.id));
  page.append(h("div", { class: "page-head" },
    h("div", { class: "titles" }, h("h1", null, `${r.id} · ${r.host}`),
      h("div", { class: "sub" }, `${fmtTime(r.waktu)} UTC · ${r.attack.id} ${r.attack.nama} · ${d.aturan_terpicu.length} aturan terpicu · `,
        `${r.n_event} event terpilih dari ${fmtNum(d.kasus.n_event_rekaman)} di kelompok ini`)),
    h("div", { class: "actions" }, sevChip(r.severity), statusChip(r.status_mesin), ...warnChips(r.peringatan))));

  const fw = d.firewall;
  if (fw.injeksi) {
    page.append(banner("bad", "triangle-alert", h("b", null, "Instruksi terdeteksi di isi log. "),
      fw.temuan.map((t) => `${t.event}.${t.field} (${t.kode.map(codeLabel).join(", ")})`).join("; "),
      ". Teks ini diperlakukan sebagai data: tidak disalin ke laporan, disunting sebelum dibaca LLM, dan aksi berisiko tidak diusulkan. Kasus dieskalasi ke analis."));
  } else if (r.aset_terlindungi) {
    page.append(banner("warn", "server", h("b", null, `${r.host} termasuk aset terlindungi. `),
      "Isolasi otomatis tidak pernah diusulkan untuk DC, SIEM, DNS, gateway, dan aset OT (HMI/PLC/SCADA/RTU/EWS); keputusan ada pada komandan/analis, dan untuk aset OT pada insinyur proses."));
  }

  const rules = d.aturan_terpicu;
  const left = h("div", null,
    card("Ringkasan aturan", { icon: "file-text" },
      h("p", { id: "ringkasan-aturan" }, d.keputusan.ringkasan_aturan),
      rules.length ? h("div", { class: "tbl-wrap" }, h("table", { class: "t" },
        h("thead", null, h("tr", null, h("th", null, "Aturan"), h("th", null, "Judul"), h("th", null, "Kategori"), h("th", null, "Severity"))),
        h("tbody", null, rules.map((x) => h("tr", null, h("td", { class: "mono" }, x.id), h("td", null, x.judul), h("td", null, x.kategori),
          h("td", null, h("span", { class: `chip sev-${x.severity === "high" ? "tinggi" : x.severity === "medium" ? "sedang" : "rendah"}` }, x.severity))))))) : null),
    card(`Bukti (${d.event.length} event)`, { icon: "list-checks", flush: true }, evidenceTable(d)),
    fw.temuan.length ? card("Temuan firewall masukan", { icon: "triangle-alert" },
      h("div", { class: "tbl-wrap" }, h("table", { class: "t" },
        h("thead", null, h("tr", null, h("th", null, "Event"), h("th", null, "Field"), h("th", null, "Kode"), h("th", null, "Cuplikan yang cocok pola (ternormalisasi)"))),
        h("tbody", null, fw.temuan.map((t) => h("tr", null, h("td", { class: "mono" }, t.event), h("td", { class: "mono" }, t.field),
          h("td", null, t.kode.map((c) => h("div", null, h("span", { class: "tag" }, c), " ", codeLabel(c)))), h("td", null, h("div", { class: "inert flagged" }, t.cuplikan)))))))) : null,
    simulationCard(d));
  const ai = aiCard(d, ctx, rerender);
  const right = h("div", null, decisionCard(d), ai, reviewCard(d, ctx, rerender),
    card("Jejak audit kasus ini", { icon: "link-2", right: h("a", { href: "#/audit", class: "small" }, "Semua entri") },
      h("table", { class: "t" }, h("tbody", null, d.audit.map((e) => h("tr", null, h("td", { class: "mono" }, `#${e.seq}`),
        h("td", null, KIND[e.kind] || e.kind), h("td", { class: "hash" }, short(e.hash, 14)))))),
      h("p", { class: "muted small" }, `SHA-256 kasus: `, h("span", { class: "hash" }, short(d.kasus.sha256, 24)))));
  page.append(h("div", { class: "grid2" }, left, right));
  cleanups = () => ai._cleanup && ai._cleanup();
  return () => cleanups && cleanups();
}
