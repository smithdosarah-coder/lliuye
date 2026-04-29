# Credit Intelligence Matrix · 信贷 AI 智能体矩阵

众安信科 AI 中台 / 乾策平台 X-Nexus · 6 Agent 协作平台 · 面向银行客户经理 / 审贷员 / 合规官 / 风险经理。

**Production**: <https://liuye.me> (ECS 139.196.30.69 · main 分支 · cloudflared tunnel)
**Dev branch**: `chore/l0-infra`

---

## 1. 6 Agent

| Agent | 中文 | 功能 |
|---|---|---|
| Agent1 channel | 获客 | look-alike 拓客 (基于已成交客户 + 外网搜) |
| Agent2 riskctrl | 风控 | DSL 规则生成 + 回测 |
| Agent3 credit | 授信 | Agent6 下游决策引擎 (对公+对私) |
| Agent4 alert | 预警 | 客户行为变化驱动 · 知识库批量扫描 |
| Agent5 compliance | 合规 | 政策事件驱动 · 业务制度违规扫 |
| Agent6 report | 报告 | Evidence-First 三阶段 + QC blocker |

详见 [docs/reset/north-star.md](docs/reset/north-star.md) (产品 north star + 6 Agent 闭环路径)。

---

## 2. 当前状态

项目处于 **"全新出发" reset 工程阶段** (起 2026-04-29):
- Step 2 conflict scan (架构审视 + 找冲突)
- Step 1 cleanup (Phase A · 7 worker · workspace 4 gate / shared infra / Letterpress 真清 / PRD 重写)
- Step 3 PRD + 商业化 (Phase B · 数据飞轮 + 商业化 doc)

**入口文档**: [RESET_MASTER_PLAN.md](RESET_MASTER_PLAN.md) — umbrella 索引
**新 session / compression 后必读**: [CLAUDE.md §14](CLAUDE.md) (6 reset docs 阅读顺序)

---

## 3. 启动 (Dev)

### 后端

```bash
py scripts/start_uvicorn.py
```

自动从项目根 `.env` 加载 `DEEPSEEK_API_KEY` / `TAVILY_API_KEY` / `DASHSCOPE_API_KEY` 等 env · 校验缺失 key 后调 uvicorn。

首次部署:
```bash
cp .env.example .env
# 填值
```

监听 `:8000` (per .env `PORT=8000`)。

### 前端

```bash
cd web && npm run dev
```

Next.js 16 · 监听 `:3000` · `next.config.ts` rewrites `/api/*` 到 `127.0.0.1:8000`。

### Agent6 v16 主管线 (CLI)

```bash
py v16_pipeline.py --source samples/<模板>.docx --material samples
```

Classifier → generator → QC gate 全链路。10 个 `v16_*.py` 实现。详见 [docs/contracts/rfc/20260418-v16-llm-abstraction-upgrade.md](docs/contracts/rfc/20260418-v16-llm-abstraction-upgrade.md)。

---

## 4. 部署 (Production)

main CLI 改 web/* 后**自动**部署 (per [CLAUDE.md §13.1](CLAUDE.md)):

```bash
bash scripts/deploy_to_ecs.sh           # 完整 (含 npm build · 5-10 min)
bash scripts/deploy_to_ecs.sh --skip-build  # 仅后端 restart
```

脚本封装: stash + pull + pip install + build + restart + healthcheck。

ECS 跑 4 systemd service: `nginx` / `cloudflared` / `lliuye-frontend` / `lliuye-backend`。

---

## 5. 关键文档

- [`CLAUDE.md`](CLAUDE.md) — 项目工程行为规范 (给 AI 看)
- [`RESET_MASTER_PLAN.md`](RESET_MASTER_PLAN.md) — reset 工程 umbrella
- [`docs/reset/`](docs/reset/) — north star / Phase A 7 worker / Codex mesh 协议 / state snapshot
- [`docs/contracts/`](docs/contracts/) — 接口契约 (可验收 spec)
- [`docs/handoff/decisions-log.md`](docs/handoff/decisions-log.md) — Q-NNN 决策事实日志
- [`docs/handoff/mesh.json`](docs/handoff/mesh.json) — multi-CLI mesh 配置
- [`docs/features-inventory.md`](docs/features-inventory.md) — F-001..F-064 feature inventory
- [`docs/scorecard/definition-of-done.md`](docs/scorecard/) — 银行交付 DoD 5 层

---

## 6. 仓库布局 (顶层)

```
agent_{channel,credit,alert,compliance,riskctrl,report}/  # 6 Agent backend
api_server.py                                              # FastAPI 总线
v16_pipeline.py + 9 v16_*.py                              # Agent6 主管线
shared/                                                    # 跨 agent 共用 (sources / kb_scan / llm)
web/                                                       # Next.js 16 frontend
data/                                                      # mock + feedback + KB
evaluation/                                                # 6 agent eval YAML
scripts/                                                   # 启动 / 部署 / orchestrator
docs/                                                      # 全部文档
legacy_gradio/                                             # 已归档 Gradio v9.0 + form_filler 等
.claude/                                                   # mesh worktrees 状态(本地 · gitignored)
```

---

## 7. 环境变量

详见 [`.env.example`](.env.example)。当前必需:

```
DEEPSEEK_API_KEY=sk-xxx
TAVILY_API_KEY=tvly-xxx
DASHSCOPE_API_KEY=sk-xxx        # Qwen
PORT=8000
KB_SCAN_DEMO_MODE=true|false
```

LLM keys 已 rotated 2026-04-29 · 历史 commit 含旧 keys 但已 dead (per decisions-log:1272 + 2026-04-29 安全事件清理)。

---

## 8. License / Author

内部项目 · 众安信科 AI 中台 · 刘野
