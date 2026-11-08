"""Two independent, visual route-choice calls. No simulator or model import here."""
import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

DIRECTIONS = ('front', 'front_left', 'left', 'back_left', 'back', 'back_right',
              'right', 'front_right', 'unclear')
CASE_KEYS = {'sample_id', 'instruction', 'checkpoint_frame', 'wrong_end_frame',
             'images', 'approach_actions', 'attempt_actions'}
IMAGE_KEYS = {'id', 'frame', 'phase', 'path', 'sha256'}


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def exact_keys(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError('Unexpected object fields')


def text(value, allow_empty=False):
    if not isinstance(value, str) or len(value) > 2000 or (not allow_empty and not value.strip()):
        raise ValueError('Expected a bounded text field')


def string_list(value, allowed=None, nonempty=False):
    if not isinstance(value, list) or len(value) > 32 or any(not isinstance(x, str) for x in value):
        raise ValueError('Expected a string list')
    if len(set(value)) != len(value) or (nonempty and not value):
        raise ValueError('Duplicate or missing list entries')
    for item in value:
        text(item)
    if allowed is not None and not set(value) <= set(allowed):
        raise ValueError('Unknown reference')


def validate_case(case):
    # Reject unexpected metadata rather than relying on callers to strip ground truth.
    exact_keys(case, CASE_KEYS)
    text(case['sample_id']); text(case['instruction'])
    cp, end = case['checkpoint_frame'], case['wrong_end_frame']
    if type(cp) is not int or type(end) is not int or not 0 <= cp < end:
        raise ValueError('Invalid checkpoint/error boundary')
    images = case['images']
    if not isinstance(images, list) or not 2 <= len(images) <= 8:
        raise ValueError('Expected at most eight distinct input images')
    seen = set()
    for im in images:
        exact_keys(im, IMAGE_KEYS)
        if type(im['frame']) is not int or im['frame'] < 0:
            raise ValueError('Invalid image frame')
        if im['id'] != 'F%04d' % im['frame'] or im['id'] in seen:
            raise ValueError('Image identifiers must be unique and bound to frames')
        seen.add(im['id'])
        if im['phase'] == 'checkpoint_context':
            if im['frame'] > cp:
                raise ValueError('Call one cannot see the later attempt')
        elif im['phase'] == 'wrong_attempt':
            if not cp < im['frame'] <= end:
                raise ValueError('Attempt frame outside the recorded interval')
        else:
            raise ValueError('Unknown image phase')
        if Path(im['path']).is_absolute() or '..' in Path(im['path']).parts:
            raise ValueError('Expected a relative prepared image path')
        if not isinstance(im['sha256'], str) or len(im['sha256']) != 64:
            raise ValueError('Missing image hash')
    frames = [im['frame'] for im in images]
    if frames != sorted(set(frames)) or cp not in frames or end not in frames:
        raise ValueError('Images must retain checkpoint, endpoint and chronological order')
    for name, lower, upper in [('approach_actions', 0, cp), ('attempt_actions', cp, end)]:
        actions = case[name]
        if not isinstance(actions, list):
            raise ValueError('Expected actions')
        indices = []
        for action in actions:
            exact_keys(action, {'frame', 'action'})
            idx = action['frame']
            if type(idx) is not int or not lower <= idx < upper:
                raise ValueError('Action must precede its resulting observation')
            if action['action'] not in ('FORWARD', 'LEFT', 'RIGHT', 'STOP', 'WAIT'):
                raise ValueError('Unknown action')
            indices.append(idx)
        if indices != sorted(set(indices)):
            raise ValueError('Actions must be ordered and unique')
    return case


def select_evenly(rows, count):
    if count < 2:
        raise ValueError('At least two samples are required')
    if len(rows) <= count:
        return list(rows)
    return [rows[round(i * (len(rows) - 1) / (count - 1))] for i in range(count)]


def schema(stage):
    s = {'type': 'string'}
    strings = {'type': 'array', 'items': s}
    def obj(properties):
        return {'type': 'object', 'properties': properties, 'required': list(properties),
                'additionalProperties': False}
    if stage == 1:
        branch = obj({'id': s, 'direction': {'enum': list(DIRECTIONS)}, 'landmark': s,
                      'destination_hypothesis': s, 'incoming': {'enum': ['yes', 'no', 'unknown']},
                      'evidence_ids': strings})
        return obj({'view_summary': s, 'branches': {'type': 'array', 'items': branch, 'maxItems': 8},
                    'coverage': {'enum': ['complete', 'partial', 'insufficient']},
                    'uncertainties': strings})
    if stage != 2:
        raise ValueError('Expected call 1 or 2')
    nullable = {'type': ['string', 'null']}
    return obj({'status': {'enum': ['selected', 'insufficient_evidence']},
                'wrong_branch_id': nullable, 'wrong_branch_evidence_ids': strings,
                'error_reason': s, 'instruction_evidence': strings, 'excluded_branch_ids': strings,
                'selected_branch_id': nullable,
                'selected_direction': {'enum': list(DIRECTIONS) + [None]},
                'route_description': s, 'selection_evidence_ids': strings,
                'confidence': {'enum': ['high', 'medium', 'low']}, 'uncertainties': strings})


def validate_inventory(answer, image_ids):
    exact_keys(answer, schema(1)['properties'])
    text(answer['view_summary'])
    string_list(answer['uncertainties'])
    if answer['coverage'] not in ('complete', 'partial', 'insufficient'):
        raise ValueError('Invalid inventory coverage')
    branches = answer['branches']
    if not isinstance(branches, list) or len(branches) > 8:
        raise ValueError('Invalid branch list')
    for n, b in enumerate(branches, 1):
        exact_keys(b, schema(1)['properties']['branches']['items']['properties'])
        if b['id'] != 'B%d' % n or b['direction'] not in DIRECTIONS:
            raise ValueError('Branches require contiguous IDs and current-view directions')
        if b['incoming'] not in ('yes', 'no', 'unknown'):
            raise ValueError('Invalid incoming-route flag')
        text(b['landmark']); text(b['destination_hypothesis'])
        string_list(b['evidence_ids'], image_ids, nonempty=True)
    if not branches and answer['coverage'] != 'insufficient':
        raise ValueError('Empty inventory must be insufficient')
    return answer


def validate_choice(answer, inventory, image_ids, instruction):
    exact_keys(answer, schema(2)['properties'])
    branches = {b['id']: b for b in inventory['branches']}
    for key in ('wrong_branch_id', 'selected_branch_id'):
        if answer[key] is not None and (not isinstance(answer[key], str) or answer[key] not in branches):
            raise ValueError('Choice cannot invent a branch missing from call one')
    wrong, selected = answer['wrong_branch_id'], answer['selected_branch_id']
    string_list(answer['wrong_branch_evidence_ids'], image_ids, nonempty=wrong is not None)
    string_list(answer['selection_evidence_ids'], image_ids, nonempty=selected is not None)
    string_list(answer['excluded_branch_ids'], branches)
    if answer['excluded_branch_ids'] != ([wrong] if wrong is not None else []):
        raise ValueError('Exclude exactly the identified wrong branch')
    string_list(answer['instruction_evidence'])
    if any(quote not in instruction for quote in answer['instruction_evidence']):
        raise ValueError('Instruction evidence must quote the supplied instruction')
    for key in ('error_reason', 'route_description'):
        text(answer[key])
    string_list(answer['uncertainties'])
    if answer['confidence'] not in ('high', 'medium', 'low'):
        raise ValueError('Invalid confidence')
    if answer['status'] == 'selected':
        if wrong is None or selected is None or selected == wrong or not answer['instruction_evidence']:
            raise ValueError('Selection requires an identified wrong branch and a distinct task-supported branch')
        if answer['selected_direction'] != branches[selected]['direction']:
            raise ValueError('Selected direction must retain call-one orientation')
    elif answer['status'] == 'insufficient_evidence':
        if selected is not None or answer['selected_direction'] is not None or not answer['uncertainties']:
            raise ValueError('Abstention requires null choice and an explicit limitation')
    else:
        raise ValueError('Invalid decision status')
    return answer


def build_messages(case, prepared, stage, system_prompt, inventory=None, embed_images=True):
    validate_case(case)
    if stage not in (1, 2):
        raise ValueError('Unknown call')
    images = [im for im in case['images'] if stage == 2 or im['phase'] == 'checkpoint_context']
    metadata = {'current_view_id': 'F%04d' % case['checkpoint_frame'],
                'image_order': [{k: im[k] for k in ('id', 'frame', 'phase')} for im in images],
                'approach_action_commands': case['approach_actions'],
                'orientation': 'All branch directions are relative to current_view_id after virtual return.'}
    if stage == 2:
        validate_inventory(inventory, [im['id'] for im in case['images'] if im['phase'] == 'checkpoint_context'])
        metadata.update(instruction=case['instruction'], branch_inventory=inventory,
                        previous_attempt_action_commands=case['attempt_actions'],
                        event='The previous attempt took a wrong route. Identify it from the evidence; the current view has returned to the checkpoint.')
    elif inventory is not None:
        raise ValueError('First call must be independent of previous answers')
    content = [{'type': 'text', 'text': json.dumps(metadata, ensure_ascii=False)}]
    for im in images:
        path = Path(prepared) / im['path']
        if file_hash(path) != im['sha256']:
            raise ValueError('Prepared image changed')
        content.append({'type': 'text', 'text': 'Image %s (%s)' % (im['id'], im['phase'])})
        url = ('data:image/png;base64,' + base64.b64encode(path.read_bytes()).decode()) if embed_images else (
            'PREVIEW_ONLY:image_sha256:' + im['sha256'])
        content.append({'type': 'image_url', 'image_url': {'url': url}})
    content.append({'type': 'text', 'text': 'Return only JSON matching this schema: ' + json.dumps(schema(stage))})
    # Each call contains only a system message and a newly constructed user message.
    return [{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': content}]


def payload(messages, model_config, sample_id, stage):
    result = {'model': model_config['model'], 'messages': messages, 'temperature': 0.0,
              'max_tokens': model_config['max_tokens'], 'response_format': {'type': 'json_object'},
              'stream': True}
    if model_config['backend'] == 'glm':
        result.update(thinking={'type': 'enabled'}, reasoning_effort=model_config['reasoning_effort'])
    elif model_config['backend'] == 'qwen_local':
        result.update(chat_template_kwargs={'enable_thinking': False},
                      seed=int(hashlib.sha256(('%s:%s:%s' % (sample_id, stage, model_config['seed'])).encode()).hexdigest()[:8], 16) & 0x7fffffff)
    else:
        raise ValueError('Unsupported backend')
    return result


def verify_prepared(prepared, code_root):
    prepared = Path(prepared)
    manifest = read(prepared / 'manifest.json')
    for relative, expected in manifest['files_sha256'].items():
        if file_hash(prepared / relative) != expected:
            raise ValueError('Prepared file changed: ' + relative)
    for relative, expected in manifest['code_sha256'].items():
        if file_hash(Path(code_root) / relative) != expected:
            raise ValueError('Code differs from preparation; prepare a new revision: ' + relative)
    dataset = read(prepared / 'dataset.json')
    if len(dataset['cases']) != 10 or len({c['sample_id'] for c in dataset['cases']}) != 10:
        raise ValueError('Expected the fixed ten distinct samples')
    for case in dataset['cases']:
        validate_case(case)
        for im in case['images']:
            if file_hash(prepared / im['path']) != im['sha256']:
                raise ValueError('Prepared image changed')
    return dataset
