"""Online v006 deviation review and two-stage Recovery at retained JEV nodes."""
import json

from core.serial_pipeline import DEDUP, ROOT, SerialAPI, SerialDecisions, save, semantic_settings
from run_deviation_progress_review import uniform_between, validate_v005
from run_recovery_branch_review import validate as validate_branches
from run_recovery_branch_instruction import instruction_context, validate as validate_instruction


BRANCH_DIR = 'experiments/agent_recovery/branch_review_v001'
V006_PROMPTS = dict(
    dedup=DEDUP + '/prompt_zh.txt',
    deviation='experiments/deviation_progress/v006/prompt_zh.txt',
    branch_review=BRANCH_DIR + '/prompt_zh.txt',
    branch_instruction='experiments/agent_recovery/branch_instruction_v001/prompt_zh.txt',
)
INITIAL_PROGRESS = {
    'zh': '首次有效节点：尚未确认此前完成了哪些导航要求。',
    'en': 'First retained node: prior completion of navigation requirements is unconfirmed.',
}
NODE_VIEWS = (('C_left70', 70, '左侧 +70°'), ('C_front', 0, '正前 0°'),
              ('C_right70', -70, '右侧 −70°'))
OFFSETS = (2, 5, 8, 10)


class V006API(SerialAPI):
    prompt_paths = V006_PROMPTS
    request_timeout = 900

    def __init__(self, directory, config):
        super().__init__(directory, config)
        self.branch_schema = json.loads((ROOT / BRANCH_DIR / 'output_schema.json').read_text())

    def deviation(self, a, b, frames, instruction, progress, initialization=False):
        start, end = a['index'], b['index']
        indices = sorted({start, *uniform_between(start, end), end})
        request = dict(mode='initialization' if initialization else 'segment', previous_id=a['id'],
                       current_id=b['id'], previous_frame=start, current_frame=end,
                       instruction_en=instruction, prior_semantic_progress=progress['zh'],
                       coverage='Endpoint observations plus up to five uniformly sampled intermediate observations. '
                                'Frames are not necessarily consecutive. Review ends at B.')
        images = []
        for i in indices:
            role = 'A=B' if start == end else 'A' if i == start else 'B' if i == end else 'history'
            images.append((frames[i], f'角色 {role}；实际观测帧 F{i}。'))
        try:
            answer = self.ask('deviation', request, images)
            return validate_v005(answer, dict(request, images=[dict(frame=i) for i in indices]))
        except (ValueError, KeyError, TypeError) as exc:
            # The offline v006 runner preserves the last trusted progress on format errors.
            self.invalid_answer('deviation', exc)
            return None

    def invalid_answer(self, stage, error):
        folder = self.directory / 'requests' / f'{self.sequence:05d}_{stage}'
        save(folder / 'validation_error.json', dict(stage=stage, error=str(error)))

    def recovery(self, target, frames, instruction, progress, render_views):
        c = target['index']
        if c + OFFSETS[-1] >= len(frames):
            return dict(status='input_incomplete', checkpoint=c, available_through=len(frames)-1)
        views = render_views(frames[c])
        if [v['image_id'] for v in views] != [v[0] for v in NODE_VIEWS] or any(v['index'] != c for v in views):
            raise ValueError('Wrong checkpoint view or step')
        images = [(v, f"{v['image_id']} | actual_step={c} | {v['view_label']}") for v in views]
        for offset in OFFSETS:
            f = frames[c + offset]
            if f['index'] != c + offset:
                raise ValueError('Wrong post-checkpoint frame')
            images.append((f, f'C_plus{offset} | actual_step={c+offset} | C+{offset} step 实际前视'))
        settings = dict(semantic_settings(self.config, 'branch_review'), top_k=-1, max_tokens=4096)
        message = f'节点 C 的观测 step：{c}。以下按固定顺序提供七张图像。\n输出 JSON Schema：\n'
        stage = 'branch_review'
        try:
            review = self.ask(stage, message + json.dumps(self.branch_schema, ensure_ascii=False),
                              images, settings=settings)
            errors = validate_branches(review, self.branch_schema)
            if errors:
                raise ValueError('; '.join(errors))
            context = instruction_context(instruction, progress, review)
            stage = 'branch_instruction'
            result = self.ask(stage, context, [(v, v['image_id']+' | '+v['view_label']) for v in views],
                              settings=dict(settings, max_tokens=512))
            errors = validate_instruction(result, context)
            if errors:
                raise ValueError('; '.join(errors))
        except (ValueError, KeyError, TypeError) as exc:
            self.invalid_answer(stage, exc)
            return dict(status='invalid_answer', stage=stage, error=str(exc))
        return dict(status='selected' if result['selected_branch_id'] is not None else 'no_alternative',
                    previous_attempt=review['previous_attempt'], **result)


class V006Decisions(SerialDecisions):
    """Hold only the last raw candidate while it can still be replaced by dedup."""
    def __init__(self, api, instruction, log, prior_progress=None, sampler=None):
        super().__init__(api, instruction, log, prior_progress or INITIAL_PROGRESS.copy(), sampler)
        self.tail = None
        self.carried_progress = prior_progress

    def observe(self, frame):
        candidate = self.sample(frame)
        previous = self.tail
        if candidate is not None:
            self.tail = candidate
            relation = self.api.dedup(previous, candidate, self.frames) if previous else 'first'
            self.log('candidate', candidate=candidate, previous=previous['id'] if previous else None,
                     relation=relation)
            if previous and relation != 'same':
                return self.review(previous)
        elif previous and frame['index'] >= previous['emittedAt'] + 8:
            # All possible replacements within the frozen <=8 step rule have now arrived.
            self.tail = None
            return self.review(previous)
        return None

    def review(self, candidate, terminal=False, stop_requested=False):
        node = dict(candidate, source_id=candidate['id'], id=f'S{len(self.nodes)+1:02d}',
                    terminal_node=terminal, retained_at=self.frames[-1]['index'])
        self.nodes.append(node)
        self.log('node', node=node)
        a = self.anchor or node
        answer = self.api.deviation(a, node, self.frames, self.instruction, self.progress,
                                    initialization=self.anchor is None)
        self.log('deviation', previous=a['id'], node=node['id'], answer=answer,
                 status='valid' if answer else 'invalid_answer', terminal=terminal, stop_requested=stop_requested)
        if answer is None:
            if stop_requested:
                raise ValueError('Invalid deviation verdict for proposed STOP')
            return None
        if answer['verdict'] == 'consistent':
            self.anchor = node
            # A single post-handoff initialization image cannot replace the trusted
            # task history brought back from the checkpoint.
            self.progress = self.carried_progress or answer['semantic_progress']
            self.carried_progress = None
            return None
        return dict(target=self.anchor, progress=self.progress, detected_at=node['retained_at'],
                    alarm_node=node, answer=answer)

    def terminal(self, frame):
        self.frames.append(frame)
        return self.review_endpoint(stop_requested=False)

    def review_endpoint(self, *, stop_requested):
        # A STOP proposal uses the current policy observation, already in frames.
        if self.tail:
            alarm = self.review(self.tail)
            self.tail = None
            if alarm:
                return alarm
        index = self.frames[-1]['index']
        return self.review(dict(id=None, index=index, emittedAt=index), terminal=not stop_requested,
                           stop_requested=stop_requested)
