// Pembangun DOM kecil. Semua teks masuk sebagai text node, jadi isi log tidak pernah menjadi HTML.
const SVGNS = "http://www.w3.org/2000/svg";

export function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  if (attrs) setAttrs(el, attrs);
  append(el, children);
  return el;
}

export function s(tag, attrs, ...children) {
  const el = document.createElementNS(SVGNS, tag);
  if (attrs) for (const [k, v] of Object.entries(attrs)) if (v !== null && v !== undefined && v !== false) el.setAttribute(k, String(v));
  append(el, children);
  return el;
}

function setAttrs(el, attrs) {
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "dataset") Object.assign(el.dataset, v);
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
    else if (k === "value") el.value = v;
    else if (k === "checked") el.checked = !!v;
    else el.setAttribute(k, v === true ? "" : String(v));
  }
}

export function append(el, children) {
  for (const c of children.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    el.appendChild(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

export function clear(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
  return el;
}

export function icon(name, cls = "") {
  const svg = s("svg", { class: `ic ${cls}`.trim(), "aria-hidden": "true", focusable: "false" });
  const use = document.createElementNS(SVGNS, "use");
  use.setAttribute("href", `vendor/lucide/icons.svg#i-${name}`);
  svg.appendChild(use);
  return svg;
}

export function btn(label, opts = {}) {
  const b = h("button", { type: opts.type || "button", class: `btn ${opts.cls || ""}`.trim(), onclick: opts.onclick,
    disabled: opts.disabled, title: opts.title, "aria-label": opts.aria });
  if (opts.icon) b.appendChild(icon(opts.icon));
  if (label) b.appendChild(document.createTextNode(label));
  return b;
}

export function setBusy(b, busy, label) {
  if (!b._orig) b._orig = Array.from(b.childNodes).map((n) => n.cloneNode(true));
  b.disabled = !!busy;
  b.setAttribute("aria-busy", busy ? "true" : "false");
  clear(b);
  if (busy) append(b, [icon("loader-circle", "spin"), label || "Memproses"]);
  else append(b, b._orig.map((n) => n.cloneNode(true)));
}

export function card(title, opts = {}, ...body) {
  const head = h("div", { class: "card-h" }, opts.icon ? icon(opts.icon) : null, h("h2", null, title), opts.right || null);
  return h("section", { class: `card ${opts.cls || ""}`.trim(), "aria-label": title }, head,
    h("div", { class: `card-b ${opts.flush ? "flush" : ""}`.trim() }, ...body));
}

export function loading(text = "Memuat") {
  return h("div", { class: "loading", role: "status" }, icon("loader-circle", "spin"), text);
}

export function banner(kind, iconName, ...body) {
  return h("div", { class: `banner ${kind}`, role: kind === "bad" ? "alert" : null }, icon(iconName), h("div", null, ...body));
}

export function kv(pairs, cls = "kv") {
  const dl = h("dl", { class: cls });
  for (const [k, v] of pairs) {
    if (v === null || v === undefined) continue;
    dl.append(h("dt", null, k), h("dd", null, v));
  }
  return dl;
}

// ------------------------------------------------------------- format
const BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];

export function parseTime(v) {
  if (!v) return null;
  let t = String(v).trim().replace(" ", "T").replace(/(\.\d{3})\d+/, "$1");
  if (!/[zZ]|[+-]\d\d:?\d\d$/.test(t)) t += "Z";
  const d = new Date(t);
  return isNaN(d.getTime()) ? null : d;
}

export function fmtTime(v, withSec = true) {
  const d = parseTime(v);
  if (!d) return v ? String(v) : "-";
  const p = (n) => String(n).padStart(2, "0");
  return `${p(d.getUTCDate())} ${BULAN[d.getUTCMonth()]} ${d.getUTCFullYear()} ${p(d.getUTCHours())}:${p(d.getUTCMinutes())}` +
    (withSec ? `:${p(d.getUTCSeconds())}` : "");
}

export function fmtNum(n, digits = 0) {
  if (n === null || n === undefined || Number.isNaN(n)) return "-";
  return Number(n).toLocaleString("id-ID", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function fmtBytes(n) {
  if (n === null || n === undefined) return "-";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${fmtNum(n / 1024, 1)} KB`;
  if (n < 1024 ** 3) return `${fmtNum(n / 1024 / 1024, 1)} MB`;
  return `${fmtNum(n / 1024 ** 3, 2)} GB`;
}

export function short(hash, n = 12) {
  return hash ? `${hash.slice(0, n)}…` : "-";
}
