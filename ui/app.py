"""WeMM-Video local interface: run GGUF models on this Mac without the terminal.

Start it from the project root:

    .venv-gguf/bin/python ui/app.py
"""
import argparse
from dataclasses import fields
from pathlib import Path
import tempfile

import gradio as gr

import history
from paths import MODEL_REPOS, ROOT, RUNS_DIR
from presets import PRESETS
import runner
import setup_checks

DEFAULTS = runner.Settings()
RUN_TAB, HISTORY_TAB, SETUP_TAB = 'run', 'history', 'setup'
CSS = """
.status-line {font-size: 14px}
.metrics table {width: 100%}
footer {display: none !important}
"""


# ---------- shared helpers ----------

def settings_from(size, revision, prompt, images, audio, video, use_soundtrack,
                  fps, max_frames, total_pixels, max_new_tokens, gpu_layers, threads, context):
    return runner.Settings(
        size=size, revision=(revision or 'main').strip(), prompt=prompt or '',
        images=list(images or []), audio=list(audio or []), video=video or None,
        use_soundtrack=bool(use_soundtrack), fps=float(fps or 1), max_frames=int(max_frames or 1),
        total_pixels=int(total_pixels or 262144), max_new_tokens=int(max_new_tokens or 1),
        gpu_layers=int(gpu_layers or 0), threads=int(threads or 1), context=int(context or 8192))


def model_note(size):
    for row_size, repo_id, downloaded, disk in setup_checks.models():
        if row_size == size:
            state = f'downloaded, {disk}' if downloaded else 'not downloaded yet. The first run downloads it'
            return f'`{repo_id}` · GGUF Q4_K_M · {state}'
    return ''


def metrics_markdown(run):
    m = history.metrics(run)
    header = '| ' + ' | '.join(m) + ' |'
    divider = '|' + '---|' * len(m)
    values = '| ' + ' | '.join(str(v) for v in m.values()) + ' |'
    return '\n'.join([header, divider, values])


def limit_warning(run):
    if run.finish_reason == 'length':
        return ('⚠️ The answer hit the token limit and is cut off. '
                'Raise **Max new tokens** under Advanced and run again.')
    return ''


# ---------- Run tab ----------

def preview_command(*values):
    settings = settings_from(*values)
    if settings.size not in MODEL_REPOS:
        return ''
    # Show where uploads will live once the run copies them, not Gradio's temp folder.
    inputs = RUNS_DIR / '<new-run>' / 'inputs'
    tmp = tempfile.gettempdir()

    def shown(path):
        return str(inputs / Path(path).name) if str(Path(path).resolve()).startswith(
            str(Path(tmp).resolve())) else path

    settings.images = [shown(p) for p in settings.images]
    settings.audio = [shown(p) for p in settings.audio]
    settings.video = shown(settings.video) if settings.video else None
    return runner.terminal_command(settings, RUNS_DIR / '<new-run>' / 'result.json')


def start_run(*values):
    settings = settings_from(*values)
    problems = runner.validate(settings)
    empty = ('', [], '', '', '', None)
    if problems:
        yield ('**Can’t start:** ' + ' '.join(problems), *empty)
        return
    log_text = ''
    run_dir = None
    for event in runner.run(settings):
        stage = event['stage']
        log_text = event.get('log', log_text)
        run_dir = event.get('run_dir', run_dir)
        if stage == 'preparing':
            status = '◌ Preparing the run folder…'
        elif stage == 'downloading':
            status = f'◌ Getting **{settings.repo_id}**. The first download can take a while…'
        elif stage == 'running' and runner.is_cancelling():
            status = '◌ Stopping…'
        elif stage == 'running':
            status = (f'✓ Model ready · ◌ Running on {"Metal" if settings.gpu_layers else "CPU"}, '
                      f'{event.get("elapsed", 0):.0f} s')
        else:
            break
        yield (status, '', [], '', '', log_text, run_dir)

    run = history.load_run(run_dir) if run_dir else None
    if stage == 'done' and run:
        status = f'✓ Done in {run.result.get("seconds", 0):.1f} s · saved to `runs/{run.id}`'
        yield (status, run.answer, history.frame_images(run), history.audio_summary(run),
               metrics_markdown(run) + '\n\n' + limit_warning(run), log_text, run_dir)
    elif stage == 'cancelled':
        yield ('Cancelled. The partial run folder is kept in History.', '', [], '', '', log_text, run_dir)
    else:
        yield ('✗ The run failed. Open the log below for details.', '', [], '', '', log_text, run_dir)


