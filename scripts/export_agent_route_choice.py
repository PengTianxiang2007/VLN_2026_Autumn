"""Export prepared inputs or real answers using the shared Crossing visual style; CPU only."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.agent_route_choice import digest, file_hash, now, read, write
from scripts.report_agent_route_choice import load_run


def check_translation(original, translated, stage):
    """Only descriptive text may change; never repair the model's decision."""
    if not isinstance(original, dict) or not isinstance(translated, dict) or set(original) != set(translated):
        raise ValueError('Translation changed answer fields')
    prose = {'view_summary', 'branches', 'uncertainties'} if stage == 1 else {
        'error_reason', 'instruction_evidence', 'route_description', 'uncertainties'}
    for key in original.keys() - prose:
        if original[key] != translated[key]:
            raise ValueError('Translation changed structural value: ' + key)
    for key in ('uncertainties', 'instruction_evidence'):
        if key in original and (len(original[key]) != len(translated[key]) or
                                not all(isinstance(s, str) and s for s in translated[key])):
            raise ValueError('Translation changed list coverage: ' + key)
    if stage == 1:
        if len(original['branches']) != len(translated['branches']):
            raise ValueError('Translation changed branch count')
        for a, b in zip(original['branches'], translated['branches']):
            if set(a) != set(b) or any(a[k] != b[k] for k in a if k not in ('landmark', 'destination_hypothesis')):
                raise ValueError('Translation changed branch identity, direction or evidence')
    return translated


