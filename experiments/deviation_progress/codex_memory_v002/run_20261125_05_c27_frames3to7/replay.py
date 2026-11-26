"""Fork five C27 terminal reviews with three to seven additional interval frames."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
from experiments.deviation_progress.codex_memory_v002.run_20261125_04_c27_interval7.replay import BASE, run_comparison

if __name__ == "__main__":
    run_comparison(BASE / HERE.name, (7, 6, 5, 4, 3), 4, Path(__file__))
