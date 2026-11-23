"""Build the first-pass RGB/map review cards after an R2R recording is complete."""
import argparse
import json
import math
from pathlib import Path

from review_rxr_crossing_failures import prepare_cards


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    status = json.loads((args.source / "status.json").read_text())
    if status["state"] != "complete":
        parser.exit(1, f"Recording ended with state {status['state']}.\n")
    scores = [json.loads(row) for row in (args.source / "result.json").read_text().splitlines()]
    metrics = ("success", "spl", "ne", "os")
    failures = [row for row in scores if row["success"] == 0 and
                all(math.isfinite(row[key]) for key in metrics)]
    if len(failures) != status["scored"] - status["successes"]:
        raise ValueError("Failure count differs from the completed recording")
    prepare_cards(args.source, args.output, failures)


if __name__ == "__main__":
    main()
