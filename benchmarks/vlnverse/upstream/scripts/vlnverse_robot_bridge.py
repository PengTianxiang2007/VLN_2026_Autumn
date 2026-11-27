"""Expose the project H1 bridge when VLNVerse owns the ``scripts`` package.

The evaluator imports this package before recovery. Resolve the existing bridge
from its project directory instead of depending on namespace-package ordering.
"""
from pathlib import Path
import sys

_project_scripts = str(Path(__file__).resolve().parents[4] / "scripts")
sys.path.insert(0, _project_scripts)
try:
    from vlnverse_robot_bridge import serve
finally:
    sys.path.remove(_project_scripts)
