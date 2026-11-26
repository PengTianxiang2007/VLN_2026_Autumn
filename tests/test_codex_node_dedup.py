"""Scoped contracts: CLI sessions, failure handling, and frozen dedup semantics."""
import json
from dataclasses import replace
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from core.codex_client import CodexCallError, CodexConfig, CodexSession, sha256
from core.codex_node_dedup import comparison_input, output_schema, run_case
from core.codex_checkpoint_review import MODE, run_case as run_memory_case


class CodexDedupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.image = self.root / "frame.png"
        self.image.write_bytes(b"fake image for transport-only tests")

    def config(self, mode="ok"):
        executable = self.root / ("fake_codex_" + mode)
        executable.write_text(f"#!{sys.executable}\n" + '''
import json, pathlib, sys, uuid
args = sys.argv[1:]
prompt = sys.stdin.read()
thread = args[2] if args[1] == 'resume' else str(uuid.uuid4())
target = pathlib.Path(args[args.index('--output-last-message') + 1])
metadata = json.loads((target.parent/'request.json').read_text())['metadata']
answer = dict(previous_id=metadata.get('previous_id','a'), current_id=metadata.get('current_id','b'),
              relation='same', matched_branches=[dict(description='同一门洞',a_frames=['A0'],b_frames=['B0'])],
              a_only=[], b_only=[], reason='两组提供同一入口。')
''' + f"mode = {mode!r}\n" + '''
if mode == 'absent_evidence': answer['matched_branches'][0]['a_frames'] = ['A+9']
if mode == 'removed_frame': answer['matched_branches'][0]['a_frames'] = ['A+1']
if metadata.get('mode') == 'checkpoint_memory_v003':
    if 'current_id' not in metadata:
        answer = dict(ready=True)
    else:
        name = metadata['current_id'].split(':')[1]
        eligibility = 'not_eligible' if name == 'S03' else 'uncertain' if name == 'S05' else 'eligible'
        relation = 'not_compared' if eligibility == 'not_eligible' or metadata['previous_id'] is None else 'same' if name in ('S02', 'S05') else 'different'
        answer.update(previous_id=metadata['previous_id'], eligibility=eligibility,
                      eligibility_reason='Visible routes.', reason='Branch judgment.', relation=relation)
        if relation == 'not_compared': answer['matched_branches'] = []
target.write_text('not json' if mode == 'bad_json' else json.dumps(answer,ensure_ascii=False))
print(json.dumps(dict(type='thread.started',thread_id=thread)))
if mode == 'reconnected': print(json.dumps(dict(type='error',message='Reconnecting... 1/5 (429 Too Many Requests)')))
print(json.dumps(dict(type='turn.completed',usage=dict(input_tokens=10,output_tokens=5))))
sys.exit(2 if mode == 'exit_error' else 0)
''', encoding="utf-8")
        executable.chmod(0o700)
        return CodexConfig(binary=str(executable), home=str(self.root / "fake_home"), timeout_seconds=10)

    def node(self, name, index):
        return dict(id=name, index=index, ready_at_frame=index + 5,
                    candidate_id=f"C01:{name}:F{index}", images=[
                        dict(frame=index + offset, label="F0" if offset == 0 else f"F{offset:+d}",
                             path="frame.png", image_id=sha256(self.image))
                        for offset in range(-2, 3)])

    def test_explicit_resume_and_independent_case_sessions(self):
        config = self.config()
        first = CodexSession(self.root / "one", config)
        a = first.ask("first", [self.image], output_schema(), label="A_B")
        b = first.ask("second", [self.image], output_schema(), label="B_C")
        second = CodexSession(self.root / "two", config)
        c = second.ask("other case", [], output_schema(), label="A_B")
        self.assertEqual(a["thread_id"], b["thread_id"])
        self.assertNotEqual(a["thread_id"], c["thread_id"])
        self.assertEqual(b["resumed_thread_id"], a["thread_id"])
        request = json.loads((Path(b["directory"]) / "request.json").read_text())
        self.assertEqual(request["command"][1:4], ["exec", "resume", a["thread_id"]])
        self.assertNotIn("--last", request["command"])
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", request["command"])
        self.assertEqual(Path(request["images"][0]["path"]).read_bytes(), self.image.read_bytes())
        self.assertEqual((Path(b["directory"]) / "prompt.txt").read_text(), "second")

    def test_nonzero_exit_rejects_even_existing_final_output(self):
        session = CodexSession(self.root / "failed", self.config("exit_error"))
        with self.assertRaises(CodexCallError):
            session.ask("p", [], output_schema(), label="A_B")
        self.assertEqual(json.loads((session.directory / "session.json").read_text())["status"], "error")
        with self.assertRaises(CodexCallError):
            session.ask("retry", [], output_schema(), label="A_B")

    def test_successful_cli_retry_accepts_completed_response(self):
        session = CodexSession(self.root / "reconnected", self.config("reconnected"))
        response = session.ask("p", [], output_schema(), label="A_B")
        self.assertEqual(response["status"], "ok")

    def test_same_deletes_old_and_large_gap_skips_codex(self):
        case = dict(case_number=1, episode_id="837", nodes=[
            self.node("S01", 2), self.node("S02", 5), self.node("S03", 15)])
        result = run_case(case, self.root, self.root / "dedup", self.config())
        self.assertEqual(result["final_active_ids"], ["S02", "S03"])
        self.assertEqual(result["summary"]["model_calls"], 1)
        self.assertEqual(result["decisions"][1]["action"], "replace_previous")
        self.assertEqual([n["id"] for n in case["nodes"]], ["S01", "S02", "S03"])

    def test_invalid_json_and_absent_evidence_preserve_both(self):
        for mode in ("bad_json", "absent_evidence"):
            with self.subTest(mode=mode):
                case = dict(case_number=1, episode_id="837", nodes=[self.node("S01", 2), self.node("S02", 5)])
                result = run_case(case, self.root, self.root / mode, self.config(mode))
                self.assertEqual(result["final_active_ids"], ["S01", "S02"])
                self.assertEqual(result["summary"]["format_errors"], 1)
                self.assertEqual(result["decisions"][1]["relation"], "uncertain")

    def test_transport_failure_does_not_commit_candidate(self):
        case = dict(case_number=1, episode_id="837", nodes=[self.node("S01", 2), self.node("S02", 5)])
        out = self.root / "transport_failure"
        with self.assertRaises(CodexCallError):
            run_case(case, self.root, out, self.config("exit_error"))
        state = json.loads((out / "state.json").read_text())
        self.assertEqual((state["status"], state["processed"], state["active_ids"]), ("error", 1, ["S01"]))
        self.assertFalse((out / "result.json").exists())

    def test_missing_start_frames_and_no_extra_task_context(self):
        a, b = self.node("S01", 0), self.node("S02", 5)
        for im in a["images"][:2]:
            im.clear()
        a["images"][:2] = [dict(frame=-2, label="F-2", missing=True), dict(frame=-1, label="F-1", missing=True)]
        a.update(instruction="secret route", pose=[1, 2, 3])
        prompt, images, metadata = comparison_input(a, b, self.root)
        self.assertEqual(len(images), 8)
        self.assertEqual(metadata["image_labels"][2]["label"], "A0")
        self.assertNotIn("secret route", prompt)
        self.assertIn("缺失", prompt)
        b["images"][0]["image_id"] = "incorrect"
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            comparison_input(a, b, self.root)

    def test_timeout_stops_only_owned_child(self):
        child = unittest.mock.Mock(pid=12345)
        child.poll.return_value = None
        with patch("core.codex_client.os.killpg") as kill:
            CodexSession._stop(child)
        kill.assert_called_once_with(12345, __import__("signal").SIGTERM)
        child.wait.assert_called_once_with(timeout=5)

    def test_three_frame_prompt_attachments_and_reference_validation(self):
        nodes = [self.node("S01", 2), self.node("S02", 5)]
        for node in nodes:
            node["images"] = [im for im in node["images"] if im["label"] in ("F-2", "F0", "F+2")]
        prompt, images, metadata = comparison_input(*nodes, self.root, (-2, 0, 2))
        self.assertEqual(len(images), 6)
        self.assertEqual([im["label"] for im in metadata["image_labels"]],
                         ["A-2", "A0", "A+2", "B-2", "B0", "B+2"])
        for label in ("A-1", "A+1", "B-1", "B+1"):
            self.assertNotIn(label, prompt)
        for mode, expected_errors in (("ok", 0), ("removed_frame", 1)):
            result = run_case(dict(case_number=1, episode_id="837", nodes=nodes,
                                   observation_offsets=[-2, 0, 2]), self.root,
                              self.root / ("three_" + mode), self.config(mode))
            self.assertEqual(result["summary"]["format_errors"], expected_errors)
            self.assertEqual(result["final_active_ids"], ["S01", "S02"] if expected_errors else ["S02"])

    def test_parallel_cases_keep_separate_sessions_and_ordered_results(self):
        config = self.config()
        cases = [dict(case_number=i, episode_id=str(i), nodes=[self.node("S01", 2), self.node("S02", 5)])
                 for i in range(1, 4)]
        manifest = self.root / "input.json"
        manifest.write_text(json.dumps(dict(upstream_policy="existing_raw_sampled_nodes",
                                            image_root=str(self.root), cases=cases)))
        out = self.root / "parallel"
        command = [sys.executable, "scripts/run_codex_node_dedup.py", "--input", str(manifest),
                   "--output", str(out), "--workers", "3", "--codex-bin", config.binary,
                   "--codex-home", config.home]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=90)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        status = json.loads((out / "status.json").read_text())
        results = json.loads((out / "results.json").read_text())
        self.assertEqual((status["status"], status["workers"], status["completed_cases"]), ("complete", 3, 3))
        self.assertEqual([c["case_number"] for c in results["cases"]], [1, 2, 3])
        self.assertEqual(len({c["thread_id"] for c in results["cases"]}), 3)
        outcomes = [json.loads(line) for line in completed.stdout.splitlines()]
        self.assertEqual(len({r["worker_pid"] for r in outcomes if "worker_pid" in r}), 3)

    def test_memory_review_references_retained_checkpoint_and_sends_each_candidate_once(self):
        nodes = [self.node(f"S{i:02d}", frame) for i, frame in enumerate([2, 5, 10, 20, 25], 1)]
        for node in nodes:
            node["images"] = [im for im in node["images"] if im["label"] in ("F-2", "F0", "F+2")]
        case = dict(case_number=1, episode_id="837", nodes=nodes, observation_offsets=[-2, 0, 2], mode=MODE)
        result = run_memory_case(case, self.root, self.root / "memory", self.config())
        self.assertEqual(result["final_active_ids"], ["S02", "S05"])
        self.assertEqual([d["previous_id"] for d in result["decisions"]], [None, "S01", "S02", "S02", "S04"])
        self.assertEqual([d["action"] for d in result["decisions"]],
                         ["append_current", "replace_previous", "reject_current", "append_current", "replace_previous"])
        self.assertEqual(result["summary"]["model_calls"], 5)
        self.assertEqual(result["summary"]["uncertain"], 1)
        turns = sorted((self.root / "memory/codex/turns").iterdir())
        requests = [json.loads((turn / "request.json").read_text()) for turn in turns]
        self.assertEqual([len(r["images"]) for r in requests], [0, 3, 3, 3, 3, 3])
        self.assertTrue(all(r["resumed_thread_id"] == result["thread_id"] for r in requests[1:]))
        self.assertTrue(all((turn / "prompt.txt").read_text().isascii() for turn in turns))

    def test_resume_preserves_decisions_and_routes_child_through_new_proxy(self):
        nodes = [self.node(f"S{i:02d}", frame) for i, frame in enumerate([2, 5, 10], 1)]
        for node in nodes:
            node["images"] = [im for im in node["images"] if im["label"] in ("F-2", "F0", "F+2")]
        case = dict(case_number=1, episode_id="837", nodes=nodes, observation_offsets=[-2, 0, 2], mode=MODE)
        old = self.root / "old"
        config = self.config()
        original = run_memory_case(case, self.root, old, config)
        (old / "decisions.jsonl").write_text(json.dumps(original["decisions"][0]) + "\n")
        resumed_case = dict(case, resume_from=str(old), reuse_pending_images="S02")
        with patch("core.codex_client.subprocess.Popen", wraps=subprocess.Popen) as spawn:
            result = run_memory_case(resumed_case, self.root, self.root / "resumed",
                                     replace(config, proxy_url="http://127.0.0.1:17982"))
        self.assertEqual(result["thread_id"], original["thread_id"])
        self.assertEqual(result["decisions"][0], original["decisions"][0])
        self.assertEqual(result["final_active_ids"], original["final_active_ids"])
        turns = sorted((self.root / "resumed/codex/turns").iterdir())
        requests = [json.loads((turn / "request.json").read_text()) for turn in turns]
        self.assertEqual([len(r["images"]) for r in requests], [0, 3])
        self.assertEqual(len(spawn.call_args_list), 2)
        for call in spawn.call_args_list:
            self.assertEqual(call.kwargs["env"]["HTTPS_PROXY"], "http://127.0.0.1:17982")


if __name__ == "__main__":
    unittest.main()
