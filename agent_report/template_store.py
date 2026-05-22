# -*- coding: utf-8 -*-
"""agent_report.template_store — Q6-B 用户自定义 docx 模板持久化 + 自动 placeholder lint.

设计 (per Q6-B 选 B 路径 · 2026-05-21):
  - 用户通过 `POST /api/report/upload-template` 上传 .docx · 后端跑 byte-level diff
    standalone lint (`scripts/lint/liuye_docx_residue_check.lint_docx_standalone`) ·
    返 placeholder_count / placeholder_keys / residue_count / residue_samples ·
    持久化到 ``data/kb/templates/{template_id}/`` 含 docx + metadata.json
  - ``GET /api/report/templates`` 列 5 个内置 + 已上传 user templates · 前端 dropdown 渲染
  - ``V16FillRequest.source_docx`` 支持 ``"user-template:{template_id}"`` 格式 ·
    v16_fill 解析 template_id → 真路径

多用户隔离 (per Q-053 决策):
  - **共享** (shared) 模式 · 不按 user_id 隔离 (MVP)
  - metadata.json 含 ``uploader`` 字段 (审计 / 追溯责任) · 一份模板全员可见
  - 未来若需 user-level 隔离 · 加 ``visibility="private"`` + uploader filter (Phase 2)

Boundary (per CLAUDE.md "不动 v16 pipeline 核心"):
  - 不动 v16_runner / v16_generator / v16_step1_extract
  - 仅写 agent_report/template_store.py + agent_report/api.py 加 2 endpoint
  - 不改 V16FillRequest schema (复用 source_docx 字段) · 仅在 v16_fill 解析阶段加 prefix 识别
"""
from __future__ import annotations

import json
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 模板根目录 · 与 data/kb/report/{report_id}/ (材料) 隔离 · 防混淆
TEMPLATE_ROOT = PROJECT_ROOT / "data" / "kb" / "templates"
# Soft-delete 归档目录 · DELETE / supersede 把老模板搬这里 · 不真删 · 留 audit trail
TEMPLATE_ARCHIVE_DIRNAME = ".archived"

# 5 个内置模板 · 与前端 SSOT (single source of truth)
# 前端 dropdown / v16/fill 默认 source_docx 都消费此列表 · 修改时同步前端 ReportWorkspace
BUILTIN_TEMPLATES: list[dict[str, str]] = [
    {
        "template_path": "samples/经纬测绘_对公成稿A.docx",
        "name": "对公成稿 A · 经纬测绘",
        "type": "builtin",
        "business_line": "corporate",
    },
    {
        "template_path": "samples/兴业资管_对公成稿B.docx",
        "name": "对公成稿 B · 兴业资管",
        "type": "builtin",
        "business_line": "corporate",
    },
    {
        "template_path": "samples/普惠申报书_骨架型.docx",
        "name": "普惠申报书 · 骨架型",
        "type": "builtin",
        "business_line": "inclusive",
    },
    {
        "template_path": "samples/科创贷申报书_模板.docx",
        "name": "科创贷申报书 · 模板",
        "type": "builtin",
        "business_line": "corporate",
    },
    {
        "template_path": "samples/小微对私授信申报书_模板.docx",
        "name": "小微对私授信申报书",
        "type": "builtin",
        "business_line": "retail",
    },
]

# 上传体积上限 (10 MB) · 与前端 hint 同步 · 限制存储 + 防 docx 炸弹
MAX_TEMPLATE_BYTES = 10 * 1024 * 1024


def make_template_id() -> str:
    """生成 user template id (user- 前缀 · UUID4 前 12 hex)."""
    return f"user-{uuid.uuid4().hex[:12]}"


def template_dir(template_id: str) -> Path:
    """template_id → 持久化目录 (data/kb/templates/{id}/)."""
    return TEMPLATE_ROOT / template_id


def safe_filename(name: str) -> str:
    """清洗文件名 · 仅保留 basename · 去路径分隔符."""
    safe = Path(name).name.replace("\\", "_").replace("/", "_")
    if not safe:
        safe = f"template_{int(datetime.now().timestamp())}.docx"
    return safe


