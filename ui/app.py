"""WeMM-Video local interface: run GGUF models on this Mac without the terminal.

Start it from the project root:

    .venv-gguf/bin/python ui/app.py
"""
import argparse
from dataclasses import fields
from html import escape
from pathlib import Path
import tempfile

import gradio as gr

import history
from paths import MODEL_REPOS, ROOT, RUNS_DIR
from presets import PRESETS
import runner
import setup_checks
from theme import CSS, build_theme
import views

DEFAULTS = runner.Settings()
RUN_TAB, HISTORY_TAB, SETUP_TAB = 'run', 'history', 'setup'
TABLE_HEADERS = ['When', 'Model', 'Input', 'Prompt', 'Total', 'Result']


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
            return views.model_note(repo_id, downloaded, disk)
    return ''


# ---------- Run tab ----------

def preview_command(*values):
    settings = settings_from(*values)
    if settings.size not in MODEL_REPOS:
        return ''
    # Show where uploads will live once the run copies them, not Gradio's temp folder.
    inputs = RUNS_DIR / '<new-run>' / 'inputs'
    tmp = str(Path(tempfile.gettempdir()).resolve())

    def shown(path):
        return str(inputs / Path(path).name) if str(Path(path).resolve()).startswith(tmp) else path

    settings.images = [shown(p) for p in settings.images]
    settings.audio = [shown(p) for p in settings.audio]
    settings.video = shown(settings.video) if settings.video else None
    return runner.terminal_command(settings, RUNS_DIR / '<new-run>' / 'result.json')


def run_view(status, *, empty=None, results=None, answer=None, summary=None, log=None,
             log_open=None, run_dir=None, busy=None):
    """Updates for: status, empty state, results, answer, summary, log, log accordion,
    run folder, Run button, Cancel button. None leaves a component as it is."""
    keep = gr.update()
    if busy is None:
        run_btn = cancel_btn = keep
    elif busy:
        run_btn = gr.Button('Running…', interactive=False)
        cancel_btn = gr.Button(interactive=True)
    else:
        run_btn = gr.Button('Run', interactive=True)
        cancel_btn = gr.Button(interactive=False)
    return (
        status,
        keep if empty is None else gr.HTML(visible=empty),
        keep if results is None else gr.Column(visible=results),
        keep if answer is None else answer,
        keep if summary is None else summary,
        keep if log is None else log,
        keep if log_open is None else gr.Accordion(visible=True, open=log_open),
        keep if run_dir is None else run_dir,
        run_btn,
        cancel_btn,
    )


def start_run(*values):
    settings = settings_from(*values)
    problems = runner.validate(settings)
    if problems:
        yield run_view(views.status('Can’t start: ' + escape(' '.join(problems)), 'error'))
        return
    device = 'Metal' if settings.gpu_layers else 'CPU'
    log_text, run_dir, stage = '', None, 'preparing'
    for event in runner.run(settings):
        stage = event['stage']
        log_text = event.get('log', log_text)
        run_dir = event.get('run_dir', run_dir)
        if stage in ('preparing', 'downloading'):
            text = (f'Getting <code>{escape(settings.repo_id)}</code>. '
                    'The first download can take a while.') if stage == 'downloading' else 'Preparing the run…'
            yield run_view(views.status(text, 'working', step='model'), empty=False, results=False,
                           log=log_text, log_open=False, run_dir=run_dir, busy=True)
        elif stage == 'running':
            if runner.is_cancelling():
                text = 'Stopping…'
            else:
                text = f'Running on {device} · <span class="wm-num">{event.get("elapsed", 0):.0f} s</span>'
            yield run_view(views.status(text, 'working', step='inference', done_steps=('model',)),
                           log=log_text)
        else:
            break

    run = history.load_run(run_dir) if run_dir else None
    if stage == 'done' and run:
        text = (f'Done in <span class="wm-num">{run.result.get("seconds", 0):.1f} s</span> · '
                f'<span title="runs/{escape(run.id)}">saved to History</span>')
        yield run_view(views.status(text, 'done', done_steps=('model', 'inference', 'saved')),
                       empty=False, results=True, answer=run.answer, summary=views.summary(run),
                       log=log_text, log_open=False, busy=False)
    elif stage == 'cancelled':
        yield run_view(views.status('Cancelled. The partial run is kept in History.', 'idle'),
                       empty=True, results=False, log=log_text, busy=False)
    else:
        yield run_view(views.status('The run failed. The log below shows what wemm-native reported.',
                                    'error'), empty=True, results=False, log=log_text,
                       log_open=True, busy=False)


