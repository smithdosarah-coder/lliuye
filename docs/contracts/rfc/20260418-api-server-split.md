# RFC: api_server.py 路由拆分到 agent_*/api.py

**发起人**：主 CLI（事后补 RFC）
**日期**：2026-04-18
**变更类型**：红区（`api_server.py` + 新建 `shared/api_utils.py`）
**关联 commit**：`d08df08 refactor(api): split api_server.py inline routes into agent_*/api.py`
**审批状态**：✅ POST-HOC APPROVED（主 CLI）

---

## 0. 为什么是事后 RFC

时间线：
- `d08df08` 落于 2026-04-18 早段（api 拆分）
- `f38564f` 落于 2026-04-18 晚段（shared-change-protocol v1.0 发布）

commit 在协议发布前 ≈5 分钟落地，技术上**不构成 v1.0 协议违规**。但 api_server.py 是 5/5 Agent 共用的 mount 点，属后续 v1.1 协议框架下的红区，为审计可追溯性补此 RFC。

## 1. 变更内容

### 拆分动机

原 `api_server.py` 把 6 个 Agent 的 FastAPI 路由（`/api/channel/*`、`/api/credit/*` 等）全部内联，文件膨胀到 600+ 行，多 CLI 并行开发时注定冲突。拆分后各 Agent 自己维护 `agent_<n>/api.py`，主入口只做 mount。

### 具体改动

**`api_server.py`**（主入口）：
- 保留：FastAPI app 初始化、CORS、健康检查、SSE 编码 helpers
- 移除：所有 `/api/<agent>/*` 内联路由
- 新增：`_mount_agent_routes()` 自动发现 `agent_*/api.py` 并挂载

**`shared/api_utils.py`**（新建）：
- SSE 事件编码（5 段阶段 `ingest` / `extract` / `infer` / `write` / `audit`）
- 统一错误响应格式
- 从 `api_server.py` 抽出的共用 helpers

**`agent_*/api.py`**（6 个新文件）：
- 各 Agent 自己的路由实现
- 通过 `_mount_agent_routes()` 被主入口发现并挂载

## 2. 影响面

| 文件 | 被谁用 | 变更类型 | 兼容性 |
|---|---|---|---|
| `api_server.py` | 所有前端请求入口 | 路由外移 | ✅ URL 路径不变 |
| `shared/api_utils.py` | 所有 agent_*/api.py | 新文件 | ✅ |
| `agent_<n>/api.py` | 各自 Agent | 新文件 | ✅ |

**URL 契约完全保持** —— 前端看不到任何变化。

## 3. 替代方案

**Alt-A**：继续膨胀 `api_server.py`，多 CLI 并行冲突靠 merge 解决
- 否决：Pre-Phase-0 阶段就已经触发 3 次冲突，不可持续

**Alt-B（本方案）**：按 Agent 拆分 + mount 自动发现

**Alt-C**：改 FastAPI 子 App 并独立部署（每 Agent 独立进程）
- 否决：Phase 1 不需要独立部署，增加运维复杂度

## 4. 红区清单影响

本次拆分促使**红区清单保留 `api_server.py`**（mount 入口仍是共享单点），并**追加 `shared/api_utils.py`**。均已在协议 v1.0 §1.1 列明。

## 5. 验证

- [x] `/tmp/start_uvicorn.py` 启动正常
- [x] 6 个 Agent 路由全部可访问（`/api/channel/` `/api/credit/` `/api/report/` `/api/alert/` `/api/compliance/` `/api/riskctrl/`）
- [x] SSE 流式事件协议不变

## 6. 审批

- **主 CLI POST-HOC APPROVED** · 2026-04-18
- 留档理由：红区变更的审计链应完整，无论时间先后。未来对 `api_server.py` / `shared/api_utils.py` 的任何修改必须事前 RFC。
