"""Visual identity: stone neutrals, one teal accent, IBM Plex for type.

Teal marks the primary action and the current selection only. Amber means
"cut off" (token limit) and red means "failed"; nothing else is coloured.
Light and dark follow the system setting.
"""
import gradio as gr

FONT = [gr.themes.GoogleFont('IBM Plex Sans'), 'ui-sans-serif', 'system-ui', 'sans-serif']
FONT_MONO = [gr.themes.GoogleFont('IBM Plex Mono'), 'ui-monospace', 'SFMono-Regular', 'monospace']


def build_theme():
    theme = gr.themes.Base(
        primary_hue=gr.themes.colors.teal,
        secondary_hue=gr.themes.colors.teal,
        neutral_hue=gr.themes.colors.stone,
        radius_size=gr.themes.sizes.radius_md,
        spacing_size=gr.themes.sizes.spacing_md,
        text_size=gr.themes.sizes.text_md,
        font=FONT,
        font_mono=FONT_MONO,
    )
    return theme.set(
        body_background_fill='*neutral_100',
        body_background_fill_dark='*neutral_950',
        background_fill_primary='white',
        background_fill_primary_dark='*neutral_900',
        background_fill_secondary='*neutral_50',
        background_fill_secondary_dark='*neutral_950',
        border_color_primary='*neutral_200',
        border_color_primary_dark='*neutral_800',
        color_accent='*primary_600',
        color_accent_soft='*primary_50',
        color_accent_soft_dark='*primary_950',
        layout_gap='12px',

        block_background_fill='white',
        block_background_fill_dark='*neutral_900',
        block_border_width='1px',
        block_border_color='*neutral_200',
        block_border_color_dark='*neutral_800',
        block_radius='10px',
        block_shadow='none',
        block_shadow_dark='none',
        block_label_background_fill='transparent',
        block_label_background_fill_dark='transparent',
        block_label_border_width='0px',
        block_label_border_width_dark='0px',
        block_label_shadow='none',
        block_label_text_color='*neutral_600',
        block_label_text_color_dark='*neutral_400',
        block_label_text_size='*text_sm',
        block_label_text_weight='500',
        block_label_padding='0',
        block_label_margin='0',
        block_title_background_fill='transparent',
        block_title_background_fill_dark='transparent',
        block_title_border_width='0px',
        block_title_border_width_dark='0px',
        block_title_text_color='*neutral_600',
        block_title_text_color_dark='*neutral_400',
        block_title_text_size='*text_sm',
        block_title_text_weight='500',
        block_title_padding='0',
        block_info_text_color='*neutral_500',
        block_info_text_color_dark='*neutral_400',
        panel_background_fill='white',
        panel_background_fill_dark='*neutral_900',
        panel_border_color='*neutral_200',
        panel_border_color_dark='*neutral_800',

        input_background_fill='*neutral_50',
        input_background_fill_dark='*neutral_950',
        input_background_fill_focus='white',
        input_background_fill_focus_dark='*neutral_950',
        input_border_color='*neutral_200',
        input_border_color_dark='*neutral_700',
        input_border_color_hover='*neutral_300',
        input_border_color_hover_dark='*neutral_600',
        input_border_color_focus='*primary_500',
        input_border_color_focus_dark='*primary_500',
        input_shadow='none',
        input_shadow_dark='none',
        input_shadow_focus='0 0 0 3px rgb(20 184 166 / 0.22)',
        input_shadow_focus_dark='0 0 0 3px rgb(45 212 191 / 0.22)',
        input_radius='8px',

        button_primary_background_fill='*primary_600',
        button_primary_background_fill_hover='*primary_700',
        button_primary_background_fill_dark='*primary_500',
        button_primary_background_fill_hover_dark='*primary_400',
        button_primary_border_color='*primary_600',
        button_primary_border_color_dark='*primary_500',
        button_primary_text_color='white',
        button_primary_text_color_dark='*neutral_950',
        button_primary_shadow='0 1px 2px rgb(28 25 23 / 0.12)',
        button_secondary_background_fill='white',
        button_secondary_background_fill_hover='*neutral_100',
        button_secondary_background_fill_dark='*neutral_800',
        button_secondary_background_fill_hover_dark='*neutral_700',
        button_secondary_border_color='*neutral_300',
        button_secondary_border_color_dark='*neutral_700',
        button_secondary_text_color='*neutral_800',
        button_secondary_text_color_dark='*neutral_100',
        button_secondary_shadow='none',

        checkbox_background_color_selected='*primary_600',
        checkbox_background_color_selected_dark='*primary_500',
        checkbox_border_color_selected='*primary_600',
        checkbox_border_color_selected_dark='*primary_500',
        checkbox_label_background_fill='*neutral_50',
        checkbox_label_background_fill_dark='*neutral_950',
        checkbox_label_background_fill_hover='*neutral_100',
        checkbox_label_background_fill_hover_dark='*neutral_800',
        checkbox_label_background_fill_selected='*primary_50',
        checkbox_label_background_fill_selected_dark='*primary_950',
        checkbox_label_border_color='*neutral_200',
        checkbox_label_border_color_dark='*neutral_700',
        checkbox_label_border_color_selected='*primary_500',
        checkbox_label_border_color_selected_dark='*primary_500',
        checkbox_label_border_width='1px',
        checkbox_label_text_color_selected='*primary_800',
        checkbox_label_text_color_selected_dark='*primary_200',
        checkbox_label_shadow='none',

        loader_color='*primary_500',
        slider_color='*primary_500',
        table_even_background_fill='white',
        table_even_background_fill_dark='*neutral_900',
        table_odd_background_fill='*neutral_50',
        table_odd_background_fill_dark='*neutral_950',
        table_row_focus='*primary_50',
        table_row_focus_dark='*primary_950',
        code_background_fill='*neutral_50',
        code_background_fill_dark='*neutral_950',
    )