def cancel_run():
    # While a run is active its own event stream reports "Stopping…" and then
    # "Cancelled", so this handler only speaks up when there is nothing to stop.
    if runner.cancel():
        return gr.update()
    return views.status('Nothing is running.', 'idle')


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
        rows.append([run.when.strftime('%b %d, %H:%M') if run.when else '',
                     f'{run.size} · {run.device}', run.input_label, run.prompt,
                     m['Total'], run.stopped_by or '—'])
        ids.append(run.id)
    return rows, ids


def refresh_history(size_filter, search):
    rows, ids = history_rows(size_filter, search)
    choices = [(f'{r[0]} · {r[1]} · {r[2]}', i) for r, i in zip(rows, ids)]
    return rows, ids, gr.Dropdown(choices=choices, value=None)


def select_run(ids, evt: gr.SelectData):
    row = evt.index[0] if isinstance(evt.index, (list, tuple)) else evt.index
    if row is None or row >= len(ids):
        return (None, views.detail_empty(), gr.Column(visible=False), gr.Column(visible=False),
                '', '', '', '', '')
    run = history.load_run(RUNS_DIR / ids[row])
    return (run.id, views.detail_heading(run), gr.Column(visible=True), gr.Column(visible=True), run.answer,
            views.summary(run), history.terminal_command(run), '', '')


def compare_with(other_id):
    if not other_id:
        return '', ''
    run = history.load_run(RUNS_DIR / other_id)
    return run.answer, views.stats(run) + views.limit_note(run)


def load_into_run(run_id):
    if not run_id:
        return (*[gr.update()] * len(fields(runner.Settings)), gr.update(), gr.Tabs())
    s = history.settings_for(history.load_run(RUNS_DIR / run_id))
    values = [s.get(f.name, getattr(DEFAULTS, f.name)) for f in fields(runner.Settings)]
    extra_media = bool(s.get('images') or s.get('audio'))
    return (*values, gr.Accordion(open=extra_media), gr.Tabs(selected=RUN_TAB))


def finder_for(run_id):
    if run_id:
        history.show_in_finder(history.load_run(RUNS_DIR / run_id))


def ask_trash(run_id):
    if not run_id:
        return gr.Button(visible=False), gr.Button(visible=False), views.message('Select a run first.', 'warn')
    return (gr.Button(visible=True), gr.Button(visible=True),
            views.message(f'Move <code>runs/{escape(run_id)}</code> to the Trash? '
                          'You can put it back from the Trash later.', 'warn'))


def confirm_trash(run_id, size_filter, search):
    note = ''
    if run_id:
        target = history.move_to_trash(history.load_run(RUNS_DIR / run_id))
        note = views.message(f'Moved to the Trash: <code>{escape(str(target))}</code>')
    rows, ids, dropdown = refresh_history(size_filter, search)
    return (gr.Button(visible=False), gr.Button(visible=False), note, rows, ids, dropdown,
            None, views.detail_empty(), gr.Column(visible=False), gr.Column(visible=False))


def cancel_trash():
    return gr.Button(visible=False), gr.Button(visible=False), ''


# ---------- Setup tab ----------

def models_table():
    return [[size, repo, 'Downloaded' if done else 'Not downloaded', disk or '—']
            for size, repo, done, disk in setup_checks.models()]


