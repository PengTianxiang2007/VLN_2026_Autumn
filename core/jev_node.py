"""JEV/System One interface for local Crossing-node scoring.

The request is deliberately typed: JEV receives one chronological image state,
one five-level Score question, and three independent directional Noul questions.
It does not generate free-form reasoning.
"""
import base64
import hashlib
import json
import math
import subprocess
import time
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

DEFAULT_ENDPOINT = 'https://api.site/v1/systemone'
DEFAULT_MODEL = 'jev-1.14.0'
DIRECTION_KEYS = ('forward_route', 'left_route', 'right_route')

STATE_CONTEXT_EN = (
    'The images are chronological RGB observations from an indoor navigating robot. '
    'The last image is the current view; earlier images clarify nearby geometry and '
    'space that remains accessible. Judge the current local situation, not the route '
    'correctness or navigation difficulty.'
)
STATE_CONTEXT_ZH = (
    '这些图像是室内导航机器人的按时间顺序排列的 RGB 观测。最后一张是当前视图；'
    '较早图像用于澄清附近几何结构以及仍可进入的空间。判断当前局部情形，不判断路线'
    '正确性或导航难度。'
)

SCORE_INSTRUCTIONS_EN = (
    'Using the chronological images, score how strongly the CURRENT position is a '
    'local route-choice node with at least two distinct traversable choices now or '
    'after only a short nearby continuation. Turning back along a demonstrably '
    'traversable incoming route may count as one choice. Do not treat a distant '
    'doorway as a current choice when the robot must first travel down a passage to '
    'reach it. Use earlier images only when the indicated route remains accessible '
    'from the current decision area.'
)
SCORE_INSTRUCTIONS_ZH = (
    '结合按时间顺序排列的图像，对当前位置在多大程度上构成局部路线选择节点进行评分。'
    '该节点应在当前或只经过短距离邻近移动后，拥有至少两条不同且可通行的选择。'
    '如果有可靠证据表明来路仍可通行，掉头返回可以算作一个选择。如果机器人必须先沿'
    '通道前行一段才能到达远处的门口，不要把该门口当作当前选择。只有较早图像显示的'
    '路线仍可从当前决策区域到达时，才使用该较早图像。'
)

SCORE_LEVELS_EN = (
    'Only one route is supported; every other direction is clearly blocked or '
    'resolves into that same route.',
    'One extra candidate direction has a weak cue, such as a partial doorway, wall '
    'edge, or occluded continuation, but its distinctness or traversability is doubtful.',
    'One route is supported and a second route is plausible: a side opening, short '
    'turn, or occluded continuation provides concrete but incomplete evidence.',
    'Two distinct choices are likely traversable from the current local area, although '
    'one may be partly occluded or visible only in an earlier frame.',
    'At least two distinct choices are directly visible or strongly supported as '
    'traversable and accessible at or immediately adjacent to the current position.',
)
SCORE_LEVELS_ZH = (
    '只有一条路线得到支持；其他方向都明确封闭，或者属于同一条路线。',
    '另一个候选方向存在弱线索，例如只露出一部分的门洞、墙端或被遮挡的空间延续，'
    '但其独立性或可通行性仍然存疑。',
    '已有一条路线得到支持，同时第二条路线具有合理性：侧向开口、短距离转弯或被遮挡的'
    '空间延续提供了具体但不完整的证据。',
    '当前局部区域很可能有两条不同且可通行的选择，其中一条可能只被部分遮挡或只在较早'
    '图像中可见。',
    '至少两条不同选择直接可见，或者有强证据表明它们可从当前位置或其紧邻区域通行并进入。',
)

DIRECTION_INSTRUCTIONS_EN = {
    'forward_route': (
        'Does FORWARD from the current heading contain a distinct traversable route '
        'available at or immediately adjacent to the current position?'
    ),
    'left_route': (
        'Does LEFT of the current heading contain a distinct traversable route '
        'available at or immediately adjacent to the current position? Include a '
        'partially visible side opening only when concrete geometry supports continued '
        'enterable space.'
    ),
    'right_route': (
        'Does RIGHT of the current heading contain a distinct traversable route '
        'available at or immediately adjacent to the current position? Include a '
        'partially visible side opening only when concrete geometry supports continued '
        'enterable space.'
    ),
}
DIRECTION_INSTRUCTIONS_ZH = {
    'forward_route': (
        '当前朝向的前方，在当前位置或其紧邻区域，是否有一条不同且可通行的路线？'
    ),
    'left_route': (
        '当前朝向的左侧，在当前位置或其紧邻区域，是否有一条不同且可通行的路线？'
        '只有当具体几何结构支持门洞后仍有可进入空间时，才计入仅部分可见的侧向开口。'
    ),
    'right_route': (
        '当前朝向的右侧，在当前位置或其紧邻区域，是否有一条不同且可通行的路线？'
        '只有当具体几何结构支持门洞后仍有可进入空间时，才计入仅部分可见的侧向开口。'
    ),
}

