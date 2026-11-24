"""HTML fragments for the interface: header, status, empty state, results, timeline."""
from html import escape

import history

# One icon family: 24px grid, 1.75 stroke, round caps, drawn with currentColor.
_PATHS = {
    'check': '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    'x': '<path d="M6 6l12 12M18 6L6 18"/>',
    'alert': '<path d="M12 4l9 16H3z"/><path d="M12 10v4.5M12 17.5v.01"/>',
    'spinner': '<path d="M12 3a9 9 0 1 1-9 9" />',
    'film': '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M7 5v14M17 5v14M3 9.5h4M3 14.5h4M17 9.5h4M17 14.5h4"/>',
    'wave': '<path d="M3 12h2M7 8v8M11 5v14M15 9v6M19 7v10M21 12h0"/>',
    'clock': '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    'text': '<path d="M5 6h14M5 10h14M5 14h10M5 18h7"/>',
    'mark': '<path d="M4 7l3.2 10L12 8l4.8 9L20 7"/>',
}


def icon(name, cls='wm-ico'):
    return (f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" '
            f'aria-hidden="true">{_PATHS[name]}</svg>')


def file_url(path):
    return '/gradio_api/file=' + escape(str(path), quote=True)


def header(checks):
    """App header band with a runtime summary chip."""
    by_name = {name: (ok, detail) for ok, name, detail in checks}
    runner_ok = by_name.get('wemm-native', (False, ''))[0]
    metal_ok = by_name.get('Metal GPU offload', (False, ''))[0]
    if not runner_ok:
        chip = '<span class="wm-dot bad"></span>Runtime not built'
    else:
        chip = f'<span class="wm-dot"></span>wemm-native · {"Metal" if metal_ok else "CPU"}'
    return (f'<div class="wm-header"><div class="wm-mark">{icon("mark")}</div>'
            f'<div><div class="wm-title">WeMM-Video</div>'
            f'<div class="wm-sub">Run omni-modal GGUF models on this Mac</div></div>'
            f'<div class="wm-chip">{chip}</div></div>')


_STEPS = [('model', 'Model'), ('inference', 'Inference'), ('saved', 'Saved')]


def status(text, kind='idle', step=None, done_steps=()):
    """kind: idle | working | done | error. step: the active step key."""
    lead = {'working': icon('spinner', 'wm-ico wm-spin'), 'done': icon('check'),
            'error': icon('alert'), 'idle': icon('clock')}[kind]
    steps = ''
    if kind in ('working', 'done'):
        chips = []
        for key, label in _STEPS:
            if key in done_steps:
                chips.append(f'<span class="wm-step done">{icon("check")}{label}</span>')
            elif key == step:
                chips.append(f'<span class="wm-step active">{label}</span>')
            else:
                chips.append(f'<span class="wm-step">{label}</span>')
        steps = f'<span class="wm-steps">{"".join(chips)}</span>'
    role = ' role="alert"' if kind == 'error' else ' aria-live="polite"'
    return f'<div class="wm-status {kind}"{role}>{lead}<span>{text}</span>{steps}</div>'


def empty_state():
    return ('<div class="wm-empty"><h3>Your answer appears here</h3>'
            '<p>Add a video, image, or audio file, or just write a prompt, then press Run. '
            'Each run is saved to <code>runs/</code> and listed in History.</p><ul>'
            f'<li>{icon("text")}The model’s answer, ready to copy</li>'
            f'<li>{icon("film")}The frames it sampled, placed on the video’s timeline</li>'
            f'<li>{icon("wave")}The audio windows it listened to</li>'
            f'<li>{icon("clock")}How long prefill and generation took</li></ul></div>')


def message(text, kind='ok'):
    lead = {'ok': icon('check'), 'error': icon('alert'), 'warn': icon('alert'),
            'working': icon('spinner', 'wm-ico wm-spin')}[kind]
    return f'<div class="wm-msg {kind}">{lead}<span>{text}</span></div>'


def stats(run):
    r = run.result
    total = r.get('seconds')
    prefill = r.get('prefill_seconds')
    generate = total - prefill if total is not None and prefill is not None else None
    tokens_out = len(r.get('token_ids') or [])
    reason = run.stopped_by or '—'
    reason_cls = 'warn' if run.finish_reason == 'length' or run.status in ('failed', 'cancelled') else 'ok'

    def cell(label, value, cls=''):
        return f'<div><dt>{label}</dt><dd class="{cls}">{value}</dd></div>'

    def secs(value):
        return f'{value:.1f} s' if value is not None else '—'

    return ('<dl class="wm-stats">'
            + cell('Input tokens', r.get('input_tokens', '—'))
            + cell('Output tokens', tokens_out or '—')
            + cell('Prefill', secs(prefill))
            + cell('Generation', secs(generate))
            + cell('Total', secs(total))
            + cell('Stopped by', escape(reason), reason_cls)
            + '</dl>')


def limit_note(run):
    if run.finish_reason != 'length':
        return ''
    limit = (run.meta.get('settings') or {}).get('max_new_tokens')
    limit_text = f' of {limit}' if limit else ''
    return (f'<div class="wm-note warn">{icon("alert")}<span>The answer used the full token '
            f'budget{limit_text} and is cut off. Raise <b>Max new tokens</b> in Advanced '
            'settings and run it again.</span></div>')


