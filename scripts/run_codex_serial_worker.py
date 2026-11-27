"""One CPU review worker per live episode; stdout is a JSON boundary protocol."""
import json
from pathlib import Path
import signal
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.codex_serial_review import review_stream
from core.codex_serial_guard import PipelineGuardError
from core.codex_client import save, now


def main():
    folder = Path(sys.argv[1]).resolve()
    config = json.loads((folder / "config.json").read_text())
    output = sys.stdout

    def stop(*_):
        raise SystemExit("Review worker cancelled")

    signal.signal(signal.SIGTERM, stop)

    def receive():
        line = sys.stdin.readline()
        return json.loads(line) if line else None

    def reply(row):
        output.write(json.dumps(row) + "\n")
        output.flush()

    try:
        review_stream(folder, config, receive, reply)
    except PipelineGuardError as error:
        save(folder / "worker_failure.json", dict(error.record(), time=now(), scored=False))
        raise
    except Exception as error:
        save(folder / "worker_failure.json", dict(stage="review_worker", code="worker_exception",
             attempts=0, error_type=type(error).__name__, time=now(), scored=False))
        raise


if __name__ == "__main__":
    main()