NOUL_CRITERIA_EN = {
    'true': (
        'Visible geometry or clear continuation evidence supports a distinct enterable '
        'route in this direction at the current local decision area.'
    ),
    'false': (
        'No distinct route is supported in this direction, or the area is clearly '
        'closed or not enterable.'
    ),
}
NOUL_CRITERIA_ZH = {
    'true': '可见几何结构或清晰的延续证据表明，当前局部决策区域的该方向上存在一条不同且可进入的路线。',
    'false': '该方向上没有证据支持一条不同路线，或者该区域明确封闭、不可进入。',
}

FALLBACK_INSTRUCTIONS_EN = (
    'Does the CURRENT robot step qualify as a fallback point? A fallback point is '
    'a compact local decision position where the robot is currently at, or '
    'immediately approaching, at least two distinct physically plausible onward '
    'routes available now or after only a few nearby steps. Count routes leading '
    'into different passages, rooms, or meaningful travel directions, including '
    'nearby side doorways and continuing forward. Turning back along the incoming '
    'route counts only when the provided images support that it remains '
    'traversable and directly accessible from the current location. Do not count '
    'a distant doorway if the robot must first continue along a passage to reach '
    'it. Do not count an opening reached only after taking another current route, '
    'minor furniture gaps, mirrors, closed doors, or invented exits outside the '
    'observed views. Judge the CURRENT view; earlier images may clarify an '
    'entrance or route that remains accessible from the current location.'
)
FALLBACK_INSTRUCTIONS_ZH = (
    '当前机器人 step 是否可以作为回退点？回退点是一个紧凑的局部决策位置：机器人'
    '当前位于、或即将接近该位置，并且现在或仅经过附近几步后，存在至少两条不同且'
    '物理上可通行的后续路线。计入通向不同通道、房间或有意义的行进方向的路线，'
    '包括附近侧门和继续前行。只有当所提供图像支持来路仍然可通行，并且可以从当前'
    '位置直接到达时，掉头返回才计入一个选择。如果机器人必须先沿通道继续前行才能'
    '到达远处门洞，不要计入该门洞。不要计入只有在选择当前另一条路线后才能到达的'
    '开口、微小家具缝隙、镜子、关闭的门，或观察视图之外虚构的出口。判断当前视图；'
    '较早图像只能用于澄清仍可从当前位置到达的入口或路线。'
)

FALLBACK_CRITERIA_EN = {
    'true': (
        'At least two distinct, physically plausible onward routes are available '
        'at the current position or immediately nearby under the stated boundaries.'
    ),
    'false': (
        'The current step has only one supported route, only a route that is too '
        'distant or already passed, or insufficient visual support for a second '
        'distinct route.'
    ),
}
FALLBACK_CRITERIA_ZH = {
    'true': (
        '按照给定边界，在当前位置或紧邻区域存在至少两条不同且物理上可通行的后续路线。'
    ),
    'false': (
        '当前 step 只支持一条路线，或者只存在过于遥远、已经经过的路线，或者视觉证据'
        '不足以支持第二条不同路线。'
    ),
}

NEAR_FALLBACK_CONTEXT_EN = (
    "You are observing RGB images from an indoor visual navigation robot in "
    "chronological order. The last image is the robot's current view; earlier "
    "images provide nearby spatial structure, historical viewpoints, and "
    "information about potentially occluded areas. Your task is to decide "
    "whether the robot's current position is suitable as a potential navigation "
    "fallback point (checkpoint candidate). You only need to judge whether the "
    "local space offers an opportunity to make different route choices in the "
    "near future. You do not need to judge whether the navigation route is "
    "correct, nor determine the final fallback position."
)
NEAR_FALLBACK_CONTEXT_ZH = (
    "你正在观察室内视觉导航机器人按时间顺序排列的 RGB 图像。最后一张是机器人当前"
    "视图，较早图像提供附近空间结构、历史视角和可能被遮挡区域的信息。你的任务是"
    "判断机器人当前位置是否适合作为潜在导航回退点（Checkpoint Candidate）。你只"
    "需要判断局部空间是否存在近期可以做出不同路线选择的机会，不需要判断导航路线"
    "是否正确，也不需要确定最终回退位置。"
)