CSS = """
:root {
  --wm-ink: #0f1d1c;
  --wm-ink-text: #e6f1ef;
  --wm-ink-muted: #9fb7b3;
  --wm-warn-bg: #fdf3dc; --wm-warn-fg: #7a4a06; --wm-warn-icon: #b26b09;
  --wm-err-bg: #fbe7e6;  --wm-err-fg: #8a1f1b;  --wm-err-icon: #c2352e;
  --wm-ok-fg: #0f6b5f;
  --wm-track: var(--neutral-200);
}
.dark {
  --wm-warn-bg: #3a2a0c; --wm-warn-fg: #f6d08e; --wm-warn-icon: #f0b44c;
  --wm-err-bg: #3d1716;  --wm-err-fg: #f5b4b0;  --wm-err-icon: #ef6b63;
  --wm-ok-fg: #5eead4;
  --wm-track: var(--neutral-700);
}
footer { display: none !important; }
.gradio-container { max-width: 1320px !important; }
::selection { background: rgb(20 184 166 / 0.28); }
input, textarea { caret-color: var(--primary-600); }
* { scrollbar-width: thin; scrollbar-color: var(--neutral-400) transparent; }
.wm-num, .wm-stats dd, table td { font-variant-numeric: tabular-nums; }

/* Header band */
.wm-header { display: flex; align-items: center; gap: 14px; padding: 14px 18px;
  background: var(--wm-ink); color: var(--wm-ink-text); border-radius: 12px; }
.wm-mark { width: 28px; height: 28px; border-radius: 7px; background: #14b8a6;
  display: grid; place-items: center; color: var(--wm-ink); flex: none; }
.wm-title { font-size: 17px; font-weight: 600; letter-spacing: -0.01em; line-height: 1.2; }
.wm-sub { font-size: 13px; color: var(--wm-ink-muted); }
.wm-chip { margin-left: auto; display: inline-flex; align-items: center; gap: 8px;
  font-size: 13px; padding: 6px 10px; border-radius: 999px; background: rgb(255 255 255 / 0.07);
  color: var(--wm-ink-text); white-space: nowrap; }
.wm-dot { width: 8px; height: 8px; border-radius: 50%; background: #2dd4bf; }
.wm-dot.bad { background: #ef6b63; }

/* Status line */
.wm-status { display: flex; align-items: center; gap: 10px; min-height: 40px; padding: 8px 12px;
  border-radius: 10px; background: var(--background-fill-primary);
  border: 1px solid var(--border-color-primary); font-size: 14px; }
.wm-status .wm-steps { display: flex; gap: 6px; margin-left: auto; }
.wm-step { display: inline-flex; align-items: center; gap: 5px; font-size: 12px;
  color: var(--body-text-color-subdued); padding: 3px 8px; border-radius: 999px;
  background: var(--background-fill-secondary); }
.wm-step.active { color: var(--primary-700); background: var(--color-accent-soft); }
.dark .wm-step.active { color: var(--primary-200); }
.wm-step.done { color: var(--wm-ok-fg); }
.wm-status.error { background: var(--wm-err-bg); color: var(--wm-err-fg); border-color: transparent; }
.wm-status.error svg { color: var(--wm-err-icon); }
.wm-ico { width: 16px; height: 16px; flex: none; }
.wm-spin { animation: wm-spin 0.9s linear infinite; }
@keyframes wm-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .wm-spin { animation: none; } }

/* Empty state */
.wm-empty { padding: 28px 24px; border: 1px dashed var(--border-color-primary);
  border-radius: 12px; color: var(--body-text-color-subdued); }
.wm-empty h3 { margin: 0 0 6px; font-size: 16px; font-weight: 600; color: var(--body-text-color); }
.wm-empty p { margin: 0; font-size: 14px; line-height: 1.55; max-width: 60ch; }
.wm-empty ul { margin: 14px 0 0; padding: 0; list-style: none; display: grid; gap: 8px; font-size: 14px; }
.wm-empty li { display: flex; gap: 8px; align-items: flex-start; }
.wm-empty li svg { margin-top: 2px; color: var(--primary-600); }

/* Stats strip */
.wm-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: 1px; margin: 0; border-radius: 10px; overflow: hidden;
  background: var(--border-color-primary); border: 1px solid var(--border-color-primary); }
.wm-stats div { background: var(--background-fill-primary); padding: 10px 12px; }
.wm-stats dt { font-size: 12px; color: var(--body-text-color-subdued); margin: 0 0 2px; }
.wm-stats dd { margin: 0; font-family: var(--font-mono); font-size: 15px; font-weight: 500;
  color: var(--body-text-color); }
.wm-stats dd.warn { color: var(--wm-warn-icon); }
.wm-stats dd.ok { color: var(--wm-ok-fg); }
.wm-note { display: flex; gap: 10px; align-items: flex-start; margin-top: 10px; padding: 10px 12px;
  border-radius: 10px; font-size: 14px; line-height: 1.5; }
.wm-note.warn { background: var(--wm-warn-bg); color: var(--wm-warn-fg); }
.wm-note.warn svg { color: var(--wm-warn-icon); margin-top: 2px; }

/* Signature: what the model saw and heard */
.wm-timeline { margin-top: 14px; padding: 14px; border-radius: 12px;
  background: var(--background-fill-primary); border: 1px solid var(--border-color-primary); }
.wm-tl-head { display: flex; justify-content: space-between; align-items: baseline;
  font-size: 13px; color: var(--body-text-color-subdued); margin-bottom: 10px; }
.wm-tl-head b { font-weight: 600; color: var(--body-text-color); font-size: 14px; }
.wm-frames { display: grid; gap: 6px; }
.wm-frames a { display: block; border-radius: 6px; overflow: hidden; line-height: 0;
  outline-offset: 2px; background: var(--background-fill-secondary); }
.wm-frames img { width: 100%; aspect-ratio: 4 / 3; object-fit: cover;
  transition: transform 160ms cubic-bezier(.2,.7,.2,1); }
.wm-frames a:hover img { transform: scale(1.04); }
.wm-ruler { position: relative; height: 34px; margin-top: 10px; }
.wm-ruler .track { position: absolute; left: 0; right: 0; top: 6px; height: 4px;
  border-radius: 2px; background: var(--wm-track); }
.wm-ruler .tick { position: absolute; top: 2px; width: 2px; height: 12px; margin-left: -1px;
  border-radius: 1px; background: var(--primary-600); }
.dark .wm-ruler .tick { background: var(--primary-400); }
.wm-ruler .lbl { position: absolute; top: 18px; transform: translateX(-50%);
  font-family: var(--font-mono); font-size: 11px; color: var(--body-text-color-subdued); white-space: nowrap; }
.wm-ruler .lbl.first { transform: none; }
.wm-ruler .lbl.last { transform: translateX(-100%); }
.wm-audio { position: relative; height: 26px; margin-top: 4px; }
.wm-audio .seg { position: absolute; top: 0; height: 26px; border-radius: 6px;
  background: var(--color-accent-soft); color: var(--primary-800); font-size: 12px;
  display: flex; align-items: center; padding: 0 8px; overflow: hidden; white-space: nowrap;
  border: 1px solid rgb(20 184 166 / 0.35); }
.dark .wm-audio .seg { color: var(--primary-200); }
.wm-tl-legend { display: flex; gap: 16px; margin-top: 10px; font-size: 12px;
  color: var(--body-text-color-subdued); }
.wm-tl-legend span { display: inline-flex; align-items: center; gap: 6px; }
.wm-tl-legend i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; }

/* History detail heading */
.wm-detail h3 { margin: 0 0 4px; font-size: 16px; font-weight: 600; }
.wm-detail p { margin: 0; font-size: 14px; color: var(--body-text-color-subdued); line-height: 1.5; }
.wm-detail code { font-size: 12px; }

/* Setup checks */
.wm-checks { list-style: none; margin: 0; padding: 0; border: 1px solid var(--border-color-primary);
  border-radius: 10px; overflow: hidden; background: var(--background-fill-primary); }
.wm-checks li { display: grid; grid-template-columns: 20px minmax(130px, 38%) minmax(0, 1fr); gap: 10px; align-items: center;
  padding: 9px 12px; font-size: 14px; border-top: 1px solid var(--border-color-primary); }
.wm-checks li:first-child { border-top: 0; }
.wm-checks .ok svg { color: var(--wm-ok-fg); }
.wm-checks .bad svg { color: var(--wm-err-icon); }
.wm-checks code { font-size: 12px; color: var(--body-text-color-subdued); background: none;
  padding: 0; overflow-wrap: anywhere; }
.wm-msg { display: flex; gap: 8px; align-items: flex-start; font-size: 14px; line-height: 1.5; }
.wm-msg.error { color: var(--wm-err-fg); }
.wm-msg.ok svg { color: var(--wm-ok-fg); }
.wm-msg.warn { color: var(--wm-warn-fg); }

.wm-danger button, button.wm-danger { color: var(--wm-err-fg) !important; }

/* Layout fixes over Gradio defaults */
.wm-video { border-width: 0 !important; }
.wm-results { position: sticky; top: 12px; align-self: flex-start; }
.wm-table table, .wm-table th, .wm-table td, .wm-table span, .wm-table input {
  font-family: var(--font) !important; font-size: 13px; }
.wm-table td:first-child, .wm-table td:nth-child(5) { white-space: nowrap; }
.wm-table th { color: var(--body-text-color-subdued); font-weight: 500; }
.wm-end { align-self: flex-end; }
.wm-tl-legend i.audio { background: var(--color-accent-soft); border: 1px solid rgb(20 184 166 / 0.55); }
.dark .wm-tl-legend i.audio { background: rgb(20 184 166 / 0.25); }
.wm-model-note { padding: 0 12px 10px !important; background: var(--block-background-fill) !important; }
.wm-header .wm-title { color: var(--wm-ink-text); }
.wm-header .wm-sub { color: var(--wm-ink-muted); }
.wm-model-line { margin: 0; font-size: 13px; color: var(--body-text-color-subdued); }
.wm-model-line code { font-size: 12px; background: none; padding: 0; }
"""
