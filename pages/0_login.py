from __future__ import annotations

import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT / "frontend" / "pages" / "0_login.py"), run_name="__main__")
