"""Compatibility wrapper for the project-owned persistent runtime restoration."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).resolve().parents[3] / "scripts/restore_isaac.py"), run_name="__main__")
