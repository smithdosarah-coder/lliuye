# agent_report — FastAPI + SSE 后端

包装 V13 `form_filler.FormFillAgent.run()` 引擎,为 Next.js 前端(`web/`)提供流式生成能力。

## 启动

```bash
# 开发模式(端口 8002,与 agent_credit 的 8001 避让)
py -m uvicorn agent_report.api:app --port 8002 --reload

# 或直接跑
py agent_report/api.py
```

环境变量:
- `DEEPSEEK_API_KEY` — 真 pipeline 模式必需;未设置时 LLM caller 会返回空串,流程不崩但内容为空
- `PORT` — 默认 8002

## 端点

### `POST /api/report/fill`

流式生成信贷报告,返回 SSE。

Query 参数:
- `mock=0|1` — 0 真 pipeline / 1 走预置场景
- `preset=dingsheng_trade|zhangsan_restaurant` — mock 模式下的场景

FormData:
- `files` — 上传的材料文件(真 pipeline 模式必需,支持 .docx/.pdf/.xlsx/.xls/.doc/.txt)

### `POST /api/report/refine`

外因补答续跑。

Body:
```json
{ "session_id": "<uuid>", "answers": [{"id": "q_ext_001", "value": "..."}] }
```

当前版本只重跑 `external_factor` 标签相关 section(stub 实现,真正接入由 V14-C 负责)。

### `GET /downloads/<file>`

下载 outputs/ 目录下的 docx。文件名会做 basename 净化防目录穿越。

### `GET /health`

健康检查。

## 事件契约(SSE)

```
event: stage
data: {"stage": "ingest|extract|infer|write|audit", "progress": 0.0-1.0, "message": "..."}

event: done
data: {
  "session_id": "<uuid4>",
  "report_docx_url": "/downloads/<file>.docx",
  "enterprise_profile": { /* EnterpriseProfile, 与 agent_credit schema 对齐 */ },
  "pending_questions": [{"id","section_id","question","hint","input_type"}],
  "downstream_handoff": {
    "credit":     "/credit?preset=<KEY>",
    "alert":      "/alert?preset=<KEY>",
    "compliance": "/compliance?preset=<KEY>"
  }
}

event: error
data: {"stage": "...", "message": "..."}
```

5 段阶段映射(真 pipeline 内部日志 -> 5 段):

| 阶段 | 触发关键词(form_filler 日志) |
|------|------------------------------|
| `ingest` | 材料加载 / 材料KB / 材料全文索引 / 企业画像锚点 |
| `extract` | 财务事实库 / KB 预填 / truth_fill / 结构化预填 |
| `infer` | 模板语义 / 扫描模版 / 分析模板 / 逐节生成模式 |
| `write` | 生成段落 / Section / Phase1/2/3 / 节生成 |
| `audit` | 校验 / validator / sanitize / affiliate / 清理 |

## Session Store

- 内存字典 + UUID4 key + 30 分钟 TTL
- 每次读写惰性 GC 过期 session
- 真·多实例部署需要换 Redis,当前架构单进程足够

## Mock 模式

- `D:\刘野\众安\客户经理助理\06_信贷报告助手\fixtures\<preset>.json` 若存在则加载,否则回退 `mock_fixtures._EMBEDDED_STUBS`
- 内嵌场景:`dingsheng_trade`(对公批发/下行) / `zhangsan_restaurant`(对私餐饮/健康)
- Mock 模式下 `report_docx_url` 指向 outputs/ 下最新一份 `section_gen_test_*.docx`(若无则 null)

## 约束

- 不修改 `section_generator.py / form_filler.py / prompts.py / material_anchor.py / truth_fill.py`(V14-C 负责)
- 不修改 `web/` 下任何文件(V14-B 负责)
- Pending questions 当前返回 stub,等 V14-C Agent 接入真 question generator