def refresh_setup():
    checks = setup_checks.checks()
    logs = setup_checks.build_logs()
    return (views.checks_list(checks), views.header(checks), models_table(),
            gr.Dropdown(choices=logs, value=logs[0] if logs else None),
            setup_checks.read_build_log(logs[0]) if logs else '')


def download(size):
    repo = MODEL_REPOS[size]
    yield views.message(f'Downloading <code>{repo}</code>. This can take several minutes.', 'working'), gr.update()
    try:
        setup_checks.download_model(repo)
        yield views.message(f'<code>{repo}</code> is downloaded.'), models_table()
    except Exception as error:
        yield views.message(f'Download failed: {escape(str(error))}', 'error'), models_table()


def ask_delete(size):
    repo = MODEL_REPOS[size]
    row = next((r for r in setup_checks.models() if r[1] == repo), None)
    if not row or not row[2]:
        return gr.Button(visible=False), gr.Button(visible=False), views.message(
            f'<code>{repo}</code> isn’t downloaded.', 'warn')
    return (gr.Button(visible=True), gr.Button(visible=True), views.message(
        f'Permanently delete <code>{repo}</code> ({row[3]}) from the Hugging Face cache? '
        'This can’t be undone; you’d need to download it again.', 'warn'))


def confirm_delete(size):
    freed = setup_checks.delete_model(MODEL_REPOS[size])
    return (gr.Button(visible=False), gr.Button(visible=False),
            views.message(f'Deleted <code>{MODEL_REPOS[size]}</code>, freed {freed}.'), models_table())


def run_rebuild():
    text = ''
    for text, _code in setup_checks.rebuild():
        yield text
    yield text


# ---------- layout ----------

