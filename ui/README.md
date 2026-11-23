# WeMM-Video local interface

A browser interface for the native GGUF runtime. It runs the same
`native/run_hf.py` command builder and the same `wemm-native` binary you
would use in a terminal, and it saves every run to `runs/`.

## Start it

Build the native runtime first (see [native/README.md](../native/README.md)),
then from the project root:

```bash
.venv-gguf/bin/python -m pip install -r ui/requirements.txt
.venv-gguf/bin/python ui/app.py
```

It opens at <http://127.0.0.1:7860> and listens only on this computer.
Use `--port` to pick another port and `--no-browser` to skip opening a tab.

## Tabs

- **Run**: pick a model size, add a video, images, or audio, write a prompt,
  and press Run. Advanced holds every `run_hf.py` option. "Same run in the
  terminal" shows the equivalent command. Cancel stops `wemm-native`.
- **History**: every run in `runs/`, including runs you start in a terminal
  with `--output runs/<name>/result.json`. Shows the answer, the frames the
  model saw, timing, and the command to repeat it. "Load settings into Run"
  copies a past run's settings back to the Run tab.
- **Setup**: checks for `wemm-native`, Metal, ffmpeg, and `huggingface_hub`;
  downloads or deletes models from the Hugging Face cache; rebuilds the
  native runtime and keeps its log in `logs/build/`.

## What a run folder holds

```
runs/2026-11-23_1452_2b-metal_apollo-11-first-steps-video-audio/
├── result.json            # what wemm-native wrote: answer, tokens, timing
├── result.json.evidence/  # decoded frames, audio features, the exact request
├── inputs/                # copies of the media you uploaded
├── previews/              # PNG versions of the frames for the browser
├── run.json               # settings, terminal command, and status
└── run.log                # wemm-native output
```

## Differences from running `run_hf.py` yourself

| Setting | `run_hf.py` default | Interface default |
| --- | --- | --- |
| `--gpu-layers` | 0 (CPU) | 99 (Metal) |
| `--max-new-tokens` | 128 | 512 |
| `--max-frames` | 4 | 8 |
| `--output` | required | chosen automatically under `runs/` |

## Files

| File | Role |
| --- | --- |
| `app.py` | Page layout and event wiring |
| `runner.py` | Builds the command with `run_hf.make_command`, runs and cancels `wemm-native` |
| `history.py` | Reads `runs/`, converts frames, reconstructs commands for older runs |
| `setup_checks.py` | Runtime checks, model cache, rebuilds |
| `views.py` | HTML pieces: header, status line, empty states, stats, and the frame timeline |
| `theme.py` | Gradio theme and CSS: stone neutrals, one teal accent, IBM Plex |
| `presets.py` | Prompt presets |
| `paths.py` | Shared locations and the model list |
