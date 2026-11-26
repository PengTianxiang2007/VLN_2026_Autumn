"""Repeat the five C27 reviews with reversed submission order and identical inputs."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
from experiments.deviation_progress.codex_memory_v002.run_20261125_04_c27_interval7.replay import BASE, run_comparison

if __name__ == "__main__":
    run_comparison(BASE / HERE.name, (3, 4, 5, 6, 7), 4, Path(__file__))
