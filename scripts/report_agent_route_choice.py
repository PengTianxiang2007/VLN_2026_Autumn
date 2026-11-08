"""Review and score local route decisions, with evaluation labels isolated from inference."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.agent_route_choice import (file_hash, now, read, string_list, text,
                                     validate_choice, validate_inventory, write)


def load_run(prepared, run):
    manifest = read(run / 'manifest.json')
    if manifest['prepared_manifest_sha256'] != file_hash(prepared / 'manifest.json'):
        raise ValueError('Run belongs to a different prepared dataset')
    frozen = read(prepared / 'manifest.json')['files_sha256']
    for name in ('dataset.json', 'evaluation_only.json'):
        if frozen[name] != file_hash(prepared / name):
            raise ValueError('Frozen input or evaluation labels changed')
    cases = read(prepared / 'dataset.json')['cases']
    if manifest['sample_order'] != [c['sample_id'] for c in cases]:
        raise ValueError('Run sample order differs')
    return cases


def create_review(prepared, run, destination):
    if destination.exists():
        raise FileExistsError('Use a new review filename')
    cases = load_run(prepared, run)
    labels = {c['sample_id']: c for c in read(prepared / 'evaluation_only.json')['labels']}
    reviews = []
    for case in cases:
        folder = run / 'cases' / case['sample_id']
        first, second = folder / 'call1_answer.json', folder / 'call2_answer.json'
        inventory = read(first) if first.exists() else None
        reviews.append({'sample_id': case['sample_id'], 'episode_id': labels[case['sample_id']]['episode_id'],
                        'expected_route': labels[case['sample_id']]['expected_route'],
                        'wrong_route': labels[case['sample_id']]['wrong_route'],
                        'call1_answer_sha256': file_hash(first) if first.exists() else None,
                        'call2_answer_sha256': file_hash(second) if second.exists() else None,
                        'reviewed': False, 'reviewer': '', 'evidence_ids': [], 'notes': '',
                        'branch_matches': {b['id']: None for b in inventory['branches']} if inventory else {},
                        'error_reason_supported': None})
    write(destination, {'run_manifest_sha256': file_hash(run / 'manifest.json'),
                         'prepared_manifest_sha256': file_hash(prepared / 'manifest.json'),
                         'mapping_values': ['expected_route', 'wrong_route', 'other', 'unclear'],
                         'instructions': 'Map predicted branch IDs using the frozen labels and actual RGB; evaluate meanings, not literal left/right from map captions. Do not rewrite labels to favor predictions. Fill every branch match, reviewer, evidence, notes and error_reason_supported for each reviewed result.',
                         'cases': reviews})


def score(prepared, run, review, destination):
    if destination.exists():
        raise FileExistsError('Do not overwrite a prior score')
    cases = load_run(prepared, run)
    grades = read(review)
    if grades['run_manifest_sha256'] != file_hash(run / 'manifest.json') or grades['prepared_manifest_sha256'] != file_hash(prepared / 'manifest.json'):
        raise ValueError('Review belongs to different inputs or run')
    ids = [c['sample_id'] for c in grades['cases']]
    if ids != [c['sample_id'] for c in cases]:
        raise ValueError('Review must cover the ten fixed samples in order')
    rows = []
    for case, grade in zip(cases, grades['cases']):
        folder = run / 'cases' / case['sample_id']
        first, second = folder / 'call1_answer.json', folder / 'call2_answer.json'
        for path, field in [(first, 'call1_answer_sha256'), (second, 'call2_answer_sha256')]:
            if grade[field] != (file_hash(path) if path.exists() else None):
                raise ValueError('Answers changed since review template was created')
        state = read(folder / 'status.json') if (folder / 'status.json').exists() else {'phase': 'pending'}
        row = {'sample_id': case['sample_id'], 'phase': state['phase'], 'reviewed': False}
        if first.exists() and second.exists():
            inventory, choice = read(first), read(second)
            validate_inventory(inventory, [im['id'] for im in case['images'] if im['phase'] == 'checkpoint_context'])
            validate_choice(choice, inventory, [im['id'] for im in case['images']], case['instruction'])
            row['selected'] = choice['status'] == 'selected'
            if type(grade['reviewed']) is not bool:
                raise ValueError('reviewed must be boolean')
            if grade['reviewed']:
                text(grade['reviewer']); text(grade['notes'])
                string_list(grade['evidence_ids'], [im['id'] for im in case['images']], nonempty=True)
                matches = grade['branch_matches']
                if not isinstance(matches, dict) or set(matches) != {b['id'] for b in inventory['branches']}:
                    raise ValueError('Every predicted branch needs an explicit semantic match')
                if any(x not in ('expected_route', 'wrong_route', 'other', 'unclear') for x in matches.values()):
                    raise ValueError('Unfinished semantic branch review')
                if type(grade['error_reason_supported']) is not bool:
                    raise ValueError('Explicit evidence-grounded error explanation review required')
                wrong = matches.get(choice['wrong_branch_id']) == 'wrong_route'
                correct = matches.get(choice['selected_branch_id']) == 'expected_route'
                row.update(reviewed=True, inventory_covers_both=('expected_route' in matches.values() and 'wrong_route' in matches.values()),
                           wrong_branch_correct=wrong, chosen_branch_correct=correct,
                           error_reason_supported=grade['error_reason_supported'], joint_correct=wrong and correct)
        rows.append(row)
    pending = sum(r['phase'] == 'pending' for r in rows)
    answered = sum('selected' in r for r in rows)
    reviewed = sum(r['reviewed'] for r in rows)
    # Request failures and abstentions count against all-ten success only once all
    # available answers are actually reviewed. Missing reviews never become failures.
    complete = pending == 0 and reviewed == answered
    keys = ['inventory_covers_both', 'wrong_branch_correct', 'chosen_branch_correct', 'error_reason_supported', 'joint_correct']
    counts = {key: sum(r.get(key, False) for r in rows) for key in keys}
    summary = {'phase': 'scored' if complete else 'review_incomplete', 'created_at': now(),
               'fixed_denominator': 10, 'answered_samples': answered, 'reviewed_samples': reviewed,
               'pending_samples': pending, 'selected_samples': sum(r.get('selected', False) for r in rows),
               'reviewed_counts': counts, 'all_ten_rates': {k: v / 10 for k, v in counts.items()} if complete else None,
               'review_sha256': file_hash(review), 'run_manifest_sha256': file_hash(run / 'manifest.json'),
               'interpretation': 'Offline local branch choice at known crossings after known wrong attempts; not navigation SR.', 'cases': rows}
    write(destination, summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['review-template', 'score'])
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--review', type=Path)
    args = parser.parse_args()
    if args.command == 'review-template':
        create_review(args.prepared, args.run, args.destination)
    else:
        if args.review is None:
            parser.error('score requires --review')
        score(args.prepared, args.run, args.review, args.destination)


if __name__ == '__main__':
    main()
