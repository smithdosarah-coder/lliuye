# Worker Askout Protocol

**适用对象**：mesh worker CLI（P3F + Phase 4+ 所有 worker）
**强制等级**：违反 = REJECT-V2 不论其他验收
**触发缘起**：Q-035（agent6 worker 在 chat 输出 spec-gap askout · main CLI patrol 看不到 · user 转发中转 · 60min+ 阻塞）

---

## 核心 rule

**❌ 禁止**：
- worker 在 Claude REPL chat 输出 "askout / blocker / 等裁决 / Q-XXX candidate" 等内容
- worker 把决策问题留在 chat · 等用户截图转发主 CLI

**✅ 必须**：
- worker 任何 blocker / askout / spec gap / red-line conflict → **commit `Signal: Q-NNN-RAISED` + body 全文**
- main CLI patrol 走 git log 不看 chat · trailer 没挂 = 信息丢失

---

## Q-NNN-RAISED commit body 模板

```
ask(<worker-name>): <一句话主题 · ≤ 60 字>

## 背景
<1-2 段 · 是什么场景触发了 askout · 为啥 onboarding 没覆盖>

## 数据
<具体数字 / 实测结果 / 命令输出 · 让 main CLI 不用再跑就能判断>

## 候选方案（≥ 2）
A. <方案 A · 1 段 · 含 trade-off>
B. <方案 B · 1 段 · 含 trade-off>
C. <方案 C 严格按字面 spec 走 · 即便不可行也列出 · 让 main CLI 看到所有选项>

## Worker 推荐
<选哪个 + 为啥>

## 等待
等 main CLI commit `Signal: A-NNN-RESOLVED` + body 含裁决 + follow-up

Signal: Q-NNN-RAISED
```

---

## 编号约定

- Q-NNN 是全局递增 · 看 `docs/handoff/decisions-log.md` 找最大已用编号 + 1
- 不要用本地 worker 的局部编号
- 如果 worker fork 时 main 已经用了 Q-033 但 worker 不知道 · 用 candidate 编号 + 在 body 里说明 "Q-NNN candidate · 等 main 确认"——main CLI 裁决时分配真正编号

---

## main CLI 响应

main CLI patrol 5min 内 · 看到 `Signal: Q-NNN-RAISED` 立即：

1. 读 commit body 完整
2. （可选）spawn subagent verify worker 的数据
3. 写 `docs/handoff/decisions-log.md` 加 [Q-NNN] + [A-NNN]
4. commit `Signal: P3F-QXXX-RESOLVED` + body 含裁决 + follow-up
5. 告诉 user 复制裁决摘要给 worker（worker 看到 main commit 后继续）

**预期周转**：≤ 1 patrol cycle（≤ 5min）

---

## 反例（Q-035 触发场景 · 严禁重演）

agent6 worker 跑 Task B 发现 v16 漂移红线在 baseline 上不可达 · 在 chat 输出：

```
Q-033 candidate · Task B 阻塞
数据 ...
根因 ...
3 候选路径 ...
推荐 A · 等你裁决
```

**问题**：
- 没 commit `Signal: Q-NNN-RAISED`
- main CLI patrol 看 git log = 看不到这条 askout
- user 看 chat = 转发我 = user 当 message bus
- 60min+ 阻塞

**正确做法**应该是：worker 直接 commit `chore(agent6): ask Q-035 · v16 drift baseline mismatch` body 含同样内容 + `Signal: Q-NNN-RAISED` trailer · main CLI patrol 1 cycle 内自动接到 · 立即裁决。

---

## Resume 协议

worker resume（任何新 CLI 窗口进来）必读 `AGENT_IDENTITY.md` + 本 protocol。AGENT_IDENTITY 应在红线 section ref 本文件：

```markdown
## 红线
- ❌ ...
- ❌ **chat askout 禁用** · 任何 blocker 必走 commit trailer · 详见
     docs/process/worker-askout-protocol.md
- ✅ ...
```

---

## 适用范围 + 例外

- ✅ P3F + Phase 4+ 所有 worker · onboarding / kickoffs 必含本红线 ref
- ✅ multi-cli-mesh skill template `AGENT_IDENTITY.md.tpl` 建议同步加（user 决定 · scope 跨项目）
- ❌ 旧 batch worker 已 close · 不回填
- 🟡 例外：worker 在 chat 与用户做 quick clarification（非 blocker）OK · 但任何决策 / spec gap 必走 trailer
