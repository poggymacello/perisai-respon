// Tentang / Status sistem: versi, mode, cek model, integritas mesin, offline, uji kinerja, lisensi, deklarasi.
import { api } from "../api.js";
import { banner, btn, card, clear, fmtBytes, fmtNum, h, icon, kv, setBusy, short } from "../dom.js";
import { DECLARATION, DEFENSIVE, LICENSES, NOTE_LLAMA } from "../about.js";

function ok(b, yes = "ya", no = "tidak") {
  return h("span", { class: `chip ${b ? "st-ok" : "st-esc"}` }, icon(b ? "circle-check" : "circle-x"), b ? yes : no);
}

export async function render(page, _params, ctx) {
  const st = await ctx.refreshStatus();
  clear(page);
  const llm = st.llm;
  const chk = llm.model.cek;
  page.append(h("div", { class: "page-head" }, h("div", { class: "titles" }, h("h1", null, "Status sistem"),
    h("div", { class: "sub" }, `${st.aplikasi.nama} ${st.aplikasi.versi} · mesin v${st.mesin.versi} · ${st.mode === "demo" ? "demo publik" : "desktop"}`))));

  const benchOut = h("div", { id: "hasil-kinerja", "aria-live": "polite" });
  const benchBtn = btn("Uji kinerja di perangkat ini", { icon: "gauge", cls: "primary" });
  benchBtn.addEventListener("click", async () => {
    setBusy(benchBtn, true, "Mengukur");
    try {
      const r = await api.post("/api/uji-kinerja");
      clear(benchOut).append(h("div", { class: "stats" },
        ...[["Median per kasus", `${fmtNum(r.median_ms, 2)} ms`], ["Persentil 95", `${fmtNum(r.p95_ms, 2)} ms`], ["Maksimum", `${fmtNum(r.maks_ms, 2)} ms`],
          ["Pengukuran", fmtNum(r.n)], ["Kasus", `${r.n_kasus} (${r.sumber})`], ["Putaran", fmtNum(r.putaran)]]
          .map(([l, n]) => h("div", { class: "stat" }, h("div", { class: "n" }, n), h("div", { class: "l" }, l)))),
        h("p", { class: "muted small" }, "Yang diukur: firewall masukan + detektor aturan + policy v1.2.2 untuk satu kasus, tanpa LLM. ",
          `CPU: ${st.perangkat.cpu}, ${st.perangkat.inti_logis} inti logis.`));
    } catch (e) { ctx.toast(e.message, "bad"); } finally { setBusy(benchBtn, false); }
  });
  const llmOut = h("div", { "aria-live": "polite" });
  const llmBtn = btn("Uji LLM lokal (±30 dtk)", { icon: "cpu", disabled: !llm.tersedia, title: llm.tersedia ? null : llm.alasan });
  llmBtn.addEventListener("click", async () => {
    let job;
    try { job = await api.post("/api/uji-kinerja/llm"); } catch (e) { ctx.toast(e.message, "bad"); return; }
    setBusy(llmBtn, true, "LLM berjalan");
    const txt = h("div", { class: "small muted" });
    const bar = h("div");
    clear(llmOut).append(h("div", { class: "progress" }, bar), txt);
    const tick = async () => {
      const j = await api.get(`/api/tugas/${job.id}`).catch(() => null);
      if (!j) { timer = setTimeout(tick, 2000); return; }
      bar.style.width = `${Math.min(95, (j.detik_berjalan / (j.perkiraan_detik || 40)) * 100)}%`;
      txt.textContent = `${j.tahap} · ${fmtNum(j.detik_berjalan)} dtk`;
      if (j.status === "selesai") {
        const r = j.hasil;
        setBusy(llmBtn, false);
        clear(llmOut).append(kv([["Waktu LLM untuk 1 kasus", `${fmtNum(r.detik_llm, 1)} dtk`],
          ["Muat model", r.detik_muat_model === null ? "sudah dimuat sebelumnya" : `${fmtNum(r.detik_muat_model, 1)} dtk (sekali per sesi aplikasi)`],
          ["Firewall / policy", `${fmtNum(r.firewall_ms, 2)} ms / ${fmtNum(r.policy_ms, 2)} ms`],
          ["Keluaran JSON valid", r.usulan_valid ? "ya" : "tidak"], ["Thread CPU", r.thread]], "kv wide"),
          h("p", { class: "muted small" }, "Pengukuran ini tidak dicatat sebagai triase dan tidak masuk jejak audit."));
        return;
      }
      if (j.status === "gagal") { setBusy(llmBtn, false); clear(llmOut).append(banner("bad", "triangle-alert", j.galat)); return; }
      timer = setTimeout(tick, 1000);
    };
    let timer = setTimeout(tick, 500);
    cleanupTimers.push(() => clearTimeout(timer));
  });
  const cleanupTimers = [];

  const integ = st.mesin.integritas;
  const newBtn = btn(st.mode === "demo" ? "Mulai ulang demo" : "Mulai sesi baru", { icon: "archive" });
  newBtn.addEventListener("click", async () => {
    const msg = st.mode === "demo" ? "Mulai ulang demo dengan data contoh baru?"
      : "Mulai sesi baru? Sesi sekarang (kasus dan jejak audit) tetap tersimpan di folder data, tidak dihapus.";
    if (!window.confirm(msg)) return;
    setBusy(newBtn, true, "Membuat sesi");
    try { await api.post("/api/sesi/baru"); ctx.toast("Sesi baru dimulai."); ctx.refreshBadge(); ctx.go("#/antrean"); } catch (e) { ctx.toast(e.message, "bad"); setBusy(newBtn, false); }
  });

  const grid = h("div", { class: "grid-cards" },
    card("Versi", { icon: "hash" }, kv([["Aplikasi", st.aplikasi.versi], ["Mesin PERISAI", `v${st.mesin.versi}`], ["Jalur keputusan", h("span", { class: "mono" }, st.mesin.jalur)],
      ["Python", st.perangkat.python], ["Mode", st.mode === "demo" ? "demo publik (data contoh, unggah mati)" : "desktop (lokal)"]], "kv wide")),
    card("Mode analisis", { icon: "cpu" },
      h("div", { class: "decision-action" }, st.mode_analisis === "llm" ? "LLM lokal aktif" : "Mode aturan"),
      h("p", null, st.mode_analisis === "llm"
        ? "Kategori dan aksi tetap dari aturan. LLM lokal hanya menulis DRAF AI per kasus atas permintaan analis."
        : `Kategori, aksi, dan ringkasan dari aturan. Draf AI tidak tersedia: ${llm.alasan}.`),
      kv([["llama_cpp di build ini", ok(llm.llama_cpp)], ["Model dimuat", ok(llm.dimuat)], ["Thread CPU untuk LLM", llm.thread]], "kv wide")),
    card("Model lokal", { icon: "database" },
      kv([["Berkas", llm.model.nama || "tidak ditemukan"], ["Sumber", llm.model.sumber || "-"], ["Ukuran", fmtBytes(llm.model.ukuran)],
        ["Cek SHA-256", llm.memeriksa ? "sedang memeriksa…" : chk ? h("span", null, ok(chk.ok, chk.status, chk.status)) : "-"],
        ["SHA-256 berkas", chk && chk.sha256 ? h("span", { class: "hash", title: chk.sha256 }, short(chk.sha256, 24)) : "-"],
        ["SHA-256 acuan", llm.model.sha256_acuan ? h("span", { class: "hash", title: llm.model.sha256_acuan }, short(llm.model.sha256_acuan, 24)) : "-"]], "kv wide"),
      h("h3", { class: "mt" }, "Lokasi yang dicari (urut)"),
      h("ol", { class: "reasons small" }, llm.lokasi_model.map((l) => h("li", null, h("span", { class: "mono" }, l.lokasi), ` (${l.keterangan})`, l.ada ? " · ada" : ""))),
      h("p", { class: "muted small" }, "Untuk mengaktifkan mode LLM: salin qwen2.5-1.5b-instruct-q3_k_m.gguf (0,92 GB, lihat README) ke salah satu lokasi di atas, ",
        "lalu buka ulang aplikasi. Hash yang tidak cocok membuat aplikasi tetap di mode aturan.")),
    card("Integritas kode mesin", { icon: "list-checks", right: ok(integ.ok, "cocok dengan hash beku", "TIDAK cocok") },
      h("p", { class: "muted small" }, `Dibandingkan dengan prototype/frozen/*.sha256; ${integ.cara}.`),
      h("table", { class: "t" }, h("tbody", null, integ.berkas.map((b) => h("tr", null, h("td", { class: "mono" }, b.berkas),
        h("td", null, ok(b.cocok, "cocok", "beda")), h("td", { class: "small muted" }, b.acuan)))))),
    card("Jaringan", { icon: "server" },
      kv([["Alamat server", `${st.jaringan.bind}${st.jaringan.port ? ":" + st.jaringan.port : ""}`],
        ["Hanya perangkat ini", ok(st.jaringan.lokal_saja)], ["Halaman ke host lain", "diblokir (CSP connect-src 'self')"],
        ["Telemetri", "tidak ada"], ["Aset frontend", "dibundel di aplikasi, tanpa CDN atau font web"]], "kv wide")),
    card("Data dan sesi", { icon: "folder-open", right: newBtn },
      kv([["Folder data", h("span", { class: "mono" }, st.data.folder)], ["Sesi aktif", h("span", { class: "mono" }, st.sesi.id)],
        ["Kasus", fmtNum(st.sesi.n_kasus)], ["Impor", fmtNum(st.sesi.n_impor)], ["Entri audit", fmtNum(st.sesi.n_audit)]], "kv wide")),
    card("Perangkat", { icon: "cpu" }, kv([["Sistem operasi", st.perangkat.os], ["CPU", st.perangkat.cpu], ["Inti logis", st.perangkat.inti_logis]], "kv wide")));

  page.append(card("Uji kinerja di perangkat ini", { icon: "gauge" },
      h("p", null, "Mengukur latensi jalur keputusan di perangkat ini (bukan angka dari laptop tim)."),
      h("div", { class: "actions" }, benchBtn, llmBtn), benchOut, llmOut),
    grid, h("div", { class: "mt" }),
    card("Lisensi dan asal-usul", { icon: "file-text", flush: true },
      h("table", { class: "t" }, h("tbody", null, LICENSES.map(([a, b]) => h("tr", null, h("td", null, a), h("td", null, b))))),
      h("div", { class: "card-b" }, h("p", { class: "muted small" }, NOTE_LLAMA))),
    card("Deklarasi (Rulebook Kartika Cyber Hackathon 2026, bagian G: Ketentuan Karya)", { icon: "info" },
      kv(DECLARATION, "kv wide"), h("p", { class: "muted small mt" }, DEFENSIVE)));
  if (st.antarmuka === "browser") {
    const q = btn("Keluar aplikasi", { icon: "power", cls: "danger" });
    q.addEventListener("click", async () => {
      try { await api.post("/api/keluar"); clear(page).append(banner("info", "info", "Aplikasi ditutup. Tab ini boleh ditutup.")); } catch (e) { ctx.toast(e.message, "bad"); }
    });
    page.append(card("Mode browser", { icon: "power" }, h("p", null, "Aplikasi berjalan di browser bawaan. Tutup server lokal dengan tombol ini."), q));
  }
  return () => cleanupTimers.forEach((f) => f());
}
