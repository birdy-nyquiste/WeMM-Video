"""Locations shared by the interface modules."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
NATIVE_DIR = ROOT / 'native'
RUNS_DIR = ROOT / 'runs'
BUILD_LOGS_DIR = ROOT / 'logs' / 'build'

# native/run_hf.py is a script, not a package. Put its folder on the import
# path so the interface reuses its command builder instead of copying it.
if str(NATIVE_DIR) not in sys.path:
    sys.path.insert(0, str(NATIVE_DIR))

MODEL_REPOS = {
    '2B': 'tencent/WeMM-Video-2B-GGUF',
    '4B': 'tencent/WeMM-Video-4B-GGUF',
    '9B': 'tencent/WeMM-Video-9B-GGUF',
    '35B-A3B': 'tencent/WeMM-Video-35BA3B-GGUF',
}
BUNDLE_FILES = ['language.gguf', 'mmproj.gguf', 'audio.gguf']


def size_for_repo(repo_id):
    for size, repo in MODEL_REPOS.items():
        if repo == repo_id:
            return size
    return repo_id.rsplit('/', 1)[-1]
