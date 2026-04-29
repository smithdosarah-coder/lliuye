# ECS Deploy Handoff · 2026-04-27 · 给新 main CLI

> **Resume 一句话指令**：「读完本文件 + git status + 最近 5 commit · 然后等用户指令」。
> 不要重新摸 ECS·所有现状都在这文件里。

---

## 一句话现状

6 Agent 信贷 AI 产品已部署阿里云 ECS·通过 Cloudflare tunnel 给 https://liuye.me·**但 6 个 Workspace UI 全部 frontend-only mock·后端 100% 没接**。你的工作：把 6 Agent 全接前后端 + 大量 UI 改动。**5 天客户走访倒计时**。

---

## 关键凭证（**已 redact** · 2026-04-29 安全事件后清理 · 真值仅在 .env / 本地 keypair / CF dashboard）

```
ECS:
  IP:        139.196.30.69
  user:      admin (sudo NOPASSWD)
  OS:        Alibaba Cloud Linux 3 (RHEL 8 兼容·dnf)
  SSH key:   ~/.ssh/id_ed25519_aliyun_demo (本地 git bash 路径 · 真 key 不在仓库)
  password:  [REDACTED · 已 rotate 2026-04-29 · 真值仅运维知 · keypair 是主路径]

LLM keys (在 ECS .env 和本地 .env · gitignored · **不在文档**):
  DEEPSEEK_API_KEY=[REDACTED · 见 .env]   # 旧 key 已禁用 2026-04-29
  TAVILY_API_KEY=[REDACTED · 见 .env]     # 旧 key 已禁用 2026-04-29
  DASHSCOPE_API_KEY=[REDACTED · 见 .env]  # 旧 key 已禁用 2026-04-29

Cloudflare tunnel:
  Tunnel ID:    [REDACTED · 见 CF dashboard]
  Tunnel name:  credit-demo
  Account:      [REDACTED · 见 1Password / CF dashboard]
  Credentials:  ECS:/home/admin/.cloudflared/<tunnel-id>.json (路径仅 ECS 内可见)
  cert.pem:     ECS:/home/admin/.cloudflared/cert.pem (CF API auth · 路径仅 ECS 内可见)
```

**安全事件背景** (decisions-log §I-024 · 2026-04-29):
- repo 是 GitHub public · 本文件原含 3 个 LIVE LLM key + ECS SSH password + CF tunnel ID
- 上次同类事件 (decisions-log:1272) DeepSeek key `sk-358b17ce...` 已禁
- 本次 3 LLM key 全部 rotate · ECS .env 同步 · `lliuye-backend` 已 restart
- 历史 commit 仍含旧值 · 但旧值已 dead · 同 decisions-log:1274 处理(不 filter-repo · 禁 key 即止血)

---

## 当前 ECS 跑的 4 个 systemd service（连验证）

```bash
ssh -i ~/.ssh/id_ed25519_aliyun_demo admin@139.196.30.69 \
  'systemctl status nginx cloudflared lliuye-frontend lliuye-backend --no-pager | head -20'
```

期望全部 `active (running)`：

| Service | 干啥 | 端口 |
|---|---|---|
| `nginx.service` | 反代 :80 → :3000 (next) + :8000 (api) · server_name 含 liuye.me/api/demo | :80 |
| `cloudflared.service` | tunnel ID dd427133- · 4 个 connector to CF San Jose | (出栈·无入端口) |
| `lliuye-frontend.service` | Next.js production build (`npm start`) | :3000 |
| `lliuye-backend.service` | uvicorn FastAPI (api_server:app · venv python3.11) | :8000 |

**ECS 路径**：`/home/admin/lliuye/` (git clone of `smithdosarah-coder/lliuye` · branch `main` · HEAD `903d7b3`)。

---

## 当前用户能访问的 URL（公网验证 200 OK）

```
https://liuye.me/login        ← Next.js 修复版登录页
https://demo.liuye.me/login   (同上)
https://api.liuye.me/login    (同上)
```

DNS：3 条 Tunnel record（CF dashboard 里显示 type=Tunnel·实际是 CNAME → `dd427133-...cfargotunnel.com`）·全部橙云 (Proxied)·CF Universal SSL 自动给 HTTPS。
Page Rule：`*liuye.me/*` · Cache Level: **Bypass**（防 stale HTML，已用户配好）。

---

## 前任 CLI 这一轮做了什么（按时间）

