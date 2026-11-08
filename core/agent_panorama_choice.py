"""Strict, map-free request and response contracts for Crossing route-choice v002."""
import base64
import json
from pathlib import Path
from core.agent_route_choice import (DIRECTIONS, digest, exact_keys, file_hash, read,
                                     string_list, text, validate_case as validate_old_case)


def schema(stage):
    s = {'type': 'string'}
    ss = {'type': 'array', 'items': s}
    nullable = {'type': ['string', 'null']}
    def obj(p):
        return {'type': 'object', 'properties': p, 'required': list(p), 'additionalProperties': False}
    if stage == 1:
        branch = obj(dict(id=s, direction={'type': 'string', 'enum': list(DIRECTIONS)}, landmark=s,
                          destination_hypothesis=s, panorama_view_ids=ss, evidence_ids=ss,
                          incoming={'type': 'string', 'enum': ['yes', 'no', 'unknown']}))
        return obj(dict(view_summary=s, branches={'type': 'array', 'items': branch},
                        incoming_branch_id=nullable, incoming_evidence_ids=ss, incoming_reason=s,
                        coverage={'type': 'string', 'enum': ['complete', 'partial', 'insufficient']}, uncertainties=ss))
    if stage != 2:
        raise ValueError('Expected call 1 or 2')
    return obj(dict(status={'type': 'string', 'enum': ['selected', 'insufficient_evidence']},
                    wrong_branch_id=nullable, wrong_branch_evidence_ids=ss, error_reason=s,
                    incoming_branch_id=nullable, incoming_evidence_ids=ss, incoming_reason=s,
                    excluded_branch_ids=ss, instruction_evidence=ss, selected_branch_id=nullable,
                    selected_direction={'type': ['string', 'null'], 'enum': list(DIRECTIONS) + [None]},
                    selected_panorama_view_ids=ss, route_description=s, selection_evidence_ids=ss,
                    confidence={'type': 'string', 'enum': ['high', 'medium', 'low']}, uncertainties=ss))


def validate_case(case):
    exact_keys(case, {'sample_id', 'instruction', 'checkpoint_frame', 'wrong_end_frame',
                      'images', 'approach_actions', 'attempt_actions'})
    panos = [im for im in case['images'] if im['phase'] == 'crossing_panorama']
    if len(panos) != 8:
        raise ValueError('Exactly eight registered panorama views required')
    for i, im in enumerate(panos):
        exact_keys(im, {'id', 'yaw_deg', 'phase', 'path', 'sha256'})
        if im['id'] != f'V{i}' or im['yaw_deg'] != i * 45:
            raise ValueError('Panorama order and V0-relative angle changed')
    history = []
    for im in case['images']:
        if Path(im['path']).is_absolute() or '..' in Path(im['path']).parts:
            raise ValueError('Expected a prepared relative RGB path')
        if not isinstance(im['sha256'], str) or len(im['sha256']) != 64:
            raise ValueError('Missing image hash')
        if im['phase'] == 'crossing_panorama':
            continue
        exact_keys(im, {'id', 'frame', 'phase', 'path', 'sha256'})
        if im['phase'] not in ('approach_history', 'wrong_attempt'):
            raise ValueError('Unknown image phase')
        history.append(dict(im, phase='checkpoint_context' if im['phase'] == 'approach_history' else 'wrong_attempt'))
    if case['images'] != panos + [im for im in case['images'] if im['phase'] != 'crossing_panorama']:
        raise ValueError('Panorama must precede chronological historical observations')
    validate_old_case(dict(case, images=history))
    if len(case['images']) != 16 or sum(im['phase'] == 'approach_history' for im in case['images']) != 4:
        raise ValueError('Expected 8 panorama + 4 approach + 4 wrong-attempt images')
    return case


def ids_for(case, stage):
    return [im['id'] for im in case['images'] if stage == 2 or im['phase'] != 'wrong_attempt']


def incoming_evidence(ids, case):
    phases = {im['id']: im['phase'] for im in case['images']}
    return {'approach_history', 'crossing_panorama'} <= {phases[i] for i in ids}


def validate_inventory(answer, case):
    exact_keys(answer, schema(1)['properties'])
    text(answer['view_summary']); text(answer['incoming_reason'])
    string_list(answer['uncertainties'])
    if answer['coverage'] not in ('complete', 'partial', 'insufficient') or not isinstance(answer['branches'], list):
        raise ValueError('Invalid inventory coverage or branches')
    panos, known = {f'V{i}' for i in range(8)}, ids_for(case, 1)
    for i, b in enumerate(answer['branches'], 1):
        exact_keys(b, schema(1)['properties']['branches']['items']['properties'])
        if b['id'] != f'B{i}' or b['direction'] not in DIRECTIONS or b['incoming'] not in ('yes', 'no', 'unknown'):
            raise ValueError('Invalid branch ID, direction or incoming flag')
        text(b['landmark']); text(b['destination_hypothesis'])
        string_list(b['panorama_view_ids'], panos, nonempty=True)
        string_list(b['evidence_ids'], known, nonempty=True)
    branches = {b['id']: b for b in answer['branches']}
    incoming = answer['incoming_branch_id']
    if incoming is not None and (not isinstance(incoming, str) or incoming not in branches):
        raise ValueError('Incoming ID missing from inventory')
    yes = [b['id'] for b in answer['branches'] if b['incoming'] == 'yes']
    if yes != ([incoming] if incoming else []):
        raise ValueError('Incoming flag and top-level ID disagree')
    string_list(answer['incoming_evidence_ids'], known, nonempty=incoming is not None)
    if incoming is not None and not incoming_evidence(answer['incoming_evidence_ids'], case):
        raise ValueError('Positive incoming identification requires approach and panorama evidence')
    if not branches and answer['coverage'] != 'insufficient':
        raise ValueError('Empty branch list must be insufficient')
    return answer