NEAR_FALLBACK_INSTRUCTIONS_EN = (
    "Decide whether the robot's current position has value as a potential "
    "fallback point.\n\n"
    "[FALLBACK-POINT DEFINITION]\n"
    "A fallback point is a state close to a local route-decision position. At the "
    "current position, or after continuing forward from it for no more than about "
    "5 action steps, the robot can choose different traversable routes leading "
    "into different passages, rooms, or areas with a clear spatial distinction. "
    "At most about 7 action steps are allowed. A branch that requires more than "
    "7 steps to reach does not belong to the current candidate fallback point. "
    "The emphasis is whether different routes can actually be selected in the "
    "near future, not whether a fork is visible in the distance.\n\n"
    "[RULE 1: STRICT LOCAL-DISTANCE LIMIT]\n"
    "Prioritize positions where the robot can make a different route choice at "
    "the current position or within the next 5 action steps. For a branch reached "
    "at step 6 or 7, consider it only when the visual evidence indicates that it "
    "truly belongs to the immediately adjacent local region. Exclude branches "
    "that are farther than about 7 steps. For example, in a long corridor, even "
    "if a left fork is clearly visible in the distance, the current position is "
    "not a candidate fallback point when the robot must continue along the only "
    "corridor for a substantial distance before reaching it. The key question is "
    "how close the branch is to the current state, not how clearly it appears in "
    "the image. If RGB alone cannot accurately count action steps, estimate "
    "whether the branch is in the immediately adjacent range from corridor "
    "length, floor perspective, wall positions, and earlier images. Do not treat "
    "a visually distant fork as a nearby branch.\n\n"
    "[RULE 2: ACTIVELY USE WEAK VISUAL CUES]\n"
    "A fully visible intersection is not required, and both complete passages do "
    "not need to be visible in the current image. A potential branch may be "
    "inferred when credible local spatial-continuation cues exist nearby. "
    "Examples include floor that continues laterally behind a wall corner, door "
    "frame, or occluder; a wall edge that indicates a side opening; local "
    "perspective structure showing that the corridor edge forms another passage; "
    "a small amount of floor leading to another space at the image boundary; or "
    "an earlier image showing a nearby accessible area that is only partially "
    "visible after the camera orientation changed. Even when only a small part is "
    "visible, if the cue is spatially plausible and the branch is sufficiently "
    "close, actively consider the current position as a candidate. Do not reject "
    "a potential branch merely because its entrance is not fully shown, the side "
    "passage cannot be completely observed, or camera orientation is limited.\n\n"
    "[RULE 3: USE HISTORICAL IMAGES TO UNDERSTAND LOCAL SPACE]\n"
    "All images are in chronological order. Use earlier images to supplement "
    "spatial structure outside the current view, especially lateral openings, "
    "doorways, continuing floor, and wall changes seen as the robot approached or "
    "passed an intersection. A branch may be partially or completely invisible "
    "in the current image, but may still count when earlier images provide "
    "credible evidence and the robot remains near that branch and can enter it "
    "within the action-step limit. An old branch that is clearly behind the robot "
    "and would require a long return trip must not count. Do not invent hidden "
    "passages without any visual basis.\n\n"
    "[RULE 4: DISTINGUISH A REAL ROUTE CHOICE FROM ORDINARY SPACE]\n"
    "A valid candidate should provide value for entering different spatial areas. "
    "An ordinary straight corridor, a single path with only one feasible forward "
    "direction, an ordinary bend without an additional branch, or a position at "
    "which the robot can only turn around and return along the incoming path do "
    "not count as candidates. A wide hall or open area is not automatically a "
    "fallback point; consider it only when recognizable different exits or "
    "spatial branches exist. Mirrors, windows, wall texture, shadows, closed "
    "doors, and impassable gaps cannot by themselves be valid branch evidence. "
    "However, do not mistake a real but partially occluded entrance for an "
    "ordinary wall or impassable area.\n\n"
    "[RULE 5: CANDIDATE DETECTION FIRST; REDUCE MISSES]\n"
    "This is first-stage high-recall candidate detection, not final fallback-point "
    "confirmation. For a sufficiently nearby branch with clear or reasonable "
    "evidence of local spatial continuation, lean toward retaining it as a "
    "candidate even when all passages cannot be fully observed. A stronger model "
    "will later verify candidates. Do not be overly conservative because visual "
    "evidence is incomplete, but do not ignore the distance limit or mark a "
    "position as a candidate without spatial evidence merely to increase recall.\n\n"
    "[FINAL JUDGMENT]\n"
    "Combine the current view and historical images to decide whether the current "
    "position is near a local decision area that can soon produce different "
    "traversable choices. Prioritize choices within 5 steps, allow at most about "
    "7 steps, strictly exclude distant branches, and actively retain nearby "
    "branches supported by credible weak geometric cues. Output the probability "
    "that the current position is a potential fallback-point candidate."
)
NEAR_FALLBACK_INSTRUCTIONS_ZH = (
    "判断机器人当前位置是否具有作为潜在回退点的价值。\n\n"
    "【回退点定义】\n"
    "回退点是一个接近局部路线决策位置的状态。机器人在当前位置，或从当前位置继续"
    "前进约 5 个动作步以内，能够选择不同的可通行路线，进入不同的通道、房间或具有"
    "明确空间区别的区域。最多允许约 7 个动作步，超过 7 步才能到达的分支不属于当前"
    "位置的候选回退点。重点是不同路线能否在近期实际被选择，而不是远处是否能够看见"
    "分叉。\n\n"
    "【规则一：严格的局部距离限制】\n"
    "优先识别当前位置或未来 5 步以内即可做出不同通行选择的位置。对于第 6–7 步"
    "才能到达的分支，只有当视觉证据表明它确实属于紧邻的局部区域时才予以考虑。"
    "超过约 7 步的远处分支必须排除。例如，在一条长走廊中，即使可以清楚看见远处的"
    "左侧岔路，只要机器人必须沿唯一通道继续行进较长距离才能到达，该位置就不应成为"
    "候选回退点。判断的关键是分支距离机器人当前状态有多近，而不是分支在图像中是否"
    "清晰可见。若仅凭 RGB 无法准确计算动作步数，应结合走廊长度、地板透视、墙体"
    "位置以及历史图像估计分支是否处于紧邻范围，不要把视觉上很远的岔路判为附近分支。"
    "\n\n"
    "【规则二：积极利用微弱视觉线索】\n"
    "不要求完整看清一个路口，也不要求在当前画面中同时看见两条完整通道。只要附近"
    "存在可信的局部空间延伸线索，就允许推断潜在分支。例如：地板在墙角、门框或遮挡物"
    "后方继续向侧面延伸；墙壁边缘暗示侧面存在开口；走廊边缘呈现另一条通道的局部"
    "透视结构；画面边缘露出少量通向另一空间的地板；较早图像显示附近存在可进入区域，"
    "但当前因朝向变化而只能部分观察。即使只看到一小部分，只要这些线索在空间几何上"
    "合理，且分支足够接近，就应积极考虑将当前位置判为候选。不要因为入口没有完整显示、"
    "侧向通道不可完全观察或相机朝向受限，就直接否定潜在分支。\n\n"
    "【规则三：结合历史图像理解局部空间】\n"
    "所有图像按照时间顺序排列。利用较早图像补充当前视角之外的空间结构，特别关注"
    "机器人接近或经过路口时，画面中出现的侧向开口、门洞、延伸地板和墙体变化。一个"
    "分支即使在当前画面中部分或完全不可见，只要历史图像提供可信证据，并且机器人当前"
    "仍然处于该分支附近、能够在限定步数内进入，就可以作为候选。已经明显远离、需要"
    "较长距离返回才能进入的旧分支不能计入。不要凭空假设没有任何视觉依据的隐藏通道。"
    "\n\n"
    "【规则四：区分真正的路线选择与普通空间】\n"
    "有效候选应当具有进入不同空间区域的路线选择价值。普通直走长廊、只有一个可行"
    "前进方向的单一路径、没有额外分支的普通转弯，以及仅仅可以原路掉头返回的位置，"
    "不算候选。宽阔大厅或开放区域本身不必然构成回退点，只有存在可辨认的不同通行出口"
    "或空间分支时才考虑。镜子、窗户、墙面纹理、阴影、封闭房门和不可通行的缝隙不能"
    "单独作为有效分支证据。但不要把部分遮挡的真实入口误认为普通墙面或不可通行区域。"
    "\n\n"
    "【规则五：候选检测优先，减少漏检】\n"
    "这是第一阶段的高召回率候选检测，而不是最终回退点确认。对于足够接近、具有明确"
    "或合理局部空间延伸线索的分支，应倾向于保留候选，即使无法完整看清所有通道。"
    "后续会由更强的模型进一步验证。不要因为视觉证据不完整就过度保守；但也不能为了"
    "提高召回率而忽略距离限制，或者将没有空间证据的位置判断为候选。\n\n"
    "【最终判断】\n"
    "综合当前视图与历史图像，判断当前位置是否靠近一个能够很快产生不同通行选择的"
    "局部决策区域。优先 5 步以内，最多不超过约 7 步。对远处分支严格排除；对附近"
    "具有可信微弱几何线索的分支积极保留。输出当前位置是潜在回退点候选的判断概率。"
)