1. SSH keypair 配置 `~/.ssh/id_ed25519_aliyun_demo` → admin@139.196.30.69 通
2. 修复 `web/src/components/shell/AuthGate.tsx`：login race（initialMountRef 区分初始 mount vs 登录提交）
3. 修复 `web/src/app/login/_components/LoginForm.tsx`：移除 submitting state（防卡死）+ effect-driven redirect
4. 部署 cloudflared on ECS（替代笔记本 cloudflared·systemd 守护）
5. 修复 `/etc/nginx/nginx.conf` default server 块冲突（注释掉·备份 `nginx.conf.bak.20260427`）
6. 同步 .env 三 key 到 ECS（旧 key `sk-...88fe` 和 `tvly-...kM2v` 已废·当前 5575 / FbDx / 4b4a）
7. 用户改 Cloudflare DNS 3 条 Tunnel record + Page Rule cache bypass

---

## 6 Agent E2E 现状 matrix（接管 audit · 2026-04-27 14:30）

| Agent | UI route | Backend endpoint | 后端 mounted? | 前端调后端? | 真 LLM? | E2E |
|---|---|---|---|---|---|---|
| Agent1 channel | /archive/channel | `/api/channel/run` (SSE) + scenarios + export_xlsx | ✅ api_server.py:186 | ❌ frozen mock `CHANNEL_SESSION` | ✅ DeepSeek | 🟡 |
| Agent2 riskctrl | /archive/riskctrl | `/api/riskctrl/dsl_gen` + backtest | ✅ api_server.py:189 | ❌ frozen mock | ❌ 不调 | 🔴 |
| Agent3 credit | /archive/credit | `/api/credit/decision` + presets + export_docx | ✅ api_server.py:185 | ❌ frozen mock | ❌ 不调 | 🔴 |
| Agent4 alert | /archive/alert | `/api/alert/scan` (SSE) | ✅ api_server.py:188 | ❌ frozen mock | ⚠️ KB_DEMO 锁 mock | 🔴 |
| Agent5 compliance | /archive/compliance | `/api/compliance/policy_scan` | ✅ api_server.py:187 | ❌ frozen mock | ⚠️ KB_DEMO 锁 mock | 🔴 |
| Agent6 report | /archive/report | `/api/report/fill` (SSE) + refine + downloads | ✅ api_server.py:184 | ❌ frozen mock | ✅ DeepSeek + 真文件上传 (mock=0) | 🟡 |

**ScanCTA「演示」按钮全调死路径**：`POST /api/run/{agent}` (`web/src/components/shared/ScanCTA.tsx:113`)·这个 endpoint **在 api_server.py 里不存在**·fetch fail 后 fallback 到前端假进度条（5 步 × 450ms）。用户看到完美进度条·后端啥也没收到。

每个 Workspace 都从 `web/src/lib/mock/{agent}.ts` import 硬编 SESSION fixture·永远不调 backend。

`/today` 也是 100% 硬编 (`web/src/lib/mock/today.ts`)·没 API 调用·所以"进入界面直接显示了数据"。

---

## 用户决定的工作路径（C 路）

- **全 6 Agent UI 接前后端**（5-15 天工作量·用户接受）
- 同时**大量 UI 改动**：
  - `/today` 改空白框架 + "开始演示"按钮触发数据（现状是 100% 硬编）
  - 黑洞 login 集成（`design_mockups/login-motion-prototype.html` untracked·替换当前 cosmic 星球版本）
  - 6 Workspace UI 调整（具体由用户后续给）
- 用户接受 mesh 派 worker 工作模式

---

## 推荐 mesh worker 切分（建议·你 main CLI 决定）

按 worktree-per-Agent 切 6 worker（用 multi-cli-mesh skill）：

```
agent1-channel-wire   (branch: feat/agent1-frontend-backend-wire)
agent2-riskctrl-wire
agent3-credit-wire
agent4-alert-wire
agent5-compliance-wire
agent6-report-wire
```

每个 worker 任务模板：
1. 删 Workspace 对 `lib/mock/{agent}` 的 import
2. 改用 SWR / fetch SSE 调真后端 endpoint
3. 处理 loading / error / retry states
4. 删该 Agent 的 ScanCTA 调用·或改 endpoint 为 `/api/{agent}/run`
5. Playwright e2e 测（login → 选 persona → 点演示 → 看真 LLM response）

