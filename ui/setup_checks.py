"""Report what the native runtime needs, and manage downloaded models and builds."""
from datetime import datetime
from importlib import metadata
from pathlib import Path
import shutil
import subprocess
import sys

from paths import BUILD_LOGS_DIR, MODEL_REPOS, NATIVE_DIR, ROOT
from runner import find_runner


def _cmake_flag(name):
    cache = NATIVE_DIR / 'build-cpu' / 'CMakeCache.txt'
    if not cache.is_file():
        return None
    for line in cache.read_text(errors='ignore').splitlines():
        if line.startswith(name + ':'):
            return line.split('=', 1)[-1]
    return None


def checks():
    """Return (ok, name, detail) rows for the Setup tab."""
    rows = []
    runner = find_runner()
    rows.append((runner is not None, 'wemm-native',
                 str(runner.relative_to(ROOT)) if runner and runner.is_relative_to(ROOT)
                 else str(runner or 'Not built. Use Rebuild runtime below.')))
    metal = _cmake_flag('GGML_METAL')
    if sys.platform == 'darwin':
        rows.append((metal == 'ON', 'Metal GPU offload',
                     'Enabled in the build' if metal == 'ON' else 'Not enabled in native/build-cpu'))
    for tool in ('ffmpeg', 'ffprobe'):
        path = shutil.which(tool)
        rows.append((path is not None, tool, path or 'Not found. Install it with: brew install ffmpeg'))
    try:
        hub = metadata.version('huggingface_hub')
        rows.append((True, 'huggingface_hub', f'{hub}, {Path(sys.prefix).name}'))
    except metadata.PackageNotFoundError:
        rows.append((False, 'huggingface_hub', 'Not installed in this environment'))
    for tool in ('cmake', 'git'):
        path = shutil.which(tool)
        rows.append((path is not None, f'{tool} (for rebuilding)', path or 'Not found'))
    return rows


def _human(size):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if size < 1024 or unit == 'GB':
            return f'{size:.1f} {unit}' if unit == 'GB' else f'{size:.0f} {unit}'
        size /= 1024


def models():
    """Return one row per GGUF size: (size, repo_id, downloaded, disk size)."""
    from huggingface_hub import scan_cache_dir
    try:
        cached = {repo.repo_id: repo for repo in scan_cache_dir().repos}
    except Exception:
        cached = {}
    rows = []
    for size, repo_id in MODEL_REPOS.items():
        repo = cached.get(repo_id)
        rows.append((size, repo_id, repo is not None,
                     _human(repo.size_on_disk) if repo else ''))
    return rows


def download_model(repo_id, revision='main'):
    from huggingface_hub import snapshot_download
    from paths import BUNDLE_FILES
    return snapshot_download(repo_id=repo_id, revision=revision, allow_patterns=BUNDLE_FILES)


def delete_model(repo_id):
    """Permanently remove every cached revision of one model. Returns the freed size."""
    from huggingface_hub import scan_cache_dir
    cache = scan_cache_dir()
    hashes = [rev.commit_hash for repo in cache.repos if repo.repo_id == repo_id
              for rev in repo.revisions]
    if not hashes:
        return ''
    strategy = cache.delete_revisions(*hashes)
    strategy.execute()
    return strategy.expected_freed_size_str


def build_logs():
    if not BUILD_LOGS_DIR.is_dir():
        return []
    return sorted((p.name for p in BUILD_LOGS_DIR.glob('*.log')), reverse=True)


def read_build_log(name, tail=400):
    path = BUILD_LOGS_DIR / name
    if not name or not path.is_file():
        return ''
    lines = path.read_text(errors='replace').splitlines()
    return '\n'.join(lines[-tail:])


def rebuild():
    """Run native/build.py --backend cpu, yielding the growing log; saves it to logs/build/."""
    BUILD_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y-%m-%d_%H%M')
    log_path = BUILD_LOGS_DIR / f'{stamp}_cpu-build.log'
    command = [sys.executable, str(NATIVE_DIR / 'build.py'), '--backend', 'cpu']
    lines = [f'$ {" ".join(command)}']
    with log_path.open('w') as log:
        process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in process.stdout:
            log.write(line)
            lines.append(line.rstrip('\n'))
            yield '\n'.join(lines[-400:]), None
        code = process.wait()
    outcome = 'ok' if code == 0 else 'failed'
    final = log_path.with_name(f'{stamp}_cpu-build-{outcome}.log')
    log_path.rename(final)
    lines.append(f'Build {"finished" if code == 0 else "failed"} (exit code {code}). Log: {final.relative_to(ROOT)}')
    yield '\n'.join(lines[-400:]), code
