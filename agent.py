# -*- coding: utf-8 -*-
"""
Agent 引擎 v7.5

v7.5 变更（双模式支持）：
★ 新增"填空模式" — 支持普惠授信申报表等结构化表格模版
★ FormFillAgent 集成 — 段落级 LLM 重写 + 复选框勾选 + 表格填充
★ process_form_fill() — 独立的填空流水线，绕过叙述模式的 tool-calling 循环
★ 模式切换 — 同一 Agent 实例支持 narrative / form_fill 双模式

v7.4 核心修复保留：
材料自动注入 · 元文本清理 · 待补充合并 · 批注合并 · 弹性字数 · 智能财务注入

v7.3 及之前功能保留：
.doc 二进制解析 / 模版热替换 / 财务附注增强 / 强制搜索+自省+质量门控+智能去重
"""

import json
import re
import time
import os
import queue
import threading
import traceback as _traceback
from typing import Generator

from llm import LLMClient
from memory import MemoryManager
from tools import get_tool_schemas, PURE_TOOL_FUNCTIONS, _smart_truncate
from prompts import (
    AGENT_SYSTEM_PROMPT,
    CHAPTER_PROMPTS, REVIEW_PROMPT, REVISE_PROMPT,
    FINANCIAL_EXTRACT_PROMPT, FILE_CLASSIFY_PROMPT,
    MATERIAL_AUDIT_PROMPT, SELF_REFLECT_PROMPT,
)
from config import MAX_AGENT_STEPS, SEARCH_ENABLED, SELF_REFLECT_ENABLED


