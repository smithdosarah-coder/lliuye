# data-foundation · REJECT-V2 GO Prompt

> **定位**：1 条 GO 指令，粘给 data-foundation worker CLI（worker resume 汇报完后）。
> **生效前提**：`PRODUCT-HARDENING-BATCH-1-DISPATCHED` + 本批次 Q-028 / A-028 已落 main。
> **取代**：`docs/handoff/product-hardening-batch-1-kickoffs.md` 的 ③ data-foundation 小节（v1 被 REJECT-V2）。
> **主 CLI 仲裁**：任何 worker 开 Q-NNN / RFC，主 CLI 回 A-NNN 后 worker 才能继续。

---

## data-foundation (v2 返工版)

```
REJECT-V2 GO。原批次被判形态错（yaml 把答案喂到模型嘴边）。按 v2 onboarding 返工：

1. 先 commit 一条 doc-only commit，trailer:
   Signal: PRODUCT-HARDENING-BATCH-1-V2-ACK

2. ACK 后强制先做：
   git fetch origin chore/l0-infra
   git log origin/chore/l0-infra --format='%h %s' -10
   读 docs/handoff/decisions-log.md Q-028 / A-028
   读 docs/onboarding/data-foundation-phase-1-v2.md 全文
   参照项目 CLAUDE.md §3.4 环境边界原则（反结果导向第 5 条）

3. 删老产物（Task A 首个 commit 带 embedded Signal: DATA-LEGACY-PURGED）:
   git rm -r data/mock/wide-base/
   git rm -r data/mock/schemas/
   git rm data/mock/deep-pillar/shortlist.md
   git rm -r data/mock/deep-pillar/pits/

4. Task A → B → C → D → E 顺序，每 Task 独立 commit：
   - A: 推翻 v1 + 新建 data/mock/{deep-pillar,channel-kb,compliance-kb}/ 空目录 + README → Signal: DATA-SCHEMA-V2-DONE
   - B: 深柱 5 家完整材料包（Agent6 + Agent3 共用 · DP001-DP005 · 每家 20-40 份异构材料 · 6 大类 · 命名混乱 · 数字有合理矛盾 · 跨 2022-2025 · 4 档难度 PM 内部维护 · 零答案字段）→ Signal: DATA-DEEP-PILLAR-5-DONE
   - C: Agent1 内部 KB（historical-clients 10-15 家简要画像 / marketing-preferences 3-5 份 / product-catalog 1 份 · 不含外部候选企业池）→ Signal: CHANNEL-KB-DONE
   - D: Agent5 内部制度库（credit-sop / customer-admission / kyc-aml / risk-preference / review-checklists 5 个子目录 · 仿银行内部 SOP 体例 · 不含外部政策）→ Signal: COMPLIANCE-KB-DONE
   - E: 全轨完成 → Signal: READY-FOR-DATA-FOUNDATION-B1-V2-REVIEW

5. 红线：严守反结果导向 5 原则，特别是新第 5 条"环境边界"——Agent1/5 的外部世界不要 mock。
   - 不做 yaml 清洗版本（禁止 companies.yaml / entities.yaml / prefilled.yaml）
   - 不标难度档、不标坑位答案（盲测法）
   - 形态必须真实：文件夹 + 异构格式 + 命名噪声 + 三方数字矛盾 + 零答案字段
   - 企业名脱敏不能是真实存续企业；数字打乱保量级
   - 不抢 code-urgent / code-arch / evaluation / Agent6 业务代码的地盘

关键参照:
- 中锐网络续贷材料包（用户本地）: D:\刘野\众安\新建文件夹\2026.3.25续贷材料
  你可以 ls 看形态（命名 / 分类 / 子目录 / 扩展名混用）但不能复制其内容
- 反 5 原则: 盲测 / 分层 / 真实锚定 / 脱敏再造 / 环境边界

每 Task 独立 commit，不攒。开干。
```

---

## 新主 CLI 使用说明

1. 用户 / 主 CLI 确认 data-foundation worker 已在 `D:/claude code/demo-data-foundation` worktree resume
2. 本文 v2 prompt 粘给 worker
3. 进度追踪：
   - `py C:/Users/Mr.S/.claude/skills/multi-cli-mesh/scripts/mesh_status.py`
   - 关注 signal: `PRODUCT-HARDENING-BATCH-1-V2-ACK` → `DATA-LEGACY-PURGED` → `DATA-SCHEMA-V2-DONE` → `DATA-DEEP-PILLAR-5-DONE` → `CHANNEL-KB-DONE` → `COMPLIANCE-KB-DONE` → `READY-FOR-DATA-FOUNDATION-B1-V2-REVIEW`

**预计 ACK**：5-15 分钟
**预计全轨 READY**：5-7 天（最长在 Task B 深柱 5 家材料包）
