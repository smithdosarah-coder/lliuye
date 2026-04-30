import os

if os.environ.get("ALLOW_LEGACY_GRADIO") != "1":
    raise ImportError(
        "legacy_gradio archived (2026-04-29) · v16 主管线已替代 form_filler / narrative_pipeline · "
        "Set ALLOW_LEGACY_GRADIO=1 only for emergency demo fallback (see CLAUDE.md §16)."
    )
