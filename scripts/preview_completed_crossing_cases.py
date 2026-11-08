"""Create offline review sheets for completed cases; never change inference or score prefixes."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path

from preview_crossing_checkpoint import frozen_core, read_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    run = args.output/'runs'/args.tag
    manifest = read_json(run/'manifest.json')
    if manifest['split'] == 'validation' and not (args.output/'selection_decision.json').exists():
        raise ValueError('Validation is still sealed')
    core = frozen_core(run, manifest)
    inputs = read_json(args.output/'inputs.json')
    private = read_json(args.output/'evaluation/cases.json')
    destination = args.output/'reports'/(args.tag+'_case_previews')
    destination.mkdir(parents=True, exist_ok=True)
    import cv2
    import numpy as np
    cv2.setNumThreads(1)
    created = []
    for episode in manifest['episodes']:
        result_path = run/'cases'/episode/'result.json'
        metadata_path = destination/(episode+'.json')
        if metadata_path.exists() or not result_path.exists():
            continue
        result = read_json(result_path)
        if not result['complete']:
            continue
        source, case = inputs[episode], private[episode]
        valid = [o['frame'] for o in source['observations'] if not o['terminal'] and not o['rgb_reused']]
        if result['observations'] != len(valid):
            raise ValueError('Completed case has incomplete observation coverage')
        metric = core.evaluate_events(result['events'], case['steps'], case['encounters'], radius=1.0)
        labels = defaultdict(list)
        for prediction in metric['predictions']:
            label = {'matched':'TP', 'unmatched_prediction':'FP', 'duplicate_prediction':'DUP-FP'}[prediction['label']]
            labels[prediction['frame']].append(label+' '+prediction['prediction_id']+' '+prediction.get('crossing_id',''))
        for encounter in case['encounters']:
            if encounter['id'] in metric['missed_encounters']:
                labels[encounter['closest_frame']].append('FN '+encounter['id'])
        if not labels:
            for frame in sorted({valid[0], valid[len(valid)//2], valid[-1]}):
                labels[frame].append('No matched reference visits or predictions')
        capture = cv2.VideoCapture(source['video'])
        if not capture.isOpened() or (int(capture.get(3)), int(capture.get(4))) != (960,640):
            raise ValueError('Unexpected source recording layout')
        tiles = []
        try:
            for frame, notes in sorted(labels.items()):
                capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
                ok, composite = capture.read()
                if not ok:
                    raise ValueError('Cannot read review frame')
                tile = np.zeros((272,320,3), dtype=np.uint8)
                tile[32:] = cv2.resize(composite[:480,:640], (320,240))
                caption = 'f'+str(frame)+' | '+'; '.join(notes)
                cv2.putText(tile, caption[:54], (4,20), cv2.FONT_HERSHEY_SIMPLEX,.38,(255,255,255),1)
                tiles.append(tile)
        finally:
            capture.release()
        columns = min(4, len(tiles))
        canvas = np.zeros((((len(tiles)+columns-1)//columns)*272, columns*320,3), dtype=np.uint8)
        for index, tile in enumerate(tiles):
            y,x = (index//columns)*272,(index%columns)*320
            canvas[y:y+272,x:x+320] = tile
        ok, encoded = cv2.imencode('.jpg', canvas, [cv2.IMWRITE_JPEG_QUALITY,90])
        if not ok:
            raise ValueError('Cannot encode review sheet')
        image_path = destination/(episode+'.jpg')
        image_path.write_bytes(encoded.tobytes())
        metadata = dict(episode_id=episode, tag=args.tag, complete=True, metrics=metric,
                        review_frames={str(k):v for k,v in sorted(labels.items())},
                        image=str(image_path.resolve()), created_at=datetime.now(timezone.utc).isoformat(),
                        scope='Offline evaluation only; complete cases only; these images are never model inputs. Full causal audit is performed by build_crossing_review.py.')
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n')
        created.append(metadata)
    print(json.dumps(created, ensure_ascii=False))


if __name__ == '__main__':
    main()
