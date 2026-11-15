// Jalur OT: sensor proses di luar batas normal, usulan putus PLC ditolak, catatan HMI ditampilkan inert.
import { api } from "../api.js";
import { banner, card, clear, fmtNum, h, icon, kv, s } from "../dom.js";
import { VERDICT, actionText } from "../labels.js";

const K_SECONDS = 10; // perisai/ot.py: jendela 60 dtk berbunyi bila tag melanggar >= 10 dtk

function envelopeChart(t) {
  const W = 760, X0 = 120, X1 = 730;
  const [lo, hi] = t.normal;
  const top = Math.ceil((Math.max(hi, t.nilai) * 1.12) / 50) * 50;
  const x = (v) => X0 + ((X1 - X0) * v) / top;
  const ticks = [];
  for (let v = 0; v <= top; v += top > 300 ? 100 : 50) ticks.push(v);
  const xs = (v) => X0 + ((X1 - X0) * v) / t.jendela_detik;
  const svg = s("svg", { class: "ot-chart", viewBox: `0 0 ${W} 190`, role: "img",
    "aria-label": `${t.tag}: nilai ${t.nilai}, batas normal ${lo} sampai ${hi}; ${t.detik_melanggar} dari ${t.jendela_detik} detik di luar batas normal` },
    s("text", { x: 0, y: 44 }, t.tag),
    s("text", { x: 0, y: 60, class: "small" }, "nilai tag"),
    s("rect", { class: "band", x: x(lo), y: 26, width: x(hi) - x(lo), height: 30 }),
    s("text", { x: (x(lo) + x(hi)) / 2, y: 20, "text-anchor": "middle" }, `batas normal ${fmtNum(lo)}–${fmtNum(hi)}`),
    s("line", { class: "axis", x1: X0, y1: 64, x2: X1, y2: 64 }),
    ...ticks.flatMap((v) => [s("line", { class: "axis", x1: x(v), y1: 64, x2: x(v), y2: 69 }),
      s("text", { x: x(v), y: 82, "text-anchor": "middle" }, fmtNum(v))]),
    s("line", { class: "marker-line", x1: x(t.nilai), y1: 22, x2: x(t.nilai), y2: 62 }),
    s("circle", { class: "marker", cx: x(t.nilai), cy: 41, r: 5 }),
    s("text", { x: x(t.nilai) + 8, y: 45, "font-weight": "600" }, fmtNum(t.nilai, 1)),
    s("text", { x: 0, y: 134 }, "detik melanggar"),
    s("text", { x: 0, y: 150 }, `jendela ${t.jendela_detik} dtk`),
    s("rect", { class: "bar-bg", x: X0, y: 122, width: X1 - X0, height: 18 }),
    s("rect", { class: "bar-fg", x: X0, y: 122, width: xs(t.detik_melanggar) - X0, height: 18 }),
    s("line", { class: "axis", x1: xs(K_SECONDS), y1: 116, x2: xs(K_SECONDS), y2: 146, "stroke-dasharray": "3 2" }),
    s("text", { x: xs(K_SECONDS), y: 112, "text-anchor": "middle" }, `ambang ${K_SECONDS} dtk`),
    s("text", { x: xs(t.detik_melanggar) + 8, y: 136, "font-weight": "600" }, `${t.detik_melanggar} dari ${t.jendela_detik} dtk`),
    s("text", { x: X0, y: 176 }, `${t.host} · ${t.waktu}`));
  return svg;
}

export async function render(page) {
  const d = await api.get("/api/ot");
  clear(page);
  const k = d.keputusan;
  const hmi = d.kasus.events.find((e) => e.EventID === "HMI-CATATAN");
  page.append(h("div", { class: "page-head" }, h("div", { class: "titles" }, h("h1", null, "Jalur OT"),
    h("div", { class: "sub" }, "Data sensor proses (gaya HAI 21.03) → pengecekan batas normal tiap sensor → keputusan khusus aset proses (PLC/HMI tidak pernah diputus). Contoh sintetis dari demo.py skenario 5c."))));
  page.append(banner("info", "info", h("b", null, "Kebijakan OT: "),
    "PLC, HMI, RTU, SIS, dan EWS tidak pernah diisolasi atau diblokir oleh sistem, bahkan dengan persetujuan di layar ini. ",
    "Memutus pengendali bisa menghentikan proses fisik. Aksi akhir selalu eskalasi ke insinyur proses dan operator lapangan."));
  const left = h("div", null,
    card("Sensor di luar batas normal", { icon: "gauge" }, ...d.tag.map(envelopeChart),
      h("p", { id: "ringkasan-ot" }, k.ringkasan),
      h("p", { class: "muted small" }, "Profil per tag dari data normal (kuantil 0,05 % dan 99,95 %). Satu jendela 60 detik berbunyi bila ada tag ",
        `yang melanggar ≥ ${K_SECONDS} detik.`)),
    card("Catatan HMI (teks bebas)", { icon: "file-text" },
      h("div", { class: "inert-label" }, h("span", { class: "field-name" }, `${hmi.id}.Message`), `${hmi.Hostname} · ditampilkan sebagai teks biasa`),
      h("div", { class: "inert flagged" }, hmi.Message),
      d.firewall.injeksi ? banner("bad", "triangle-alert", "Firewall pola menandai catatan ini.")
        : banner("warn", "triangle-alert", h("b", null, "Firewall pola tidak menandai catatan ini. "),
          "Kalimat klaim otoritas ini tidak ada di daftar pola. Penolakan di bawah datang dari aturan aset OT, bukan dari detektor pola.")),
    card("Daftar periksa operator", { icon: "list-checks" }, h("ol", { class: "checklist" }, d.checklist.map((c) => h("li", null, c)))));
  const right = h("div", null,
    card("Keputusan OT", { icon: "list-checks" },
      h("div", { class: "muted small" }, "Usulan (dibuat tangan, meniru LLM yang menuruti catatan HMI)"),
      h("div", { class: "decision-action" }, icon("ban", "lg"), actionText(d.usulan.aksi), h("span", { class: `verdict ${k.verdict}` }, VERDICT[k.verdict] || k.verdict)),
      h("div", { class: "muted small" }, "Aksi akhir"),
      h("div", { class: "decision-action" }, icon("user", "lg"), `Eskalasi ke ${k.final_action.ke}`),
      kv([["Status", k.final_status], ["Kategori", k.kategori], ["Sumber", k.source]], "kv wide"),
      h("h3", { class: "mt" }, "Alasan"),
      h("ol", { class: "reasons" }, k.reasons.map((r) => h("li", null, r)))),
    card("Ringkasan AI", { icon: "sparkles", cls: "ai-panel", right: h("span", { class: "ai-label" }, "DRAF AI · bukan dasar keputusan") },
      h("p", { class: "muted small" }, "Dari ringkasan usulan buatan tangan di atas, disaring per kalimat."),
      k.draf_ai ? h("blockquote", { class: "inert" }, k.draf_ai) : h("p", null, h("i", null, "Kosong.")),
      h("h3", { class: "mt" }, `Kalimat yang dibuang (${k.kalimat_dibuang.length})`),
      h("ul", { class: "dropped" }, k.kalimat_dibuang.map((x) => h("li", null, h("div", { class: "s inert" }, x), h("span", { class: "tag" }, "KLAIM_TIDAK_DIDUKUNG"))))),
    h("p", { class: "muted small" }, `Sumber: ${d.sumber}.`));
  page.append(h("div", { class: "grid2" }, left, right));
}
