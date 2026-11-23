"""Run a frozen H1 visual rollback batch. Start from the repository root."""
import base64
import getpass
import hashlib
import json
import math
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import time
import traceback

import httpx


ROOT = Path.cwd()
SERIES = "inverse_rollback/vlm_action_v001"
FIRST = "run_20261123_03_deepseek3"
RUN = f"{SERIES}/{os.environ.get('VLN_ROLLBACK_RUN_ID', FIRST)}"
RECORD = ROOT / "experiments" / RUN
OUT = ROOT / "outputs" / RUN
DATA = ROOT / "outputs" / SERIES / "run_20261123_02"
ORIGINAL = ROOT / "outputs/offline_route_dataset/v001/run_20261118_01/dataset"
NATIVE = ROOT / "outputs/inverse_rollback/v002/run_20261122_01_backward_rgb22/source"
CAPTURE = ROOT / "outputs/multiview_capture/v001/run_20261117_03/code"
SELECTION = Path(os.environ.get("VLN_ROLLBACK_CASE_FILE", RECORD / "cases.json"))
IDS = tuple(json.loads(SELECTION.read_bytes())) if SELECTION.exists() else ("C03", "C05", "C07")
PROMPTS = Path(os.environ.get("VLN_ROLLBACK_PROMPT_DIR", ROOT / "experiments" / SERIES / FIRST))
PROTOCOL = os.environ.get("VLN_ROLLBACK_PROTOCOL", "description_joint")
if PROTOCOL not in ("description_joint", "seven_action_judge"):
    raise ValueError(f"Unknown rollback protocol: {PROTOCOL}")
MOVES = {"FORWARD": 1, "LEFT": 2, "RIGHT": 3}
ENDPOINT = "https://api.deepseek.com/chat/completions"
SETTINGS = dict(model="deepseek-flash", temperature=0, top_p=1, max_tokens=4096,
                thinking={"type": "disabled"}, response_format={"type": "json_object"})


def read(path):
    return json.loads(path.read_bytes())


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def status(phase, **data):
    save(OUT / "status.json", dict(phase=phase, time=time.time(), pid=os.getpid(), **data))


def image_ref(label, path, expected_hash):
    return dict(label=label, path=str(path.relative_to(ROOT)), sha256=expected_hash)


def validate(answer, stage):
    if not isinstance(answer, dict):
        raise ValueError("Expected a JSON object")
    if answer.get("type") == "json_object":
        answer = {k: v for k, v in answer.items() if k != "type"}
    if stage == "outbound":
        if set(answer) != {"route_description"} or not isinstance(answer["route_description"], str) or not answer["route_description"].strip():
            raise ValueError("Missing outbound description")
    elif stage == "action":
        actions = answer.get("actions")
        if (set(answer) != {"actions"} or not isinstance(actions, list) or len(actions) != 4
                or any(not isinstance(a, str) or a not in MOVES for a in actions)):
            raise ValueError("Expected exactly four native actions")
    elif stage == "judge":
        if set(answer) != {"arrived"} or type(answer["arrived"]) is not bool:
            raise ValueError("Expected an arrival boolean")
    else:
        if set(answer) != {"arrived", "actions"} or type(answer["arrived"]) is not bool:
            raise ValueError("Invalid arrival decision")
        actions = answer["actions"]
        if not isinstance(actions, list) or len(actions) != (0 if answer["arrived"] else 4) or any(a not in MOVES for a in actions):
            raise ValueError("Invalid return action list")
    return answer