def build_app():
    with gr.Blocks(title='WeMM-Video') as app:
        header = gr.HTML(views.header(setup_checks.checks()))
        with gr.Tabs() as tabs:
            # ----- Run -----
            with gr.Tab('Run', id=RUN_TAB):
                with gr.Row(equal_height=False):
                    with gr.Column(scale=5, min_width=360):
                        with gr.Group():
                            size = gr.Radio(list(MODEL_REPOS), value=DEFAULTS.size, label='Model')
                            model_info = gr.HTML(model_note(DEFAULTS.size), elem_classes='wm-model-note')
                        with gr.Group():
                            video = gr.Video(label='Video', sources=['upload'], height=170,
                                             elem_classes='wm-video')
                            use_soundtrack = gr.Checkbox(value=True, label='Use the soundtrack',
                                                         info='Let the model hear the video’s audio')
                        with gr.Accordion('Images and audio files', open=False) as media_acc:
                            with gr.Row():
                                images = gr.File(label='Images', file_count='multiple',
                                                 file_types=['image'], type='filepath', height=130)
                                audio = gr.File(label='Audio', file_count='multiple',
                                                file_types=['audio'], type='filepath', height=130)
                        with gr.Group():
                            preset = gr.Dropdown(list(PRESETS), value=None, label='Start from a preset')
                            prompt = gr.Textbox(label='Prompt', lines=3,
                                                value=PRESETS['Describe the scene and summarize the speech'])
                        with gr.Row():
                            run_btn = gr.Button('Run', variant='primary', scale=3)
                            cancel_btn = gr.Button('Cancel', scale=1, interactive=False)
                        with gr.Accordion('Advanced settings', open=False):
                            with gr.Row():
                                fps = gr.Number(DEFAULTS.fps, label='FPS', minimum=0.1, step=0.5)
                                max_frames = gr.Number(DEFAULTS.max_frames, label='Max frames',
                                                       minimum=1, precision=0)
                                max_new_tokens = gr.Number(DEFAULTS.max_new_tokens, label='Max new tokens',
                                                           minimum=1, precision=0)
                            with gr.Row():
                                total_pixels = gr.Number(DEFAULTS.total_pixels, label='Total pixels',
                                                         minimum=1, precision=0)
                                gpu_layers = gr.Number(DEFAULTS.gpu_layers, label='GPU layers (0 = CPU)',
                                                       minimum=0, precision=0)
                                threads = gr.Number(DEFAULTS.threads, label='Threads', minimum=1, precision=0)
                            with gr.Row():
                                context = gr.Number(DEFAULTS.context, label='Context', minimum=512, precision=0)
                                revision = gr.Textbox(DEFAULTS.revision, label='Revision')
                        with gr.Accordion('Same run in the terminal', open=False):
                            command = gr.Code(language='shell', interactive=False, lines=4,
                                              max_lines=8, wrap_lines=True, show_label=False)
                    with gr.Column(scale=7, min_width=420, elem_classes='wm-results'):
                        status = gr.HTML(views.status('Ready. Choose a model and media, then press Run.'))
                        empty = gr.HTML(views.empty_state())
                        with gr.Column(visible=False) as results:
                            answer = gr.Textbox(label='Answer', lines=8, max_lines=24,
                                                interactive=False, buttons=['copy'])
                            summary = gr.HTML()
                            open_btn = gr.Button('Show run folder in Finder', size='sm')
                        with gr.Accordion('Log', open=False, visible=False) as log_acc:
                            log = gr.Textbox(lines=12, max_lines=12, autoscroll=True,
                                             show_label=False, interactive=False)
                        run_dir = gr.State(None)

            # ----- History -----
            with gr.Tab('History', id=HISTORY_TAB):
                with gr.Row(equal_height=False):
                    size_filter = gr.Dropdown(['All models', *MODEL_REPOS], value='All models',
                                              label='Model', scale=1, min_width=160)
                    search = gr.Textbox(label='Search prompts and answers', scale=4,
                                        placeholder='ladder, transcribe, eclipse…')
                    refresh_btn = gr.Button('Refresh', scale=0, min_width=110, elem_classes='wm-end')
                table = gr.Dataframe(headers=TABLE_HEADERS, datatype=['str'] * 6,
                                     column_widths=['14%', '12%', '24%', '30%', '9%', '11%'],
                                     interactive=False, wrap=True, max_height=300,
                                     elem_classes='wm-table')
                ids = gr.State([])
                selected = gr.State(None)
                with gr.Row(equal_height=False):
                    with gr.Column(scale=7):
                        detail = gr.HTML(views.detail_empty())
                        with gr.Column(visible=False) as h_body:
                            h_answer = gr.Textbox(label='Answer', lines=6, max_lines=20,
                                                  interactive=False, buttons=['copy'])
                            h_summary = gr.HTML()
                            with gr.Accordion('Repeat in the terminal', open=False):
                                h_command = gr.Code(language='shell', interactive=False, lines=3,
                                                    max_lines=8, wrap_lines=True, show_label=False)
                    with gr.Column(scale=4, min_width=280, visible=False) as h_actions:
                        load_btn = gr.Button('Load settings into Run', variant='primary')
                        with gr.Row():
                            h_finder = gr.Button('Show in Finder', size='sm')
                            trash_btn = gr.Button('Move to Trash', size='sm', elem_classes='wm-danger')
                        trash_note = gr.HTML()
                        with gr.Row():
                            trash_yes = gr.Button('Move to Trash', variant='stop', size='sm', visible=False)
                            trash_no = gr.Button('Keep it', size='sm', visible=False)
                        compare = gr.Dropdown([], label='Compare with another run')
                        c_answer = gr.Textbox(label='Other answer', lines=6, max_lines=20,
                                              interactive=False)
                        c_summary = gr.HTML()

            # ----- Setup -----
            with gr.Tab('Setup', id=SETUP_TAB):
                with gr.Row(equal_height=False):
                    with gr.Column(min_width=440):
                        gr.Markdown('### Runtime')
                        checks = gr.HTML()
                        setup_refresh = gr.Button('Check again', size='sm')
                        with gr.Accordion('Rebuild the native runtime', open=False):
                            gr.Markdown('Runs `native/build.py --backend cpu` (Metal is included on '
                                        'macOS). It takes a few minutes and saves its log to `logs/build/`.')
                            rebuild_btn = gr.Button('Rebuild runtime')
                            rebuild_log = gr.Textbox(label='Build output', lines=10, max_lines=10,
                                                     autoscroll=True, interactive=False)
                        with gr.Accordion('Earlier build logs', open=False):
                            log_pick = gr.Dropdown([], label='Log')
                            log_view = gr.Textbox(show_label=False, lines=10, max_lines=10,
                                                  interactive=False)
                    with gr.Column(min_width=440):
                        gr.Markdown('### Models')
                        model_table = gr.Dataframe(headers=['Size', 'Repository', 'Status', 'On disk'],
                                                   column_widths=['80px', '46%', '130px', '90px'],
                                                   interactive=False, elem_classes='wm-table')
                        with gr.Row(equal_height=False):
                            model_pick = gr.Dropdown(list(MODEL_REPOS), value='4B', label='Model',
                                                     scale=2, min_width=120)
                            download_btn = gr.Button('Download', scale=1, elem_classes='wm-end')
                            delete_btn = gr.Button('Delete…', scale=1, elem_classes='wm-danger wm-end')
                        model_msg = gr.HTML()
                        with gr.Row():
                            delete_yes = gr.Button('Delete it', variant='stop', size='sm', visible=False)
                            delete_no = gr.Button('Keep it', size='sm', visible=False)

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
            start_run, run_inputs,
            [status, empty, results, answer, summary, log, log_acc, run_dir, run_btn, cancel_btn],
            concurrency_limit=1, concurrency_id='native', show_progress='hidden')
        run_event.then(refresh_history, history_inputs, history_outputs)
        run_event.then(model_note, size, model_info)
        cancel_btn.click(cancel_run, None, status, queue=False)
        open_btn.click(open_run_folder, run_dir, None)

        refresh_btn.click(refresh_history, history_inputs, history_outputs)
        size_filter.change(refresh_history, history_inputs, history_outputs)
        search.submit(refresh_history, history_inputs, history_outputs)
        table.select(select_run, ids,
                     [selected, detail, h_body, h_actions, h_answer, h_summary, h_command, c_answer,
                      c_summary])
        compare.change(compare_with, compare, [c_answer, c_summary])
        load_btn.click(load_into_run, selected, [*run_inputs, media_acc, tabs])
        h_finder.click(finder_for, selected, None)
        trash_btn.click(ask_trash, selected, [trash_yes, trash_no, trash_note])
        trash_no.click(cancel_trash, None, [trash_yes, trash_no, trash_note])
        trash_yes.click(confirm_trash, [selected, size_filter, search],
                        [trash_yes, trash_no, trash_note, table, ids, compare, selected, detail, h_body,
                         h_actions])

        setup_outputs = [checks, header, model_table, log_pick, log_view]
        setup_refresh.click(refresh_setup, None, setup_outputs)
        log_pick.change(setup_checks.read_build_log, log_pick, log_view)
        rebuild_btn.click(run_rebuild, None, rebuild_log,
                          concurrency_limit=1, concurrency_id='native').then(
            refresh_setup, None, setup_outputs)
        download_btn.click(download, model_pick, [model_msg, model_table], concurrency_limit=1)
        delete_btn.click(ask_delete, model_pick, [delete_yes, delete_no, model_msg])
        delete_no.click(lambda: (gr.Button(visible=False), gr.Button(visible=False), ''),
                        None, [delete_yes, delete_no, model_msg])
        delete_yes.click(confirm_delete, model_pick, [delete_yes, delete_no, model_msg, model_table])

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
        theme=build_theme(), css=CSS, footer_links=[])


if __name__ == '__main__':
    main()