def cancel_run():
    # While a run is active, its own event stream reports "Stopping…" and then
    # "Cancelled", so this handler only speaks up when there is nothing to stop.
    return gr.update() if runner.cancel() else 'Nothing is running.'


def open_run_folder(run_dir):
    run = history.load_run(run_dir) if run_dir else None
    if run:
        history.show_in_finder(run)


# ---------- History tab ----------

def history_rows(size_filter, search):
    rows, ids = [], []
    needle = (search or '').lower().strip()
    for run in history.list_runs():
        if size_filter and size_filter != 'All models' and run.size != size_filter:
            continue
        if needle and needle not in (run.prompt + ' ' + run.input_label + ' ' + run.answer).lower():
            continue
        m = history.metrics(run)
        rows.append([run.when.strftime('%b %d, %H:%M') if run.when else '', run.size, run.device,
                     run.input_label, run.prompt, m['Prefill'], m['Total'], m['Stopped by']])
        ids.append(run.id)
    return rows, ids


def refresh_history(size_filter, search):
    rows, ids = history_rows(size_filter, search)
    choices = [(f'{r[0]} · {r[1]} {r[2]} · {r[3]}', i) for r, i in zip(rows, ids)]
    return rows, ids, gr.Dropdown(choices=choices, value=None)


def select_run(ids, evt: gr.SelectData):
    row = evt.index[0] if isinstance(evt.index, (list, tuple)) else evt.index
    if row is None or row >= len(ids):
        return (None, 'Select a run in the table.', '', [], '', '', '', '', '')
    run = history.load_run(RUNS_DIR / ids[row])
    title = (f'**{run.size} · {run.device} · {run.when:%b %d, %H:%M}**  \n'
             f'Prompt: {run.prompt or "—"}  \nInput: {run.input_label}  \nFolder: `runs/{run.id}`')
    return (run.id, title, run.answer, history.frame_images(run),
            metrics_markdown(run) + '\n\n' + limit_warning(run), history.audio_summary(run),
            history.terminal_command(run), '', '')


def compare_with(other_id):
    if not other_id:
        return '', ''
    run = history.load_run(RUNS_DIR / other_id)
    return run.answer, metrics_markdown(run)


def load_into_run(run_id):
    if not run_id:
        return (*[gr.update()] * len(fields(runner.Settings)), gr.Tabs())
    s = history.settings_for(history.load_run(RUNS_DIR / run_id))
    values = [s.get(f.name, getattr(DEFAULTS, f.name)) for f in fields(runner.Settings)]
    return (*values, gr.Tabs(selected=RUN_TAB))


def finder_for(run_id):
    if run_id:
        history.show_in_finder(history.load_run(RUNS_DIR / run_id))


def ask_trash(run_id):
    if not run_id:
        return gr.Button(visible=False), gr.Button(visible=False), 'Select a run first.'
    return (gr.Button(visible=True), gr.Button(visible=True),
            f'Move `runs/{run_id}` to the Trash? You can put it back from the Trash later.')


def confirm_trash(run_id, size_filter, search):
    note = ''
    if run_id:
        target = history.move_to_trash(history.load_run(RUNS_DIR / run_id))
        note = f'Moved to the Trash: `{target}`'
    rows, ids, dropdown = refresh_history(size_filter, search)
    return (gr.Button(visible=False), gr.Button(visible=False), note, rows, ids, dropdown,
            None, '', '', [], '', '', '')


def cancel_trash():
    return gr.Button(visible=False), gr.Button(visible=False), ''


# ---------- Setup tab ----------