def ask(key, case_dir, name, stage, text, images):
    directory = case_dir / "requests" / name
    directory.mkdir(parents=True, exist_ok=False)
    prompt = (OUT / "source" / (stage + "_en.txt")).read_text()
    save(directory / "input.json", dict(text=text, images=images, settings=SETTINGS, endpoint=ENDPOINT, prompt=prompt))
    content = [dict(type="text", text=json.dumps(text, ensure_ascii=False))]
    for item in images:
        data = (ROOT / item["path"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise ValueError("Input image hash mismatch")
        content.append(dict(type="text", text=item["label"]))
        content.append(dict(type="image_url", image_url=dict(url="data:image/png;base64," + base64.b64encode(data).decode(), detail="high")))
    body = dict(SETTINGS, messages=[dict(role="system", content=prompt), dict(role="user", content=content)])
    with httpx.Client(timeout=httpx.Timeout(300, connect=30), follow_redirects=False, trust_env=False) as client:
        reply = client.post(ENDPOINT, headers={"Authorization": "Bearer " + key}, json=body)
    safe = reply.text.replace(key, "[redacted]")
    (directory / "response.json").write_text(safe)
    save(directory / "transport.json", dict(http_status=reply.status_code, time=time.time()))
    reply.raise_for_status()
    choice = json.loads(safe)["choices"][0]
    if choice.get("finish_reason") != "stop":
        raise ValueError("Incomplete model reply")
    answer = validate(json.loads(choice["message"]["content"]), stage)
    save(directory / "answer.json", answer)
    return answer


def prepare(key):
    rows = [row for row in read(DATA / "manifest.json")["cases"] if row["case_id"] in IDS]
    if tuple(c["case_id"] for c in rows) != IDS:
        raise ValueError("Frozen selection changed")
    source = OUT / "source"
    source.mkdir(parents=True, exist_ok=False)
    stages = ("action", "judge") if PROTOCOL == "seven_action_judge" else ("outbound", "return")
    for stage in stages:
        if "json" not in (PROMPTS / (stage + "_en.txt")).read_text().lower():
            raise ValueError(f"DeepSeek JSON mode requires the word JSON in the {stage} prompt")
    for path in (Path(__file__), NATIVE / "run_inverse_rollback.py", DATA / "source/eval_config.py",
                 *(PROMPTS / (stage + "_en.txt") for stage in stages)):
        shutil.copy2(path, source / path.name)
    save(OUT / "manifest.json", dict(cases=rows, data=str(DATA.relative_to(ROOT)), dataset_sha256=sha(DATA/"manifest.json"),
         seed=2, protocol=PROTOCOL, settings=SETTINGS, git_head=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
         sources={p.name:sha(p) for p in source.iterdir()}, position_threshold_m=0.35, native_budget_ticks=25000))
    reuse = read(Path(os.environ["VLN_ROLLBACK_REUSE"])) if "VLN_ROLLBACK_REUSE" in os.environ else {}
    for case in rows:
        cid = case["case_id"]
        directory = OUT / "cases" / cid
        ref_file = DATA / case["reference"]
        ref = read(ref_file)
        frames = ref["observations"]
        if len(frames) != 7:
            raise ValueError("Expected seven historical observations")
        def pic(label, item):
            return image_ref(label, ref_file.parent / item["image"], item["sha256"])
        historical = [pic(f'{f["role"]} F{f["step"]}', f) for f in frames]
        first = ref["action_start_step"]
        intervals = [{"from": f'F{before["step"]}', "to": f'F{after["step"]}',
                      "actions":ref["actions"][before["step"]-first:after["step"]-first]} for before, after in zip(frames, frames[1:])]
        if PROTOCOL == "seven_action_judge":
            if [a for interval in intervals for a in interval["actions"]] != ref["actions"]:
                raise ValueError("The intervals must cover every outbound action")
            save(directory / "fixed.json", historical)
            save(directory / "outbound_steps.json", dict(outbound_intervals=intervals))
            continue
        with (ORIGINAL / "inputs" / case["episode_id"] / "observations.jsonl").open() as f:
            target = next(r for r in map(json.loads, f) if r["step"] == first)
        reverse, = [im for im in target["views_360"] if abs(im["relative_yaw_deg"]) == 180]
        fixed = [pic(label, frames[index]) for label, index in (("A_FRONT",0),("MID_FRONT",3),("B_FRONT",6))]
        fixed.append(image_ref("A_REVERSE", ORIGINAL / reverse["image"], reverse["sha256"]))
        save(directory / "fixed.json", fixed)
        status("outbound_request", case=cid)
        text = dict(outbound_intervals=intervals)
        if cid in reuse:
            prior = ROOT / reuse[cid]
            metadata = read(prior / "input.json")
            if (metadata["text"] != text or metadata["images"] != historical or metadata["settings"] != SETTINGS
                    or metadata["prompt"] != (source / "outbound_en.txt").read_text()):
                raise ValueError("Cannot reuse a different outbound request")
            validate(read(prior/"answer.json"), "outbound")
            shutil.copytree(prior, directory/"requests/outbound")
        else:
            ask(key, directory, "outbound", "outbound", text, historical)
        print("Outbound description complete", cid, flush=True)


def gpu_admission():
    sys.path.insert(0, str(ROOT))
    from scripts.evaluate import check_gpu
    while True:
        raw = subprocess.check_output(["nvidia-smi","--query-gpu=index,memory.free,utilization.gpu","--format=csv,noheader,nounits"],text=True)
        choices = [tuple(map(int, line.split(","))) for line in raw.splitlines()]
        for gpu, free, util in sorted(choices, key=lambda item: -item[1]):
            if free >= 12000 and util <= 10:
                info = check_gpu(gpu, 12000, allow_shared=True)
                info["existing_cwds"] = {}
                for row in info["existing_processes"]:
                    pid = row.split(",")[-1].strip()
                    try:
                        info["existing_cwds"][pid] = os.readlink("/proc/" + pid + "/cwd")
                    except OSError:
                        info["existing_cwds"][pid] = "unavailable"
                save(OUT / "admission.json", dict(info, utilization=util, time=time.time()))
                return gpu
        status("waiting_for_gpu")
        time.sleep(20)


def input_key():
    key = getpass.getpass("DeepSeek key (hidden): ") if sys.stdin.isatty() else sys.stdin.readline().strip()
    if not key:
        raise ValueError("Missing runtime credential")
    return key


def start(key, resume=False):
    launcher = OUT/"source/run_vlm_rollback.py"
    if resume:
        if list(OUT.glob("cases/*/actions.jsonl")):
            raise RuntimeError("Cannot restart an episode with recorded physical actions")
        previous = read(OUT/"status.json")
        fix = OUT/"source"/f"resume_{time.time_ns()}"
        fix.mkdir()
        launcher = fix/"run_vlm_rollback.py"
        shutil.copy2(__file__,launcher)
        save(fix/"provenance.json",dict(previous_status=previous,script_sha256=sha(launcher)))
        for cid in IDS if PROTOCOL == "description_joint" else ():
            req = OUT/"cases"/cid/"requests/outbound"
            if not (req/"answer.json").exists():
                choice = read(req/"response.json")["choices"][0]
                if choice.get("finish_reason") != "stop":
                    raise ValueError("Incomplete stored outbound response")
                save(req/"answer.json",validate(json.loads(choice["message"]["content"]),"outbound"))
    else:
        OUT.mkdir(parents=True, exist_ok=False)
        prepare(key)
    gpu = gpu_admission()
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu), VLN_SIM_RENDER_GPU=str(gpu), VLN_EVAL_SEED="2", PYTHONHASHSEED="2",
               VLN_SIM_CACHE_ROOT=str(CAPTURE / "benchmarks/vlnverse/runner"), HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
               OMP_NUM_THREADS="4", MKL_NUM_THREADS="4", OPENBLAS_NUM_THREADS="4")
    rows = read(OUT/"manifest.json")["cases"]
    pending = [c for c in rows if not (OUT/"cases"/c["case_id"]/"result.json").exists()]
    while pending:
        status("starting_isaac", gpu=gpu, cases=[c["case_id"] for c in pending])
        with (OUT / f"isaac_{pending[0]['case_id']}.log").open("x") as log:
            command = ["bash", str(ROOT/"scripts/run_crossing_panorama_isaac.sh"), str(launcher), "worker", str(gpu)]
            subprocess.run(command, input=key+"\n", text=True, stdout=log, stderr=subprocess.STDOUT, env=env, check=True)
        remaining = [c for c in pending if not (OUT/"cases"/c["case_id"]/"result.json").exists()]
        if len(remaining) == len(pending):
            raise RuntimeError("Isaac exited without completing a case")
        pending = remaining
    results = [read(OUT/"cases"/c["case_id"]/"result.json") for c in rows]
    save(OUT/"summary.json", dict(results=results, passed=sum(r["passed"] for r in results)))
    status("complete", cases=len(results), passed=sum(r["passed"] for r in results))


