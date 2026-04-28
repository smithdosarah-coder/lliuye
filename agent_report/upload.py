# -*- coding: utf-8 -*-
"""agent_report.upload — Stage C.1 multipart 材料上传 + 解析摘要.

设计:
  - 持久化客户上传材料到 ``data/kb/report/{report_id}/`` 目录
  - 同步轻量解析(取字符数 / 文件类型 / 大小) · 不做 LLM 分析(那是 fill 阶段)
  - 返 ``{report_id, file_summary}`` 供前端在 fill 阶段引用同一 report_id 跳过重传
  - empty-state-design-protocol §3 兼容: 上传是 user-driven trigger · 后端不
    auto-fire LLM · 仅持久化 + 元数据

Boundary:
  - 不动 v16_*.py · 不动其他 Agent · 仅写 agent_report/ 目录
  - 解析复用 ``tools._read_single_file`` (与 api.py 现有 fill 路径一致)
"""
from __future__ import annotations

import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# 支持的文件类型 (与 api.py _load_uploaded_materials 保持一致)
_SUPPORTED_EXTS = {".txt", ".docx", ".doc", ".pdf", ".xlsx", ".xls",
                   ".jpg", ".jpeg", ".png"}

UPLOAD_ROOT = PROJECT_ROOT / "data" / "kb" / "report"


def make_report_id() -> str:
    """生成新 report_id (= session_id 的别名 · UUID4)."""
    return str(uuid.uuid4())


def upload_dir(report_id: str) -> Path:
    """report_id → 持久化目录."""
    return UPLOAD_ROOT / report_id


def persist_file(report_id: str, name: str, content: bytes) -> Path:
    """落盘单个文件 · 返保存路径.

    Args:
        report_id: 持久化目录 key
        name: 文件名 (取 basename · 去除路径分隔符)
        content: 字节内容

    Returns:
        本地保存路径 (Path)
    """
    safe_name = Path(name).name.replace("\\", "_").replace("/", "_")
    if not safe_name:
        safe_name = f"upload_{int(datetime.now().timestamp())}.bin"
    target_dir = upload_dir(report_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / safe_name
    # 同名冲突: 加序号
    if target.exists():
        stem = target.stem
        suffix = target.suffix
        idx = 1
        while target.exists():
            target = target_dir / f"{stem}_{idx}{suffix}"
            idx += 1
    target.write_bytes(content)
    return target


def parse_file_summary(saved_path: Path) -> dict[str, Any]:
    """轻量解析 · 取文件元数据 + 字符数 (失败给 0 不抛)."""
    summary: dict[str, Any] = {
        "name": saved_path.name,
        "type": saved_path.suffix.lower().lstrip("."),
        "size_bytes": saved_path.stat().st_size if saved_path.exists() else 0,
        "parsed_chars": 0,
        "parse_status": "ok",
    }
    if saved_path.suffix.lower() not in _SUPPORTED_EXTS:
        summary["parse_status"] = "skipped"
        summary["parse_note"] = "unsupported_ext"
        return summary

    try:
        from tools import _read_single_file  # type: ignore
    except ImportError:
        summary["parse_status"] = "deferred"
        summary["parse_note"] = "tools.read 不可用 · 推迟到 fill 阶段"
        return summary

    try:
        text = _read_single_file(str(saved_path)) or ""
        summary["parsed_chars"] = len(text)
        if not text:
            summary["parse_status"] = "empty"
    except Exception as e:  # noqa: BLE001 — 单个文件失败不阻塞整批上传
        summary["parse_status"] = "error"
        summary["parse_note"] = f"{type(e).__name__}: {e}"

    return summary


def persist_files(report_id: str, files: list[tuple[str, bytes]]) -> list[dict[str, Any]]:
    """批量落盘 + 解析 · 返每个文件的 summary.

    Args:
        report_id: 持久化目录 key
        files: list of (filename, content_bytes)

    Returns:
        list of file_summary dict (同 parse_file_summary 输出 · 加 ``saved_path``)
    """
    summaries: list[dict[str, Any]] = []
    for name, content in files:
        try:
            saved = persist_file(report_id, name, content)
        except (OSError, ValueError) as e:
            summaries.append({
                "name": Path(name).name,
                "type": "",
                "size_bytes": 0,
                "parsed_chars": 0,
                "parse_status": "save_failed",
                "parse_note": f"{type(e).__name__}: {e}",
            })
            continue
        summary = parse_file_summary(saved)
        summary["saved_path"] = str(saved.relative_to(PROJECT_ROOT))
        summaries.append(summary)
    return summaries


def cleanup_report_dir(report_id: str) -> bool:
    """清理一份 report_id 对应的上传目录(测试用 / TTL 清理用)."""
    target = upload_dir(report_id)
    if not target.exists():
        return False
    try:
        shutil.rmtree(target)
        return True
    except OSError:
        return False


def list_report_files(report_id: str) -> list[Path]:
    """列出已上传文件路径 · fill 阶段消费."""
    target = upload_dir(report_id)
    if not target.is_dir():
        return []
    return [p for p in target.iterdir() if p.is_file()]


__all__ = [
    "UPLOAD_ROOT",
    "cleanup_report_dir",
    "list_report_files",
    "make_report_id",
    "parse_file_summary",
    "persist_file",
    "persist_files",
    "upload_dir",
]
