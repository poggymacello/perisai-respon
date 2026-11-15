// Masuk (hanya demo publik): pilih peran. Hak akses ditegakkan di server (api.require), bukan hanya di tampilan.
import { api } from "../api.js";
import { btn, clear, h, icon, setBusy } from "../dom.js";

const ICON = { operator: "eye-off", analis: "user-check", admin: "server" };
const DEMO_NAMA = { operator: "Serda Rina", analis: "Lettu Andi", admin: "Kapten Dimas" };

export async function render(page, _params, ctx) {
  const d = await api.get("/api/peran");
  clear(page);
  if (!d.wajib) {
    page.append(h("div", { class: "page-head" }, h("div", { class: "titles" }, h("h1", null, "Masuk"),
      h("div", { class: "sub" }, "Aplikasi desktop dipakai satu operator di laptop posko, jadi tidak memakai login."))));
    return;
  }
  let chosen = d.masuk ? d.masuk.peran : "analis";
  const nama = h("input", { class: "input", maxlength: "80", value: d.masuk ? d.masuk.nama : DEMO_NAMA[chosen], "aria-label": "Nama tampilan" });
  const cards = h("div", { class: "role-grid", role: "radiogroup", "aria-label": "Pilih peran" });
  function draw() {
    clear(cards).append(...d.peran.map((p) => h("button", { type: "button", role: "radio", class: "role-card", "aria-checked": String(p.id === chosen),
      onclick: () => { const auto = Object.values(DEMO_NAMA).includes(nama.value); chosen = p.id; if (auto) nama.value = DEMO_NAMA[p.id]; draw(); } },
      h("span", { class: "role-ic" }, icon(ICON[p.id] || "user")),
      h("b", null, p.label), h("span", { class: "role-desc" }, p.tugas),
      h("span", { class: "role-perm" }, p.izin.includes("tinjau") ? "boleh menyetujui aksi" : "tidak bisa menyetujui aksi"))));
  }
  draw();
  const go = btn("Masuk", { icon: "arrow-right", cls: "primary lg" });
  go.addEventListener("click", async () => {
    setBusy(go, true, "Masuk");
    try {
      const m = await api.post("/api/masuk", { peran: chosen, nama: nama.value.trim() });
      await ctx.refreshPeran();
      ctx.toast(`Masuk sebagai ${m.label}: ${m.nama}. Tercatat di jejak audit.`);
      ctx.go(m.izin.includes("demo") ? "#/demo" : "#/antrean");
    } catch (e) { ctx.toast(e.message, "bad"); setBusy(go, false); }
  });
  page.append(h("div", { class: "signin" },
    h("div", { class: "signin-head" },
      h("span", { class: "brand-mark lg", "aria-hidden": "true" }, icon("shield-check")),
      h("div", { class: "eyebrow" }, "Demo publik · data sintetis"),
      h("h1", null, "Masuk ke PERISAI-RESPON"),
      h("p", { class: "sub" }, "Pilih peran untuk mencoba pembagian tugas. Server menolak aksi di luar hak peran, misalnya admin tidak bisa menyetujui isolasi.")),
    cards,
    h("div", { class: "signin-foot" },
      h("label", { class: "field" }, h("span", null, "Nama tampilan (fiktif)"), nama),
      go),
    h("p", { class: "small muted signin-note" }, "Tanpa kata sandi karena ini demo. Di satuan, peran diikat ke akun dan masuk tercatat di jejak audit, sama seperti di sini.")));
}