def resolve_template_path(source_docx: str) -> Path:
    """解析 source_docx 字段 → 真实 docx 路径.

    支持两种格式:
      - "samples/xxx.docx"           → PROJECT_ROOT / source_docx (内置)
      - "user-template:{template_id}" → 读 metadata.json 拼路径 (user 上传)

    抛 FileNotFoundError 当 user template 不存在 · caller (api.py v16_fill) 翻 404.
    """
    if source_docx.startswith("user-template:"):
        template_id = source_docx.split(":", 1)[1].strip()
        if not template_id:
            raise FileNotFoundError(f"user-template id 为空 · source_docx={source_docx!r}")
        meta_path = template_dir(template_id) / "metadata.json"
        if not meta_path.exists():
            raise FileNotFoundError(
                f"user template {template_id!r} metadata.json 不存在 · "
                f"path={meta_path}"
            )
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise FileNotFoundError(
                f"user template {template_id!r} metadata.json 解析失败 · {exc}"
            ) from exc
        docx_path = template_dir(template_id) / meta.get("filename", "")
        if not docx_path.exists():
            raise FileNotFoundError(
                f"user template {template_id!r} docx 不存在 · path={docx_path}"
            )
        return docx_path

    # 内置 · 项目相对路径
    return (PROJECT_ROOT / source_docx).resolve()


def persist_template(
    *,
    file_bytes: bytes,
    original_filename: str,
    template_name: str,
    business_line: str = "corporate",
    uploader: str = "unknown",
) -> dict[str, Any]:
    """落盘 user template + 跑 standalone lint + 写 metadata.json.

    Returns:
        metadata dict (含 template_id / placeholder_count / residue_count / ...)
        前端拿此作 validation_report 显示给客户经理.

    Raises:
        ValueError: 体积超限 / 扩展名不对 · caller (api.py) 翻 400/413.
        OSError: 落盘失败 · caller 翻 500.
    """
    if not original_filename.lower().endswith(".docx"):
        raise ValueError(f"仅接受 .docx 文件 · 拒 {Path(original_filename).suffix!r}")
    if len(file_bytes) > MAX_TEMPLATE_BYTES:
        raise ValueError(
            f"模板体积 {len(file_bytes)/1024/1024:.1f} MB 超限 "
            f"({MAX_TEMPLATE_BYTES//1024//1024} MB)"
        )
    if len(file_bytes) < 100:
        raise ValueError(f"文件太小 {len(file_bytes)} bytes · 疑似空文件或损坏")

    template_id = make_template_id()
    tdir = template_dir(template_id)
    tdir.mkdir(parents=True, exist_ok=True)

    safe_name = safe_filename(original_filename)
    docx_path = tdir / safe_name
    docx_path.write_bytes(file_bytes)

    # 跑 standalone lint (per 治本不治标 · byte-level diff 通用机制)
    try:
        from scripts.lint.liuye_docx_residue_check import lint_docx_standalone
        lint_report = lint_docx_standalone(docx_path)
    except ImportError as exc:
        # lint 依赖缺失 · 不阻塞 · 标 SKIP (per 客户底线 · 字段填不了标 "未能自动写入")
        lint_report = {
            "placeholder_count": 0,
            "placeholder_keys": [],
            "residue_count": 0,
            "residue_samples": [],
            "validation": "SKIP",
            "element_count": 0,
            "error": f"lint 模块不可用 · {exc}",
        }
    except Exception as exc:  # noqa: BLE001 — lint 失败不阻塞上传 · 标 ERROR
        lint_report = {
            "placeholder_count": 0,
            "placeholder_keys": [],
            "residue_count": 0,
            "residue_samples": [],
            "validation": "ERROR",
            "element_count": 0,
            "error": f"lint 失败 · {type(exc).__name__}: {exc}",
        }

    metadata: dict[str, Any] = {
        "template_id": template_id,
        "template_name": template_name,
        "filename": safe_name,
        "business_line": business_line,
        "uploader": uploader,
        "uploaded_at": datetime.now().isoformat(timespec="seconds"),
        "size_bytes": len(file_bytes),
        # lint 报告 spread
        "placeholder_count": lint_report["placeholder_count"],
        "placeholder_keys": lint_report["placeholder_keys"],
        "residue_count": lint_report["residue_count"],
        "residue_samples": lint_report["residue_samples"],
        "validation": lint_report["validation"],
        "element_count": lint_report["element_count"],
        "lint_error": lint_report.get("error"),
        # 引用句柄 · 给前端 + V16FillRequest 用
        "template_ref": f"user-template:{template_id}",
    }
    meta_path = tdir / "metadata.json"
    meta_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return metadata