def checks_markdown():
    lines = ['| | Check | Detail |', '|---|---|---|']
    for ok, name, detail in setup_checks.checks():
        lines.append(f'| {"✅" if ok else "❌"} | {name} | `{detail}` |')
    return '\n'.join(lines)


def models_table():
    return [[size, repo, 'Downloaded' if done else 'Not downloaded', disk]
            for size, repo, done, disk in setup_checks.models()]


def refresh_setup():
    logs = setup_checks.build_logs()
    return (checks_markdown(), models_table(),
            gr.Dropdown(choices=logs, value=logs[0] if logs else None),
            setup_checks.read_build_log(logs[0]) if logs else '')


def download(size):
    repo = MODEL_REPOS[size]
    yield f'◌ Downloading `{repo}`. This can take several minutes…', gr.update()
    try:
        setup_checks.download_model(repo)
        yield f'✓ `{repo}` is downloaded.', models_table()
    except Exception as error:
        yield f'✗ Download failed: {error}', models_table()


def ask_delete(size):
    repo = MODEL_REPOS[size]
    row = next((r for r in setup_checks.models() if r[1] == repo), None)
    if not row or not row[2]:
        return gr.Button(visible=False), gr.Button(visible=False), f'`{repo}` isn’t downloaded.'
    return (gr.Button(visible=True), gr.Button(visible=True),
            f'Permanently delete `{repo}` ({row[3]}) from the Hugging Face cache? '
            'This can’t be undone; you would need to download it again.')


def confirm_delete(size):
    freed = setup_checks.delete_model(MODEL_REPOS[size])
    return (gr.Button(visible=False), gr.Button(visible=False),
            f'Deleted `{MODEL_REPOS[size]}`, freed {freed}.', models_table())


def run_rebuild():
    for text, code in setup_checks.rebuild():
        yield text
    yield text


# ---------- layout ----------

