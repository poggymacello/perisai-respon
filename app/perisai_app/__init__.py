"""PERISAI-RESPON aplikasi desktop/web: antarmuka analis di atas mesin `perisai` (prototype/perisai, v1.2.2).

Mesin tidak diubah. Aplikasi ini hanya memanggilnya sebagai pustaka: impor log -> kasus -> keputusan v1.2.2 ->
audit berantai hash -> laporan CSIRT. Persetujuan analis hanya dicatat di audit, tidak pernah dieksekusi ke sistem.
"""

APP_NAME = "PERISAI-RESPON"
APP_VERSION = "1.0.0"
ENGINE_VERSION = "1.2.2"  # perisai/v12.py (decide_v12 + guard_draft), lihat frozen/CODE_V12_posthoc.sha256