def validate_choice(answer, inventory, case):
    exact_keys(answer, schema(2)['properties'])
    branches = {b['id']: b for b in inventory['branches']}
    for key in ('wrong_branch_id', 'incoming_branch_id', 'selected_branch_id'):
        v = answer[key]
        if v is not None and (not isinstance(v, str) or v not in branches):
            raise ValueError('Choice references a branch absent from the first call')
    wrong, incoming, selected = [answer[k] for k in ('wrong_branch_id', 'incoming_branch_id', 'selected_branch_id')]
    known = ids_for(case, 2)
    for prefix, identity in [('wrong_branch', wrong), ('incoming', incoming), ('selection', selected)]:
        string_list(answer[prefix + '_evidence_ids'], known, nonempty=identity is not None)
    string_list(answer['excluded_branch_ids'], branches)
    if set(answer['excluded_branch_ids']) != {x for x in (wrong, incoming) if x is not None}:
        raise ValueError('Exclusions must equal deduplicated wrong/incoming union')
    if inventory['incoming_branch_id'] is not None and incoming is not None and incoming != inventory['incoming_branch_id']:
        raise ValueError('Cannot silently replace the first-call incoming identification')
    if incoming is not None and not incoming_evidence(answer['incoming_evidence_ids'], case):
        raise ValueError('Incoming evidence must include approach history and panorama')
    string_list(answer['instruction_evidence'])
    if any(q not in case['instruction'] for q in answer['instruction_evidence']):
        raise ValueError('Instruction evidence must be exact substrings')
    string_list(answer['selected_panorama_view_ids'], {f'V{i}' for i in range(8)})
    string_list(answer['uncertainties'])
    for key in ('error_reason', 'incoming_reason', 'route_description'):
        # No selected route exists in an abstention. The published JSON schema
        # allows an empty string here; do not confuse it with a failed decision.
        text(answer[key], allow_empty=(key == 'route_description' and answer['status'] == 'insufficient_evidence'))
    if answer['confidence'] not in ('high', 'medium', 'low'):
        raise ValueError('Invalid confidence')
    if answer['status'] == 'selected':
        if wrong is None or incoming is None or selected is None or selected in answer['excluded_branch_ids']:
            raise ValueError('Selection requires identified exclusions and a different branch')
        if not answer['instruction_evidence'] or answer['selected_direction'] != branches[selected]['direction']:
            raise ValueError('Selection requires task evidence and unchanged direction')
        views = answer['selected_panorama_view_ids']
        if not views or not set(views) <= set(branches[selected]['panorama_view_ids']):
            raise ValueError('Selected panorama evidence must belong to selected branch')
    elif answer['status'] == 'insufficient_evidence':
        if selected is not None or answer['selected_direction'] is not None or answer['selected_panorama_view_ids'] or answer['selection_evidence_ids'] or not answer['uncertainties']:
            raise ValueError('Abstention requires null selection and explicit uncertainty')
    else:
        raise ValueError('Invalid decision status')
    return answer


def build_messages(case, prepared, stage, prompt, inventory=None, embed=True):
    validate_case(case)
    if stage not in (1, 2):
        raise ValueError('Unknown stage')
    ims = [im for im in case['images'] if im['id'] in ids_for(case, stage)]
    metadata = dict(reference_view_id='V0', image_order=[{k: im[k] for k in ('id', 'phase', 'frame', 'yaw_deg') if k in im} for im in ims],
                    orientation='Yaw increases to the left from V0; all directions refer to V0. Historical pose alignment is not assumed.',
                    approach_action_commands=case['approach_actions'])
    if stage == 1:
        if inventory is not None:
            raise ValueError('First call has no previous answer')
    else:
        validate_inventory(inventory, case)
        metadata.update(branch_inventory=inventory, instruction=case['instruction'],
                        previous_attempt_action_commands=case['attempt_actions'],
                        event='The original attempt took a wrong route; identify it and the original incoming route, exclude both, then choose.')
    content = [{'type': 'text', 'text': json.dumps(metadata, ensure_ascii=False)}]
    for im in ims:
        path = Path(prepared) / im['path']
        if file_hash(path) != im['sha256']:
            raise ValueError('Prepared RGB changed')
        content.append({'type': 'text', 'text': f"Image {im['id']} ({im['phase']})"})
        url = 'data:image/png;base64,' + base64.b64encode(path.read_bytes()).decode() if embed else 'PREVIEW_ONLY:sha256:' + im['sha256']
        content.append({'type': 'image_url', 'image_url': {'url': url}})
    content.append({'type': 'text', 'text': 'Return only JSON with this schema: ' + json.dumps(schema(stage))})
    return [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': content}]


def verify_prepared(prepared):
    p = Path(prepared)
    manifest = read(p / 'manifest.json')
    for rel, expected in manifest['files_sha256'].items():
        if file_hash(p / rel) != expected:
            raise ValueError('Prepared artifact changed: ' + rel)
    cases = read(p / 'dataset.json')['cases']
    if len(cases) != 10 or [c['sample_id'] for c in cases] != [f'sample_{i:02d}' for i in range(1, 11)]:
        raise ValueError('Fixed cohort changed')
    for c in cases:
        validate_case(c)
        for im in c['images']:
            if file_hash(p / im['path']) != im['sha256']:
                raise ValueError('RGB changed')
    return cases