class CreditReportAgent:
    """信贷报告 Agent v7.5 — 支持叙述报告模式 + 填空申报表模式"""

    VERSION = "v7.5"

    def __init__(self, api_key: str, provider: str = "deepseek"):
        self.llm = LLMClient(provider=provider, api_key=api_key)
        self.memory = MemoryManager()
        self.tool_schemas = get_tool_schemas()


        # 运行状态
        self.session_id = f"session_{int(time.time())}"
        self.step_count = 0
        self.is_waiting_for_user = False
        self.pending_question = ""

        # 持久化工作状态
        self.uploaded_files: list[str] = []
        self.file_contents: dict[str, str] = {}
        self.classified: dict[str, list] = {}
        self.chapters: dict[str, str] = {}
        self.fin_extracted: str = ""
        self.audit_result: str = ""
        self.files_read: bool = False
        self.files_classified: bool = False
        self.materials_audited: bool = False
        self.financial_extracted: bool = False
        self.report_reviewed: bool = False
        self.report_exported: bool = False
        self.last_export_error: str | None = None

        # ★ v7.5: 填空模式
        self.mode: str = "narrative"  # "narrative" | "form_fill"
        self.form_template_path: str = ""  # 填空模版路径
        self.form_output_dir: str = ""  # 可选：填空输出目录
        self.form_fill_done: bool = False
        self.form_fill_output: str = ""    # 填空结果文件路径

        # ★ v5: 模版支持
        self.template_path: str = ""
        self.template_structure: str = ""
        # ★ v7: 模版全文
        self.template_full_text: str = ""

        # ★ v7: 搜索结果缓存
        self.search_results: dict[str, str] = {}  # query → result
        self.search_done: bool = False

        # ★ v7: 自省状态
        self.self_reflected: bool = False

    # ====== 模版支持 ======

    def set_template(self, path: str):
        """设置报告模版"""
        self.template_path = path
        from word_export import parse_template_structure, parse_template_full_text
        self.template_structure = parse_template_structure(path)
        # ★ v7: 提取模版全文
        self.template_full_text = parse_template_full_text(path)

    def _get_template_chapter(self, ch_num: int) -> str:
        """★ v7.2: 从模版全文中提取第ch_num章内容"""
        if not self.template_full_text:
            return ""
        ch_markers = [
            ("一、授信客户背景", 1),
            ("二、经营", 2),
            ("三、财务", 3),
            ("四、结论", 4), ("四、授信方案", 4),
        ]
        text = self.template_full_text
        positions = []
        for marker, num in ch_markers:
            idx = text.find(marker)
            if idx >= 0:
                positions.append((idx, num))
        positions.sort()
        for i, (pos, num) in enumerate(positions):
            if num == ch_num:
                start = pos
                end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
                chunk = text[start:end].strip()
                return _smart_truncate(chunk, 5000)
        return ""

    def _parse_template(self) -> str:
        """返回模版描述（注入到 prompt）— v7 增加全文参考"""
        parts = []
        if self.template_structure:
            parts.append(
                "\n\n## 用户指定了报告模版\n"
                f"模版标题结构如下，请尽量按此结构组织章节内容：\n{self.template_structure}\n"
            )
        if self.template_full_text:
            # ★ v7: 注入模版全文（截断到合理长度），让 Agent 参考分析深度
            truncated = self.template_full_text[:8000]
            if len(self.template_full_text) > 8000:
                truncated += f"\n... (模版全文共 {len(self.template_full_text)} 字，已截取前8000字)"
            parts.append(
                "\n## ★ 模版报告参考正文（重要！请借鉴分析深度和写法）\n"
                "以下是一份真实的授信调查报告模版的正文内容。"
                "请特别注意它的分析深度——比如上下游分析如何逐一列出供应商名称和金额，"
                "财务分析如何逐科目引用数字做跨年对比。你的报告要达到同等深度。\n\n"
                f"{truncated}\n"
            )
        return "".join(parts)

    # ====== v7.4: 材料自动注入 ======

    def _build_materials_text(self, max_chars: int = 60000,
                              categories: str | None = None) -> str:
        """★ v7.4 核心修复：从 self.file_contents 自动构建材料文本。

        不再依赖 LLM 传 materials 参数 — LLM 无法在工具调用中传递 100K+ 文本。
        categories: 可选，"financial" 只取财务类文件，None 取全部。
        """
        if not self.file_contents:
            return ""

        parts = []
        for fname, content in self.file_contents.items():
            content_stripped = content.strip()
            if not content_stripped:
                continue

            # 按类别过滤（如果有分类结果）
            if categories == "financial" and self.classified:
                # B=财务报表, C=附注/审计 → 只取这两类
                b_indices = self.classified.get("B", [])
                c_indices = self.classified.get("C", [])
                fin_indices = set(b_indices + c_indices)
                file_list = list(self.file_contents.keys())
                try:
                    idx = file_list.index(fname)
                    if idx not in fin_indices:
                        continue
                except ValueError:
                    pass

            parts.append(f"===== {fname} =====\n{content_stripped}")

        if not parts:
            # 类别过滤后为空 → 回退到全部材料
            parts = [
                f"===== {fn} =====\n{ct.strip()}"
                for fn, ct in self.file_contents.items() if ct.strip()
            ]

        full_text = "\n\n".join(parts)
        return _smart_truncate(full_text, max_chars)

    def _is_extraction_failure(self, text: str) -> bool:
        """★ v7.4: 检测财务提取是否失败（返回的是空结果/失败消息）"""
        if not text or len(text) < 100:
            return True
        fail_indicators = [
            "未能提取到任何", "未能提取", "无法提取",
            "材料内容为空白", "没有找到任何财务数据",
            "所有材料中均未找到", "未包含任何实质性",
        ]
        # 如果前200字中包含失败标志
        head = text[:200]
        return any(ind in head for ind in fail_indicators)

    @staticmethod
    def _clean_meta_text(text: str) -> str:
        """★ v7.4: 清理 LLM 输出中泄露的中间步骤元文本。

        这些是 extract_financial_data / audit_materials 的输出格式，
        不应该出现在最终报告正文中。
        """
        import re as _re

        # 匹配整段元文本块（从标志行到下一个空行或章节标题）
        meta_block_patterns = [
            # "提取总结：..." 整块
            r'提取总结[：:][^\n]*(?:\n(?![\n（(一二三四五六七八九十]).*)*',
            # "缺失材料清单" 整块
            r'【?缺失材料清单】?[：:]?[^\n]*(?:\n(?![\n（(一二三四五六七八九十]).*)*',
            # "重要表格数据摘要" 整块
            r'【?重要表格数据摘要】?[：:]?[^\n]*(?:\n(?![\n（(一二三四五六七八九十]).*)*',
            # "材料盘点" 整块
            r'【?材料盘点】?[：:]?[^\n]*(?:\n(?![\n（(一二三四五六七八九十]).*)*',
            # "公司基本信息\n公司全称：" 类的列表输出
            r'(?:^|\n)公司基本信息\s*\n(?:[^\n]*[：:][^\n]*\n?)*',
            r'(?:^|\n)经营信息\s*\n(?:[^\n]*[：:][^\n]*\n?)*',
            r'(?:^|\n)财务信息\s*\n(?:[^\n]*[：:][^\n]*\n?)*',
            r'(?:^|\n)授信相关\s*\n(?:[^\n]*[：:][^\n]*\n?)*',
        ]

        cleaned = text
        for pat in meta_block_patterns:
            cleaned = _re.sub(pat, '', cleaned)

        # 单行元文本（"由于您提供的材料..." / "材料列表中并未..."）
        meta_line_patterns = [
            r'^(?:由于您提供的|材料列表中|上述材料中|本次任务未能|以下是从材料中).*$',
            r'^(?:根据您提供的材料列表|从提供的材料来看).*(?:为空白|无法|未能).*$',
        ]
        for pat in meta_line_patterns:
            cleaned = _re.sub(pat, '', cleaned, flags=_re.MULTILINE)

        # 清理多余空行
        cleaned = _re.sub(r'\n{3,}', '\n\n', cleaned)
        return cleaned.strip()

    @staticmethod
    def _consolidate_pending(text: str) -> str:
        """★ v7.4: 合并连续的"（待补充）"行。

        3行以上连续的 待补充/未提供 → 合并为1行"（以上信息待补充相关材料后完善）"
        """
        import re as _re
        lines = text.split('\n')
        result = []
        pending_count = 0
        pending_subjects = []

        def _flush_pending():
            nonlocal pending_count, pending_subjects
            if pending_count >= 3:
                # 合并为1行
                result.append("（以上信息待补充相关材料后完善）")
            elif pending_count > 0:
                # 少于3行保留原样
                for _ in range(pending_count):
                    result.append("（待补充）")
            pending_count = 0
            pending_subjects = []

        pending_re = _re.compile(
            r'^\s*[（(]?待补充[)）]?\s*$|'
            r'^\s*.{0,15}(?:未提供|未涉及|数据缺失|信息缺失|无法分析|无法计算)\s*$'
        )

        for line in lines:
            if pending_re.match(line.strip()) if line.strip() else False:
                pending_count += 1
            else:
                _flush_pending()
                result.append(line)

        _flush_pending()
        return '\n'.join(result)

    # ====== 防重复 ======

    def _should_skip_tool(self, tool_name: str, args: dict) -> str | None:
        if tool_name == "read_files" and self.files_read:
            return "[已完成] 文件已读取，内容在缓存中。"
        if tool_name == "classify_documents" and self.files_classified:
            return f"[已完成] 文件已分类: {json.dumps(self.classified, ensure_ascii=False)}"
        if tool_name == "audit_materials" and self.materials_audited:
            return f"[已完成] 材料已盘点。\n{self.audit_result[:500]}"
        if tool_name == "extract_financial_data" and self.financial_extracted:
            return f"[已完成] 财务已提取。\n{self.fin_extracted[:500]}"
        if tool_name == "export_to_word" and self.report_exported:
            return "[已完成] 报告已导出 Word。"
        return None

    # ====== 自动导出 ======

    def _all_chapters_ready(self) -> bool:
        return all(f"ch{i}" in self.chapters and self.chapters[f"ch{i}"]
                   for i in range(1, 5))

    def _auto_export(self) -> str | None:
        self.last_export_error = None
        if self.report_exported:
            return None
        if not self._all_chapters_ready():
            return None
        try:
            if self.template_path:
                from word_export import make_word_from_template
                path = make_word_from_template(
                    self.template_path, self.chapters,
                    client_name=self._guess_client_name(),
                )
            else:
                from word_export import make_word_report
                path = make_word_report(
                    self._guess_client_name(), "", "", "", "", "",
                    self.chapters,
                )
            self.report_exported = True
            return path
        except Exception as e:
            self.last_export_error = str(e)
            return None

    def _guess_client_name(self) -> str:
        ch1 = self.chapters.get("ch1", "")
        m = re.search(
            r'借款人[是为]?\s*"?'
            r'([^，。,\n"]+?'
            r'(?:有限公司|股份公司|集团有限公司|有限责任公司|研究院|设计院|银行|企业))',
            ch1,
        )
        if m:
            return m.group(1).strip()
        m = re.search(r'借款人[是为]?"?([^，。,\n"]{2,20})', ch1)
        if m:
            return m.group(1).strip()
        for fname in self.uploaded_files:
            base = os.path.basename(fname).rsplit(".", 1)[0]
            if len(base) >= 2:
                return base[:20]
        return "客户"

    # ====== 鲁棒导出 ======

    def _tool_export_robust(self, args: dict) -> str:
        client_name = args.get("client_name", "")
        chapters = args.get("chapters", None)

        if isinstance(chapters, dict):
            valid = any(len(v) > 100 for v in chapters.values() if isinstance(v, str))
            if not valid:
                chapters = None
        if not chapters:
            chapters = self.chapters

        if not any(chapters.get(f"ch{i}") for i in range(1, 5)):
            return "[错误] 没有已写好的章节内容，请先用 write_chapter 或 write_all_chapters 撰写。"

        credit_amount = args.get("credit_amount", "")
        industry = args.get("industry", "")
        pd_rating = args.get("pd_rating", "")
        apply_unit = args.get("apply_unit", "")
        credit_type = args.get("credit_type", "")

        try:
            if self.template_path:
                from word_export import make_word_from_template
                path = make_word_from_template(
                    self.template_path, chapters,
                    client_name=client_name or self._guess_client_name(),
                )
            else:
                from word_export import make_word_report
                path = make_word_report(
                    client_name or self._guess_client_name(),
                    credit_amount, industry, pd_rating,
                    apply_unit, credit_type, chapters,
                )
            self.report_exported = True
            return path
        except Exception as e:
            return f"[导出失败] {e}"

    # ====== 工作状态 ======

    def _build_work_state_summary(self) -> str:
        lines = []
        if self.uploaded_files:
            fnames = [f.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] for f in self.uploaded_files]
            lines.append(f"📁 文件({len(self.uploaded_files)}): {', '.join(fnames)}")
        if self.files_read:
            lines.append("✅ read_files 完成")
        if self.files_classified:
            lines.append("✅ classify_documents 完成")
        if self.materials_audited:
            lines.append("✅ audit_materials 完成")
        if self.financial_extracted:
            lines.append("✅ extract_financial_data 完成")
        # ★ v7: 搜索状态
        if self.search_results:
            lines.append(f"✅ search_web 完成（{len(self.search_results)}次搜索）")
        ch_status = []
        for i in range(1, 5):
            key = f"ch{i}"
            if key in self.chapters and self.chapters[key]:
                ch_status.append(f"第{i}章 ✅ ({len(self.chapters[key])}字)")
            else:
                ch_status.append(f"第{i}章 ❌")
        if any(k in self.chapters for k in ["ch1", "ch2", "ch3", "ch4"]):
            lines.append(f"📝 {' | '.join(ch_status)}")
        # ★ v7: 自省状态
        if self.self_reflected:
            lines.append("✅ self_reflect 完成")
        if self.report_reviewed:
            lines.append("✅ review_report 完成")
        if self.report_exported:
            lines.append("✅ 已导出 Word")
        if self.template_path:
            lines.append(f"📋 模版已加载: {os.path.basename(self.template_path)}")
        next_step = self._suggest_next_step()
        if next_step:
            lines.append(f"🎯 下一步: {next_step}")
        return "\n".join(lines) if lines else ""

    def _suggest_next_step(self) -> str:
        if not self.files_read and self.uploaded_files:
            return "read_files"
        if self.files_read and not self.materials_audited:
            return "audit_materials + extract_financial_data"
        if self.materials_audited and not self.search_results and SEARCH_ENABLED:
            return "search_web（搜索行业信息）"
        for i in range(1, 5):
            if f"ch{i}" not in self.chapters:
                return f"write_all_chapters（或 write_chapter 第{i}章）"
        if self._all_chapters_ready() and not self.self_reflected and SELF_REFLECT_ENABLED:
            return "self_reflect（审视报告质量）"
        if self._all_chapters_ready() and not self.report_exported:
            return "export_to_word（或系统自动导出）"
        return ""

    # ====== v7.5: 填空模式流水线 ======

    def process_form_fill(self, user_message: str, uploaded_files: list[str] | None = None
                          ) -> Generator[dict, None, None]:
        """★ v7.5: 填空申报表模式 — 绕过 tool-calling 循环，直接用 FormFillAgent"""
        from form_filler import FormFillAgent
        from tools import tool_read_files, _expand_paths

        # 1. 注册上传文件
        if uploaded_files:
            for fp in uploaded_files:
                if fp not in self.uploaded_files:
                    self.uploaded_files.append(fp)

        # 1b. ★ v7.10: 检测用户消息中的本地文件夹路径，自动添加
        if user_message:
            import re as _re
            # Match Windows paths like D:\xxx\xxx or C:/xxx/xxx
            path_matches = _re.findall(
                r'[A-Za-z]:[\\\/][\w\u4e00-\u9fff .\\\/\-（）()]+', user_message)
            for pm in path_matches:
                pm = pm.strip().rstrip('\\/')
                if os.path.isdir(pm) and pm not in self.uploaded_files:
                    self.uploaded_files.append(pm)
                    yield {"type": "thinking",
                           "content": f"检测到本地文件夹: {pm}，将递归扫描其中的文件"}
                elif os.path.isfile(pm) and pm not in self.uploaded_files:
                    self.uploaded_files.append(pm)

        # 2. 检查前置条件
        if not self.form_template_path:
            yield {"type": "message", "content": "⚠️ 请先在左侧上传填空模版文件（.docx）。"}
            yield {"type": "done", "content": "缺少模版"}
            return

        if not self.uploaded_files:
            yield {"type": "message", "content": "⚠️ 请上传企业材料文件（PDF/Word/Excel）。"}
            yield {"type": "done", "content": "缺少材料"}
            return

        yield {"type": "thinking", "content": "填空模式启动..."}

        # 3. 读取材料文件（排除模版本身）
        material_files = [f for f in self.uploaded_files
                          if os.path.abspath(f) != os.path.abspath(self.form_template_path)]
        if not material_files:
            yield {"type": "message", "content": "⚠️ 请上传企业材料文件（不含模版）。"}
            yield {"type": "done", "content": "缺少材料"}
            return

        # Build a stable map: display_name -> full path
        # Used by truth-first deterministic extractors (Excel/PDF parsing),
        # so we don't have to rely on LLM for numeric facts.
        expanded_paths = _expand_paths(material_files)
        file_path_map: dict[str, str] = {}
        for fp in expanded_paths:
            try:
                fname = os.path.basename(fp)
                parent = os.path.basename(os.path.dirname(fp))
                display_name = f"{parent}/{fname}" if parent else fname
                file_path_map[display_name] = fp
            except Exception:
                continue
        self._file_path_map = file_path_map

        if not self.file_contents:
            yield {"type": "tool_call", "name": "read_files", "status": "running",
                   "args_preview": f"{len(material_files)} 个文件"}
            try:
                raw = tool_read_files(material_files)
                # 解析到 file_contents
                for section in raw.split("===== "):
                    if section.strip():
                        parts = section.split(" =====\n", 1)
                        if len(parts) == 2:
                            k = parts[0].strip()
                            # tool_read_files header includes " (xxxx字)" — strip to keep keys stable
                            k = re.sub(r"\s*\(\d+字\)\s*$", "", k)
                            self.file_contents[k] = parts[1]
                self.files_read = True
                yield {"type": "tool_result", "name": "read_files",
                       "result": f"已读取 {len(self.file_contents)} 个文件"}
            except Exception as e:
                yield {"type": "message", "content": f"❌ 文件读取失败: {e}"}
                yield {"type": "done", "content": "读取失败"}
                return
        else:
            yield {"type": "tool_call", "name": "read_files", "status": "skipped"}
            yield {"type": "tool_result", "name": "read_files", "result": "已缓存"}

        # 4. 构建 LLM 调用函数
        def llm_caller(system_prompt: str, user_prompt: str) -> str:
            return self.llm.simple_chat(system_prompt, user_prompt)

        # 5. 准备输出路径
        tpl_base = os.path.splitext(os.path.basename(self.form_template_path))[0]
        output_dir = (self.form_output_dir or "").strip() or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "outputs"
        )
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{tpl_base}_filled_{int(time.time())}.docx")

        # 6. 运行 FormFillAgent（★ v7.14 进度通过 Queue 实时流式推送到 yield）
        progress_q: queue.Queue = queue.Queue()
        result_holder = {}  # {"path": ..., "agent": ...} or {"error": ..., "tb": ...}

        def progress_cb(msg: str):
            progress_q.put(("progress", msg))

        def _run_fill():
            try:
                _agent = FormFillAgent(
                    llm_caller,
                    self.file_contents,
                    file_path_map=getattr(self, "_file_path_map", {}) or file_path_map,
                )
                _path = _agent.run(self.form_template_path, output_path, progress_cb)
                result_holder["path"] = _path
                result_holder["agent"] = _agent
            except Exception as _e:
                result_holder["error"] = _e
                result_holder["tb"] = _traceback.format_exc()
            finally:
                progress_q.put(("done", None))

        yield {"type": "thinking", "content": f"开始填写 {len(self.file_contents)} 份材料 → 模版"}
        yield {"type": "tool_call", "name": "form_fill", "status": "running",
               "args_preview": "字段提取 + 复选框 + 表格 + 示例段落"}

        t = threading.Thread(target=_run_fill, daemon=True)
        t.start()

        # 实时消费进度队列
        while True:
            try:
                kind, msg = progress_q.get(timeout=60)
            except queue.Empty:
                yield {"type": "tool_result", "name": "form_fill",
                       "result": "⚠️ 等待填写进度超时（60秒），仍在运行..."}
                continue
            if kind == "done":
                break
            yield {"type": "tool_result", "name": "form_fill", "result": msg}

        t.join(timeout=10)  # 确保线程已退出

        if "error" in result_holder:
            tb = result_holder.get("tb", "No traceback available")
            e = result_holder.get("error", "Unknown error")
            yield {"type": "message",
                   "content": f"❌ 填空处理出错: {e}\n\n```\n{tb}\n```"}
        elif "path" not in result_holder:
            yield {"type": "message",
                   "content": "❌ 填空处理异常结束：未返回结果文件。请重试。"}
        else:
            result_path = result_holder["path"]
            filler_agent = result_holder["agent"]
            self.form_fill_output = result_path
            self.form_pending_tags = getattr(filler_agent, 'pending_tags', [])
            validation_blocked = bool(getattr(filler_agent, '_validation_blocked', False))
            validation_blockers = list(getattr(filler_agent, '_validation_blockers', []) or [])
            self.form_fill_done = not validation_blocked

            stats = filler_agent.stats
            summary = f"\u2705 \u5df2\u586b\u5145{stats['filled']}/{stats['total_sections']} \u4e2a\u533a\u5757"
            if stats["errors"]:
                summary += f"\n\u26a0\ufe0f {len(stats['errors'])} \u5904\u586b\u5145\u5931\u8d25"
            if validation_blocked:
                summary = f"\u26d4 \u8f93\u51fa\u5df2\u88ab\u963b\u65ad\uff0c\u5171 {len(validation_blockers)} \u4e2a\u95ee\u9898"
                for item in validation_blockers[:5]:
                    summary += f"\n- {item.get('code')}: {item.get('message')}"
            if self.form_pending_tags:
                by_cat: dict = {}
                for tg in self.form_pending_tags:
                    cat = tg.get("category", "\u5f85\u4eba\u5de5\u5904\u7406")
                    by_cat.setdefault(cat, []).append(tg)
                tag_lines = [f"\n\n\u26a0\ufe0f **{len(self.form_pending_tags)} \u5904\u5185\u5bb9\u5df2\u6dfb\u52a0\u4fa7\u680f\u6807\u7b7e**"]
                for cat, ct in sorted(by_cat.items()):
                    tag_lines.append(f"\n**{cat}** ({len(ct)}\u9879)")
                    for tg in ct[:5]:
                        tag_lines.append(f"- {tg['label'][:40]}")
                    if len(ct) > 5:
                        tag_lines.append(f"- *...\u5171{len(ct)-5}\u9879*")
                summary += "".join(tag_lines)

            if not validation_blocked:
                yield {"type": "file", "path": result_path}
            else:
                yield {"type": "validation_blocked", "path": result_path, "blockers": validation_blockers}
            yield {"type": "message", "content": summary}
            if self.form_pending_tags:
                yield {"type": "pending_tags", "tags": self.form_pending_tags}

        yield {"type": "done", "content": "填空完成"}

    # ====== 主循环 ======

    def process_message(self, user_message: str, uploaded_files: list[str] | None = None
                        ) -> Generator[dict, None, None]:
        # ★ v7.5: 填空模式路由
        if self.mode == "form_fill":
            yield from self.process_form_fill(user_message, uploaded_files)
            return
        conv = self.memory.get_conversation(self.session_id)
        conv.add_message("user", user_message)

        if uploaded_files:
            for fp in uploaded_files:
                if fp not in self.uploaded_files:
                    self.uploaded_files.append(fp)
            conv.set_context("uploaded_files", self.uploaded_files)

        if self.is_waiting_for_user:
            self.is_waiting_for_user = False
            self.pending_question = ""

        memory_context = self.memory.build_context_prompt(self.session_id)
        work_state = self._build_work_state_summary()
        template_info = self._parse_template()

        extra_context = ""
        if memory_context:
            extra_context += f"\n## 历史记忆\n{memory_context}"
        if work_state:
            extra_context += f"\n## 当前工作状态\n{work_state}"
        if template_info:
            extra_context += template_info

        # ★ v7: 搜索结果摘要注入
        if self.search_results:
            search_summary = "\n\n## 网络搜索结果\n"
            for query, result in self.search_results.items():
                search_summary += f"\n搜索「{query}」:\n{result[:1500]}\n"
            extra_context += search_summary

        system_prompt = AGENT_SYSTEM_PROMPT.format(memory_context=extra_context)

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conv.get_messages_for_llm())

        if self.uploaded_files:
            file_names = [f.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] for f in self.uploaded_files]
            files_msg = (
                f"[系统] 已上传 {len(self.uploaded_files)} 个文件: {', '.join(file_names)}\n"
                f"路径: {json.dumps(self.uploaded_files, ensure_ascii=False)}\n"
            )
            if self.files_read:
                files_msg += "★ 已读取，不要再调 read_files。"
            else:
                files_msg += "请先 read_files。"
            messages.append({"role": "system", "content": files_msg})

        if self.chapters:
            ch_summary = "\n\n".join(
                f"【第{k.replace('ch','')}章 ({len(v)}字)】\n{v[:300]}..."
                for k, v in sorted(self.chapters.items())
            )
            messages.append({
                "role": "system",
                "content": f"[系统] 已有章节（不要重写）：\n{ch_summary}"
            })

        effective_max_steps = MAX_AGENT_STEPS  # ★ v7: 用 config 中的值（18）

        for step in range(effective_max_steps):
            self.step_count += 1
            yield {"type": "thinking", "content": f"步骤 {step + 1}/{effective_max_steps}"}

            try:
                response = self.llm.chat(messages, tools=self.tool_schemas)
            except Exception as e:
                yield {"type": "message", "content": f"模型调用出错: {e}"}
                yield {"type": "done", "content": "错误终止"}
                return

            if not response["tool_calls"]:
                text = response["content"] or ""
                conv.add_message("assistant", text)
                yield {"type": "message", "content": text}

                export_path = self._auto_export()
                if export_path:
                    yield {"type": "file", "path": export_path}
                elif self.last_export_error:
                    yield {"type": "export_error", "content": self.last_export_error}

                yield {"type": "done", "content": "回合结束"}
                return

            assistant_msg = {"role": "assistant", "content": response["content"]}
            assistant_msg["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": json.dumps(tc["arguments"], ensure_ascii=False),
                    },
                }
                for tc in response["tool_calls"]
            ]
            messages.append(assistant_msg)

            for tc in response["tool_calls"]:
                tool_name = tc["name"]
                tool_args = tc["arguments"]
                tool_id = tc["id"]

                cached = self._should_skip_tool(tool_name, tool_args)
                if cached:
                    yield {"type": "tool_call", "name": tool_name, "status": "skipped"}
                    yield {"type": "tool_result", "name": tool_name, "result": cached}
                    messages.append({
                        "role": "tool", "tool_call_id": tool_id,
                        "content": cached,
                    })
                    continue

                yield {"type": "tool_call", "name": tool_name, "status": "running",
                       "args_preview": _preview_args(tool_args)}

                try:
                    result = self._execute_tool(tool_name, tool_args)
                except Exception as e:
                    result = f"[工具错误] {tool_name}: {e}"

                self._update_work_state(tool_name, tool_args, result)

                if tool_name == "ask_user":
                    self.is_waiting_for_user = True
                    self.pending_question = tool_args.get("question", "")
                    yield {"type": "message", "content": self.pending_question}
                    messages.append({
                        "role": "tool", "tool_call_id": tool_id,
                        "content": "[等待用户回答]",
                    })
                    yield {"type": "done", "content": "等待用户"}
                    return

                if tool_name == "export_to_word" and result and not result.startswith("["):
                    yield {"type": "file", "path": result}

                yield {"type": "tool_result", "name": tool_name,
                       "result": result[:500] if len(result) > 500 else result}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": _smart_truncate(result, 12000),
                })

                # ★ v7: write 完成后，先自省再导出
                if tool_name in ("write_chapter", "write_all_chapters"):
                    if self._all_chapters_ready():
                        # ★ v7: 自动自省
                        if SELF_REFLECT_ENABLED and not self.self_reflected:
                            yield {"type": "thinking", "content": "自动自省检查中..."}
                            self._auto_self_reflect()
                            self.self_reflected = True
                            yield {"type": "tool_result", "name": "self_reflect",
                                   "result": "自省检查并修正完成"}

                        # 自动导出
                        export_path = self._auto_export()
                        if export_path:
                            yield {"type": "file", "path": export_path}
                        elif self.last_export_error:
                            yield {"type": "export_error", "content": self.last_export_error}

        # 步数上限
        state_msg = self._build_work_state_summary()
        yield {"type": "message",
               "content": f"本轮已达步数上限。\n{state_msg}\n\n发'继续'让我接着做。"}

        export_path = self._auto_export()
        if export_path:
            yield {"type": "file", "path": export_path}
        elif self.last_export_error:
            yield {"type": "export_error", "content": self.last_export_error}

        yield {"type": "done", "content": "步数上限"}

    # ====== v7: 自动自省 ======

    def _auto_self_reflect(self):
        """写完4章后，自动用 LLM 自省每一章，修正遗漏"""
        for ch_num in range(1, 5):
            ch_key = f"ch{ch_num}"
            content = self.chapters.get(ch_key, "")
            if not content or len(content) < 100:
                continue

            # 构建自省上下文：原材料摘要 + 当前章节
            context_parts = []
            if self.fin_extracted and ch_num in (2, 3, 4):
                context_parts.append(f"【财务数据摘要】\n{self.fin_extracted[:3000]}")
            if self.audit_result:
                context_parts.append(f"【材料盘点结果】\n{self.audit_result[:2000]}")

            user_msg = ""
            if context_parts:
                user_msg += "\n".join(context_parts) + "\n\n"
            user_msg += f"【第{ch_num}章当前内容】\n{content}"

            try:
                revised = self.llm.simple_chat(SELF_REFLECT_PROMPT, user_msg)
                # 只有修正后内容不短于原文80%才替换（防止自省截断）
                if revised and len(revised) >= len(content) * 0.8:
                    self.chapters[ch_key] = revised
            except Exception:
                pass  # 自省失败不影响主流程

    # ====== 状态更新 ======

    def _update_work_state(self, tool_name: str, args: dict, result: str):
        if tool_name == "read_files":
            self.files_read = True
            if result and not result.startswith("["):
                for section in result.split("===== "):
                    if section.strip():
                        parts = section.split(" =====\n", 1)
                        if len(parts) == 2:
                            fname = parts[0].strip()
                            self.file_contents[fname] = parts[1]
        elif tool_name == "classify_documents":
            self.files_classified = True
        elif tool_name == "audit_materials":
            self.materials_audited = True
        elif tool_name == "extract_financial_data":
            self.financial_extracted = True
        elif tool_name == "review_report":
            self.report_reviewed = True
        elif tool_name == "export_to_word":
            if result and not result.startswith("["):
                self.report_exported = True
        # ★ v7: 搜索状态
        elif tool_name == "search_web":
            query = args.get("query", "")
            if query and result and not result.startswith("[搜索失败]"):
                self.search_results[query] = result
                self.search_done = True
        elif tool_name == "self_reflect":
            self.self_reflected = True

    # ====== 工具执行 ======

    def _execute_tool(self, name: str, args: dict) -> str:
        if name == "read_files":
            return PURE_TOOL_FUNCTIONS["read_files"](args.get("file_paths", []))

        if name == "export_to_word":
            return self._tool_export_robust(args)

        if name == "write_all_chapters":
            return self._tool_write_all_chapters(args)

        # ★ v7: 网络搜索
        if name == "search_web":
            return self._tool_search_web(args)

        # ★ v7: 自省（手动调用版）
        if name == "self_reflect":
            return self._tool_self_reflect(args)

        if name == "classify_documents":
            return self._tool_classify(args)
        elif name == "extract_financial_data":
            return self._tool_extract_financial(args)
        elif name == "audit_materials":
            return self._tool_audit(args)
        elif name == "write_chapter":
            return self._tool_write_chapter(args)
        elif name == "review_report":
            return self._tool_review(args)
        elif name == "revise_chapter":
            return self._tool_revise(args)
        elif name == "recall_memory":
            return self._tool_recall_memory(args)
        elif name == "save_lesson":
            return self._tool_save_lesson(args)
        elif name == "ask_user":
            return args.get("question", "")
        return f"[未知工具: {name}]"

    # ====== v7: 网络搜索工具 ======

    def _tool_search_web(self, args: dict) -> str:
        query = args.get("query", "")
        max_results = args.get("max_results", 5)
        if not query:
            return "[搜索失败] 未提供搜索关键词"

        # 检查缓存
        if query in self.search_results:
            return f"[缓存] {self.search_results[query]}"

        result = PURE_TOOL_FUNCTIONS["search_web"](query, max_results)
        if result and not result.startswith("[搜索失败]"):
            self.search_results[query] = result
        return result

    # ====== v7: 自省工具（手动调用版） ======

    def _tool_self_reflect(self, args: dict) -> str:
        focus = args.get("focus", "")
        if not self._all_chapters_ready():
            return "[自省跳过] 还没有写完全部4章。请先 write_all_chapters。"

        self._auto_self_reflect()
        self.self_reflected = True

        summary = []
        for i in range(1, 5):
            ch_len = len(self.chapters.get(f"ch{i}", ""))
            summary.append(f"第{i}章: {ch_len}字")

        return f"自省检查完成，已自动修正遗漏。\n当前各章字数: {' | '.join(summary)}"

    # ====== write_all_chapters ======

    def _force_search_if_needed(self) -> list[str]:
        """★ v7.1: 在写作前强制执行搜索（不依赖 LLM 决策）"""
        if not SEARCH_ENABLED or self.search_done:
            return []

        search_log = []
        # 从已有文件内容推断客户名和行业
        client_name = self._guess_client_name()
        industry_keywords = []

        # 从 audit_result / file_contents 中提取行业关键词
        all_text = (self.audit_result or "") + " " + " ".join(self.file_contents.values())[:5000]
        # 尝试提取行业
        import re as _re
        for pat in [
            r'(?:所属|属于|从事).*?行业[为是：:\s]*([\u4e00-\u9fff]+(?:业|服务|工程))',
            r'(?:主营|经营).*?(?:范围|业务)[包括为是：:\s]*([\u4e00-\u9fff]{4,20})',
        ]:
            m = _re.search(pat, all_text)
            if m:
                industry_keywords.append(m.group(1))
                break

        # 构建搜索查询
        queries = []
        if client_name:
            queries.append(f"{client_name} 企业信息 经营情况")
        if industry_keywords:
            queries.append(f"{industry_keywords[0]} 行业发展趋势 2024 2025")
        elif client_name:
            queries.append(f"{client_name} 行业分析 市场前景")

        if not queries:
            queries = ["环保行业 市场分析 发展趋势 2025"]

        for query in queries[:2]:  # 最多搜索2次
            if query in self.search_results:
                continue
            try:
                result = PURE_TOOL_FUNCTIONS["search_web"](query, 5)
                if result and not result.startswith("[搜索失败]"):
                    self.search_results[query] = result
                    search_log.append(f"🔍 搜索「{query}」✅")
                else:
                    search_log.append(f"🔍 搜索「{query}」⚠️ 无结果")
            except Exception as e:
                search_log.append(f"🔍 搜索「{query}」❌ {e}")

        self.search_done = True
        return search_log

    def _tool_write_all_chapters(self, args: dict) -> str:
        basic_info = args.get("basic_info", "")
        materials = args.get("materials", "")
        special = args.get("special_instructions", "")

        # ★★★ v7.4 核心修复 ★★★
        # v7.3 致命 bug：LLM 在调用 write_all_chapters 时无法通过 args["materials"]
        # 传递 100K+ 字符的材料全文。LLM 往往只传文件名或简短摘要，
        # 导致章节生成 LLM 看不到任何实际数据 → 全篇"待补充"。
        # 修复：自动从 self.file_contents 构建材料文本
        if len(materials.strip()) < 500 and self.file_contents:
            materials = self._build_materials_text(max_chars=60000)

        # ★ v7.1: 写作前强制搜索
        search_log = self._force_search_if_needed()

        results = []
        if search_log:
            results.extend(search_log)

        prev_text = ""

        for ch_num in range(1, 5):
            ch_key = f"ch{ch_num}"
            if ch_key in self.chapters and len(self.chapters[ch_key]) > 200:
                results.append(f"第{ch_num}章: 已有({len(self.chapters[ch_key])}字)，跳过")
                prev_text += f"\n{self.chapters[ch_key][:500]}"
                continue

            prompt = CHAPTER_PROMPTS.get(ch_num, CHAPTER_PROMPTS[1])
            user_msg = f"【基础信息】\n{basic_info}\n"

            # ★ v7.4: 按章节智能选取材料
            if materials:
                if ch_num == 3:
                    # ch3 财务分析 → 优先注入财务类材料
                    fin_mat = self._build_materials_text(max_chars=50000,
                                                        categories="financial")
                    if len(fin_mat) > 500:
                        user_msg += f"\n【参考材料（财务相关）】\n{fin_mat}\n"
                    else:
                        user_msg += f"\n【参考材料】\n{_smart_truncate(materials, 50000)}\n"
                elif ch_num == 2:
                    user_msg += f"\n【参考材料】\n{_smart_truncate(materials, 50000)}\n"
                else:
                    user_msg += f"\n【参考材料】\n{_smart_truncate(materials, 20000)}\n"

            if prev_text:
                user_msg += f"\n【已生成内容】\n{_smart_truncate(prev_text, 8000)}\n"
            if special:
                user_msg += f"\n【特殊要求】\n{special}\n"

            # ★ v7.4: 智能财务注入 — 仅当提取成功时才注入结构化数据
            if self.fin_extracted and ch_num in (2, 3):
                if not self._is_extraction_failure(self.fin_extracted):
                    user_msg += f"\n【结构化财务数据】\n{self.fin_extracted}\n"
                # 如果提取失败，不注入无用的"未能提取..."文本

            if self.audit_result and ch_num == 2:
                if not self._is_extraction_failure(self.audit_result):
                    user_msg += f"\n【材料盘点结果】\n{self.audit_result}\n"

            # ★ v7.2: 按章节拆分注入模版（比注入全文更精准）
            tpl_ch = self._get_template_chapter(ch_num)
            if tpl_ch:
                user_msg += (
                    f"\n【模版参考 — 第{ch_num}章的写法范例（必须模仿此风格和结构！）】\n"
                    f"以下是模版报告中对应章节的原文。请严格模仿它的：\n"
                    f"1. 子节结构（哪些小标题、分几部分）\n"
                    f"2. 分析方式（如何用数据做趋势分析、如何引用具体名称和金额）\n"
                    f"3. 叙述风格（完整句子、分析性语言、非数据罗列）\n"
                    f"用当前客户的数据替换模版中的数据。\n\n"
                    f"{tpl_ch}\n"
                )
            elif self.template_full_text:
                user_msg += (
                    f"\n【模版报告参考正文（借鉴分析深度）】\n"
                    f"{_smart_truncate(self.template_full_text, 6000)}\n"
                )
            elif self.template_structure:
                user_msg += f"\n【模版结构参考】\n{self.template_structure}\n"

            # ★ v7: 搜索结果注入（第1章和第2章最需要行业信息）
            if self.search_results and ch_num in (1, 2):
                search_text = "\n".join(
                    f"搜索「{q}」:\n{r[:800]}"
                    for q, r in self.search_results.items()
                )
                user_msg += f"\n【网络搜索参考信息】\n{search_text}\n"

            text = self.llm.simple_chat(prompt, user_msg)

            # ★ v7.4: 后处理 — 清理元文本 + 合并待补充
            text = self._clean_meta_text(text)
            text = self._consolidate_pending(text)

            self.chapters[ch_key] = text
            prev_text += f"\n{text[:500]}"
            results.append(f"第{ch_num}章: {len(text)}字 ✅")

        total = sum(len(self.chapters.get(f"ch{i}", "")) for i in range(1, 5))

        # ★ v7.2: 质量门控 — 自动检查并修正常见问题
        gate_log = self._quality_gate()
        if gate_log:
            results.extend(gate_log)

        total_after = sum(len(self.chapters.get(f"ch{i}", "")) for i in range(1, 5))
        return f"全部章节撰写完成！\n" + "\n".join(results) + f"\n总计: {total_after}字"

    # ====== v7.2: 质量门控 ======

    def _quality_gate(self) -> list[str]:
        """写完全部章节后自动检查：元文本、待补充、审计标记、单位、重复率"""
        import re as _re
        log = []

        for ch_key in ["ch1", "ch2", "ch3", "ch4"]:
            text = self.chapters.get(ch_key, "")
            if not text:
                continue
            original_len = len(text)
            modified = text

            # ★ v7.4 新增: 元文本清理（提取总结、缺失清单等不应出现在正文）
            modified = self._clean_meta_text(modified)

            # ★ v7.4 新增: 合并连续待补充
            modified = self._consolidate_pending(modified)

            # 1. 清理审计/盘点标记
            audit_patterns = [
                r'[：:]\s*存在[，,。]?(?:\s*[（(].*?[)）])?',
                r'[：:]\s*不存在[，,。]?(?:\s*[（(].*?[)）])?',
                r'(?:提供|给出)?摘要中未(?:提及|涉及|列出)[^。]*。?',
                r'(?:标注找到了|于财务报表附注)[^。]*。?',
            ]
            for pat in audit_patterns:
                modified = _re.sub(pat, '', modified)

            # 2. 单位转换：原始元 → 万元
            def _yuan_to_wan(m):
                try:
                    val = float(m.group(1).replace(',', ''))
                    wan = val / 10000
                    if wan >= 10000:
                        return f"{wan/10000:.2f}亿元"
                    return f"{wan:.2f}万元"
                except:
                    return m.group(0)
            modified = _re.sub(
                r'([\d,]{6,}(?:\.\d{1,2})?)\s*元(?![/])',
                _yuan_to_wan, modified
            )

            # 3. 清理空行过多
            modified = _re.sub(r'\n{3,}', '\n\n', modified)
            modified = _re.sub(r'^[^\S\n]*[：:]\s*$', '', modified, flags=_re.MULTILINE)

            if modified != text:
                self.chapters[ch_key] = modified
                diff = original_len - len(modified)
                log.append(f"🔧 {ch_key}: 质量门控清理 ({diff:+d}字)")

        # 4. 跨章节智能去重检查
        dedup_log = self._smart_dedup()
        log.extend(dedup_log)

        return log

    def _smart_dedup(self) -> list[str]:
        """★ v7.2: 智能去重 — 检测跨章节完全重复段落，保留分析最深的一处"""
        import re as _re
        log = []

        # 提取每章的段落
        ch_paras = {}
        for ch_key in ["ch1", "ch2", "ch3", "ch4"]:
            text = self.chapters.get(ch_key, "")
            paras = [p.strip() for p in text.split('\n') if len(p.strip()) > 30]
            ch_paras[ch_key] = paras

        # 找跨章节重复段落（相同文本出现在不同章节）
        from collections import defaultdict
        para_locations = defaultdict(list)  # para_text -> [(ch_key, index)]
        for ch_key, paras in ch_paras.items():
            for i, p in enumerate(paras):
                # 用前60字作为key（避免微小差异）
                key = p[:60]
                para_locations[key].append((ch_key, i, p))

        removed_count = 0
        for key, locations in para_locations.items():
            if len(locations) < 2:
                continue
            # 检查是否跨章节（同一章节内的重复也处理）
            # 保留第一次出现，删除后续完全重复的
            for ch_key, idx, para_text in locations[1:]:
                text = self.chapters[ch_key]
                # 只删除完全重复（不是部分引用）
                if para_text in text:
                        text = text.replace(para_text, '', 1)
                        self.chapters[ch_key] = text
                        removed_count += 1

        if removed_count > 0:
            # 清理多余空行
            for ch_key in ["ch1", "ch2", "ch3", "ch4"]:
                import re
                self.chapters[ch_key] = re.sub(r'\n{3,}', '\n\n', self.chapters[ch_key])
            log.append(f"🔧 智能去重: 移除{removed_count}处跨章节重复段落")

        return log

    # ====== LLM 工具 ======

    def _tool_classify(self, args: dict) -> str:
        files_summary = args.get("files_summary", [])
        user_msg = ""
        for i, f in enumerate(files_summary, 1):
            user_msg += f"\n\n===== 文件{i}: {f.get('filename', f'文件{i}')} =====\n{f.get('preview', '')[:6000]}"
        result = self.llm.simple_chat(FILE_CLASSIFY_PROMPT, user_msg)
        classified = {"A": [], "B": [], "C": [], "D": []}
        for line in result.strip().split("\n"):
            m = re.match(r'(\d+)\s*[→\->:：]\s*([ABCDabcd])', line.strip())
            if m:
                idx = int(m.group(1)) - 1
                cat = m.group(2).upper()
                if 0 <= idx < len(files_summary) and cat in classified:
                    classified[cat].append(idx)
        self.classified = classified
        return json.dumps(classified, ensure_ascii=False)

    def _tool_extract_financial(self, args: dict) -> str:
        text = args.get("financial_text", "")
        # ★ v7.4 核心修复：LLM 无法在 tool call 中传递 100K+ 字符，
        # 如果 text 太短，自动从 self.file_contents 拉取财务相关材料
        if len(text.strip()) < 500 and self.file_contents:
            text = self._build_materials_text(max_chars=60000, categories="financial")
        result = self.llm.simple_chat(
            FINANCIAL_EXTRACT_PROMPT,
            _smart_truncate(text, 60000),
        )
        self.fin_extracted = result
        return result

    def _tool_audit(self, args: dict) -> str:
        text = args.get("all_materials_text", "")
        # ★ v7.4 核心修复：同上，自动从缓存拉取材料
        if len(text.strip()) < 500 and self.file_contents:
            text = self._build_materials_text(max_chars=25000)
        result = self.llm.simple_chat(
            MATERIAL_AUDIT_PROMPT,
            _smart_truncate(text, 25000),
        )
        self.audit_result = result
        return result

    def _tool_write_chapter(self, args: dict) -> str:
        ch_num = args.get("chapter_number", 1)
        basic_info = args.get("basic_info", "")
        materials = args.get("materials", "")
        prev = args.get("previous_chapters", "")
        special = args.get("special_instructions", "")

        # ★ v7.4 核心修复：自动从 file_contents 注入材料
        if len(materials.strip()) < 500 and self.file_contents:
            if ch_num == 3:
                materials = self._build_materials_text(max_chars=50000,
                                                      categories="financial")
            else:
                materials = self._build_materials_text(max_chars=50000)

        prompt = CHAPTER_PROMPTS.get(ch_num, CHAPTER_PROMPTS[1])
        user_msg = f"【基础信息】\n{basic_info}\n"
        if materials:
            mat_limit = 50000 if ch_num in (2, 3) else 20000
            user_msg += f"\n【参考材料】\n{_smart_truncate(materials, mat_limit)}\n"
        if prev:
            user_msg += f"\n【已生成内容】\n{_smart_truncate(prev, 8000)}\n"
        if special:
            user_msg += f"\n【特殊要求】\n{special}\n"

        # ★ v7.4: 智能财务注入
        if self.fin_extracted and ch_num in (2, 3):
            if not self._is_extraction_failure(self.fin_extracted):
                user_msg += f"\n【结构化财务数据】\n{self.fin_extracted}\n"
        if self.audit_result and ch_num == 2:
            if not self._is_extraction_failure(self.audit_result):
                user_msg += f"\n【材料盘点结果】\n{self.audit_result}\n"

        # ★ v7: 模版全文
        if self.template_full_text:
            user_msg += (
                f"\n【模版报告参考正文（借鉴分析深度）】\n"
                f"{_smart_truncate(self.template_full_text, 6000)}\n"
            )
        elif self.template_structure:
            user_msg += f"\n【模版结构参考】\n{self.template_structure}\n"

        # ★ v7: 搜索结果注入
        if self.search_results and ch_num in (1, 2):
            search_text = "\n".join(
                f"搜索「{q}」:\n{r[:800]}"
                for q, r in self.search_results.items()
            )
            user_msg += f"\n【网络搜索参考信息】\n{search_text}\n"

        result = self.llm.simple_chat(prompt, user_msg)

        # ★ v7.4: 后处理
        result = self._clean_meta_text(result)
        result = self._consolidate_pending(result)

        ch_key = f"ch{ch_num}"
        self.chapters[ch_key] = result
        return result

    def _tool_review(self, args: dict) -> str:
        report = args.get("full_report", "")
        return self.llm.simple_chat(REVIEW_PROMPT, report)

    def _tool_revise(self, args: dict) -> str:
        ch_num = args.get("chapter_number", 1)
        current = args.get("current_content", "")
        comments = args.get("review_comments", "")
        context = args.get("full_report_context", "")

        user_msg = (
            f"【需修正的章节】第{ch_num}章\n\n"
            f"【当前内容】\n{current}\n\n"
            f"【审查意见】\n{comments}\n"
        )
        if context:
            user_msg += f"\n【全文上下文】\n{_smart_truncate(context, 8000)}"

        result = self.llm.simple_chat(REVISE_PROMPT, user_msg)
        ch_key = f"ch{ch_num}"
        self.chapters[ch_key] = result
        return result

    def _tool_recall_memory(self, args: dict) -> str:
        query_type = args.get("query_type", "preferences")
        if query_type == "similar_reports":
            results = self.memory.reports.search_similar(
                industry=args.get("industry", ""),
                client_name=args.get("client_name", ""),
            )
            if not results:
                return "没有历史报告。"
            lines = [f"- {r['client_name']}（{r['industry']}）" for r in results]
            return "相关报告:\n" + "\n".join(lines)
        elif query_type == "preferences":
            prefs = self.memory.knowledge.get_all_preferences()
            return ("偏好:\n" + "\n".join(f"- {k}: {v}" for k, v in prefs.items())) if prefs else "无偏好记录。"
        elif query_type == "lessons":
            lessons = self.memory.knowledge.get_lessons()
            if not lessons:
                return "无经验记录。"
            lines = []
            for cat, items in lessons.items():
                for item in items[-3:]:
                    lines.append(f"- [{cat}] {item['content']}")
            return "经验:\n" + "\n".join(lines)
        return "未知类型。"

    def _tool_save_lesson(self, args: dict) -> str:
        category = args.get("category", "user_feedback")
        content = args.get("content", "")
        self.memory.knowledge.add_lesson(category, content)
        return f"已记录: [{category}] {content}"

    def save_report_to_memory(self, client_name: str, industry: str, feedback: str = ""):
        if self.chapters:
            return self.memory.reports.save_report(
                client_name=client_name,
                industry=industry,
                chapters=self.chapters,
                feedback=feedback,
                metadata={"fin_extracted": bool(self.fin_extracted)},
            )
        return None


def _preview_args(args: dict) -> str:
    preview = {}
    for k, v in args.items():
        if isinstance(v, str) and len(v) > 100:
            preview[k] = v[:80] + f"...({len(v)}字)"
        elif isinstance(v, list) and len(v) > 3:
            preview[k] = f"[{len(v)}项]"
        else:
            preview[k] = v
    return json.dumps(preview, ensure_ascii=False)
