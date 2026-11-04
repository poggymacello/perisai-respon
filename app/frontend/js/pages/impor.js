// Impor log: seret-lepas / pilih berkas, ringkasan parse.
import { api, download } from "../api.js";
import { banner, btn, card, clear, fmtBytes, fmtNum, fmtTime, h, icon, kv, setBusy, short } from "../dom.js";
import { loadSample } from "./antrean.js";

const ACCEPT = ".xml,.json,.jsonl,.ndjson,.evtx,.txt";
const SAMPLES = ["contoh_wevtutil.xml", "contoh_batalyon.xml", "contoh_winlogbeat.json"];

function resultCard(r) {
  return card("Hasil impor", { icon: "circle-check", right: h("a", { class: "btn primary sm", href: "#/antrean" }, "Buka antrean") },
    h("div", { class: "stats" },
      ...[["Event dibaca", r.n_event], ["Kasus dibuat", r.n_kasus], ["Kelompok tanpa temuan", r.n_kelompok_tanpa_temuan],
        ["Berkas", r.berkas.length], ["Jendela (menit)", r.jendela_menit], ["Waktu proses (dtk)", r.detik]]
        .map(([l, n]) => h("div", { class: "stat" }, h("div", { class: "n" }, typeof n === "number" && !Number.isInteger(n) ? fmtNum(n, 2) : fmtNum(n)), h("div", { class: "l" }, l)))),
    h("div", { class: "tbl-wrap" }, h("table", { class: "t" },
      h("thead", null, h("tr", null, h("th", null, "Berkas"), h("th", { class: "num" }, "Ukuran"), h("th", null, "SHA-256"))),
      h("tbody", null, r.berkas.map((b) => h("tr", null, h("td", { class: "mono" }, b.nama), h("td", { class: "num" }, fmtBytes(b.ukuran)),
        h("td", { class: "hash", title: b.sha256 }, short(b.sha256, 24))))))),
    h("p", { class: "muted small" }, "Kelompok event tanpa temuan aturan tidak dibuat kasus, kecuali bila teksnya berisi instruksi. ",
      `ID impor ${r.id} tercatat di jejak audit (jenis impor_log).`));
}

