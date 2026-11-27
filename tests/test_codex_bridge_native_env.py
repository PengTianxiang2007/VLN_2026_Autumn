"""Native package ordering and long TMPDIR must permit a real socket roundtrip."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class NativeBridgeEnvironmentTest(unittest.TestCase):
    def test_native_import_and_socket_roundtrip_with_long_tmpdir(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            long_tmp = Path(tmp) / ("long-native-output-" * 10)
            long_tmp.mkdir()
            env = dict(os.environ, TMPDIR=str(long_tmp), TEMP=str(long_tmp), TMP=str(long_tmp),
                       PYTHONPATH=str(root / "benchmarks/vlnverse/upstream") + os.pathsep + str(root),
                       BRIDGE_TEST_OUTPUT=str(Path(tmp) / "live"))
            code = '''import json, os, socket, threading, uuid
from pathlib import Path
from types import SimpleNamespace
from scripts.vlnverse_robot_bridge import serve
import vlnverse_robot_bridge as bridge
class FakeRobot:
    def __init__(self, *args):
        self.task = SimpleNamespace(data={"episode_id": "fixture"})
        self.moves = 0
        self.calls = 0
    def call(self, method, action, request_id):
        self.calls += 1
        return {"method": method, "request_id": request_id}
bridge.RobotTools = FakeRobot
replies = []
threads = []
def ready(path):
    endpoint = json.loads(path.read_text())
    assert endpoint["socket"].startswith("/tmp/vlnverse-h1-")
    def client():
        with socket.socket(socket.AF_UNIX) as sock:
            sock.connect(endpoint["socket"])
            sock.sendall((json.dumps({"id": str(uuid.uuid4()), "method": "observe"}) + "\\n").encode())
            replies.append(json.loads(sock.makefile("rb").readline()))
    thread = threading.Thread(target=client)
    threads.append(thread)
    thread.start()
robot = serve(None, Path(os.environ["BRIDGE_TEST_OUTPUT"]), 0,
              on_ready=ready, should_detach=lambda robot: robot.calls > 0)
for thread in threads:
    thread.join(timeout=5)
assert replies[0]["result"]["method"] == "observe"
assert robot.calls == 1
print("NATIVE_BRIDGE_SOCKET_ROUNDTRIP_OK")
'''
            result = subprocess.run([str(root / "benchmarks/vlnverse/.venv/bin/python"), "-B", "-c", code],
                cwd=root / "benchmarks/vlnverse/upstream", env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
