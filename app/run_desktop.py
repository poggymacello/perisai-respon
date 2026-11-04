"""Titik masuk PyInstaller / dev: python app\\run_desktop.py [--browser|--headless]."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from perisai_app.desktop import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