def run_case(key, env, case, native):
    import numpy as np
    cid = case["case_id"]
    directory = OUT/"cases"/cid
    images_dir = directory/"rgb"/"return"
    images_dir.mkdir(parents=True, exist_ok=False)
    sim = read(DATA/case["simulation"])
    s = sim["start_B"]["physical_state_before"]
    target = sim["target_A"]["robot_pose"]
    task, = env.env.runner.current_tasks.values()
    if task.data["episode_id"] != case["episode_id"]:
        raise RuntimeError("Unexpected episode")
    art = task.robot.articulation._articulation
    ob, ended, _ = native.tick_action(env, {"stand_still":[]}, 500)
    if ended:
        raise RuntimeError("Warmup terminated")
    offset = np.asarray(task.env_offset) - sim["historical_environment_offset"]
    art.set_world_pose(position=np.asarray(s["position"])+offset, orientation=np.asarray(s["rotation"]))
    art.set_world_velocity(np.zeros(6))
    art.set_joint_positions(np.asarray(s["joints"]))
    art.set_joint_velocities(np.asarray(s["joint_velocities"]))
    def pose():
        p, q = art.get_world_pose()
        return (p-offset).tolist(), q.tolist()
    p, q = pose()
    if not np.allclose(p,s["position"],atol=1e-4,rtol=0) or abs(np.dot(q,s["rotation"])) < .99999:
        raise RuntimeError("B pose readback mismatch")
    save(directory/"start_B.json",dict(position=p,rotation=q,physical_ticks=task.step_count))
    world = env.env.runner._world
    controller = task.robot.controllers["move_by_discrete"]
    if not math.isclose(math.degrees(controller.rotation_speed * controller.steps_per_action / controller.physics_frequency),15):
        raise RuntimeError("Unexpected turn angle")
    def move(action, phase, index):
        observation, terminal, ticks = native.tick_action(env, {"move_by_discrete":[MOVES[action]]}, controller.steps_per_action)
        p, q = pose()
        point = dict(phase=phase, index=index, action=action, ticks=ticks, physical_ticks=task.step_count,
                     position=p, rotation=q, terminated=terminal, **native.errors(p,q,target))
        with (directory/"actions.jsonl").open("a") as trace:
            trace.write(json.dumps(point)+"\n")
        return observation, terminal
    def capture(n):
        path = images_dir / f"R{n:04d}.png"
        item = native.save_native_rgb(path,task,world,ob)
        return image_ref(f"R{n}", path, item["sha256"])
    status("turnaround", case=cid)
    for turn in range(1,13):
        ob, ended = move("LEFT","turnaround",turn)
        if ended:
            break
    executed, pictures = [], []
    arrived = False
    if not ended:
        pictures.append(capture(0))
    fixed = read(directory/"fixed.json")
    separate = PROTOCOL == "seven_action_judge"
    if separate:
        outbound_steps = read(directory/"outbound_steps.json")
    else:
        description = read(directory/"requests/outbound/answer.json")["route_description"]
    while not ended:
        n = len(executed)
        if separate:
            observation = dict(pictures[-1], label=f"CURRENT R{n}")
            images = [*fixed, observation]
            if n:
                status("judge_request", case=cid, executed=n, gpu=os.environ["VLN_SIM_RENDER_GPU"])
                arrived = ask(key, directory, f"judge_{n:04d}", "judge", outbound_steps, images)["arrived"]
                if arrived:
                    break
            status("action_request", case=cid, executed=n, gpu=os.environ["VLN_SIM_RENDER_GPU"])
            answer = ask(key, directory, f"action_{n:04d}", "action", outbound_steps, images)
        else:
            indices = [i for i in (n-8,n-4,n-2,n) if i >= 0]
            imgs = [dict(pictures[i]) for i in indices]
            imgs[-1]["label"] += " CURRENT"
            boundaries = sorted({0,*indices})
            history = [dict(start=f"R{i}", end=f"R{j}", actions=executed[i:j]) for i,j in zip(boundaries,boundaries[1:])]
            status("return_request", case=cid, executed=n, gpu=os.environ["VLN_SIM_RENDER_GPU"])
            answer = ask(key,directory,f"return_{n:04d}","return",
                         dict(OUTBOUND_DESCRIPTION=description,RETURN_HISTORY=history),fixed+imgs)
            arrived = answer["arrived"]
            if arrived:
                break
        for action in answer["actions"]:
            index = len(executed)+1
            ob, ended = move(action,"return",index)
            executed.append(action)
            pictures.append(capture(index))
            if not (OUT/"startup.json").exists():
                save(OUT/"startup.json", dict(case=cid, episode=case["episode_id"], model=SETTINGS["model"], first_action=action,
                     returned_observation=pictures[-1], physical_ticks=task.step_count, terminated=ended))
            if ended:
                break
    p, q = pose()
    error = native.errors(p,q,target)
    result = dict(case=cid, arrived=arrived, physical_terminal=ended, terminal_reason=ob.get("fail_reason","") if ended else "",
                  return_actions=len(executed), turnaround_actions=turn, **error, passed=bool(arrived and error["xy_m"]<=.35))
    save(directory/"result.json", result)
    print("VLM_ROLLBACK_RESULT", json.dumps(result), flush=True)


