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
import * as uji from "./pages/uji.js";

const ROUTES = { antrean, impor, kasus, uji, audit, laporan, ot, status };
const TITLES = { antrean: "Antrean kasus", impor: "Impor log", kasus: "Detail kasus", uji: "Uji injeksi", audit: "Jejak audit",
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
  if (st.mode === "demo") el.append(h("span", { class: "pill demo keep", title: "Server publik: hanya data contoh sintetis" },
    h("span", { class: "dot" }), "Demo publik · data sintetis"));
  const llmOn = st.mode_analisis === "llm";
  el.append(h("span", { class: `pill hide-sm ${llmOn ? "on" : ""}`, title: llmOn ? "Draf AI bisa dibuat per kasus" : (st.llm.alasan || "") },
    h("span", { class: "dot" }), llmOn ? "LLM lokal aktif" : "Mode aturan"));
  const net = st.jaringan;
  el.append(h("span", { class: "pill on hide-sm", title: "Server hanya menerima koneksi dari perangkat ini; halaman tidak memanggil host lain" },
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
  document.getElementById("where").textContent = TITLES[mod];
  setNav(false);
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

// ------------------------------------------------------------- shell: sidebar, drawer, tema
const COLLAPSE_KEY = "perisai.sidebar.collapsed";

function setNav(open) {
  const app = document.getElementById("app");
  if (!app) return;
  if (open) app.setAttribute("data-nav-open", ""); else app.removeAttribute("data-nav-open");
  const mb = document.getElementById("menu-btn");
  if (mb) mb.setAttribute("aria-expanded", open ? "true" : "false");
}

function setCollapsed(on) {
  const app = document.getElementById("app");
  if (on) app.setAttribute("data-collapsed", ""); else app.removeAttribute("data-collapsed");
  const b = document.getElementById("collapse-btn");
  const label = on ? "Lebarkan sidebar" : "Ciutkan sidebar";
  b.setAttribute("aria-label", label); b.title = label;
  try { localStorage.setItem(COLLAPSE_KEY, on ? "1" : "0"); } catch (e) { /* mode privat */ }
}

function themeIcon() {
  const b = document.getElementById("theme-btn");
  const dark = window.perisaiTheme && window.perisaiTheme.current() === "dark";
  clear(b).append(icon(dark ? "sun" : "moon"));
  b.title = dark ? "Pakai tema terang" : "Pakai tema gelap";
  b.setAttribute("aria-label", b.title);
}

function initShell() {
  let collapsed = false;
  try { collapsed = localStorage.getItem(COLLAPSE_KEY) === "1"; } catch (e) { /* */ }
  setCollapsed(collapsed);
  document.getElementById("collapse-btn").addEventListener("click", () =>
    setCollapsed(!document.getElementById("app").hasAttribute("data-collapsed")));
  document.getElementById("menu-btn").addEventListener("click", () =>
    setNav(!document.getElementById("app").hasAttribute("data-nav-open")));
  document.getElementById("scrim").addEventListener("click", () => setNav(false));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") setNav(false); });
  document.getElementById("theme-btn").addEventListener("click", () => { window.perisaiTheme?.toggle(); themeIcon(); });
  themeIcon();
}

window.addEventListener("hashchange", route);
window.addEventListener("DOMContentLoaded", async () => {
  initShell();
  await ctx.refreshStatus();
  ctx.refreshBadge();
  route();
  setInterval(() => api.get("/api/ping").catch(() => {}), 30000);
});