NEAR_FALLBACK_CRITERIA_EN = {
    'true': (
        "A local route choice into a different spatial area is available at the "
        "current position or within about the next 5 action steps; at most about "
        "7 steps is allowed and the branch must belong to the immediately adjacent "
        "region. The branch may be clearly visible or supported only by credible "
        "visual cues such as local floor continuation, a wall opening, a doorway "
        "edge, or a historical viewpoint. Even when the branch is not fully shown, "
        "it should be treated as a potential candidate when it is sufficiently "
        "close and has a reasonable spatial basis."
    ),
    'false': (
        "No credible different traversable route exists at the current position or "
        "within about 7 nearby steps; or the branch is visible but still distant "
        "and requires substantial travel along a single corridor to reach; or the "
        "scene contains only an ordinary straight corridor, a single-path bend, a "
        "turnaround along the incoming route, an open area without a clearly "
        "distinct exit, or lacks credible evidence of spatial continuation."
    ),
}
NEAR_FALLBACK_CRITERIA_ZH = {
    'true': (
        "机器人当前或未来约 5 个动作步以内存在可进入不同空间区域的局部路线选择；"
        "最多允许约 7 步且必须属于紧邻区域。分支可以清晰可见，也可以仅由局部地板"
        "延伸、墙体开口、门洞边缘、历史视角等可信视觉线索支持。即使分支没有完整"
        "显示，只要距离足够近且具有合理空间依据，也应判为潜在候选。"
    ),
    'false': (
        "当前及附近约 7 步范围内没有可信的不同通行路线；或者分支虽然清晰可见，"
        "但仍然位于较远位置，需要沿唯一通道继续行进较长距离才能到达；或者只有普通"
        "直走、单一路径转弯、原路掉头、没有明确出口的开放区域，或缺乏可信空间延伸"
        "证据。"
    ),
}

