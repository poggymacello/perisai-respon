// Teks lisensi dan deklarasi. Disalin dari README.md repo (bagian "Lisensi dan asal-usul" dan "Deklarasi").
// Ubah di sini bila README berubah.
export const LICENSES = [
  ["PERISAI-RESPON (kode repo dan aplikasi ini)", "MIT"],
  ["Kendali: policy engine, pola injeksi, audit berantai (diadaptasi)", "MIT, Poggy Macello Gultom & Mohammad Ari Alexander Aziz"],
  ["Qwen2.5-1.5B-Instruct (model opsional, tidak dibundel)", "Apache-2.0"],
  ["llama.cpp / llama-cpp-python", "MIT"],
  ["OTRF Security-Datasets (data evaluasi, tidak dibundel)", "MIT"],
  ["HAI Security Dataset 21.03 (ETRI, data evaluasi OT, tidak dibundel)", "CC BY-SA 4.0"],
  ["FastAPI, Starlette, Pydantic, Uvicorn", "MIT / BSD-3-Clause"],
  ["pywebview, pythonnet", "BSD-3-Clause / MIT"],
  ["NumPy, pandas", "BSD-3-Clause"],
  ["Ikon Lucide 0.460.0", "ISC (bagian dari Feather: MIT)"],
];

export const NOTE_LLAMA = "Model Llama tidak dipakai karena lisensinya melarang penggunaan militer.";

export const DECLARATION = [
  ["Karya pre-existing", "Komponen Kendali di atas sudah ada sebelum Program. Kendali juga diikutkan di FinTechathon 2026. Domain SOC, jalur injeksi lewat log, mode offline, jalur OT, importer, dan seluruh evaluasi dikerjakan sejak 29 Okt 2026."],
  ["Alat bantu AI saat pengembangan", "Sebagian besar kode, dokumen, dan analisis disusun dengan bantuan asisten AI generatif, dengan arahan dan pemeriksaan tim."],
  ["Data", "Hanya log publik berlabel dan event demo sintetis. Tidak ada data satuan atau data pribadi."],
];

export const DEFENSIVE = "Proyek ini hanya defensif. String injeksi adalah string uji dengan host/IP fiktif dan domain .invalid.";
