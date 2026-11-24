"""Run one WeMM GGUF request with wemm-native, the same way native/run_hf.py does."""
from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
from pathlib import Path
import queue
import re
import shlex
import shutil
import subprocess
import threading
import time
from types import SimpleNamespace

from paths import BUNDLE_FILES, MODEL_REPOS, NATIVE_DIR, ROOT, RUNS_DIR
from run_hf import make_command  # native/run_hf.py, made importable by paths.py


@dataclass
class Settings:
    size: str = '2B'
    revision: str = 'main'
    prompt: str = ''
    images: list = field(default_factory=list)
    audio: list = field(default_factory=list)
    video: str | None = None
    use_soundtrack: bool = True
    fps: float = 1.0
    max_frames: int = 8
    total_pixels: int = 262144
    max_new_tokens: int = 512
    gpu_layers: int = 99
    threads: int = 4
    context: int = 8192

    @property
    def repo_id(self):
        return MODEL_REPOS[self.size]


def find_runner():
    """Return the wemm-native binary: PATH first, then the repo's install folders."""
    found = shutil.which('wemm-native')
    if found:
        return Path(found)
    for backend in ('cpu', 'cuda'):
        candidate = NATIVE_DIR / f'install-{backend}' / 'bin' / 'wemm-native'
        if candidate.is_file():
            return candidate
    return None


def validate(settings):
    """Return a list of problems that would make run_hf.py refuse the request."""
    problems = []
    if not settings.prompt.strip():
        problems.append('Enter a prompt.')
    if settings.size not in MODEL_REPOS:
        problems.append(f'Unknown model size: {settings.size}.')
    if settings.video and settings.use_soundtrack and settings.audio:
        problems.append('Turn off "Use the soundtrack" to add separate audio files, '
                        'or remove the audio files.')
    for path in settings.images + settings.audio + ([settings.video] if settings.video else []):
        if not Path(path).is_file():
            problems.append(f'Missing media file: {path}')
    if find_runner() is None:
        problems.append('wemm-native is not built. Build it from the Setup tab.')
    return problems


def _slug(text, limit=40):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:limit] or 'input'


def describe_input(settings):
    if settings.video:
        kind = 'video-audio' if settings.use_soundtrack else 'video'
        return f'{_slug(Path(settings.video).stem)}-{kind}'
    if settings.images:
        return f'{_slug(Path(settings.images[0]).stem)}-image'
    if settings.audio:
        return f'{_slug(Path(settings.audio[0]).stem)}-audio'
    return 'text'


def new_run_dir(settings):
    device = 'metal' if settings.gpu_layers > 0 else 'cpu'
    stamp = datetime.now().strftime('%Y-%m-%d_%H%M')
    base = f'{stamp}_{settings.size.lower()}-{device}_{describe_input(settings)}'
    run_dir = RUNS_DIR / base
    counter = 2
    while run_dir.exists():
        run_dir = RUNS_DIR / f'{base}-{counter}'
        counter += 1
    return run_dir


def _relative(path):
    path = Path(path)
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def terminal_command(settings, output):
    """The run_hf.py command a person would type for the same request."""
    parts = ['python', 'native/run_hf.py', '--repo-id', settings.repo_id]
    if settings.revision != 'main':
        parts += ['--revision', settings.revision]
    parts += ['--prompt', settings.prompt, '--output', _relative(output)]
    for path in settings.images:
        parts += ['--image', _relative(path)]
    for path in settings.audio:
        parts += ['--audio', _relative(path)]
    if settings.video:
        flag = '--video-audio' if settings.use_soundtrack else '--video'
        parts += [flag, _relative(settings.video)]
    parts += ['--gpu-layers', str(settings.gpu_layers), '--context', str(settings.context),
              '--threads', str(settings.threads), '--fps', f'{settings.fps:g}',
              '--max-frames', str(settings.max_frames),
              '--total-pixels', str(settings.total_pixels),
              '--max-new-tokens', str(settings.max_new_tokens)]
    return shlex.join(parts)


def _copy_inputs(settings, run_dir):
    """Copy uploaded media into the run folder so the run can be repeated later."""
    inputs = run_dir / 'inputs'
    inputs.mkdir(parents=True, exist_ok=True)

    def keep(path):
        target = inputs / Path(path).name
        counter = 2
        while target.exists():
            target = inputs / f'{Path(path).stem}-{counter}{Path(path).suffix}'
            counter += 1
        shutil.copy2(path, target)
        return str(target)

    copied = Settings(**asdict(settings))
    copied.images = [keep(p) for p in settings.images]
    copied.audio = [keep(p) for p in settings.audio]
    copied.video = keep(settings.video) if settings.video else None
    if not any((copied.images, copied.audio, copied.video)):
        inputs.rmdir()
    return copied