def list_user_templates() -> list[dict[str, Any]]:
    """枚举所有已上传 user templates · 读 metadata.json · 失败的 skip 静默.

    返列表 sort by uploaded_at DESC (最新在前) · 给前端 dropdown 渲染.
    """
    items: list[dict[str, Any]] = []
    if not TEMPLATE_ROOT.exists():
        return items
    for tdir in TEMPLATE_ROOT.iterdir():
        if not tdir.is_dir():
            continue
        # Skip soft-delete archive dir (per CRUD 完整 2026-05-21 · archive_template 搬这里)
        if tdir.name == TEMPLATE_ARCHIVE_DIRNAME or tdir.name.startswith("."):
            continue
        meta_path = tdir / "metadata.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        items.append({
            "template_path": meta.get("template_ref", f"user-template:{tdir.name}"),
            "name": meta.get("template_name", tdir.name),
            "type": "user",
            "business_line": meta.get("business_line", ""),
            "uploader": meta.get("uploader", "unknown"),
            "uploaded_at": meta.get("uploaded_at", ""),
            "placeholder_count": meta.get("placeholder_count", 0),
            "residue_count": meta.get("residue_count", 0),
            "validation": meta.get("validation", "SKIP"),
            "size_bytes": meta.get("size_bytes", 0),
            "filename": meta.get("filename", ""),
            "template_id": meta.get("template_id", tdir.name),
        })
    # 最新上传在前
    items.sort(key=lambda x: x.get("uploaded_at", ""), reverse=True)
    return items


def get_template_metadata(template_id: str) -> dict[str, Any] | None:
    """读单个 user template metadata · 缺则返 None (caller 翻 404)."""
    meta_path = template_dir(template_id) / "metadata.json"
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ───────────────────────────────────────────────────────────────────────────
# CRUD 完整 (per agent17 TODO medium-value 3 项 · 2026-05-21)
#   archive_template / rename_user_template / archive_duplicates_by_name
#   设计原则:
#     - 真删 = soft delete · 搬 .archived/{id}/ · metadata 加 archived_at + reason
#       (保 audit trail · 客户经理误删可手动 recover · 后续 GC 再考虑硬删)
#     - rename 只改 metadata.template_name + renamed_at · 不动 docx 本体 (template_id 不变 · 引用链稳定)
#     - supersede = upload 同 template_name 自动 archive 老的 (dropdown 保持干净 · UUID 仍唯一防误覆盖)
#   只允许操作 user-* template · builtin 拒 (raise PermissionError caller 翻 400)
# ───────────────────────────────────────────────────────────────────────────


def _archive_root() -> Path:
    """.archived 根目录 · lazy create."""
    return TEMPLATE_ROOT / TEMPLATE_ARCHIVE_DIRNAME