export async function render(page, _params, ctx) {
  const st = ctx.status || (await ctx.refreshStatus());
  const data = await api.get("/api/kasus");
  clear(page);
  const canUpload = st.kemampuan.unggah;
  page.append(h("div", { class: "page-head" }, h("div", { class: "titles" }, h("h1", null, "Impor log"),
    h("div", { class: "sub" }, "XML wevtutil / Get-WinEvent, JSON atau JSON-lines Winlogbeat, dan .evtx (dikonversi lokal dengan wevtutil)."))));

  const files = [];
  const list = h("ul", { class: "file-list" });
  const input = h("input", { type: "file", multiple: true, accept: ACCEPT, class: "sr-only", id: "file-input", disabled: !canUpload });
  const win = h("select", { class: "input", id: "jendela" }, ...[5, 15, 30, 60].map((m) => h("option", { value: m }, `${m} menit`)));
  win.value = "15";
  const go = btn("Impor dan triase", { icon: "play", cls: "primary", disabled: true });
  const out = h("div");

  function drawList() {
    clear(list);
    for (const [i, f] of files.entries()) {
      const ext = f.name.split(".").pop().toLowerCase();
      list.append(h("li", null, icon(ext === "evtx" ? "database" : "file-text"), h("span", { class: "nm" }, f.name),
        h("span", { class: "muted small" }, fmtBytes(f.size), ext === "evtx" ? " · dikonversi wevtutil" : ""),
        h("button", { type: "button", class: "btn sm", "aria-label": `Hapus ${f.name} dari daftar`, onclick: () => { files.splice(i, 1); drawList(); } }, icon("x"))));
    }
    go.disabled = !files.length || !canUpload;
  }
  function addFiles(fl) {
    for (const f of fl) {
      const ext = "." + f.name.split(".").pop().toLowerCase();
      if (!ACCEPT.split(",").includes(ext)) { ctx.toast(`${f.name}: format tidak didukung`, "bad"); continue; }
      if (ext === ".evtx" && !st.kemampuan.evtx) { ctx.toast(`${f.name}: konversi .evtx hanya tersedia di Windows`, "bad"); continue; }
      if (!files.some((x) => x.name === f.name && x.size === f.size)) files.push(f);
    }
    drawList();
  }
  input.addEventListener("change", () => { addFiles(input.files); input.value = ""; });

  const drop = h("div", { class: `drop ${canUpload ? "" : "disabled"}`, id: "dropzone" },
    icon("file-up", "xl"),
    h("div", null, h("b", null, "Seret berkas log ke sini"), " atau ",
      h("label", { for: "file-input", class: "linkbtn", tabindex: canUpload ? "0" : "-1", role: "button",
        onkeydown: (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } } }, "pilih berkas")),
    h("div", { class: "muted small" }, "Beberapa berkas sekaligus boleh (mis. Security + Sysmon). Maks. 200 MB per berkas."),
    input, list);
  if (canUpload) {
    for (const ev of ["dragenter", "dragover"]) drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); });
    for (const ev of ["dragleave", "drop"]) drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); });
    drop.addEventListener("drop", (e) => addFiles(e.dataTransfer.files));
  }
  // cegah browser membuka berkas yang dilepas di luar zona
  const stopNav = (e) => e.preventDefault();
  window.addEventListener("dragover", stopNav);
  window.addEventListener("drop", stopNav);

  go.addEventListener("click", async () => {
    const fd = new FormData();
    for (const f of files) fd.append("berkas", f, f.name);
    fd.append("jendela", win.value);
    setBusy(go, true, "Memproses");
    clear(out);
    try {
      const r = await api.form("/api/impor", fd);
      files.length = 0; drawList();
      out.append(resultCard(r));
      ctx.toast(`${r.n_kasus} kasus dibuat dari ${r.n_event} event.`);
      ctx.refreshBadge(); ctx.refreshStatus();
      drawHistory(await api.get("/api/kasus"));
    } catch (e) {
      out.append(banner("bad", "triangle-alert", h("b", null, "Impor gagal. "), e.message));
    } finally {
      setBusy(go, false);
      go.disabled = !files.length;
    }
  });

  const sampleBtn = btn("Muat data contoh ke antrean", { icon: "database" });
  sampleBtn.addEventListener("click", async () => {
    clear(out);
    try { const r = await loadSample(ctx, sampleBtn); out.append(resultCard(r)); drawHistory(await api.get("/api/kasus")); } catch (e) { /* toast */ }
  });

  const left = h("div", null);
  if (!canUpload) {
    left.append(banner("warn", "ban", h("b", null, "Unggah log dinonaktifkan di demo publik. "),
      "Server publik tidak boleh menerima log asli satuan. Unduh aplikasi desktop untuk memeriksa log sendiri secara offline; ",
      "di sini hanya data contoh sintetis yang dipakai."));
  }
  left.append(card("Berkas log", { icon: "upload" }, drop,
    h("div", { class: "actions", id: "impor-actions" },
      h("label", { class: "check" }, "Kelompokkan per host dan jendela ", win),
      h("div", { class: "spacer" }), go)),
    out);
  const hist = h("div");
  left.append(hist);

  function drawHistory(d) {
    clear(hist);
    if (!d.impor.length) return;
    hist.append(card("Riwayat impor di sesi ini", { icon: "clock", flush: true },
      h("div", { class: "tbl-wrap" }, h("table", { class: "t" },
        h("thead", null, h("tr", null, h("th", null, "ID"), h("th", null, "Waktu (UTC)"), h("th", null, "Jenis"), h("th", null, "Berkas"),
          h("th", { class: "num" }, "Event"), h("th", { class: "num" }, "Kasus"), h("th", { class: "num" }, "Tanpa temuan"))),
        h("tbody", null, d.impor.slice().reverse().map((i) => h("tr", null, h("td", { class: "mono" }, i.id), h("td", { class: "nowrap" }, fmtTime(i.waktu)),
          h("td", null, i.jenis), h("td", { class: "mono small" }, i.berkas.map((b) => b.nama).join(", ")),
          h("td", { class: "num" }, fmtNum(i.n_event)), h("td", { class: "num" }, fmtNum(i.n_kasus)), h("td", { class: "num" }, fmtNum(i.n_kelompok_tanpa_temuan)))))))));
  }
  drawHistory(data);

  const sampleLinks = h("ul", { class: "checklist" }, SAMPLES.map((n) => h("li", null,
    h("button", { type: "button", class: "linkbtn mono", onclick: async () => {
      try { const m = await download(`/api/sampel/${n}`, n); if (m) ctx.toast(m); } catch (e) { ctx.toast(e.message, "bad"); }
    } }, n))));

  const right = h("div", null,
    card("Ekspor log dari Windows", { icon: "file-text" },
      h("p", null, "Jalankan di PowerShell (sebagai administrator untuk log Security):"),
      h("pre", { class: "cmd" }, "wevtutil qe Security /c:500 /rd:true /f:xml > security.xml"),
      h("pre", { class: "cmd" }, "wevtutil qe Microsoft-Windows-Sysmon/Operational /c:500 /rd:true /f:xml > sysmon.xml"),
      h("p", null, "Berkas .evtx (mis. dari Event Viewer, Save All Events As) boleh langsung diimpor; aplikasi menjalankan:"),
      h("pre", { class: "cmd" }, "wevtutil qe <berkas.evtx> /lf:true /f:xml"),
      h("p", { class: "muted small" }, "JSON: keluaran Winlogbeat/NXLog satu event per baris, atau satu larik JSON.")),
    card("Data contoh sintetis", { icon: "database" },
      h("p", null, "Host fiktif *.batalyon.lab, IP privat fiktif. Tiga kasus berisi string injeksi uji (tidak berbahaya)."),
      sampleLinks,
      h("p", { class: "muted small" }, "Unduh berkas di atas untuk mencoba alur unggah, atau muat langsung:"),
      sampleBtn),
    card("Privasi", { icon: "eye-off" },
      kv([["Pemrosesan", "di perangkat ini, tanpa jaringan"], ["Berkas asli", "tidak disimpan; nama, ukuran, dan SHA-256 dicatat"],
        ["Yang disimpan", "event terpilih per kasus (maks. 8), keputusan, jejak audit"], ["Lokasi", st.data.folder]], "kv wide")));

  page.append(h("div", { class: "grid2" }, left, right));
  return () => { window.removeEventListener("dragover", stopNav); window.removeEventListener("drop", stopNav); };
}
