# -*- coding: utf-8 -*-
"""Generate and persist the completed DP002 session used by demo-form mode.

Run once on the server after configuring the LLM key.  The result is written to
``outputs/demo-form/report-default-session.json``; no synthetic report content
is created by this script.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SAMPLE_ID = "DP002_蓝汀家电"
SAMPLE_DIR = ROOT / "data" / "mock" / "deep-pillar" / SAMPLE_ID
SOURCE_DOCX = ROOT / "samples" / "经纬测绘_对公成稿A.docx"
CLASSIFIED_JSON = ROOT / "outputs" / "v16_llm_classified.json"
OUTPUT_FILE = ROOT / "outputs" / "demo-form" / "report-default-session.json"
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")

# The showcase session deliberately exposes the seven files used for this run.
DEMO_MATERIALS = (
    "1、蓝汀家电营业执照副本21.10.8.pdf",
    "1、蓝汀家电章程调档25.5.26.pdf",
    "2、财务报表2022年-蓝汀家电.xlsx",
    "2、2023年度财务报表-蓝汀家电20240103.xlsx",
    "2、2024年度财务报表-蓝汀家电.xlsx",
    "2、财务报表2025年-蓝汀家电.xlsx",
    "宁波行-蓝汀家电授信补充问题及材料.docx",
)


def _load_project_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(ROOT / ".env")


def _parse_sse(chunk: str) -> tuple[str, dict] | None:
    event = ""
    data = ""
    for line in chunk.splitlines():
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data = line[5:].strip()
    if not event or not data:
        return None
    parsed = json.loads(data)
    return event, parsed if isinstance(parsed, dict) else {}


def _load_client_metadata() -> dict:
    raw = json.loads((SAMPLE_DIR / "client_metadata.json").read_text(encoding="utf-8"))
    metadata = raw.get("client_metadata")
    if not isinstance(metadata, dict):
        raise RuntimeError("DP002 client_metadata.json 缺少 client_metadata 对象")
    return metadata


def _preflight() -> None:
    if not os.environ.get("DEEPSEEK_API_KEY", "").strip():
        raise RuntimeError("DEEPSEEK_API_KEY 未配置")
    for path in (SAMPLE_DIR, SOURCE_DOCX, CLASSIFIED_JSON):
        if not path.exists():
            raise RuntimeError(f"必需输入不存在: {path}")
    missing = [name for name in DEMO_MATERIALS if not (SAMPLE_DIR / name).is_file()]
    if missing:
        raise RuntimeError(f"DP002 缺少预定材料: {missing}")


async def _generate() -> dict:
    from agent_report.v16_runner import fill_stream

    client_metadata = _load_client_metadata()
    stage_events: list[dict] = []
    done: dict | None = None
    output_root = ROOT / "outputs"
    output_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="demo-form-dp002-", dir=output_root) as tmp:
        material_dir = Path(tmp)
        for name in DEMO_MATERIALS:
            shutil.copy2(SAMPLE_DIR / name, material_dir / name)
        async for chunk in fill_stream(
            report_id="demo-form-dp002",
            source_docx=SOURCE_DOCX,
            material_dir=material_dir,
            classified_json=CLASSIFIED_JSON,
            output_dir=output_root,
            explicit_mock=False,
            client_metadata=client_metadata,
        ):
            parsed = _parse_sse(chunk)
            if not parsed:
                continue
            event, data = parsed
            if event == "error":
                raise RuntimeError(data.get("message") or "DP002 生成失败")
            if event == "stage":
                stage_events.append({
                    "id": f"seed-stage-{len(stage_events) + 1}",
                    "at": datetime.now(SHANGHAI_TZ).isoformat(timespec="seconds"),
                    "kind": "qc.run" if data.get("stage") == "audit" else "section.done",
                    "priority": "done",
                    "label": data.get("message") or str(data.get("stage") or "生成阶段完成"),
                })
            elif event == "done":
                done = data

    if done is None:
        raise RuntimeError("v16 流结束但未返回 done 事件")
    selected_at = datetime.now(SHANGHAI_TZ).isoformat(timespec="seconds")
    stage_events.insert(0, {
        "id": "seed-template",
        "at": selected_at,
        "kind": "template.select",
        "priority": "done",
        "label": "已选用模板 · 对公成稿 A",
        "detail": "经纬测绘模板形态",
    })
    done["timeline"] = stage_events
    done["conversation"] = [{
        "id": "seed-template-message",
        "at": selected_at,
        "kind": "system-event",
        "content": "已选用模板 · 对公成稿 A",
    }]
    done["template"] = {
        "id": "tpl-corporate-a",
        "name": "对公成稿 A",
        "kind": "预置",
        "version": "经纬测绘",
        "fieldTotal": 0,
        "recentUsed": 0,
    }
    done["seeded_at"] = datetime.now(SHANGHAI_TZ).isoformat(timespec="seconds")
    # Session IDs are process-local.  The API assigns a fresh valid ID when it
    # hydrates this persisted payload after a cold start.
    done.pop("session_id", None)
    done.pop("report_id", None)
    return done


def _validate(payload: dict) -> None:
    profile = payload.get("profile") or {}
    if "蓝汀家电" not in str(profile.get("company_name") or ""):
        raise RuntimeError("seed profile 不是蓝汀家电，拒绝覆盖默认会话")
    if profile.get("unified_credit_code") != "91330782MA2XXXX022":
        raise RuntimeError("seed profile 信用代码不匹配，拒绝覆盖默认会话")
    if len(payload.get("materials") or []) != len(DEMO_MATERIALS):
        raise RuntimeError("seed 会话材料数不是 7")
    sections = payload.get("sections") or []
    if not sections or not any(str(section.get("content") or "").strip() for section in sections):
        raise RuntimeError("seed 会话没有章节正文")


def main() -> int:
    _load_project_env()
    _preflight()
    payload = asyncio.run(_generate())
    _validate(payload)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"SEEDED {OUTPUT_FILE}")
    print(
        f"company={payload['profile']['company_name']} "
        f"materials={len(payload['materials'])} sections={len(payload['sections'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
