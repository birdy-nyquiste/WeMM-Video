"""Read past runs from runs/<id>/, including runs made in the terminal."""
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
import re
import shutil
import subprocess

from paths import MODEL_REPOS, ROOT, RUNS_DIR, size_for_repo

FOLDER_NAME = re.compile(r'^(\d{4}-\d{2}-\d{2})_(\d{4})_([0-9a-z-]+?)-(metal|cpu)_(.+?)(?:-\d+)?$')
MEDIA_TOKEN = re.compile(r'<\|[^|>]+\|>|<__media__>|<[\d.]+ seconds>')


@dataclass
class Run:
    id: str
    path: Path
    when: datetime | None
    size: str
    device: str
    input_label: str
    prompt: str
    status: str
    result: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)

    @property
    def answer(self):
        return self.result.get('text', '')

    @property
    def finish_reason(self):
        return self.result.get('finish_reason', '')

    @property
    def evidence_dir(self):
        return self.path / 'result.json.evidence'

    @property
    def stopped_by(self):
        if self.status != 'done':
            return self.status
        return {'eos': 'finished', 'length': 'token limit'}.get(self.finish_reason, self.finish_reason)


def _read_json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def _prompt_from_evidence(evidence_dir):
    """Older runs have no run.json; recover the user's words from the chat template."""
    prompt = _read_json(evidence_dir / 'request.json').get('prompt', '')
    match = re.search(r'<\|im_start\|>user\n(.*?)<\|im_end\|>', prompt, re.S)
    return MEDIA_TOKEN.sub('', match.group(1)).strip() if match else ''


def _input_label(result, meta):
    settings = meta.get('settings') or {}
    video = (result.get('video_info') or [{}])[0].get('path') or settings.get('video')
    if video:
        with_audio = result.get('has_audio') if result else settings.get('use_soundtrack')
        return f'{Path(video).name}' + (' + audio' if with_audio else '')
    if settings.get('images') or any(c.get('kind') == 'image' for c in result.get('chunks', [])):
        names = [Path(p).name for p in settings.get('images', [])]
        return ', '.join(names) or 'image'
    if result.get('audio_info') or settings.get('audio'):
        return ', '.join(Path(a.get('source', '')).name for a in result.get('audio_info', [])) or 'audio'
    return 'text'


def load_run(path):
    path = Path(path)
    result = _read_json(path / 'result.json')
    meta = _read_json(path / 'run.json')
    if not result and not meta:
        return None
    match = FOLDER_NAME.match(path.name)
    when = None
    if meta.get('created'):
        when = datetime.fromisoformat(meta['created'])
    elif match:
        when = datetime.strptime(match.group(1) + match.group(2), '%Y-%m-%d%H%M')
    gpu_layers = (result.get('native_config') or {}).get('gpu_layers')
    if gpu_layers is None:
        gpu_layers = (meta.get('settings') or {}).get('gpu_layers', 0)
    if meta.get('repo_id'):
        size = size_for_repo(meta['repo_id'])
    elif match:
        size = match.group(3).upper()
    else:
        size = '?'
    prompt = (meta.get('settings') or {}).get('prompt') or _prompt_from_evidence(path / 'result.json.evidence')
    status = meta.get('status') or ('done' if result.get('status') == 'completed' else 'failed')
    return Run(id=path.name, path=path, when=when, size=size,
               device='Metal' if gpu_layers else 'CPU', input_label=_input_label(result, meta),
               prompt=prompt, status=status, result=result, meta=meta)


def list_runs():
    if not RUNS_DIR.is_dir():
        return []
    runs = [load_run(p) for p in RUNS_DIR.iterdir() if p.is_dir()]
    runs = [r for r in runs if r]
    return sorted(runs, key=lambda r: r.when or datetime.min, reverse=True)


