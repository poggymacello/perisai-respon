// Masuk (hanya demo publik), tata letak seperti halaman masuk PRAXIS: form di kiri, panel merek di kanan.
// Email + sandi diperiksa server; akun demo bisa dipakai sekali klik. Hak akses tetap ditegakkan server.
import { api } from "../api.js";
import { clear, h, icon } from "../dom.js";

function initials(n) { return n.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join(""); }

export async function render(page, _params, ctx) {
  const d = await api.get("/api/peran");
  clear(page);
  if (!d.wajib) {
    page.append(h("div", { class: "page-head" }, h("div", { class: "titles" }, h("h1", null, "Masuk"),
      h("div", { class: "sub" }, "Aplikasi desktop dipakai satu operator di laptop posko, jadi tidak memakai login."))));
    return;
  }

  const err = h("p", { class: "login-err", role: "alert", hidden: true });
  const email = h("input", { class: "login-input", type: "email", autocomplete: "username", placeholder: "nama@satuan.example", "aria-label": "Email dinas" });
  const sandi = h("input", { class: "login-input", type: "password", autocomplete: "current-password", placeholder: "Sandi Anda", "aria-label": "Sandi" });
  const eye = h("button", { type: "button", class: "login-eye", "aria-label": "Tampilkan sandi" }, icon("eye"));
  eye.addEventListener("click", () => {
    const show = sandi.type === "password";
    sandi.type = show ? "text" : "password";
    clear(eye).append(icon(show ? "eye-off" : "eye"));
    eye.setAttribute("aria-label", show ? "Sembunyikan sandi" : "Tampilkan sandi");
  });
  const submit = h("button", { type: "submit", class: "login-submit", disabled: true }, h("span", null, "Masuk"), icon("arrow-right"));
  const sync = () => { submit.disabled = !email.value.trim() || !sandi.value; };
  email.addEventListener("input", sync); sandi.addEventListener("input", sync);

  let busy = false;
  async function signIn(creds, who) {
    if (busy) return;
    busy = true; err.hidden = true;
    page.querySelectorAll("button").forEach((b) => { b.disabled = true; });
    if (who) who.querySelector(".acc-name").textContent = "Sedang masuk";
    else submit.firstChild.textContent = "Sedang masuk";
    try {
      const m = await api.post("/api/masuk", creds);
      await ctx.refreshPeran();
      ctx.toast(`Masuk sebagai ${m.nama} (${m.label}). Tercatat di jejak audit.`);
      ctx.go(m.izin.includes("demo") ? "#/demo" : "#/antrean");
    } catch (e) {
      busy = false;
      err.textContent = e.status === 401 ? "Email atau sandi salah." : (e.message || "Tidak bisa masuk. Coba lagi.");
      err.hidden = false;
      email.classList.add("bad"); sandi.classList.add("bad");
      page.querySelectorAll("button").forEach((b) => { b.disabled = false; });
      sync();
      if (who) who.querySelector(".acc-name").textContent = who.dataset.nama;
      else submit.firstChild.textContent = "Masuk";
    }
  }

  const form = h("form", { class: "login-fields", novalidate: true },
    h("label", null, "Email dinas", email),
    h("label", null, "Sandi", h("span", { class: "login-pw" }, sandi, eye)),
    err, submit);
  form.addEventListener("submit", (e) => { e.preventDefault(); signIn({ email: email.value.trim(), sandi: sandi.value }); });

  const demo = d.akun.length && d.sandi_demo ? h("div", { class: "login-demo" },
    h("div", { class: "login-or" }, h("span"), "Coba akun demo", h("span")),
    h("ul", null, d.akun.map((a) => {
      const b = h("button", { type: "button", class: "acc", dataset: { nama: a.nama } },
        h("span", { class: "acc-av" }, initials(a.nama)),
        h("span", { class: "acc-t" }, h("span", { class: "acc-name" }, a.nama), h("span", { class: "acc-sub" }, `${a.jabatan}: ${a.tugas}`)),
        icon("arrow-right"));
      b.addEventListener("click", () => signIn({ email: a.email, sandi: d.sandi_demo }, b));
      return h("li", null, b);
    })),
    h("p", { class: "login-hint" }, "Sandi demo untuk semua akun: ", h("code", null, d.sandi_demo))) : null;

  page.append(h("div", { class: "login" },
    h("section", { class: "login-left" },
      h("a", { class: "login-logo", href: "/", "aria-label": "Kembali ke halaman depan PERISAI-RESPON" },
        h("span", { class: "brand-mark" }, icon("shield-check")), h("b", null, "PERISAI", h("span", null, "-RESPON"))),
      h("div", { class: "login-box" },
        h("h1", null, "Selamat datang"),
        h("p", { class: "login-lead" }, "Masuk untuk melihat kasus yang perlu Anda tangani."),
        form, demo),
      h("p", { class: "login-foot" }, icon("shield-check"), "Di satuan, masuk memakai akun dinas dan setiap masuk tercatat di jejak audit. Data demo ini sintetis.")),
    h("aside", { class: "login-art", "aria-hidden": "true" },
      h("div", { class: "login-art-in" },
        h("p", { class: "login-art-h" }, "Ubah setiap log menjadi keputusan yang bisa dipertanggungjawabkan dengan ",
          h("span", { class: "login-art-logo" }, h("span", { class: "brand-mark" }, icon("shield-check")), "PERISAI")),
        h("ul", null,
          h("li", null, "Isi log diperlakukan sebagai data, tidak pernah sebagai perintah"),
          h("li", null, "Aksi berisiko diputuskan aturan dan disetujui analis, bukan AI"),
          h("li", null, "Setiap langkah terikat rantai hash SHA-256 yang bisa diverifikasi"))))));
  email.focus();
}
