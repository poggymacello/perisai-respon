"""Bangun sprite SVG dari ikon Lucide (lucide-static, ISC) yang dipakai aplikasi.

    npm pack lucide-static@0.460.0 && tar xzf lucide-static-0.460.0.tgz
    app\\.venv\\Scripts\\python -I app\\tools\\build_icons.py <folder package/>

Keluaran: app/frontend/vendor/lucide/icons.svg + LICENSE (disalin dari paket).
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ICONS = ["inbox", "upload", "file-text", "link-2", "activity", "info", "search", "check", "x", "triangle-alert",
         "chevron-left", "chevron-right", "download", "refresh-cw", "play", "loader-circle", "cpu", "folder-open",
         "printer", "clock", "archive", "flask-conical", "circle-check", "circle-x", "file-up", "list-checks", "server",
         "hash", "gauge", "sparkles", "square-pen", "ban", "user", "eye-off", "database", "power", "file-down", "filter"]
OUT = Path(__file__).resolve().parents[1] / "frontend" / "vendor" / "lucide"


def main(pkg: Path) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    syms = []
    for name in ICONS:
        p = pkg / "icons" / f"{name}.svg"
        if not p.exists():
            raise SystemExit(f"ikon tidak ada: {name}")
        svg = p.read_text(encoding="utf-8")
        svg = re.sub(r"<!--.*?-->", "", svg, flags=re.S)
        body = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.S).group(1).strip()
        body = re.sub(r"\s+", " ", body)
        syms.append(f'<symbol id="i-{name}" viewBox="0 0 24 24">{body}</symbol>')
    sprite = ('<svg xmlns="http://www.w3.org/2000/svg">\n'
              "<!-- Lucide 0.460.0 (ISC), https://lucide.dev, lihat LICENSE di folder ini -->\n" + "\n".join(syms) + "\n</svg>\n")
    (OUT / "icons.svg").write_text(sprite, encoding="utf-8")
    shutil.copy(pkg / "LICENSE", OUT / "LICENSE")
    print(f"{len(syms)} ikon -> {OUT / 'icons.svg'}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