COMPACT_FALLBACK_CONTEXT_EN = (
    "These images are chronological RGB observations from an indoor navigation "
    "robot. The last image is the current view; earlier images supplement nearby "
    "spatial structure and historical viewpoints. The task is to determine "
    "whether the current position is suitable as a potential navigation fallback "
    "point, not whether the navigation route is correct."
)
COMPACT_FALLBACK_CONTEXT_ZH = (
    "这些图像是室内导航机器人按时间顺序排列的 RGB 观测，最后一张为当前视图，较早"
    "图像用于补充附近的空间结构和历史视角。任务是判断当前位置是否适合作为潜在导航"
    "回退点，不判断导航路线是否正确。"
)

COMPACT_FALLBACK_INSTRUCTIONS_EN = (
    "Determine whether the robot's current position has value as a potential "
    "fallback point.\n\n"
    "A fallback point is a position where the robot can currently, or within about "
    "5 future action steps, make a different traversal choice and enter a different "
    "spatial region. Consider decision positions reachable within at most 7 steps."
    "\n\n"
    "Rules:\n"
    "1. Distance limit: Only a nearby position where a route choice can actually "
    "be made qualifies. Even if a fork is clearly visible in the distance, it does "
    "not count when the robot must continue along a single passage for a "
    "substantial distance before reaching it.\n"
    "2. Visual cues: The fork or entrance does not need to be fully visible. If "
    "credible local geometric cues indicate that another traversable space exists "
    "nearby, such as floor continuing laterally, a wall forming an opening, or a "
    "partially visible entrance, actively consider it as a candidate. Do not ignore "
    "a potential branch merely because the field of view is limited or occluded.\n"
    "3. Spatial choice: Different routes may lead to different corridors, rooms, or "
    "other enterable areas. They do not both need to be fully visible. The key is "
    "that the robot can choose to enter different spaces nearby, rather than first "
    "traveling far along a single road.\n"
    "4. Historical information: Use earlier images to supplement nearby spatial "
    "structure outside the current view. Only branches that remain nearby and can "
    "be reached within a short distance are valid; do not count branches that are "
    "already far away.\n"
    "5. Exclusions: An ordinary straight path, a single-path bend without an "
    "additional branch, a pure return along the incoming route, and an open area "
    "without credible spatial cues do not constitute valid candidates. Do not invent "
    "invisible routes.\n\n"
    "This is candidate detection, not final confirmation. For a nearby potential "
    "branch with reasonable visual cues, lean toward retaining it as a candidate "
    "to reduce misses even when it cannot be fully confirmed, but do not relax the "
    "distance requirement."
)
COMPACT_FALLBACK_INSTRUCTIONS_ZH = (
    "判断机器人当前位置是否具有作为潜在回退点的价值。\n\n"
    "回退点是指机器人当前或在未来约5个动作步内，能够做出不同的通行选择，进入不同"
    "的空间区域的位置。最多考虑7步内可以到达的决策位置。\n\n"
    "判断规则：\n"
    "1. 距离限制：只有附近可以实际做出路线选择的位置才符合条件。即使远处能够清楚"
    "看到分叉，如果还需要沿唯一通道前进较长距离才能到达，则不算回退点。\n"
    "2. 视觉线索：不要求完整看清分叉或入口。只要有可信的局部几何线索表明附近存在"
    "另一片可通行空间，例如地板向侧面延伸、墙体形成开口、部分可见的入口等，就应"
    "积极考虑为候选。不要因为视野受限或遮挡而忽略潜在分支。\n"
    "3. 空间选择：不同路线可以通向不同走廊、房间或其他可进入区域，不要求都是完整"
    "可见的通道。关键是机器人能够在附近选择进入不同空间，而不是必须先沿唯一道路"
    "继续行进很远。\n"
    "4. 历史信息：结合较早图像补充当前视野之外的附近空间结构。只有仍然靠近、可以"
    "在短距离内到达的分支才有效，不能将已经远离的分支算入。\n"
    "5. 排除情况：普通直走、没有额外分支的单一路径转弯、单纯原路返回，以及缺乏"
    "可信空间线索的开放区域，不构成有效候选。不要凭空假设不可见的路线。\n\n"
    "这是候选点检测，而不是最终确认。对于距离足够近且存在合理视觉线索的潜在分支，"
    "即使无法完整确认，也应倾向保留候选，减少漏检；但不能放宽距离要求。"
)

