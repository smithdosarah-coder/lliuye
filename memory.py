# -*- coding: utf-8 -*-
"""
记忆系统 — Agent 的长期记忆和学习能力

三层记忆:
1. 对话记忆 (ConversationMemory)  — 当前会话的上下文
2. 报告记忆 (ReportMemory)        — 历史报告摘要和反馈
3. 知识记忆 (KnowledgeMemory)     — 用户偏好、行业知识、经验教训
"""

import json
import os
import time
from datetime import datetime
from config import MEMORY_DIR, MAX_CONVERSATION_HISTORY, MAX_REPORT_MEMORY


def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)


class ConversationMemory:
    """当前会话的对话历史"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: list[dict] = []  # {role, content, timestamp}
        self.context: dict = {}          # 当前任务的结构化上下文（客户信息、材料等）

    def add_message(self, role: str, content: str):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        # 超过上限时保留最近的
        if len(self.messages) > MAX_CONVERSATION_HISTORY:
            self.messages = self.messages[-MAX_CONVERSATION_HISTORY:]

    def set_context(self, key: str, value):
        """存储任务上下文（如客户名称、已上传文件、已生成章节等）"""
        self.context[key] = value

    def get_context(self, key: str, default=None):
        return self.context.get(key, default)

    def get_messages_for_llm(self) -> list[dict]:
        """转换为 LLM 格式的消息列表"""
        return [{"role": m["role"], "content": m["content"]} for m in self.messages]

    def get_summary(self) -> str:
        """获取对话摘要（用于跨会话记忆）"""
        if not self.messages:
            return "空会话"
        user_msgs = [m["content"] for m in self.messages if m["role"] == "user"]
        return f"会话 {self.session_id}: 用户发送了 {len(user_msgs)} 条消息"


class ReportMemory:
    """历史报告记忆 — 记住生成过的报告，支持经验复用"""

    def __init__(self):
        self.store_path = os.path.join(MEMORY_DIR, "reports")
        _ensure_dir(self.store_path)
        self.index_path = os.path.join(self.store_path, "index.json")
        self.index = self._load_index()

    def _load_index(self) -> list[dict]:
        if os.path.exists(self.index_path):
            with open(self.index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save_index(self):
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)

    def save_report(self, client_name: str, industry: str,
                    chapters: dict, feedback: str = "", metadata: dict = None):
        """保存报告摘要"""
        report_id = f"rpt_{int(time.time())}"
        entry = {
            "id": report_id,
            "client_name": client_name,
            "industry": industry,
            "created_at": datetime.now().isoformat(),
            "chapter_keys": list(chapters.keys()),
            "feedback": feedback,
            "metadata": metadata or {},
        }
        # 保存完整内容
        detail_path = os.path.join(self.store_path, f"{report_id}.json")
        with open(detail_path, "w", encoding="utf-8") as f:
            json.dump({**entry, "chapters": chapters}, f, ensure_ascii=False, indent=2)

        self.index.append(entry)
        # 超过上限移除最旧的
        if len(self.index) > MAX_REPORT_MEMORY:
            old = self.index.pop(0)
            old_path = os.path.join(self.store_path, f"{old['id']}.json")
            if os.path.exists(old_path):
                os.remove(old_path)
        self._save_index()
        return report_id

    def add_feedback(self, report_id: str, feedback: str):
        """对某份报告添加反馈（用于自进化）"""
        for entry in self.index:
            if entry["id"] == report_id:
                entry["feedback"] = feedback
                break
        self._save_index()

        detail_path = os.path.join(self.store_path, f"{report_id}.json")
        if os.path.exists(detail_path):
            with open(detail_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["feedback"] = feedback
            with open(detail_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def search_similar(self, industry: str = "", client_name: str = "",
                       limit: int = 3) -> list[dict]:
        """查找相似的历史报告（简单匹配，可升级为向量检索）"""
        scored = []
        for entry in self.index:
            score = 0
            if industry and industry in entry.get("industry", ""):
                score += 2
            if client_name and client_name in entry.get("client_name", ""):
                score += 3
            if entry.get("feedback"):
                score += 1  # 有反馈的更有价值
            scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:limit] if _ > 0]

    def get_report_detail(self, report_id: str) -> dict | None:
        detail_path = os.path.join(self.store_path, f"{report_id}.json")
        if os.path.exists(detail_path):
            with open(detail_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None


class KnowledgeMemory:
    """知识记忆 — 用户偏好、行业知识、经验教训"""

    def __init__(self):
        self.store_path = os.path.join(MEMORY_DIR, "knowledge")
        _ensure_dir(self.store_path)
        self.prefs_path = os.path.join(self.store_path, "preferences.json")
        self.lessons_path = os.path.join(self.store_path, "lessons.json")
        self.preferences = self._load_json(self.prefs_path)
        self.lessons = self._load_json(self.lessons_path)

    def _load_json(self, path) -> dict:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_json(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def set_preference(self, key: str, value):
        """记录用户偏好（如：'report_style': '简洁', 'focus_areas': ['供应链']）"""
        self.preferences[key] = value
        self._save_json(self.prefs_path, self.preferences)

    def get_preference(self, key: str, default=None):
        return self.preferences.get(key, default)

    def get_all_preferences(self) -> dict:
        return self.preferences.copy()

    def add_lesson(self, category: str, content: str):
        """
        记录经验教训（自进化的核心）
        category: 'prompt_improvement', 'common_error', 'user_feedback', 'industry_knowledge'
        """
        if category not in self.lessons:
            self.lessons[category] = []
        self.lessons[category].append({
            "content": content,
            "created_at": datetime.now().isoformat(),
        })
        # 每个类别最多保留 50 条
        if len(self.lessons[category]) > 50:
            self.lessons[category] = self.lessons[category][-50:]
        self._save_json(self.lessons_path, self.lessons)

    def get_lessons(self, category: str = None) -> list[dict] | dict:
        if category:
            return self.lessons.get(category, [])
        return self.lessons

    def get_relevant_lessons(self, context: str, limit: int = 5) -> list[str]:
        """获取与当前上下文相关的经验（简单关键词匹配，可升级为语义检索）"""
        results = []
        for category, items in self.lessons.items():
            for item in items:
                # 简单相关性判断
                if any(kw in item["content"] for kw in context[:100].split()):
                    results.append(f"[{category}] {item['content']}")
        return results[:limit]


class MemoryManager:
    """统一记忆管理器"""

    def __init__(self):
        _ensure_dir(MEMORY_DIR)
        self.conversations: dict[str, ConversationMemory] = {}
        self.reports = ReportMemory()
        self.knowledge = KnowledgeMemory()

    def get_conversation(self, session_id: str) -> ConversationMemory:
        if session_id not in self.conversations:
            self.conversations[session_id] = ConversationMemory(session_id)
        return self.conversations[session_id]

    def build_context_prompt(self, session_id: str) -> str:
        """构建注入 Agent 的记忆上下文"""
        parts = []

        # 用户偏好
        prefs = self.knowledge.get_all_preferences()
        if prefs:
            parts.append("【用户偏好】\n" + "\n".join(f"- {k}: {v}" for k, v in prefs.items()))

        # 相关经验
        conv = self.get_conversation(session_id)
        if conv.context:
            industry = conv.context.get("industry", "")
            client = conv.context.get("client_name", "")
            similar = self.reports.search_similar(industry, client)
            if similar:
                parts.append("【相关历史报告】")
                for r in similar:
                    line = f"- {r['client_name']}（{r['industry']}）{r['created_at'][:10]}"
                    if r.get("feedback"):
                        line += f" | 反馈: {r['feedback']}"
                    parts.append(line)

        # 经验教训
        lessons = self.knowledge.get_lessons()
        if lessons:
            recent = []
            for cat, items in lessons.items():
                for item in items[-3:]:  # 每类最近3条
                    recent.append(f"- [{cat}] {item['content']}")
            if recent:
                parts.append("【经验教训】\n" + "\n".join(recent))

        return "\n\n".join(parts) if parts else ""