def archive_template(
    template_id: str,
    *,
    reason: str = "user_deleted",
    archived_by: str = "unknown",
) -> dict[str, Any]:
    """Soft-delete · 把 user template 搬到 .archived/{id}/ · 写 archived_at + reason 到 metadata.

    Args:
        template_id: 必须 "user-" 前缀 · builtin 拒.
        reason: "user_deleted" / "superseded_by:{new_id}" / 其他自定义.
        archived_by: 操作人 (审计 · uploader 维度).

    Returns:
        归档后 metadata dict (含 archived_at / archive_reason / archive_path).

    Raises:
        FileNotFoundError: template_id 不存在.
        PermissionError: 拒删 builtin (template_id 不以 "user-" 开头).
        OSError: 搬迁失败 (磁盘问题 caller 翻 500).
    """
    if not template_id.startswith("user-"):
        raise PermissionError(
            f"拒删 builtin template · template_id={template_id!r} · 仅 user-* 允许"
        )

    src_dir = template_dir(template_id)
    if not src_dir.exists():
        raise FileNotFoundError(
            f"template {template_id!r} 不存在 · path={src_dir}"
        )

    # 读 metadata 防丢 · 后面写归档信息
    meta_path = src_dir / "metadata.json"
    metadata: dict[str, Any] = {}
    if meta_path.exists():
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            metadata = {}

    # 准备目标 (lazy mkdir · 防 race: 同 template_id 二次归档 · 加 ts 后缀)
    archive_root = _archive_root()
    archive_root.mkdir(parents=True, exist_ok=True)
    dst_dir = archive_root / template_id
    if dst_dir.exists():
        # 极少情况 · 同 id 被搬过 · 加 ts 后缀防覆盖 audit trail
        dst_dir = archive_root / f"{template_id}__{int(datetime.now().timestamp())}"

    # 真搬 (shutil.move · cross-fs 时 copy+rm)
    shutil.move(str(src_dir), str(dst_dir))

    # 写 archived_at + reason 到新位置 metadata (audit trail)
    metadata["archived_at"] = datetime.now().isoformat(timespec="seconds")
    metadata["archive_reason"] = reason
    metadata["archived_by"] = archived_by
    metadata["archive_path"] = str(dst_dir.relative_to(TEMPLATE_ROOT))
    try:
        (dst_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        # 写归档 metadata 失败不阻塞 · 文件已搬走 caller 看到了 deleted 行为
        pass

    return metadata


def rename_user_template(
    template_id: str,
    new_name: str,
    *,
    renamed_by: str = "unknown",
) -> dict[str, Any]:
    """重命名 user template · 只改 metadata.template_name + renamed_at · 不动 docx / template_id.

    Args:
        template_id: 必须 "user-" 前缀 · builtin 拒.
        new_name: 新 template_name · 2-80 字符 · 与 upload 校验同.
        renamed_by: 操作人 (审计).

    Returns:
        更新后 metadata dict (含 template_name=new_name + renamed_at).

    Raises:
        FileNotFoundError: template_id 不存在.
        PermissionError: 拒改 builtin.
        ValueError: new_name 长度不合规.
        OSError: 写 metadata.json 失败.
    """
    if not template_id.startswith("user-"):
        raise PermissionError(
            f"拒改 builtin template · template_id={template_id!r} · 仅 user-* 允许"
        )

    name_stripped = (new_name or "").strip()
    if len(name_stripped) < 2 or len(name_stripped) > 80:
        raise ValueError(
            f"template_name 长度 2-80 字符 · 实际给了 {len(name_stripped)} 字符"
        )

    tdir = template_dir(template_id)
    meta_path = tdir / "metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError(
            f"template {template_id!r} metadata.json 不存在 · path={meta_path}"
        )

    try:
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise FileNotFoundError(
            f"template {template_id!r} metadata.json 解析失败 · {exc}"
        ) from exc

    metadata["template_name"] = name_stripped
    metadata["renamed_at"] = datetime.now().isoformat(timespec="seconds")
    metadata["renamed_by"] = renamed_by

    meta_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return metadata


def archive_duplicates_by_name(
    template_name: str,
    *,
    superseded_by: str,
    archived_by: str = "unknown",
) -> list[str]:
    """upload 同 template_name 时自动 archive 老的 · 保 dropdown 干净 (UUID 唯一仍存).

    设计 (per supersede 实施单 Step 3):
      - 新模板 upload 后 caller 调本函数 · 把所有同 template_name 的 active user 模板归档
      - reason="superseded_by:{new_template_id}" · 后续可追溯哪个 new 替换了哪个 old
      - 不影响 builtin · 只匹配 user-* · 内置 template_name 不会和 user 撞 (设计上)

    Args:
        template_name: 要去重的名字 · trim 后比较 (case-sensitive).
        superseded_by: 新模板 template_id · 写入老的 archive metadata reason.
        archived_by: 操作人 (审计).

    Returns:
        被归档的 template_id 列表 (空表示无重名 · 是首传).
    """
    name_stripped = (template_name or "").strip()
    if not name_stripped:
        return []

    archived_ids: list[str] = []
    for item in list_user_templates():
        if item.get("name", "").strip() != name_stripped:
            continue
        tid = item.get("template_id", "")
        if not tid or tid == superseded_by:
            continue  # 防自归档
        try:
            archive_template(
                tid,
                reason=f"superseded_by:{superseded_by}",
                archived_by=archived_by,
            )
            archived_ids.append(tid)
        except (FileNotFoundError, PermissionError, OSError):
            # 归档失败 silent · 不阻塞主 upload · 老的留在 dropdown 也无大碍
            continue
    return archived_ids


__all__ = [
    "BUILTIN_TEMPLATES",
    "MAX_TEMPLATE_BYTES",
    "TEMPLATE_ARCHIVE_DIRNAME",
    "TEMPLATE_ROOT",
    "archive_duplicates_by_name",
    "archive_template",
    "get_template_metadata",
    "list_user_templates",
    "make_template_id",
    "persist_template",
    "rename_user_template",
    "resolve_template_path",
    "safe_filename",
    "template_dir",
]
