// Label tampilan Bahasa Indonesia untuk kode mesin.
import { h, icon } from "./dom.js";

export const STATUS = {
  MENUNGGU_PERSETUJUAN: ["Menunggu persetujuan", "st-wait"],
  DIESKALASI: ["Dieskalasi ke analis", "st-esc"],
  DITUTUP: ["Ditutup", "st-closed"],
};
export const REVIEW = {
  DISETUJUI: ["Disetujui analis", "st-ok", "circle-check"],
  DITOLAK: ["Ditolak analis", "st-bad", "circle-x"],
  DITUTUP_ANALIS: ["Ditutup analis", "st-closed", "archive"],
};
export const WARN = {
  INJEKSI_TERDETEKSI: ["Injeksi terdeteksi", "chip-warn"],
  DRAF_AI_DISUNTING: ["Draf AI disunting", "chip-warn-soft"],
  RINGKASAN_DISUNTING: ["Ringkasan disunting", "chip-warn-soft"],
  MODE_DEGRADASI: ["Mode aturan", "st-esc"],
};
export const ACTION = {
  isolate_host: "Isolasi host",
  block_ip: "Blokir IP",
  escalate: "Eskalasi ke analis",
  no_action: "Tanpa aksi (tutup kasus)",
};
export const VERDICT = {
  BLOCK: "DITOLAK (BLOCK)",
  REQUEST_APPROVAL: "PERLU PERSETUJUAN",
  EXECUTE: "DITERIMA, tanpa aksi ke sistem",
};
export const SEV = { tinggi: "Tinggi", sedang: "Sedang", rendah: "Rendah", info: "Info" };
export const KIND = {
  impor_log: "Impor log",
  firewall: "Firewall masukan",
  usulan_llm: "Usulan LLM",
  keputusan_policy: "Keputusan policy v1",
  keputusan_v12: "Keputusan v1.2.2",
  tindakan_analis: "Tindakan analis",
};
export const CODE = {
  PROMPT_INJECTION: "instruksi ke AI",
  SOC_DIRECTIVE: "perintah aksi SOC",
  APPROVAL_OR_READER_CLAIM: "klaim izin / sapaan ke mesin",
  HIDDEN_CHARACTERS: "karakter tersembunyi",
  HOMOGLYPH: "huruf tiruan",
};

export function codeLabel(c) {
  const base = c.replace(/_(ENCODED|STITCHED)$/, "");
  const suffix = c.endsWith("_ENCODED") ? " (tersandi)" : c.endsWith("_STITCHED") ? " (terpecah)" : "";
  return (CODE[base] || base) + suffix;
}

export function sevChip(sev) {
  return h("span", { class: `chip sev-${sev}` }, SEV[sev] || sev);
}

export function statusChip(st) {
  const [l, c] = STATUS[st] || [st, "st-esc"];
  return h("span", { class: `chip ${c}` }, l);
}

export function reviewChip(st) {
  if (!st) return h("span", { class: "muted" }, "Belum");
  const [l, c, ic] = REVIEW[st] || [st, "st-esc", "check"];
  return h("span", { class: `chip ${c}` }, icon(ic), l);
}

export function warnChips(ws) {
  return ws.map((w) => {
    const [l, c] = WARN[w] || [w, "chip-warn-soft"];
    return h("span", { class: `chip ${c}` }, w === "INJEKSI_TERDETEKSI" ? icon("triangle-alert") : null, l);
  });
}

export function actionText(a) {
  if (!a) return "-";
  return (ACTION[a.jenis] || a.jenis) + (a.target ? ` → ${a.target}` : "");
}
