"""Retry a live review's logical request while keeping its thread and turn evidence."""
from collections import deque
import json
import time
from pathlib import Path

from core.codex_client import CodexCallError, CodexSession, now, sha256


def retry_wait(path, attempt, error, **context):
    delay = min(60, 2 ** min(attempt, 6))
    with path.open('a') as stream:
        stream.write(json.dumps(dict(time=now(), attempt=attempt, error=str(error),
                                     wait_seconds=delay, **context), ensure_ascii=False)+'\n')
    time.sleep(delay)


class ShadowSession(CodexSession):
    def __init__(self, directory, config):
        self.history = deque()
        directory = directory.resolve()
        if not (directory/'session.json').exists():
            super().__init__(directory, config)
            return
        self.directory, self.config = directory, config
        state = json.loads((directory/'session.json').read_text())
        self.thread_id, self.turn_count, self.failed = state['thread_id'], 0, False
        for turn in sorted((directory/'turns').glob('turn_*')):
            self.turn_count = max(self.turn_count, int(turn.name.split('_', 2)[1]))
            if not (turn/'response.json').exists():
                continue
            response = json.loads((turn/'response.json').read_text())
            if response.get('thread_id'):
                if self.thread_id and self.thread_id != response['thread_id']:
                    raise ValueError('Stored Codex thread mismatch')
                self.thread_id = response['thread_id']
            if response['status'] == 'ok' and not (turn/'invalid_answer.json').exists():
                self.history.append((turn,response))

    def ask_checked(self, validate, prompt, images, schema, *, label, metadata=None):
        if self.history:
            turn, response = self.history.popleft()
            req = json.loads((turn/'request.json').read_text())
            if (turn.name.split('_',2)[2] != label or (turn/'prompt.txt').read_text() != prompt
                    or json.loads((turn/'schema.json').read_text()) != schema
                    or [i['sha256'] for i in req['images']] != [sha256(p) for p in images]):
                raise ValueError('Stored Codex request differs from the resumed review at '+label)
            raw = (turn/'final.txt').read_text()
            return dict(response,text=raw), validate(json.loads(raw))

        attempt = 0
        while True:
            attempt += 1
            try:
                response = super().ask(prompt, images, schema, label=label, metadata=metadata)
                try:
                    answer = validate(json.loads(response['text']))
                except (ValueError, TypeError, KeyError, IndexError, AttributeError) as error:
                    (Path(response['directory'])/'invalid_answer.json').write_text(json.dumps(str(error)))
                    raise CodexCallError(f'Invalid answer for {label}: {error}') from error
                return response, answer
            except CodexCallError as error:
                self.failed = False
                retry_wait(self.directory/'retries.jsonl', attempt, error, label=label,
                           turn=self.turn_count, thread_id=self.thread_id)
