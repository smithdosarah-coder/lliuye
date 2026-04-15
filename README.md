# Credit Report Agent

众安信科 AI 中台 — 信贷报告助手(Agent6)+ 配套授信决策 / 贷中预警 / 合规核验 Web UI。

## V14 成品演示启动

### 先决条件

- Python 3.12+(已装 `pip install -r requirements.txt` 或等价依赖:`openai fastapi uvicorn python-docx openpyxl pydantic`)
- Node.js 18+ / npm 9+
- `.env` 或系统环境变量中设置 `DEEPSEEK_API_KEY=sk-xxx`(真 pipeline 必需;仅演示 Mock 可跳过)

### 一键启动

Windows:

```bat
scripts\start-dev.bat
```

Git Bash / WSL / macOS / Linux:

```bash
bash scripts/start-dev.sh
```

启动后:

- 前端:http://localhost:3000/report
- 后端:http://127.0.0.1:8002/api/report/health
- 前端通过 `next.config.ts` 的 rewrite 把 `/api/report/*` 反代到后端,浏览器看到同源。

手动启动(两个终端):

```bash
# 终端 A:后端
py -m uvicorn agent_report.api:app --port 8002 --reload

# 终端 B:前端
cd web && npm run dev
```

### Mock 模式 vs 真模式

| 维度 | MOCK ON(默认) | MOCK OFF(真 pipeline) |
|---|---|---|
| 耗时 | 约 5 秒 | 5-10 分钟 |
| 依赖 LLM | 不需要 | 需要 `DEEPSEEK_API_KEY` |
| 材料上传 | 仅记录元信息 | 真读取并解析 |
| docx 产物 | 指向历史 `outputs/section_gen_test_*.docx` | 新 session 目录下生成 |
| 适合场景 | 产品演示 / UX 走查 / 无 key 环境 | 客户真实材料走通 |

右上角 **LLM 已连接 / 未连接** 状态灯反映后端是否检测到 API Key。红灯且 Mock OFF 时 `开始生成` 会被禁用。

### 预置演示场景

左栏「DEMO PRESETS」chip 一键跑通,无需上传材料:

- **鼎盛商贸**(对公批发,下行) — `dingsheng_trade`
- **张某餐饮**(普惠个体,健康) — `zhangsan_restaurant`

### 跨 Agent 握手

报告生成完成后,`/report` 页 `继续下游流程` 卡片把 `EnterpriseProfile` 写入 `sessionStorage.enterprise_profile`,跳转到 `/credit` / `/alert` / `/compliance`。目标页 `useEffect` 读取并预填输入。

如 sessionStorage 为空,带 URL `?preset=xxx` 时会回退调用 `/api/report/preset/{key}` 拉预置画像。

### 已知限制

- **真 pipeline 耗时 5-10 min**:中途不要关页面;生成超过 10min 无进度推进会自动报超时。
- **session 存储仅内存**:后端重启后老 session_id 失效;30 分钟 TTL 自动清理 `outputs/sessions/<session_id>/` 下的材料和 docx(磁盘保护)。
- **单进程部署**:SessionStore 未落地 Redis,多实例部署需要自行替换。
- **模板**:不传 `template_file` 时使用 `templates_cache/福建普惠授信申报及审查审批意见表2025新版.docx`。

### 端点概览(后端 :8002)

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/report/health` | LLM 连接状态灯 |
| POST | `/api/report/fill?mock=0|1&preset=...&business_line=...` | 主生成端点(SSE)|
| POST | `/api/report/refine` | 外因续跑(SSE)|
| GET | `/api/report/downloads/{session_id}/{filename}` | 下载本次 session 生成的 docx |
| GET | `/api/report/downloads/legacy/{filename}` | Mock 模式兜底下载 |
| GET | `/api/report/preset/{key}` | 只读预置画像(跨 Agent 预填 fallback)|
| GET | `/downloads/{filename}` | 兼容老 URL |

### 目录结构速览

```
agent_report/         # FastAPI 后端(V14)
  api.py              # 路由 + SSE + pipeline 包装
  enterprise_profile.py  # 跨 Agent 消费的画像 schema
  session_store.py    # 内存 session + TTL
  mock_fixtures.py    # 预置演示 fixture
web/                  # Next.js 前端(V14-B/D)
  src/app/report/     # 信贷报告助手页
  src/app/credit/     # 授信决策页(消费 sessionStorage)
  src/app/alert/      # 贷中预警页
  src/app/compliance/ # 合规核验页
  src/lib/api.ts      # 后端客户端 + SSE 解析
scripts/
  start-dev.bat       # Windows 一键启动
  start-dev.sh        # Unix 一键启动
outputs/
  sessions/           # 真 pipeline 的工作目录(30min TTL)
  section_gen_test_*.docx  # 历史样本(mock 下载源)
form_filler.py 等     # V13 引擎核心(V14 禁止改动)
```

### Troubleshooting

- **前端白屏 + 控制台 CORS 报错**:检查后端是否起在 8002;`next.config.ts` rewrite 走同源,CORS 不应触发。
- **`开始生成` 灰的**:切换到 Mock 模式或配置 `DEEPSEEK_API_KEY` 重启后端。
- **下载按钮点了没反应**:确认 `docx_url` 不是 `#mock-...` 开头(那是纯浏览器端 mock 的占位)。
- **`报错: 后端连接失败`**:后端进程挂了,`scripts/start-dev.bat` 重启。