COMPACT_FALLBACK_CRITERIA_EN = {
    'true': (
        "A different traversable route can actually be selected near the current "
        "position, normally within 5 steps and never more than 7. Credible visual "
        "cues are sufficient, including partial occlusion or only locally visible "
        "spatial continuation; every branch does not need to be fully visible."
    ),
    'false': (
        "No credible different traversable route exists nearby; or a branch is "
        "visible but too far away; or there is only a single route, an ordinary "
        "bend, a return along the incoming path, or a guess without spatial evidence."
    ),
}
COMPACT_FALLBACK_CRITERIA_ZH = {
    'true': (
        "当前位置附近存在可实际选择的不同通行路线，通常在5步以内，最多不超过7步。"
        "具有可信的视觉线索即可，包括部分遮挡或仅局部可见的空间延伸，不要求完整看见"
        "所有分支。"
    ),
    'false': (
        "附近没有可信的不同通行路线；或者分支虽然可见，但距离过远；或者只有单一路线、"
        "普通转弯、原路返回或缺乏空间证据的猜测。"
    ),
}


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _prepared_png(path, expected_source_sha):
    """Return a deterministic RGB PNG that satisfies JEV image constraints."""
    raw = Path(path).read_bytes()
    source_sha = _sha256(raw)
    if source_sha != expected_source_sha:
        raise ValueError('Source RGB hash changed: ' + str(path))
    try:
        with Image.open(BytesIO(raw)) as original:
            image = ImageOps.exif_transpose(original).convert('RGB')
            width, height = image.size
            if min(width, height) < 280:
                scale = 280.0 / min(width, height)
                image = image.resize(
                    (
                        max(280, round(width * scale)),
                        max(280, round(height * scale)),
                    ),
                    Image.Resampling.LANCZOS,
                )
            elif max(width, height) > 1568:
                image.thumbnail((1568, 1568), Image.Resampling.LANCZOS)
            width, height = image.size
            if width * height > 2458624:
                raise ValueError('Image exceeds JEV total-pixel limit')
            output = BytesIO()
            image.save(output, format='PNG')
    except (OSError, ValueError) as error:
        if isinstance(error, ValueError) and 'JEV' in str(error):
            raise
        raise ValueError('Cannot decode source image: ' + str(path)) from None
    return raw, output.getvalue(), width, height


def build_request(images, dataset, model=DEFAULT_MODEL):
    """Build a secret-free JEV request from consecutive RGB observations."""
    if not 1 <= len(images) <= 3:
        raise ValueError('JEV node scoring expects one to three images')
    frame_ids = [row['frame'] for row in images]
    if frame_ids != list(range(frame_ids[0], frame_ids[0] + len(frame_ids))):
        raise ValueError('Images must be consecutive and chronological')
    if any(type(frame) is not int for frame in frame_ids):
        raise ValueError('Frame ids must be integers')

    state_frames = []
    assets = {}
    audit_images = []
    current = frame_ids[-1]
    for index, row in enumerate(images):
        path = Path(dataset) / row['rgb']
        source, png, width, height = _prepared_png(path, row['rgb_sha256'])
        source_sha = _sha256(source)
        png_sha = _sha256(png)
        reference = 'jev-frame-%02d-%s' % (index, png_sha[:16])
        if reference in assets:
            raise ValueError('Duplicate JEV image reference')
        offset = row['frame'] - current
        state_frames.append({
            'time': 'current' if offset == 0 else 'previous',
            'offset_frames': offset,
            'image': reference,
        })
        assets[reference] = {
            'type': 'image',
            'format': 'png',
            'data_base64': base64.b64encode(png).decode('ascii'),
        }
        audit_images.append({
            'frame': row['frame'],
            'offset_frames': offset,
            'source_path': str(path),
            'source_sha256': source_sha,
            'prepared_format': 'png',
            'prepared_sha256': png_sha,
            'prepared_bytes': len(png),
            'width': width,
            'height': height,
            'asset_reference': reference,
        })

    questions = {
        'node_score': {
            'type': 'score',
            'instructions': SCORE_INSTRUCTIONS_EN,
            'criteria': list(SCORE_LEVELS_EN),
        },
    }
    for key in DIRECTION_KEYS:
        questions[key] = {
            'type': 'noul',
            'instructions': DIRECTION_INSTRUCTIONS_EN[key],
            'criteria': dict(NOUL_CRITERIA_EN),
        }

    request = {
        'model': model,
        'state': {
            'context': STATE_CONTEXT_EN,
            'images': state_frames,
        },
        'assets': assets,
        'questions': questions,
    }
    return request, audit_images


def build_noul_request(images, dataset, model=DEFAULT_MODEL):
    """Build the v1 fallback-point decision as one JEV Noul question."""
    request, audit_images = build_request(images, dataset, model=model)
    request['questions'] = {
        'fallback_point': {
            'type': 'noul',
            'instructions': FALLBACK_INSTRUCTIONS_EN,
            'criteria': dict(FALLBACK_CRITERIA_EN),
        },
    }
    return request, audit_images


