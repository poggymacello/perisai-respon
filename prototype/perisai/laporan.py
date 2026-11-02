"""Laporan insiden untuk CSIRT (Markdown) dari keputusan v1.1 + jejak audit berantai hash.

Teks bebas log (command line, script) TIDAK disalin ke laporan: bisa memuat instruksi penyerang dan string alat
serang yang ditandai antivirus. Laporan menunjuk event lewat field terstruktur + id, analis membuka log asli.
"""

from __future__ import annotations

from .logs import STRUCTURED_FIELDS

_SHOW = ["EventID", "Channel", "TimeCreated", "Hostname", "SubjectUserName", "TargetUserName", "LogonType", "Image",
         "ParentImage", "TargetImage", "SourceImage", "GrantedAccess", "SourceIp", "DestinationIp", "DestinationPort",
         "IpAddress", "ServiceName", "TargetObject", "TargetFilename", "ObjectName", "ShareName"]
assert set(_SHOW) <= set(STRUCTURED_FIELDS)


def _cell(v) -> str:
    return str(v).replace("|", "\\|").replace("\n", " ")[:120]


def render(run: dict, items: list[dict], audit_verify: dict, audit_entries: list[dict]) -> str:
    """run: metadata eksekusi; items: [{'case':..., 'decision': decide_v11 dict}]."""
    by_case: dict[str, list[dict]] = {}
    for e in audit_entries:
        by_case.setdefault(e["case_id"], []).append(e)
    L = [f"# Laporan Insiden PERISAI-RESPON · {run['waktu']}", "",
         "> Dibuat otomatis. Semua aksi berisiko **menunggu persetujuan analis**; tidak ada aksi yang dijalankan sistem.", "",
         "| | |", "|---|---|",
         f"| Sumber log | {_cell(run['sumber'])} |",
         f"| Jumlah event / kasus | {run['n_event']} / {len(items)} (+{run.get('n_tanpa_temuan', 0)} kelompok event tanpa temuan aturan, tidak dibuat kasus) |",
         f"| LLM | {run['llm']} |",
         f"| Integritas model | {run['model_check']} |",
         f"| Audit | {audit_verify['entries']} entri, utuh = **{audit_verify['ok']}**, head `{audit_verify['head']}` |",
         "", "## Ringkasan", "",
         "| # | Kasus | Host | Kategori | Aksi akhir | Status | Peringatan |", "|---|---|---|---|---|---|---|"]
    for n, it in enumerate(items, 1):
        c, d = it["case"], it["decision"]
        fa = d["final_action"]
        aksi = fa["jenis"] + (f" → {fa['target']}" if fa.get("target") else "")
        L.append(f"| {n} | {_cell(c['case_id'])} | {_cell(c.get('primary_host') or '-')} | {d['kategori']} | {aksi} | "
                 f"{d['final_status']} | {', '.join(d['warnings']) or '-'} |")
    for n, it in enumerate(items, 1):
        c, d = it["case"], it["decision"]
        L += ["", f"## {n}. {_cell(c['case_id'])}", "",
              f"**Ringkasan aturan:** {d['ringkasan']}", ""]
        if d.get("draf_ai"):
            L += [f"**DRAF AI (disaring, bukan dasar keputusan):** {d['draf_ai']}", ""]
        if d.get("kalimat_dibuang"):
            L += [f"Kalimat draf AI yang dibuang: {len(d['kalimat_dibuang'])}", ""]
        L += ["**Alasan keputusan:**"] + [f"- {_cell(r)}" for r in d["reasons"]] + ["", "**Bukti (field terstruktur):**", "",
              "| id | " + " | ".join(f for f in _SHOW if any(f in e for e in c["events"])) + " |"]
        cols = [f for f in _SHOW if any(f in e for e in c["events"])]
        L.append("|---|" + "---|" * len(cols))
        for e in c["events"]:
            L.append(f"| {e['id']} | " + " | ".join(_cell(e.get(f, "")) for f in cols) + " |")
        ae = by_case.get(c["case_id"], [])
        if ae:
            L += ["", "**Jejak audit:** " + ", ".join(f"#{e['seq']} {e['kind']} `{e['entry_hash'][:16]}`" for e in ae)]
        L += ["", "Persetujuan analis: ☐ setuju ☐ tolak · nama/NRP: `[[...]]` · waktu: `[[...]]`"]
    L += ["", "---", "Teks bebas log tidak disalin ke laporan. Buka log asli dengan id event di atas. "
          f"Cek audit: `python -I triase.py --verify {run['audit_path']}`"]
    return "\n".join(L) + "\n"
