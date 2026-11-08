"""Import only this campaign's frozen VLNVerse implementation."""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENDOR = HERE / 'vendor'


def bootstrap(output):
    sys.path[:0] = [str(VENDOR), str(VENDOR / 'vlnverse/model/encoder')]
    import vlnverse
    vlnverse.PROJECT_ROOT_PATH = str(Path(output).resolve())
    return VENDOR
