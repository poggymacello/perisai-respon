// Kerangka aplikasi: router hash, status global, toast.
import { api } from "./api.js";
import { banner, clear, h, icon, loading } from "./dom.js";
import * as antrean from "./pages/antrean.js";
import * as audit from "./pages/audit.js";
import * as impor from "./pages/impor.js";
import * as kasus from "./pages/kasus.js";
import * as laporan from "./pages/laporan.js";
import * as ot from "./pages/ot.js";
import * as status from "./pages/status.js";

const ROUTES = { antrean, impor, kasus, audit, laporan, ot, status };
const TITLES = { antrean: "Antrean kasus", impor: "Impor log", kasus: "Detail kasus", audit: "Jejak audit",
  laporan: "Laporan CSIRT", ot: "Jalur OT", status: "Status sistem" };

export const ctx = {
  status: null,
  async refreshStatus() {
    try {
      this.status = await api.get("/api/status");
      renderPills();
    } catch (e) { /* ditampilkan oleh halaman */ }
    return this.status;
  },
  async refreshBadge() {
    try {
      const d = await api.get("/api/kasus");
      const b = document.getElementById("nav-badge");
      b.hidden = !d.hitung.menunggu;
      b.textContent = d.hitung.menunggu;
      b.title = `${d.hitung.menunggu} kasus menunggu persetujuan`;
    } catch (e) { /* abaikan */ }
  },
  toast(msg, kind = "") {
    const t = h("div", { class: `toast ${kind}` }, icon(kind === "bad" ? "triangle-alert" : "check"), h("div", null, msg));
    document.getElementById("toasts").appendChild(t);
    setTimeout(() => t.remove(), kind === "bad" ? 8000 : 4500);
  },
  go(hash) { location.hash = hash; },
};

function renderPills() {
  const st = ctx.status;
  const el = clear(document.getElementById("top-pills"));
  if (!st) return;
  if (st.mode === "demo") el.append(h("span", { class: "pill demo", title: "Server publik: hanya data contoh sintetis" }, "Demo publik · data sintetis"));
  const llmOn = st.mode_analisis === "llm";
  el.append(h("span", { class: `pill ${llmOn ? "on" : ""}`, title: llmOn ? "Draf AI bisa dibuat per kasus" : (st.llm.alasan || "") },
    h("span", { class: "dot" }), llmOn ? "LLM lokal aktif" : "Mode aturan"));
  const net = st.jaringan;
  el.append(h("span", { class: "pill on", title: "Server hanya menerima koneksi dari perangkat ini; halaman tidak memanggil host lain" },
    h("span", { class: "dot" }), net.lokal_saja ? `Offline · ${net.bind}${net.port ? ":" + net.port : ""}` : "Server demo"));
  document.getElementById("side-foot").textContent = `Aplikasi ${st.aplikasi.versi} · mesin v${st.mesin.versi}`;
}

let cleanup = null;
let seq = 0;

async function route() {
  const raw = location.hash.replace(/^#\/?/, "") || "antrean";
  const [name, ...rest] = raw.split("/");
  const mod = ROUTES[name] ? name : "antrean";
  for (const a of document.querySelectorAll("#nav a")) {
    const active = a.dataset.route === mod || (mod === "kasus" && a.dataset.route === "antrean");
    if (active) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  }
  document.title = `${TITLES[mod]} · PERISAI-RESPON`;
  if (cleanup) { try { cleanup(); } catch (e) { /* */ } cleanup = null; }
  const main = clear(document.getElementById("main"));
  const page = h("div", { class: "page" }, loading());
  main.appendChild(page);
  main.scrollTop = 0;
  const my = ++seq;
  try {
    const out = await ROUTES[mod].render(page, rest.map(decodeURIComponent), ctx);
    if (my !== seq) { if (typeof out === "function") out(); return; }
    cleanup = typeof out === "function" ? out : null;
  } catch (e) {
    if (my !== seq) return;
    clear(page).append(banner("bad", "triangle-alert", h("b", null, "Halaman tidak bisa dimuat. "), e.message || String(e)));
  }
}

window.addEventListener("hashchange", route);
window.addEventListener("DOMContentLoaded", async () => {
  await ctx.refreshStatus();
  ctx.refreshBadge();
  route();
  setInterval(() => api.get("/api/ping").catch(() => {}), 30000);
});