def build_near_fallback_noul_request(images, dataset, model=DEFAULT_MODEL):
    """Build the five-step/seven-step near-fallback candidate Noul request."""
    request, audit_images = build_request(images, dataset, model=model)
    request['state']['context'] = NEAR_FALLBACK_CONTEXT_EN
    request['questions'] = {
        'fallback_point': {
            'type': 'noul',
            'instructions': NEAR_FALLBACK_INSTRUCTIONS_EN,
            'criteria': dict(NEAR_FALLBACK_CRITERIA_EN),
        },
    }
    return request, audit_images


def build_compact_fallback_noul_request(images, dataset, model=DEFAULT_MODEL):
    """Build the compact five-to-seven-step fallback candidate Noul request."""
    request, audit_images = build_request(images, dataset, model=model)
    request['state']['context'] = COMPACT_FALLBACK_CONTEXT_EN
    request['questions'] = {
        'fallback_point': {
            'type': 'noul',
            'instructions': COMPACT_FALLBACK_INSTRUCTIONS_EN,
            'criteria': dict(COMPACT_FALLBACK_CRITERIA_EN),
        },
    }
    return request, audit_images


def request_digest(request):
    payload = json.dumps(
        request, ensure_ascii=False, sort_keys=True, separators=(',', ':')
    ).encode()
    return _sha256(payload)


def request_without_images(request):
    """Return an auditable request view with image payloads removed."""
    copy = json.loads(json.dumps(request))
    for reference, asset in copy.get('assets', {}).items():
        data = asset.pop('data_base64', None)
        if data is not None:
            asset['encoded_sha256'] = hashlib.sha256(data.encode()).hexdigest()
            asset['encoded_bytes'] = len(data)
    return copy


def _write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def call_api(endpoint, key, request, timeout, request_path, attempts=3):
    """POST through curl while keeping the bearer token off argv and disk."""
    if any(character in key for character in '\r\n"\\'):
        raise ValueError('Unsupported API key characters')
    if type(attempts) is not int or not 1 <= attempts <= 5:
        raise ValueError('JEV attempts must be an integer from 1 to 5')
    request_path = Path(request_path)
    _write_json(request_path, request)
    marker = '__JEV_HTTP_STATUS__:'
    config = '\n'.join([
        'url = "%s"' % endpoint,
        'request = "POST"',
        'header = "Authorization: Bearer %s"' % key,
        'header = "Content-Type: application/json"',
        'header = "Accept: application/json"',
        'header = "User-Agent: rightapi-jev-node/1.0"',
        'header = "TypeSafe-Danger-Zone-Images: true"',
        'data-binary = "@%s"' % request_path,
        'noproxy = "*"',
        'silent',
        'show-error',
        'fail-with-body',
        'max-time = %.3f' % timeout,
        'write-out = "%s%%{http_code}"' % marker,
        '',
    ])
    started = time.monotonic()
    statuses = []
    retryable = {0, 408, 429, 500, 502, 503, 504}
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            process = subprocess.run(
                ['curl', '--config', '-'],
                input=config,
                text=True,
                capture_output=True,
                timeout=timeout + 15,
                check=False,
            )
        except subprocess.TimeoutExpired:
            last_error = 'transport timeout'
            statuses.append(0)
        else:
            if marker not in process.stdout:
                detail = (process.stderr or process.stdout).replace(
                    key, '[REDACTED]'
                )
                raise RuntimeError(
                    'JEV transport failure: ' + detail[:2000]
                )
            body, status_text = process.stdout.rsplit(marker, 1)
            try:
                status = int(status_text.strip())
            except ValueError:
                raise RuntimeError(
                    'JEV transport returned an invalid HTTP status'
                ) from None
            statuses.append(status)
            if status == 200:
                raw = json.loads(body)
                if not isinstance(raw, dict):
                    raise ValueError('JEV returned a non-object response')
                return raw, time.monotonic() - started, {
                    'attempts': attempt,
                    'statuses': statuses,
                }
            detail = (
                body.strip() or process.stderr.strip()
            ).replace(key, '[REDACTED]')
            last_error = 'HTTP %d%s' % (
                status,
                ': ' + detail[:1800] if detail else '',
            )
            if status not in retryable:
                raise RuntimeError('JEV ' + last_error)
        if attempt < attempts:
            time.sleep((2, 5, 10, 20)[attempt - 1])
    raise RuntimeError('JEV ' + (last_error or 'transport failure'))


def question_translation():
    """Complete Chinese display translation; never sent as model input."""
    return {
        'state_context': STATE_CONTEXT_ZH,
        'questions': {
            'node_score': {
                'type': 'score',
                'instructions': SCORE_INSTRUCTIONS_ZH,
                'criteria': list(SCORE_LEVELS_ZH),
            },
            **{
                key: {
                    'type': 'noul',
                    'instructions': DIRECTION_INSTRUCTIONS_ZH[key],
                    'criteria': dict(NOUL_CRITERIA_ZH),
                }
                for key in DIRECTION_KEYS
            },
        },
    }


