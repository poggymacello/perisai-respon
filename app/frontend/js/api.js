// Klien REST. Semua permintaan ke server lokal yang sama (CSP connect-src 'self').
export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function call(method, path, body, isForm = false) {
  const opts = { method, headers: { Accept: "application/json" }, credentials: "same-origin" };
  if (method !== "GET") opts.headers["X-Perisai"] = "1";
  if (body !== undefined) {
    if (isForm) opts.body = body;
    else {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
  }
  let res;
  try {
    res = await fetch(path, opts);
  } catch (e) {
    throw new ApiError(0, "Server lokal tidak menjawab. Jalankan ulang aplikasi bila berlanjut.");
  }
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = null; }
  if (!res.ok) {
    let msg = data && data.detail;
    if (Array.isArray(msg)) msg = msg.map((d) => `${(d.loc || []).slice(1).join(".")}: ${d.msg}`).join("; ");
    throw new ApiError(res.status, msg || `Galat ${res.status}`);
  }
  return data;
}

export const api = {
  get: (p) => call("GET", p),
  post: (p, b) => call("POST", p, b === undefined ? {} : b),
  form: (p, fd) => call("POST", p, fd, true),
};

// Unduh berkas: di jendela desktop lewat dialog Simpan (pywebview), di browser lewat tautan biasa.
export async function download(path, filename) {
  const pv = window.pywebview && window.pywebview.api && window.pywebview.api.simpan;
  if (pv) {
    const r = await window.pywebview.api.simpan(path, filename);
    if (r && r.ok) return `Disimpan ke ${r.path}`;
    if (r && r.batal) return null;
    throw new ApiError(0, (r && r.galat) || "gagal menyimpan berkas");
  }
  const a = document.createElement("a");
  a.href = path;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  return `Mengunduh ${filename}`;
}