或先做**multiplexer endpoint** `/api/run/{agent}` 在 api_server.py · 让 ScanCTA 按钮通了再细 wire（1-2 天 vs 5-15 天 trade-off）。这是治标，但客户走访前能展示"按钮真调用了 LLM"。

UI 改动 worker 单独切：
```
ui-today-empty-frame    (/today 空白框架 + 数据触发)
ui-login-blackhole      (黑洞版本集成)
```

---

## 关键 Invariants（千万不要做）

1. ❌ **LLM key 多次轮换史**: 历次失效 key 列表已 redact · 当前 valid 仅在 .env(gitignored)· 永远不要把全 key 写进文档(本规则因 2026-04-29 安全事件加固)
2. ❌ **同上 Tavily / DashScope** · 当前活 key 仅在 .env
3. ❌ **不要 PowerShell `Get-Content -Raw` 读 UTF-8 中文文件** — zh-CN Windows 默认 CP936 解 UTF-8 → mojibake。永远用 Python 字节级（`read_bytes` / `write_bytes`）
4. ❌ **不要在 ssh 命令里塞 PowerShell `>>`** — PowerShell 解析 `>>` 当本地 redirect·会截 ssh 命令字符串·导致命令到不了远端。直接登远端 bash 跑。
5. ❌ **不要 `KB_SCAN_DEMO_MODE=false`** 给客户走访 demo — Agent1/4/5 真 Tavily 抖断 demo 翻车。当前 ECS .env 是 `=true`，保留。
6. ❌ **不要随意 `npm run build` ECS 上的 web/** — `lliuye-frontend.service` 跑着·先 stop 再 build 再 restart：
   ```bash
   sudo systemctl stop lliuye-frontend && cd ~/lliuye/web && npm run build && sudo systemctl start lliuye-frontend
   ```
7. ❌ **不要直接 `git push` 在本地** — 本地 git remote 没配 origin（只有 upstream 指向另一个 worktree）。push 走用户笔记本（用户之前手动 push 的方式我也不知道）·你只能 commit·让用户 push。
8. ❌ **不要让 ECS git tree 长期脏** — 用户改了，commit + push GitHub + ECS `git pull` 是干净路径。当前 ECS git tree **就是脏的**（M LoginForm + AuthGate + package-lock + 几个 .bak）·因为我直接 scp 上去没走 git。新 CLI 应该尽快推 GitHub 让 ECS pull 同步。

---

## ECS git tree 当前脏状态（你接管要清理）

```
M web/package-lock.json        ← 用户之前 npm install 时变了
M web/src/components/shell/AuthGate.tsx                    ← 我 scp 的修复
M web/src/app/login/_components/LoginForm.tsx              ← 我 scp 的修复
?? web/src/components/shell/AuthGate.tsx.bak.20260427      ← 我备份
?? web/src/app/login/_components/LoginForm.tsx.bak.20260427
/etc/nginx/nginx.conf          ← 我注释了 default server (备份在 nginx.conf.bak.20260427)
/home/admin/lliuye/.env        ← 我 sync 的 3 key (备份在 .env.bak.20260427)
```

清理路径：本地 commit 我的修复（已 commit·见本文件邻近的 fix commit）→ user push GitHub → ECS `git pull origin main`（如果 main 是基于 chore/l0-infra rebase）→ ECS 上 `rm *.bak.*` 清备份。

---

## 接管后第一步（你 todo）

1. **读完本文件**·别重新摸 ECS（已经摸完了）
2. **验 4 service 还活**：
   ```bash
   ssh -i ~/.ssh/id_ed25519_aliyun_demo admin@139.196.30.69 \
     'systemctl status nginx cloudflared lliuye-frontend lliuye-backend --no-pager | grep -E "Active|loaded"'
   ```
3. **curl 验证**：
   ```bash
   curl -sI --noproxy "*" https://liuye.me/login   # 期望 200 OK
   ```
4. **跟用户对齐**：
   - 路径选择：multiplexer 治标 (1-2d) / 单 Agent E2E (3-5d) / 全 6 Agent (5-15d)
   - UI 改动优先级（today 空白框架 / 黑洞 login / 客户走访话术 / ……）
   - Mesh worker 切分（按本文件推荐 vs 你建议的）
5. **invoke `multi-cli-mesh` skill** 派 worker（如果走 mesh 路径）

---

## 教训（前任 CLI 这一轮踩的坑·你避免）

1. **PowerShell `Get-Content -Raw` 中文炸**：zh-CN Windows 默认 CP936·读 UTF-8 中文文件 → mojibake。`LoginForm.tsx` 中文被编码灾难污染过一次（"客户经理" → "瀹㈡埛缁忕悊"），用 `Write` tool 重写 + Python 字节级 CRLF 转换抢救。**永远用 Python `read_bytes` / `write_bytes`** 处理中文文件 line ending 转换。
2. **.bat 文件必须 CRLF + ASCII**：Write tool 默认 LF·Windows cmd 在 LF-only `.bat` 上行边界错位（`chcp 65001` 后没换行 → 命令切碎成 "5001 不是命令"）。修复：Write 全 ASCII 内容 → PowerShell 转 CRLF + ASCII encoding。
3. **ssh 命令字符串塞本地 shell metachar 不靠谱**：PowerShell `--%` stop-parsing 对 `>>` 不可靠·导致 ssh 远端 echo 命令的 redirect 没传过去·公钥没 append 到 authorized_keys·ssh -i 401。
4. **阿里云大陆 ECS 强制 ICP 备案**：`.me` 域名不能 ICP 备案·alibaba 网络层对 host header `liuye.me` 入流量 Beaver 403 拦截。**绕开方法 = cloudflared tunnel**（agent 主动出栈连 CF·不走 ECS :80 入流量）。
5. **nginx 装包默认 server 块抢 :80**：`/etc/nginx/nginx.conf` 自带的 `server { listen 80; server_name _; root /usr/share/nginx/html; }` 跟我们 `lliuye.conf` 抢 default·偶发 nginx 选错 server·返 default 404 page (Fedora 风格)。修复：注释 nginx.conf 默认 server。
6. **早上 user 给的 LLM key 用一会儿就被轮换**：`sk-...88fe` 和 `tvly-...kM2v` 给我之后被 rotate·下午用就 401。**不要假设 user 给的 key 永远 valid**·部署前现验。
7. **next dev 静默挂死无人知**：之前笔记本 next dev 不知道何时挂了·cloudflared 一直 502·CF CDN 缓存 stale HTML 5 天·user 看的"登录页"是僵尸页面。**production 必须 systemd / pm2 守护 + healthcheck**（ECS 已 systemd 守护·OK）。
8. **zustand persist 没 skipHydration（项目级 8 处）**：`AuthGate` 修了 race 但 zustand persist 在 Next 16 SSR 还有 hydration race·refresh 时 currentUser=null 可能踢回 /login。**P1 hardening**：8 处 store 加 `skipHydration: true` + 入口 layout 调 `store.persist.rehydrate()`。

---

## 用户偏好备忘（CLAUDE.md 全局规则核心）

- **不要谄媚**：不夸"很好"·"完美"·"出色"·有问题直接说
- **结论先行**：verdict 在前·理由在后·不铺垫
- **默认 terse**：短为先·用户嫌长会说"说人话"
- **审计/review 类**：开头 1 句 verdict + 3-5 bullet/table·禁止散文
- **多档建议给分级**：高/中/低 ROI 或 🔴🟡🟢·别让用户自己排序
- **方案先行**：中等以上任务先出方案再动手·不接受无方案直接编码
- **commit 粒度 = TaskCreate 粒度**：每个 task 完成立即 commit·便于 `git revert` 精准回滚
- **治本不治标**：避免 "清缓存 / 强刷" 这种 user-side workaround·找架构层 root cause

---

## 引用文件（你接管后值得读）

- `CLAUDE.md` — 用户全局规则
- `D:/claude code/credit_report_agent_work/CLAUDE.md` — 项目规则（信贷 AI 6 Agent 架构）
- `docs/handoff/decisions-log.md` — 历史决策 log（Q-001 ~ Q-040）
- `docs/handoff/mesh.json` — multi-cli-mesh 状态看板
- `docs/commercial-readiness.md` — 客户走访演示话术 + 4 异议处理
- `web/src/components/shared/ScanCTA.tsx:113` — 死路径 fetch 那行
- `web/src/lib/mock/{agent}.ts` × 6 — 当前每个 Agent 的硬编 SESSION fixture
- `api_server.py:184-189` — 6 Agent router mount 行
- `agent_*/api.py` × 6 — 每个 Agent 的真后端 API（已 mounted·等前端调）

---

End of handoff. 5 天客户走访倒计时开始。