def frame_images(run):
    """PNG copies of the frames the model saw, with their time in the source video."""
    frames = sorted(run.evidence_dir.glob('frame-*.ppm'),
                    key=lambda p: int(re.sub(r'\D', '', p.stem) or 0))
    if not frames:
        return []
    from PIL import Image
    preview_dir = run.path / 'previews'
    preview_dir.mkdir(exist_ok=True)
    info = (run.result.get('video_info') or [{}])[0]
    indices = info.get('source_frame_indices') or []
    fps = info.get('fps') or 0
    images = []
    for i, frame in enumerate(frames):
        png = preview_dir / (frame.stem + '.png')
        if not png.exists():
            Image.open(frame).save(png)
        caption = f'{indices[i] / fps:.1f} s' if i < len(indices) and fps else frame.stem
        images.append((str(png), caption))
    return images


def audio_summary(run):
    parts = []
    for audio in run.result.get('audio_info') or []:
        parts.append(f"{audio.get('duration', 0):.1f} s · {audio.get('segments', '?')} segments · "
                     f"{audio.get('audio_tokens', '?')} audio tokens")
    return '; '.join(parts)


def metrics(run):
    r = run.result
    return {
        'Input tokens': r.get('input_tokens', '—'),
        'Prefill': f"{r['prefill_seconds']:.1f} s" if 'prefill_seconds' in r else '—',
        'Total': f"{r['seconds']:.1f} s" if 'seconds' in r else '—',
        'Stopped by': run.stopped_by or '—',
    }


def terminal_command(run):
    """The command to repeat this run in a terminal (reconstructed for older runs)."""
    if run.meta.get('terminal_command'):
        return run.meta['terminal_command']
    import shlex
    request = _read_json(run.evidence_dir / 'request.json')
    config = run.result.get('native_config') or {}
    repo = MODEL_REPOS.get(run.size, f'tencent/WeMM-Video-{run.size}-GGUF')
    parts = ['python', 'native/run_hf.py', '--repo-id', repo, '--prompt', run.prompt,
             '--output', f'runs/<new-name>/result.json']
    video = request.get('raw_video')
    if video:
        flag = '--video-audio' if request.get('use_audio_in_video') else '--video'
        parts += [flag, _relative(video)]
    parts += ['--gpu-layers', str(config.get('gpu_layers', 0)), '--context', str(config.get('context', 8192)),
              '--threads', str(config.get('threads', 4)), '--fps', f"{request.get('fps', 1):g}",
              '--max-frames', str(request.get('max_frames', 4)),
              '--total-pixels', str(request.get('total_pixels', 262144)),
              '--max-new-tokens', str(request.get('max_new_tokens', 128))]
    return shlex.join(parts)


def settings_for(run):
    """Settings to load back into the Run tab, as a plain dict."""
    if run.meta.get('settings'):
        return dict(run.meta['settings'])
    request = _read_json(run.evidence_dir / 'request.json')
    config = run.result.get('native_config') or {}
    video = request.get('raw_video')
    return {
        'size': run.size if run.size in MODEL_REPOS else '2B', 'revision': 'main', 'prompt': run.prompt,
        'images': [], 'audio': [], 'video': video if video and Path(video).is_file() else None,
        'use_soundtrack': bool(request.get('use_audio_in_video', True)),
        'fps': request.get('fps', 1.0), 'max_frames': request.get('max_frames', 4),
        'total_pixels': request.get('total_pixels', 262144),
        'max_new_tokens': request.get('max_new_tokens', 128),
        'gpu_layers': config.get('gpu_layers', 0), 'threads': config.get('threads', 4),
        'context': config.get('context', 8192),
    }


def _relative(path):
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def show_in_finder(run):
    subprocess.run(['open', '-R', str(run.path / 'result.json')
                    if (run.path / 'result.json').exists() else str(run.path)], check=False)


def move_to_trash(run):
    """Move a run folder to the macOS Trash (recoverable), never delete it outright."""
    trash = Path.home() / '.Trash'
    target = trash / run.id
    counter = 2
    while target.exists():
        target = trash / f'{run.id}-{counter}'
        counter += 1
    shutil.move(str(run.path), str(target))
    return target
