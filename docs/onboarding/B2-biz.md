# worker-B2 · Sprint 2 (BE11 商业化 doc · Codex 反对实装)

## 你是谁

worker-B2 · Phase B Sprint 2 · branch `feat/phase-b2-biz` · worktree `D:\claude code\work-B2-biz`

## 你的任务

按 `docs/reset/phase-b-charter.md` line 100-108 + `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` BE11 写商业化 doc + 多租户 architecture spec。

**关键**: Codex 反对实装多租户 (1 周缩 vs 主 CLI 原 3-4 周)。**只写 doc + spec · 不动代码**。真 isolation 推 Phase C。

### BE11 4 件交付 (1 周 · 完后释放)

1. **`docs/biz/pricing-assumptions.md`**
   - 4 种定价方案对比 (按 Agent / 按使用量 / 按客户经理席位 / 套餐)
   - 银行客户付费倾向调研 (引前面客户走访记录)
   - SaaS vs 私有部署定价差异
   - 对标: 壹账通 / 同盾 / 百融 / FICO 定价

2. **`docs/biz/multi-tenant-assumptions.md`**
   - tenant_id / org_id 数据模型 spec (字段名 + 类型 + 索引 · 不实装)
   - 数据隔离方案 (schema-per-tenant vs row-level filter · 决策矩阵)
   - 跨租户共享数据 (e.g. 公共政策库) 处理
   - LLM context 跨租户隔离方案

3. **`docs/biz/trial-flow-assumptions.md`**
   - 银行客户试用流程 (从联系 → POC → 签单 4 阶段时间线)
   - 试用环境隔离 spec (per-tenant subdomain or path)
   - POC 4 维评价标准对接 (画像 35% + 产品适配 25% + 经营策略 20% + 性能 20%)

4. **`docs/biz/sales-playbook-v1.md`**
   - 客户经理常见 objection + 答复
   - 6 Agent 矩阵 demo flow (per 北部湾首演经验)
   - 价值锚定 (vs 人工成本 / vs 竞品)

## 红线 (硬 · 违 = REJECT V2)

- **绝不动代码** · 只写 docs/biz/*.md
- 不实装 multi-tenant 数据模型 · 只 spec
- 不创建 tenant_id 字段 · 只在 doc 描述
- 不写 RBAC role · 复用现有 auth_service

## DONE signal

`WORKER-B2-BIZ-DOC-DONE` · trailer 必含:
- `REVIEW-MODE: manual`
- `REASONING-EFFORT: medium`
- `ELAPSED: <min>`
- `DOC-FILES: docs/biz/*.md (4 file)`

## 工程量

**1 周** (Codex 缩 vs 主 CLI 原 3-4 周 · 真 isolation 推 Phase C)

## 必读文件

1. `docs/onboarding/B2-biz.md` (本文)
2. `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` 找 BE11 章节
3. `docs/reset/phase-b-charter.md` line 100-108
4. CLAUDE.md (全文 · 了解项目背景)
5. `MEMORY.md` (auto-memory · 含 PM 客户走访记录 / 北部湾首演 / 银行 AI 市场对标)

## 起手第一步

```bash
cd "D:/claude code/work-B2-biz"
mkdir -p docs/biz
# read 上面 5 文件 + memory
git commit --allow-empty -m "chore(resume): WORKER-B2-RESUMED · 我理解 Sprint 2 BE11 task

任务: BE11 商业化 doc + multi-tenant arch spec only (Codex 反对实装)
4 doc: pricing + multi-tenant + trial-flow + sales-playbook
工程量: 1 周 · 完后释放
DONE signal: WORKER-B2-BIZ-DOC-DONE
红线: 绝不动代码 · 只 docs/biz/*.md · 不实装 multi-tenant 数据模型

Signal: WORKER-B2-RESUMED"
```