def _write_meta(run_dir, meta):
    (run_dir / 'run.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False))


class _Current:
    lock = threading.Lock()
    process = None
    cancelled = False


def cancel():
    """Stop the running wemm-native process, if there is one."""
    with _Current.lock:
        _Current.cancelled = True
        process = _Current.process
    if process and process.poll() is None:
        process.terminate()

        def force_kill():
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

        threading.Thread(target=force_kill, daemon=True).start()
        return True
    return False


def is_cancelling():
    return _Current.cancelled


def _download(settings):
    from huggingface_hub import snapshot_download
    try:
        path = snapshot_download(repo_id=settings.repo_id, revision=settings.revision,
                                 allow_patterns=BUNDLE_FILES, local_files_only=True)
        if all((Path(path) / name).is_file() for name in BUNDLE_FILES):
            return path, False
    except Exception:
        pass
    path = snapshot_download(repo_id=settings.repo_id, revision=settings.revision,
                             allow_patterns=BUNDLE_FILES)
    return path, True


def run(settings):
    """Run one request. Yields dicts with 'stage', 'log' and, at the end, 'run_dir'.

    Stages: preparing, downloading, running, done, failed, cancelled.
    """
    with _Current.lock:
        _Current.cancelled = False
    RUNS_DIR.mkdir(exist_ok=True)
    run_dir = new_run_dir(settings)
    run_dir.mkdir(parents=True)
    settings = _copy_inputs(settings, run_dir)
    output = run_dir / 'result.json'
    log_path = run_dir / 'run.log'
    meta = {
        'id': run_dir.name,
        'created': datetime.now().isoformat(timespec='seconds'),
        'repo_id': settings.repo_id,
        'settings': asdict(settings),
        'terminal_command': terminal_command(settings, output),
        'status': 'running',
    }
    _write_meta(run_dir, meta)
    log_lines = []

    def log(line):
        log_lines.append(line)
        with log_path.open('a') as handle:
            handle.write(line + '\n')
        return line

    def finish(status, **extra):
        meta.update(status=status, finished=datetime.now().isoformat(timespec='seconds'), **extra)
        _write_meta(run_dir, meta)
        return {'stage': status, 'log': '\n'.join(log_lines), 'run_dir': str(run_dir)}

    yield {'stage': 'preparing', 'log': log(f'Run folder: {_relative(run_dir)}'),
           'run_dir': str(run_dir)}
    try:
        yield {'stage': 'downloading',
               'log': log(f'Checking {settings.repo_id} ({settings.revision}) in the Hub cache…')}
        model_dir, downloaded = _download(settings)
        log(('Downloaded' if downloaded else 'Found cached') + f' model: {model_dir}')
    except Exception as error:  # network, auth, or a missing revision
        log(f'Could not get the model: {error}')
        yield finish('failed', error=str(error))
        return

    args = SimpleNamespace(runner=find_runner(), prompt=settings.prompt, output=output,
                           gpu_layers=settings.gpu_layers, context=settings.context,
                           threads=settings.threads, fps=settings.fps,
                           max_frames=settings.max_frames, total_pixels=settings.total_pixels,
                           max_new_tokens=settings.max_new_tokens,
                           image=[Path(p) for p in settings.images],
                           audio=[Path(p) for p in settings.audio],
                           video=Path(settings.video) if settings.video and not settings.use_soundtrack else None,
                           video_audio=Path(settings.video) if settings.video and settings.use_soundtrack else None)
    command = make_command(args, model_dir)
    meta['native_command'] = command
    _write_meta(run_dir, meta)
    log('$ ' + shlex.join(command))

    started = time.monotonic()
    process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, bufsize=1)
    with _Current.lock:
        _Current.process = process
    lines = queue.Queue()

    def pump():
        for line in process.stdout:
            lines.put(line.rstrip('\n'))
        lines.put(None)

    threading.Thread(target=pump, daemon=True).start()
    try:
        while True:
            try:
                line = lines.get(timeout=1)
            except queue.Empty:
                yield {'stage': 'running', 'elapsed': time.monotonic() - started}
                continue
            if line is None:
                break
            log(line)
            yield {'stage': 'running', 'elapsed': time.monotonic() - started,
                   'log': '\n'.join(log_lines)}
        returncode = process.wait()
    finally:
        if process.poll() is None:  # the page was closed or the event was stopped
            process.kill()
        with _Current.lock:
            _Current.process = None
            cancelled = _Current.cancelled

    wall = round(time.monotonic() - started, 2)
    if cancelled:
        log('Cancelled.')
        yield finish('cancelled', returncode=returncode, wall_seconds=wall)
    elif returncode != 0 or not output.is_file():
        log(f'wemm-native exited with code {returncode}.')
        yield finish('failed', returncode=returncode, wall_seconds=wall)
    else:
        yield finish('done', returncode=returncode, wall_seconds=wall)
