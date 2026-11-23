"""Prepare the fixed divergence-anchor Oracle and same-task native baseline; CPU only."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.oracle_auto_branch import PROTOCOL
from core.paths import resource_root
from scripts.prepare_oracle_auto_route import prepare, read_episode_ids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--episode-ids-file', type=Path, required=True)
    parser.add_argument('--official-split', type=Path,
                        default=resource_root()/'assets/VLNVerse/data/raw_data/final_splits/fine_val_unseen.json.gz')
    parser.add_argument('--config', type=Path,
                        default=ROOT/'experiments/oracle_recovery/auto_branch_v001/config.json')
    parser.add_argument('--expected-episodes', type=int)
    parser.add_argument('--geometry-root', type=Path,
                        help='Optional CPU scene geometry source. Audit only: never chooses or changes a landing.')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    ids = read_episode_ids(args.episode_ids_file)
    if args.expected_episodes is not None and len(ids) != args.expected_episodes:
        parser.error('Episode count does not match --expected-episodes')
    manifest = prepare(args.official_split, ids, json.loads(args.config.read_text()), args.output,
                       protocol=PROTOCOL, geometry_root=args.geometry_root)
    print(json.dumps(dict(output=str(args.output.resolve()), protocol=PROTOCOL,
                         episodes=manifest['episodes'], arms=list(manifest['arms']), simulation_started=False), indent=2))


if __name__ == '__main__':
    main()