def export(prepared, destination, runs, translations=None):
    if destination.exists():
        raise FileExistsError('Choose a new export destination')
    dataset = read(prepared / 'dataset.json')
    translation = read(translations) if translations else None
    instructions_zh = {}
    if translation:
        for case in dataset['cases']:
            entry = translation['cases'][case['sample_id']]
            if entry['instruction_source_sha256'] != hashlib.sha256(case['instruction'].encode()).hexdigest():
                raise ValueError('Instruction translation is bound to different input')
            instructions_zh[case['sample_id']] = entry['instruction_zh']
    labels = read(prepared / 'evaluation_only.json')['labels']
    images = {}
    for case in dataset['cases']:
        for im in case['images']:
            path = prepared / im['path']
            if file_hash(path) != im['sha256']:
                raise ValueError('Prepared RGB changed')
            images[im['sha256']] = 'data:image/png;base64,' + base64.b64encode(path.read_bytes()).decode()
    models = []
    for run in runs:
        manifest = read(run / 'manifest.json')
        run_prepared = Path(manifest['prepared'])
        load_run(run_prepared, run)
        # Runtime or transport revisions may differ; the visible evidence and prompts must not.
        for name in ('dataset.json', 'evaluation_only.json', 'prompts/01_inventory_en.txt', 'prompts/02_choose_en.txt'):
            if file_hash(prepared / name) != file_hash(run_prepared / name):
                raise ValueError('Cannot compare different inputs or prompts: ' + name)
        manifest_hash = file_hash(run / 'manifest.json')
        translated_run = translation and translation['source_run_manifest_sha256'] == manifest_hash
        answers, calls, case_statuses, bindings, provider_errors, checkpoint_views = {}, {}, {}, {}, {}, {}
        for case in dataset['cases']:
            folder = run / 'cases' / case['sample_id']
            cp = next(im for im in case['images'] if im['frame'] == case['checkpoint_frame'])
            view_checks = {}
            for call in (1, 2):
                request_path = folder / ('call%d_request.json' % call)
                if request_path.exists():
                    preview = read(request_path)['messages_image_hash_preview']
                    metadata = json.loads(preview[1]['content'][0]['text'])
                    matches = metadata['current_view_id'] == cp['id'] and any(
                        part.get('image_url', {}).get('url') == 'PREVIEW_ONLY:image_sha256:' + cp['sha256']
                        for part in preview[1]['content'])
                    if not matches:
                        raise ValueError('Displayed Crossing frame differs from the recorded model request')
                    view_checks[str(call)] = True
            checkpoint_views[case['sample_id']] = {'image_id': cp['id'], 'frame': cp['frame'],
                                                   'sha256': cp['sha256'], 'matches_recorded_request': view_checks}
            answers[case['sample_id']] = {str(stage): read(folder / ('call%d_answer.json' % stage))
                                        if (folder / ('call%d_answer.json' % stage)).exists() else None for stage in (1, 2)}
            case_statuses[case['sample_id']] = read(folder / 'status.json') if (folder / 'status.json').exists() else {'phase': 'not_started'}
            slots = {}
            for stage in (1, 2):
                path = folder / ('call%d_response.json' % stage)
                raw = read(path) if path.exists() else None
                parsed = None
                if raw:
                    try:
                        parsed = json.loads(raw['content'])
                    except (ValueError, TypeError):
                        pass
                zh = None
                if translated_run and raw:
                    entry = translation['cases'][case['sample_id']]['calls'][str(stage)]
                    if entry['source_response_sha256'] != file_hash(path):
                        raise ValueError('Translation response hash mismatch')
                    zh = check_translation(parsed, entry['answer_zh'], stage)
                slots[str(stage)] = {'parsed': parsed, 'raw_content': raw['content'] if raw else None,
                                    'answer_zh': zh, 'validated': answers[case['sample_id']][str(stage)] is not None,
                                    'response_sha256': file_hash(path) if raw else None,
                                    'finish_reason': raw.get('finish_reason') if raw else None}
            calls[case['sample_id']] = slots
            request = folder / 'call2_request.json'
            if request.exists():
                req = read(request)
                messages = req['messages_image_hash_preview']
                sent = json.loads(messages[1]['content'][0]['text'])['branch_inventory']
                inventory = answers[case['sample_id']]['1']
                bindings[case['sample_id']] = {'matches': inventory is not None and sent == inventory and req['inventory_sha256'] == digest(inventory),
                                               'inventory_sha256': req['inventory_sha256']}
            for path in folder.glob('call*_transport.jsonl'):
                for line in path.read_text().splitlines():
                    error = json.loads(line).get('provider_error')
                    if error:
                        provider_errors[str(error.get('code', 'unknown'))] = error.get('message', '')
        response_count = sum(slot['raw_content'] is not None for pair in calls.values() for slot in pair.values())
        valid_count = sum(s['phase'] == 'complete_pending_semantic_review' for s in case_statuses.values())
        invalid_count = sum(any(slot['raw_content'] is not None and not slot['validated'] for slot in pair.values()) for pair in calls.values())
        config = manifest['model_config']
        name = Path(config['model_path']).name if 'model_path' in config else config['model']
        models.append({'name': name, 'run_name': run.name, 'manifest_sha256': manifest_hash,
                       'status': read(run / 'status.json'), 'answers': answers, 'calls': calls,
                       'case_statuses': case_statuses, 'bindings': bindings, 'provider_errors': provider_errors,
                       'checkpoint_views': checkpoint_views,
                       'response_count': response_count, 'validated_samples': valid_count, 'invalid_samples': invalid_count,
                       'translation_count': sum(s['answer_zh'] is not None for pair in calls.values() for s in pair.values())})
    if translation and not any(m['manifest_sha256'] == translation['source_run_manifest_sha256'] for m in models):
        raise ValueError('Translation does not match any supplied run')
    scenes = {}
    for label in labels:
        scene = label['scene']
        if scene not in scenes:
            path = ROOT / 'outputs/checkpoint_review/seed2_25_20261103/scenes' / scene
            if (path / 'geometry.json').exists() and (path / 'floorplan.png').exists():
                scenes[scene] = {'geometry': read(path / 'geometry.json'),
                                 'image': 'data:image/png;base64,' + base64.b64encode((path / 'floorplan.png').read_bytes()).decode()}
    template = (ROOT / 'core/crossing_campaign_template.html').read_text()
    head = template.split('<body>', 1)[0].replace('Crossing · 迭代离线复核', 'Crossing · 复位后选路')
    body = (ROOT / 'core/agent_route_choice_page.html').read_text()
    data = {'cases': dataset['cases'], 'labels': labels, 'images': images, 'scenes': scenes,
            'models': models, 'prepared_manifest_sha256': file_hash(prepared / 'manifest.json'),
            'protocol': read(prepared / 'protocol.json'), 'instructions_zh': instructions_zh,
            'translation_sha256': file_hash(translations) if translations else None}
    js = (ROOT / 'core/agent_route_choice_review.js').read_text()
    page = head + body + '<script>const DATA=' + json.dumps(data, ensure_ascii=False).replace('</', '<\\/') + ';\n' + js + '</script></body></html>'
    # Reuse the already retained font; no download or server font installation.
    from fontTools import subset
    from fontTools.ttLib import TTFont
    font_config = read(ROOT / 'core/crossing_visualization_template.json')
    font = TTFont(font_config['font'], fontNumber=0)
    subsetter = subset.Subsetter(); subsetter.populate(text=page); subsetter.subset(font)
    buffer = io.BytesIO(); font.save(buffer)
    font_css = '<style>@font-face{font-family:RouteChoiceSans;src:url(data:font/ttf;base64,' + base64.b64encode(buffer.getvalue()).decode() + ") format('truetype')}body,button,input,select,textarea,pre{font-family:RouteChoiceSans,system-ui,sans-serif}</style>"
    page = page.replace('</head>', font_css + '</head>')

    license_text = Path(font_config['font_license']).read_text()
    page = page.replace('</body>', '<script type="text/plain" id="font-license">' + license_text.replace('</', '<\\/') + '</script></body>')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(page)
    write(destination.with_suffix('.manifest.json'), {'template_source': 'core/crossing_campaign_template.html',
          'template_sha256': file_hash(ROOT / 'core/crossing_campaign_template.html'),
          'adapter_sha256': file_hash(ROOT / 'core/agent_route_choice_review.js'),
          'html_sha256': file_hash(destination), 'samples': len(dataset['cases']), 'model_groups': len(models),
          'models_with_results': sum(m['response_count'] > 0 for m in models),
          'page_layout_sha256': file_hash(ROOT / 'core/agent_route_choice_page.html'),
          'font_source_sha256': file_hash(font_config['font']), 'font_license_sha256': file_hash(font_config['font_license']),
          'model_calls_by_exporter': 0, 'phase': 'input_preview' if not models else 'answer_review',
          'created_at': now(), 'exporter_sha256': file_hash(Path(__file__)),
          'translation_sha256': file_hash(translations) if translations else None,
          'run_summaries': [{k: m[k] for k in ('name', 'run_name', 'manifest_sha256', 'response_count', 'validated_samples', 'invalid_samples', 'translation_count')} for m in models]})
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--runs', type=Path, nargs='*', default=[])
    parser.add_argument('--translations', type=Path, help='Chinese translations bound to exact response hashes')
    args = parser.parse_args()
    export(args.prepared, args.destination, args.runs, args.translations)


if __name__ == '__main__':
    main()
