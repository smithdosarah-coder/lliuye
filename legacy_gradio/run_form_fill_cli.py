# -*- coding: utf-8 -*-
"""CLI runner for form-fill mode.

Usage (PowerShell):
  $env:DEEPSEEK_API_KEY = "..."   # or OPENAI_API_KEY
  py run_form_fill_cli.py --template "...docx" --materials "...folder" --provider deepseek

Optional:
  --output outputs/   # output directory for generated docx
"""

from __future__ import annotations

import argparse
import os
import sys


_EMOJI_REPL = {
    "⚠️": "[WARN] ",
    "✅": "[OK] ",
    "❌": "[ERR] ",
    "📋": "[TODO] ",
    "🟡": "[MAYBE] ",
    "🟢": "[OK] ",
    "🔍": "[SEARCH] ",
    "📝": "[FORM] ",
}


def _configure_stdio() -> None:
    # Windows terminals sometimes default to GBK; avoid crashing on emoji.
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    try:
        sys.stderr.reconfigure(errors="replace")
    except Exception:
        pass


def _sanitize(s: str) -> str:
    if not s:
        return ""
    for k, v in _EMOJI_REPL.items():
        s = s.replace(k, v)
    s = s.replace("\ufe0f", "")
    return s


def _pick_api_key(provider: str) -> str:
    # Prefer provider-specific env var, fall back to OPENAI_API_KEY for OpenAI-compatible endpoints.
    for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "MODEL_API_KEY"):
        v = (os.getenv(k) or "").strip()
        if v:
            return v
    return ""


def main() -> int:
    _configure_stdio()

    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True, help="Path to .docx template")
    ap.add_argument("--materials", required=True, help="Folder or file path(s) to materials")
    ap.add_argument("--provider", default=os.getenv("MODEL_PROVIDER", "deepseek"), help="Model provider key")
    ap.add_argument("--output", default="", help="Output directory for filled docx")
    args = ap.parse_args()

    api_key = _pick_api_key(args.provider)
    if not api_key:
        print("ERROR: missing API key. Set DEEPSEEK_API_KEY or OPENAI_API_KEY.", file=sys.stderr)
        return 2

    from agent import CreditReportAgent

    agent = CreditReportAgent(api_key=api_key, provider=args.provider)
    agent.mode = "form_fill"
    agent.form_template_path = args.template
    if (args.output or "").strip():
        agent.form_output_dir = args.output

    uploaded = [args.materials]

    output_path = ""
    pending_tags = None
    validation_blocked = False

    for event in agent.process_form_fill(args.materials, uploaded):
        t = event.get("type")
        if t == "thinking":
            print(_sanitize(f"[thinking] {event.get('content','')}"), flush=True)
        elif t == "tool_call":
            print(_sanitize(f"[tool_call] {event.get('name','')} {event.get('status','')}"), flush=True)
        elif t == "tool_result":
            print(_sanitize(f"[tool_result] {event.get('name','')}: {event.get('result','')}"), flush=True)
        elif t == "message":
            print(_sanitize(f"[message] {event.get('content','')}"), flush=True)
        elif t == "file":
            output_path = event.get("path", "") or output_path
            print(_sanitize(f"[file] {output_path}"), flush=True)
        elif t == "pending_tags":
            pending_tags = event.get("tags")
            print(_sanitize(f"[pending_tags] {len(pending_tags or [])} items"), flush=True)
        elif t == "validation_blocked":
            validation_blocked = True
            blockers = event.get("blockers") or []
            print(_sanitize(f"[validation_blocked] {len(blockers)} blockers"), flush=True)
        elif t == "done":
            print(_sanitize(f"[done] {event.get('content','')}"), flush=True)
        else:
            print(_sanitize(f"[{t}] {event}"), flush=True)

    if output_path and not validation_blocked:
        print("OUTPUT_DOCX=", output_path)

    if pending_tags is not None and output_path:
        try:
            import json

            out_json = output_path + ".pending_tags.json"
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(pending_tags, f, ensure_ascii=False, indent=2)
            print("PENDING_TAGS_JSON=", out_json)
        except Exception as e:
            print("WARN: failed to write pending_tags json:", e, file=sys.stderr)

    return 1 if validation_blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