def noul_question_translation():
    """Complete Chinese display translation for the Noul variant."""
    return {
        'state_context': STATE_CONTEXT_ZH,
        'questions': {
            'fallback_point': {
                'type': 'noul',
                'instructions': FALLBACK_INSTRUCTIONS_ZH,
                'criteria': dict(FALLBACK_CRITERIA_ZH),
            },
        },
    }


def near_fallback_question_translation():
    """Complete Chinese display translation for the near-fallback variant."""
    return {
        'state_context': NEAR_FALLBACK_CONTEXT_ZH,
        'questions': {
            'fallback_point': {
                'type': 'noul',
                'instructions': NEAR_FALLBACK_INSTRUCTIONS_ZH,
                'criteria': dict(NEAR_FALLBACK_CRITERIA_ZH),
            },
        },
    }


def compact_fallback_question_translation():
    """Complete Chinese display translation for the compact fallback variant."""
    return {
        'state_context': COMPACT_FALLBACK_CONTEXT_ZH,
        'questions': {
            'fallback_point': {
                'type': 'noul',
                'instructions': COMPACT_FALLBACK_INSTRUCTIONS_ZH,
                'criteria': dict(COMPACT_FALLBACK_CRITERIA_ZH),
            },
        },
    }


def _probability_map(value, expected_keys):
    expected = {str(key) for key in expected_keys}
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError('Unexpected probability keys')
    result = {}
    for key in expected:
        number = value[key]
        if type(number) not in (int, float) or not 0 <= number <= 1:
            raise ValueError('Probability outside 0..1')
        result[key] = float(number)
    if abs(sum(result.values()) - 1.0) > 1e-4:
        raise ValueError('Probabilities do not sum to one')
    return result


def validate_response(raw):
    """Validate the JEV response and map the 0..4 Score to the existing 1..5 scale."""
    if not isinstance(raw, dict):
        raise ValueError('JEV response must be an object')
    if not isinstance(raw.get('model'), str) or not raw['model']:
        raise ValueError('Missing JEV model')
    if not isinstance(raw.get('answers'), dict):
        raise ValueError('Missing JEV answers')
    expected = {'node_score', *DIRECTION_KEYS}
    if set(raw['answers']) != expected:
        raise ValueError('Unexpected JEV answer keys')

    node = raw['answers']['node_score']
    if node.get('type') != 'score':
        raise ValueError('node_score is not a Score answer')
    number = node.get('score')
    if type(number) not in (int, float) or not 0 <= number <= 4:
        raise ValueError('node_score outside 0..4')
    confidence = node.get('confidence')
    if type(confidence) not in (int, float) or not 0 <= confidence <= 1:
        raise ValueError('Invalid node_score confidence')
    probabilities = _probability_map(node.get('probabilities'), range(5))
    expected_number = sum(level * probability for level, probability in enumerate(
        probabilities[str(i)] for i in range(5)
    ))
    # JEV returns probabilities rounded for display; their rebuilt expectation
    # can differ slightly from the separately returned score.
    if abs(float(number) - expected_number) > 0.051:
        raise ValueError('Score does not match its probabilities')

    directions = {}
    for key in DIRECTION_KEYS:
        answer = raw['answers'][key]
        if answer.get('type') != 'noul':
            raise ValueError(key + ' is not a Noul answer')
        probability = answer.get('noul')
        if type(probability) not in (int, float) or not 0 <= probability <= 1:
            raise ValueError('Invalid ' + key + ' probability')
        directions[key] = float(probability)

    continuous = float(number) + 1.0
    rounded = max(1, min(5, int(math.floor(continuous + 0.5))))
    top = max(range(5), key=lambda level: probabilities[str(level)])
    return {
        'score': rounded,
        'score_continuous_1_5': round(continuous, 6),
        'score_0_4': float(number),
        'confidence': float(confidence),
        'probabilities_1_5': {
            str(level + 1): probabilities[str(level)] for level in range(5)
        },
        'highest_probability_score': top + 1,
        'directional_probabilities': directions,
    }


def validate_noul_response(raw):
    """Validate a single v1 fallback-point Noul response."""
    if not isinstance(raw, dict):
        raise ValueError('JEV response must be an object')
    if not isinstance(raw.get('model'), str) or not raw['model']:
        raise ValueError('Missing JEV model')
    answers = raw.get('answers')
    if not isinstance(answers, dict) or set(answers) != {'fallback_point'}:
        raise ValueError('Unexpected JEV answer keys')
    answer = answers['fallback_point']
    if answer.get('type') != 'noul':
        raise ValueError('fallback_point is not a Noul answer')
    probability = answer.get('noul')
    if type(probability) not in (int, float) or not 0 <= probability <= 1:
        raise ValueError('fallback_point probability outside 0..1')
    return {
        'probability_yes': float(probability),
        'probability_no': round(1.0 - float(probability), 12),
    }
