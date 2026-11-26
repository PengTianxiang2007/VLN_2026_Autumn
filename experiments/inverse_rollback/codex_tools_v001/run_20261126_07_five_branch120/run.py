"""Launch the five branch-entry trials on the retained H1, with one budget per episode."""
from pathlib import Path
import runpy


HERE = Path(__file__).resolve().parent


if __name__ == "__main__":
    queue = runpy.run_path(str(HERE.parent / "run_20261126_06_four_region60/queue.py"))
    queue["main"](experiment=HERE, initial_episode="kujiale_0165_53_0", move_limit=120,
                  prompt_template=HERE / "prompt.txt", objective="branch_entry")