def _fmt_time(seconds):
    return f'{seconds:.1f} s' if seconds < 60 else f'{int(seconds // 60)}:{seconds % 60:04.1f}'


def timeline(run):
    """The frames the model saw on the video's real time axis, with audio windows below."""
    frames = history.frame_images(run)
    video = (run.result.get('video_info') or [{}])[0]
    audios = run.result.get('audio_info') or []
    if not frames and not audios:
        return ''
    fps = video.get('fps') or 0
    total_frames = video.get('total_num_frames') or 0
    duration = total_frames / fps if fps and total_frames else 0
    if not duration and audios:
        duration = max(a.get('duration', 0) for a in audios)
    times = [i / fps for i in (video.get('source_frame_indices') or [])] if fps else []

    parts = ['<div class="wm-timeline">']
    head_left = '<b>What the model saw and heard</b>' if audios and frames else (
        '<b>What the model saw</b>' if frames else '<b>What the model heard</b>')
    meta = []
    if frames:
        meta.append(f'{len(frames)} of {total_frames} frames' if total_frames else f'{len(frames)} images')
    if duration:
        meta.append(_fmt_time(duration))
    parts.append(f'<div class="wm-tl-head">{head_left}<span class="wm-num">{" · ".join(meta)}</span></div>')

    if frames:
        cols = min(len(frames), 8)
        parts.append(f'<div class="wm-frames" style="grid-template-columns: repeat({cols}, minmax(0, 1fr))">')
        for i, (path, caption) in enumerate(frames):
            label = f'Frame {i + 1}, {caption}'
            parts.append(f'<a href="{file_url(path)}" target="_blank" rel="noopener" '
                         f'title="{escape(label)}"><img src="{file_url(path)}" alt="{escape(label)}" '
                         f'loading="lazy"></a>')
        parts.append('</div>')

    if duration and times:
        dense = len(times) > 10
        parts.append('<div class="wm-ruler"><div class="track"></div>')
        for i, t in enumerate(times):
            pct = max(0.0, min(100.0, t / duration * 100))
            parts.append(f'<span class="tick" style="left:{pct:.2f}%"></span>')
            if not dense or i % 2 == 0 or i == len(times) - 1:
                edge = ' first' if pct < 4 else (' last' if pct > 96 else '')
                parts.append(f'<span class="lbl{edge}" style="left:{pct:.2f}%">{_fmt_time(t)}</span>')
        parts.append('</div>')

    for audio in audios:
        a_dur = audio.get('duration') or 0
        segments = audio.get('segments') or 0
        span = duration or a_dur
        if not (a_dur and segments and span):
            continue
        window = 30.0  # Whisper-style 30-second windows (release_pcm16_whisper30)
        parts.append('<div class="wm-audio">')
        for s in range(segments):
            start, end = s * window, min((s + 1) * window, a_dur)
            if start >= end:
                continue
            left, width = start / span * 100, (end - start) / span * 100
            parts.append(f'<span class="seg" style="left:{left:.2f}%; width:calc({width:.2f}% - 4px)" '
                         f'title="Audio window {s + 1}: {start:.0f}–{end:.1f} s">'
                         f'Audio {s + 1} · {start:.0f}–{end:.0f} s</span>')
        parts.append('</div>')

    legend = []
    if times:
        legend.append('<span><i style="background:var(--primary-600)"></i>Sampled frame</span>')
    if audios:
        legend.append('<span><i class="audio"></i>Audio window</span>')
        legend.append(f'<span>{escape(history.audio_summary(run))}</span>')
    if legend:
        parts.append(f'<div class="wm-tl-legend">{"".join(legend)}</div>')
    parts.append('</div>')
    return ''.join(parts)


def summary(run):
    return stats(run) + limit_note(run) + timeline(run)


def detail_heading(run):
    when = run.when.strftime('%b %d, %H:%M') if run.when else ''
    return (f'<div class="wm-detail"><h3>{escape(run.size)} on {escape(run.device)} · {when}</h3>'
            f'<p>{escape(run.prompt or "No prompt recorded")}</p>'
            f'<p>{escape(run.input_label)} · <code>runs/{escape(run.id)}</code></p></div>')


def detail_empty():
    return ('<div class="wm-empty"><h3>Pick a run</h3><p>Select a row above to see its answer, '
            'the frames it used, and its timing. You can load its settings back into Run, '
            'or compare it with another run.</p></div>')


def checks_list(checks):
    rows = []
    for ok, name, detail in checks:
        rows.append(f'<li class="{"ok" if ok else "bad"}">{icon("check" if ok else "x")}'
                    f'<span>{escape(name)}</span><code>{escape(str(detail))}</code></li>')
    return f'<ul class="wm-checks">{"".join(rows)}</ul>'


def model_note(repo_id, downloaded, disk):
    state = f'Downloaded, {disk}' if downloaded else 'Not downloaded yet. The first run downloads it.'
    return f'<p class="wm-model-line"><code>{escape(repo_id)}</code> · Q4_K_M · {state}</p>'
