# Menerbitkan demo publik PERISAI-RESPON

Demo publik menjalankan aplikasi dengan `PERISAI_MODE=demo`. Dalam mode ini:
- yang dimuat hanya log contoh sintetis (host fiktif `*.batalyon.lab`), dan tiap pengunjung mendapat sesi sendiri lewat cookie;
- **unggah log ditolak** (HTTP 403) sebelum isi berkas dibaca. Alasannya, server publik tidak boleh menerima log asli satuan, sedangkan log asli diperiksa di aplikasi desktop yang offline;
- LLM mati, tidak ada model di image, dan triase memakai mode aturan;
- server mendengar di `0.0.0.0:7860`, port bawaan Hugging Face Spaces. Variabel `PORT` dipakai bila disediakan platform.

Langkah yang butuh akun (membuat akun, login, push) dikerjakan manusia. Agen tidak mengunggah apa pun.

## 0. Uji di laptop sendiri (Docker Desktop)
Dari akar repo:
```powershell
docker build -f app/Dockerfile -t perisai-respon-demo:1.0.0 .
docker run --rm -p 127.0.0.1:7860:7860 perisai-respon-demo:1.0.0
```
Buka http://127.0.0.1:7860. Sejak 15 Nov 2026, di mode demo `/` menampilkan **landing page** (dengan konsol serangan yang memanggil mesin asli), dan aplikasinya ada di **http://127.0.0.1:7860/app/**. Di `/app/` yang harus terlihat: label **Demo publik · data sintetis** di kanan atas, 10 kasus di antrean, dan pesan "Unggah log dinonaktifkan" di halaman Impor log. Image sudah dibangun dan diuji dengan cara ini pada 2 Nov 2026 (ukuran 426 MB; status healthcheck `healthy`; `POST /api/impor` dijawab 403).

## A. Hugging Face Spaces (SDK Docker, gratis, CPU basic)
1. Login ke https://huggingface.co, lalu **New Space**.
   - Space name: `perisai-respon-demo`
   - License: MIT
   - SDK: **Docker**, template **Blank**
   - Hardware: **CPU basic** (gratis)
   - Visibility: **Public**
2. Siapkan folder Space dari repo ini:
   ```powershell
   app\.venv\Scripts\python -I app\tools\make_space.py
   ```
   Hasilnya `app\dist\space\`, berisi `Dockerfile` di akar, `README.md` dengan metadata Space (`sdk: docker`, `app_port: 7860`), `requirements.txt`, `prototype/perisai/` (salinan mesin, tidak diubah), `app/perisai_app/`, dan `app/frontend/`.
3. Push ke repo git Space. Gunakan token akses Hugging Face dengan izin *write* sebagai password:
   ```powershell
   git clone https://huggingface.co/spaces/<USERNAME>/perisai-respon-demo hf-space
   Copy-Item -Recurse -Force app\dist\space\* hf-space\
   cd hf-space
   git add -A
   git commit -m "PERISAI-RESPON 1.0.0 demo publik (data sintetis, unggah dimatikan)"
   git push
   ```
4. Tunggu tab **Logs** sampai build selesai (±2-4 menit). Alamat demonya `https://<USERNAME>-perisai-respon-demo.hf.space`.
5. Periksa di browser: `/` menampilkan landing page, dan konsol serangan di hero berlabel "mesin asli". Lalu buka `/app/`: label demo di kanan atas, 10 kasus contoh, dan upload yang ditolak. Di **Status sistem**, mode harus "demo publik", dan integritas kode mesin harus "cocok dengan hash beku".

Catatan: Space gratis tidur setelah lama tidak dikunjungi, jadi kunjungan pertama bisa butuh ±30 detik. Sesi pengunjung disimpan di `/tmp` kontainer dan hilang saat Space dimulai ulang. Itu sesuai untuk demo.

## B. Alternatif: Render (Web Service, Docker)
1. Login ke https://render.com, lalu **New** → **Web Service**, dan hubungkan repo GitHub publik proyek ini.
2. Isi:
   - Runtime / Language: **Docker**
   - Dockerfile path: `app/Dockerfile`
   - Docker build context: `.` (akar repo)
   - Instance type: Free
   - Health check path: `/api/ping`
3. Render memberi variabel `PORT`, dan server membacanya. Variabel lain sudah diset di Dockerfile (`PERISAI_MODE=demo`).
4. Setelah deploy, periksa hal yang sama seperti langkah A.5.

## Yang tidak boleh diubah di server publik
- Jangan menghapus `PERISAI_MODE=demo`. Tanpa itu, server berjalan di mode desktop, yang memang hanya mau mendengar di 127.0.0.1 dan menerima unggahan.
- Jangan menaruh model atau log asli di image.
- Jangan memasang eksportir OpenTelemetry. Integrasi telemetri FastAPI sengaja dimatikan di `perisai_app/api.py`.

## Pembaruan
Ubah kode, jalankan ulang `app\tools\make_space.py`, salin lagi ke folder `hf-space`, lalu commit dan push. Render membangun ulang otomatis setiap ada push ke cabang yang dipilih.