def build_app():
    with gr.Blocks(title='WeMM-Video') as app:
        with gr.Tabs() as tabs:
            # ----- Run -----
            with gr.Tab('Run', id=RUN_TAB):
                with gr.Row(equal_height=False):
                    with gr.Column(scale=5):
                        size = gr.Radio(list(MODEL_REPOS), value=DEFAULTS.size, label='Model size')
                        model_info = gr.Markdown(model_note(DEFAULTS.size))
                        video = gr.Video(label='Video', sources=['upload'], height=220)
                        use_soundtrack = gr.Checkbox(value=True, label='Use the soundtrack',
                                                     info="Let the model hear the video's audio")
                        with gr.Row():
                            images = gr.File(label='Images', file_count='multiple',
                                             file_types=['image'], type='filepath', height=150)
                            audio = gr.File(label='Audio', file_count='multiple',
                                            file_types=['audio'], type='filepath', height=150)
                        preset = gr.Dropdown(list(PRESETS), value=None, label='Prompt presets')
                        prompt = gr.Textbox(label='Prompt', lines=3,
                                            value=PRESETS['Describe the scene and summarize the speech'])
                        with gr.Accordion('Advanced', open=False):
                            with gr.Row():
                                fps = gr.Number(DEFAULTS.fps, label='FPS', minimum=0.1, step=0.5)
                                max_frames = gr.Number(DEFAULTS.max_frames, label='Max frames',
                                                       minimum=1, precision=0)
                                total_pixels = gr.Number(DEFAULTS.total_pixels, label='Total pixels',
                                                         minimum=1, precision=0)
                                max_new_tokens = gr.Number(DEFAULTS.max_new_tokens, label='Max new tokens',
                                                           minimum=1, precision=0)
                            with gr.Row():
                                gpu_layers = gr.Number(DEFAULTS.gpu_layers, label='GPU layers (0 = CPU)',
                                                       minimum=0, precision=0)
                                threads = gr.Number(DEFAULTS.threads, label='Threads', minimum=1, precision=0)
                                context = gr.Number(DEFAULTS.context, label='Context', minimum=512, precision=0)
                                revision = gr.Textbox(DEFAULTS.revision, label='Revision')
                        command = gr.Code(label='Same run in the terminal', language='shell',
                                          interactive=False, lines=3, wrap_lines=True)
                        with gr.Row():
                            run_btn = gr.Button('Run', variant='primary', scale=3)
                            cancel_btn = gr.Button('Cancel', scale=1)
                    with gr.Column(scale=6):
                        status = gr.Markdown('Ready.', elem_classes='status-line')
                        answer = gr.Textbox(label='Answer', lines=8, max_lines=24,
                                            interactive=False, buttons=['copy'])
                        metrics = gr.Markdown(elem_classes='metrics')
                        frames = gr.Gallery(label='Frames the model saw', columns=4, height='auto',
                                            object_fit='contain', interactive=False)
                        audio_info = gr.Markdown()
                        with gr.Accordion('Log', open=False):
                            log = gr.Textbox(lines=12, max_lines=12, autoscroll=True,
                                             show_label=False, interactive=False)
                        run_dir = gr.State(None)
                        open_btn = gr.Button('Show run folder in Finder', size='sm')

            # ----- History -----
            with gr.Tab('History', id=HISTORY_TAB):
                with gr.Row():
                    size_filter = gr.Dropdown(['All models', *MODEL_REPOS], value='All models',
                                              label='Model', scale=1)
                    search = gr.Textbox(label='Search prompts and answers', scale=3)
                    refresh_btn = gr.Button('Refresh', scale=0, min_width=100)
                table = gr.Dataframe(headers=['When', 'Model', 'Device', 'Input', 'Prompt',
                                              'Prefill', 'Total', 'Stopped by'],
                                     interactive=False, wrap=True, max_height=320)
                ids = gr.State([])
                selected = gr.State(None)
                with gr.Row(equal_height=False):
                    with gr.Column(scale=3):
                        detail = gr.Markdown('Select a run in the table.')
                        h_answer = gr.Textbox(label='Answer', lines=6, max_lines=20,
                                              interactive=False, buttons=['copy'])
                        h_metrics = gr.Markdown(elem_classes='metrics')
                        h_frames = gr.Gallery(label='Frames', columns=8, height='auto',
                                              object_fit='contain', interactive=False)
                        h_audio = gr.Markdown()
                        h_command = gr.Code(label='Repeat in the terminal', language='shell',
                                            interactive=False, wrap_lines=True)
                    with gr.Column(scale=2):
                        load_btn = gr.Button('Load settings into Run', variant='primary')
                        h_finder = gr.Button('Show in Finder')
                        trash_btn = gr.Button('Move to Trash', variant='stop')
                        trash_note = gr.Markdown()
                        with gr.Row():
                            trash_yes = gr.Button('Yes, move to Trash', variant='stop', visible=False)
                            trash_no = gr.Button('Keep it', visible=False)
                        compare = gr.Dropdown([], label='Compare with another run')
                        c_answer = gr.Textbox(label='Other answer', lines=6, max_lines=20,
                                              interactive=False)
                        c_metrics = gr.Markdown(elem_classes='metrics')

            # ----- Setup -----
            with gr.Tab('Setup', id=SETUP_TAB):
                with gr.Row(equal_height=False):
                    with gr.Column():
                        gr.Markdown('### Runtime checks')
                        checks = gr.Markdown()
                        setup_refresh = gr.Button('Check again', size='sm')
                        gr.Markdown('### Native runtime')
                        rebuild_btn = gr.Button('Rebuild runtime')
                        rebuild_log = gr.Textbox(label='Build output', lines=10, max_lines=10,
                                                 autoscroll=True, interactive=False)
                        log_pick = gr.Dropdown([], label='Earlier build logs')
                        log_view = gr.Textbox(label='Log (last 400 lines)', lines=10, max_lines=10,
                                              interactive=False)
                    with gr.Column():
                        gr.Markdown('### Downloaded models')
                        model_table = gr.Dataframe(headers=['Size', 'Repository', 'Status', 'On disk'],
                                                   interactive=False)
                        with gr.Row():
                            model_pick = gr.Dropdown(list(MODEL_REPOS), value='4B', label='Model', scale=2)
                            download_btn = gr.Button('Download', scale=1)
                            delete_btn = gr.Button('Delete…', variant='stop', scale=1)
                        model_note_md = gr.Markdown()
                        with gr.Row():
                            delete_yes = gr.Button('Yes, delete it', variant='stop', visible=False)
                            delete_no = gr.Button('Keep it', visible=False)

        # ----- events -----
        run_inputs = [size, revision, prompt, images, audio, video, use_soundtrack, fps,
                      max_frames, total_pixels, max_new_tokens, gpu_layers, threads, context]
        for component in run_inputs:
            component.change(preview_command, run_inputs, command, show_progress='hidden')
        size.change(model_note, size, model_info, show_progress='hidden')
        preset.change(lambda name: PRESETS.get(name, gr.update()) if name else gr.update(),
                      preset, prompt)

        history_inputs = [size_filter, search]
        history_outputs = [table, ids, compare]
        run_event = run_btn.click(
            start_run, run_inputs, [status, answer, frames, audio_info, metrics, log, run_dir],
            concurrency_limit=1, concurrency_id='native')
        run_event.then(refresh_history, history_inputs, history_outputs)
        run_event.then(model_note, size, model_info)
        cancel_btn.click(cancel_run, None, status, queue=False)
        open_btn.click(open_run_folder, run_dir, None)

        refresh_btn.click(refresh_history, history_inputs, history_outputs)
        size_filter.change(refresh_history, history_inputs, history_outputs)
        search.submit(refresh_history, history_inputs, history_outputs)
        table.select(select_run, ids, [selected, detail, h_answer, h_frames, h_metrics, h_audio,
                                       h_command, c_answer, c_metrics])
        compare.change(compare_with, compare, [c_answer, c_metrics])
        load_btn.click(load_into_run, selected, [*run_inputs, tabs])
        h_finder.click(finder_for, selected, None)
        trash_btn.click(ask_trash, selected, [trash_yes, trash_no, trash_note])
        trash_no.click(cancel_trash, None, [trash_yes, trash_no, trash_note])
        trash_yes.click(confirm_trash, [selected, size_filter, search],
                        [trash_yes, trash_no, trash_note, table, ids, compare, selected, detail,
                         h_answer, h_frames, h_metrics, h_audio, h_command])

        setup_outputs = [checks, model_table, log_pick, log_view]
        setup_refresh.click(refresh_setup, None, setup_outputs)
        log_pick.change(setup_checks.read_build_log, log_pick, log_view)
        rebuild_btn.click(run_rebuild, None, rebuild_log,
                          concurrency_limit=1, concurrency_id='native').then(
            refresh_setup, None, setup_outputs)
        download_btn.click(download, model_pick, [model_note_md, model_table], concurrency_limit=1)
        delete_btn.click(ask_delete, model_pick, [delete_yes, delete_no, model_note_md])
        delete_no.click(lambda: (gr.Button(visible=False), gr.Button(visible=False), ''),
                        None, [delete_yes, delete_no, model_note_md])
        delete_yes.click(confirm_delete, model_pick, [delete_yes, delete_no, model_note_md, model_table])

        app.load(refresh_history, history_inputs, history_outputs)
        app.load(refresh_setup, None, setup_outputs)
        app.load(preview_command, run_inputs, command)
    return app


def main():
    parser = argparse.ArgumentParser(description='WeMM-Video local interface')
    parser.add_argument('--port', type=int, default=7860)
    parser.add_argument('--no-browser', action='store_true', help="Don't open a browser tab")
    args = parser.parse_args()
    RUNS_DIR.mkdir(exist_ok=True)
    build_app().queue().launch(
        server_name='127.0.0.1', server_port=args.port, inbrowser=not args.no_browser,
        allowed_paths=[str(RUNS_DIR), str(ROOT / 'examples'), tempfile.gettempdir()],
        theme=gr.themes.Soft(), css=CSS, footer_links=[])


if __name__ == '__main__':
    main()
