"""Markdown laporan CSIRT (keluaran perisai.laporan) -> HTML statis yang bisa dicetak / disimpan PDF.

Hanya subset yang dipakai laporan: judul, kutipan, tabel, daftar, tebal, kode, garis. Semua teks di-escape
lebih dulu, jadi isi log tidak bisa menyisipkan HTML.
"""

from __future__ import annotations

import html
import re

_BOLD = re.compile(r"\*\*(.+?)\*\*")
_CODE = re.compile(r"`([^`]+)`")
_SPLIT = re.compile(r"(?<!\\)\|")


def _inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = _CODE.sub(r"<code>\1</code>", s)
    s = _BOLD.sub(r"<strong>\1</strong>", s)
    return s.replace("\\|", "|")


def _cells(line: str) -> list[str]:
    parts = _SPLIT.split(line.strip())
    if parts and parts[0] == "":
        parts = parts[1:]
    if parts and parts[-1] == "":
        parts = parts[:-1]
    return [p.strip() for p in parts]


def md_to_html(md: str) -> str:
    out: list[str] = []
    lines = md.splitlines()
    i = 0
    para: list[str] = []

    def flush():
        if para:
            out.append("<p>" + " ".join(_inline(p) for p in para) + "</p>")
            para.clear()

    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not s:
            flush()
            i += 1
            continue
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\|(\s*:?-+:?\s*\|)+\s*$", lines[i + 1].strip()):
            flush()
            head = _cells(s)
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_cells(lines[i]))
                i += 1
            empty_head = all(not h for h in head)
            t = ['<div class="tbl"><table>']
            if not empty_head:
                t.append("<thead><tr>" + "".join(f"<th>{_inline(h)}</th>" for h in head) + "</tr></thead>")
            t.append("<tbody>")
            for r in rows:
                t.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>")
            t.append("</tbody></table></div>")
            out.append("".join(t))
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            flush()
            n = len(m.group(1))
            out.append(f"<h{n}>{_inline(m.group(2))}</h{n}>")
        elif s.startswith(">"):
            flush()
            out.append(f"<blockquote>{_inline(s.lstrip('> '))}</blockquote>")
        elif s == "---":
            flush()
            out.append("<hr>")
        elif s.startswith("- "):
            flush()
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(f"<li>{_inline(lines[i].strip()[2:])}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        else:
            para.append(s)
        i += 1
    flush()
    return "\n".join(out)


PRINT_CSS = """
body{font-family:"Segoe UI",system-ui,-apple-system,sans-serif;color:#1b1f24;margin:32px auto;max-width:1100px;
font-size:13px;line-height:1.5;padding:0 24px;background:#fff}
h1{font-size:20px;margin:0 0 12px}h2{font-size:16px;margin:28px 0 8px;padding-top:12px;border-top:1px solid #d0d4da}
blockquote{margin:8px 0;padding:8px 12px;border-left:3px solid #0f62ad;background:#f3f6fa}
.tbl{overflow-x:auto}table{border-collapse:collapse;width:100%;margin:8px 0;font-size:12px}
th,td{border:1px solid #d0d4da;padding:4px 8px;text-align:left;vertical-align:top}th{background:#f1f3f5}
code{font-family:"Cascadia Mono",Consolas,monospace;font-size:11.5px;background:#f1f3f5;padding:0 3px}
hr{border:0;border-top:1px solid #d0d4da;margin:24px 0}
@media print{body{margin:0;max-width:none}h2{break-after:avoid}tr{break-inside:avoid}}
"""


def standalone_html(md: str, title: str) -> str:
    return ("<!doctype html><html lang=\"id\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" "
            "content=\"width=device-width, initial-scale=1\"><title>" + html.escape(title) + "</title><style>"
            + PRINT_CSS + "</style></head><body>" + md_to_html(md) + "</body></html>")
