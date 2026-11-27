"""The live worker must retain Node across Isaac environment sanitization."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from core.codex_client import save
from core.codex_live_takeover import clean_child_env
from core.codex_serial_config import DEFAULTS
from core.codex_serial_guard import PipelineGuardError
from core.codex_serial_runtime import ReviewWorker


class NodeWorkerTests(unittest.TestCase):
    def test_real_sampler_works_with_sanitized_path(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "This deployment needs its installed Node runtime")
        with patch.dict(os.environ, {"PATH": str(Path(node).parent)}):
            env = clean_child_env()
        self.assertEqual(env["PATH"], "/usr/local/bin:/usr/bin:/bin")
        code = """from core.codex_serial_review import ActiveSampler
s = ActiveSampler()
try:
    print(s.send(dict(value=0.2, frame=0)))
finally:
    s.close()
"""
        result = subprocess.run([sys.executable, "-B", "-c", code], env=env,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_worker_exit_preserves_runtime_cause_on_broken_pipe(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            save(folder / "config.json", DEFAULTS)
            save(folder / "start.json", dict(episode_id="test", instruction="Go straight.", scene="test"))
            with patch.dict(os.environ, {"VLN_NODE_BINARY": str(folder / "missing-node")}):
                worker = ReviewWorker(folder)
            try:
                worker.child.wait(timeout=30)
                failure = json.loads((folder / "worker_failure.json").read_text())
                self.assertEqual((failure["stage"], failure["code"]), ("jev_sampler", "node_unavailable"))
                with self.assertRaises(PipelineGuardError) as caught:
                    worker.request(dict(episode_id="test", frame=0), lambda: None)
                self.assertEqual(caught.exception.code, "node_unavailable")
            finally:
                worker.close()


if __name__ == "__main__":
    unittest.main()