def worker(key,gpu):
    import resource
    sys.path.insert(0,str(OUT/"source"))
    import run_inverse_rollback as native
    sys.path[:0] = [str(CAPTURE),str(CAPTURE/"benchmarks/vlnverse/upstream")]
    sys.argv[1:] = [f"--/renderer/activeGpu={gpu}", "--/renderer/multiGpu/enabled=False"]
    from vlnverse.configs.evaluator.default_config import get_config
    from vlnverse.evaluator.utils.common import set_seed_model
    from vlnverse.evaluator.utils.eval import generate_episode
    from vlnverse.projects.dataloader.base import BasePathKeyDataloader
    from vlnverse.env import Env
    set_seed_model(2)
    cfg = get_config(runpy.run_path(str(OUT/"source/eval_config.py"))["eval_cfg"])
    settings = cfg.dataset.dataset_settings
    loader = BasePathKeyDataloader(dataset_type=cfg.dataset.dataset_type,
                 **{k:settings[k] for k in ("base_data_dir","split_data_types","robot_offset","filter_same_trajectory","filter_stairs")})
    loader.task_name = "vlm_rollback"
    rows = [r for r in read(OUT/"manifest.json")["cases"] if not (OUT/"cases"/r["case_id"]/"result.json").exists()]
    keys = {v["episode_id"]:k for k,v in loader.path_key_data.items()}
    loader.resumed_path_key_list = [keys[c["episode_id"]] for c in rows]
    cfg.task.task_settings["episodes"] = generate_episode(loader,cfg)
    env = Env.init(cfg.env,cfg.task)
    try:
        for i,case in enumerate(rows):
            env.reset([0] if i else None)
            run_case(key,env,case,native)
            if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss > 24000*1024:
                break
    except Exception as exc:
        # Isaac may exit the interpreter inside close(), before the outer handler can log the error.
        save(OUT / "worker_error.json", dict(error=repr(exc).replace(key, "[redacted]"),
                                            traceback=traceback.format_exc().replace(key, "[redacted]")))
        raise
    finally:
        env.close()


if __name__ == "__main__":
    if sys.argv[1:] in (["start"], ["resume"]):
        resume = sys.argv[1] == "resume"
        if not resume and OUT.exists():
            raise SystemExit("Run already exists")
        if resume and (not (OUT/"status.json").is_file() or read(OUT/"status.json")["phase"] != "error"
                       or list(OUT.glob("cases/*/actions.jsonl"))):
            raise SystemExit("Resume is only available for an interrupted run before the first physical action")
        credential = input_key()
        try:
            start(credential,resume)
        except Exception as exc:
            if OUT.exists():
                status("error", error=str(exc).replace(credential,"[redacted]"))
            raise
    elif len(sys.argv) == 3 and sys.argv[1] == "worker":
        worker(input_key(),int(sys.argv[2]))
    else:
        raise SystemExit("Use start from the repository root")
