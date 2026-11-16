# /sdd-next 引导协议（权威版 · v7.1）

> **权威与版本**：本文件是 `/sdd-next` 命令内容的唯一权威（2026-11-15 起入库，受 docs CI 门禁与 git 考古约束；`.zcode/commands/sdd-next.md` 仅为本机瘦指针，不入库）。流程细节以 `docs/superpowers/single-model-sdd-prompt.md`（**v8.0 自治版·核心区与 a-stock 同源**）为权威；本文件管启动面：第零步参数分诊、第一步起点判定、全程纪律、完成报告。
>
> **v7.1 变更**（2026-11-15 · /sdd-next 多专家深审 14 findings 全修）：①「已完成未归档」预检＋ARCHIVE-AS-DONE 清偿路线（实证：spec #97 完结后归档欠账半月、靠 PR #349 人工清偿）；②末块机械提取命令钉死；③完成报告增审查成本行；④入口本体入库（原 `.zcode/` 零版本控制为该轮审计唯一 C 级发现）。审计底账：GLM-5.3 六专家面板（评测科学／异模型执行者／红队 Goodhart／状态机形式化／Token·提示／人因），负结果显式——防劫持分诊、Iron Law 措辞限界、rubric 锚点存活率经逐项机械核验为通过。

按 `docs/superpowers/single-model-sdd-prompt.md`（v8.0 自治版）执行 SDD。本协议只做启动引导，流程细节以该文件为权威。

## 第零步 · 参数分诊（先于一切状态检查）

点名参数：$ARGUMENTS

参数为空 → 跳过本步直接进第一步。参数非空时先分诊，前两种情况继续走 SDD 引导：

- **点名模式**：参数是 `docs/superpowers/specs/INDEX.md` 活跃项的编号或路径 → 以其为 `$SPEC_PATH`，并在阶段 1 注册表核对时记入「非队头豁免理由（用户点名）」
- **自由文本的 SDD 选择指令**（如「处理最高优先级的」「跑一份 P0」）→ 解析为 spec 选择器：能唯一定位（等于队头，或优先级/特征唯一匹配一项活跃 spec）→ 在 progress.md 记录解析依据后照常执行；**不能唯一定位 → 列出候选并停止，不猜**。解析≠豁免价值门：阶段 1 全查照跑（v7 五问：含解法对抗回放与替代路径）
- **自由文本的非 SDD 指令**（如「审核这个命令」类要求）→ **不启动 SDD**：按参数语义直接处理，本命令的 SDD 引导到此终止
- **点名失败**（形似 spec 引用但不匹配任何 INDEX 活跃项）→ 报告用户并停止。**禁止静默回退队头模式**——那会执行一轮用户没有要求的完整 SDD。形似已归档编号的，报告时附其归档位置（`specs/archive/`）供用户参考，仍不执行

## 第一步 · 判定起点（在做任何其他事之前）

`git fetch --prune origin` 后跑三个探针。**不依赖 `spec-<N>-*` 分支命名规则**（本仓合法 SDD 批次分支可能不合该模式，如 `fix/audit-c32-c3-batch2`），**dependabot 与 gh-pages 一律排除**：

1. **progress.md 终态**（v8.0 起 per-plan workspace：`.superpowers/sdd/<spec 基名>/progress.md` 每 spec 一份单批次账本；旧 flat 多批次文件 `.superpowers/sdd/progress.md` 为 v7 遗留——存在即整体移入 `.superpowers/sdd-archive-flat-<日期>/` 后按全新一份走，不续跑）：
   - 已终结 = `## 最终状态` 段存在且内容为 merged/REJECTED/DEFERRED/ARCHIVE-AS-DONE
   - 未终结 = 无终态段，或终态是「等待用户命令 / 停止不 merge」类自由文本
2. **未合入分支**：`git branch -a --no-merged origin/main`（排除 `dependabot/`、`gh-pages`）
3. **非机器人 open PR**：`gh pr list --state open --json number,title,headRefName,author`，排除 headRefName 以 `dependabot/` 开头或作者为 dependabot bot 的条目（按分支名/作者过滤，**不按标题猜**——dependabot 标题有 bump 与 update 等多种形态）

三探针全干净 → **全新一份**（见下）。任一命中 → 按末块内容与命中来源分类处置：

- **中断**（末块流程中途断：任务缺 verdict、阶段指针不在终点）→ **断点续跑**：读 progress.md + skill ledger 重建阶段指针，从断点继续；禁止从阶段 0 重启（会重建 `.superpowers/sdd/`、产生第二套 audit-T 计数——compaction 协议明令禁止）。向用户报告续跑点后继续
- **停泊/未决**（末块工作已全部完成但终态为「等待用户指令」类自由文本；或探针 2/3 命中）→ **对账，不续跑也不直接开新份**。对每个命中逐一查归宿：`git merge-base --is-ancestor <末SHA> origin/main`，或 `gh pr list --state all --head <分支>`（squash 合并的分支在 `--no-merged` 下呈假阳性，以 PR 状态为准）。然后：
  1. **已 merge 且 progress.md 有记载** → 回写末块 `## 最终状态: merged PR #N`（附事后对账注记），向用户简报对账结果，按已终结继续（通常进全新一份）
  2. **有 open PR，或已记载但未 merge** → 停：向用户报告命中清单（分支名 / 末 SHA / 领先 main 的 commit 数），等裁决——归档活工作态或并行开第二份都违反串行纪律
  3. **无 progress.md 记载且无 open PR**（非 SDD 遗留分支，如维护性 bot 分支）→ 不阻塞启动：progress.md 记 deviation，完成报告中提醒用户清理

**全新一份**：

1. 读 `docs/superpowers/specs/INDEX.md`，**队头 = 文件序第一条活跃条目**（全优先级池，不限定 P1）。文件序即推荐序，是本命令的权威口径——**不按优先级标注自行重排**：INDEX 图例已于 v7.1 修正为「文件序即推荐序（由排序依据段定义）」；若发现新矛盾记入 progress.md deviation，照取文件序队头
2. **已完成未归档预检（v7.1）**：队头 spec 编号在 origin/main 提交史有**主题匹配**的已合提交 → **不启动执行**。命令：
   ```bash
   git log --oneline origin/main | grep -E "spec ?#?<N>([^0-9]|$)"
   ```
   （conventional 提交常带 `spec #N` / `specN` 引用，两种形态都抓）命中且 commit 主题与 spec 内容匹配 → 向用户报备证据（SHA＋标题＋PR 号），**确认后走归档清偿 docs PR**：spec 头 `Status:` 定稿 `Done (PR #M)` → 移 `specs/archive/` → INDEX 删行 → 提交 `docs(archive): <slug> done (PR #M)`。**成功归因，不是 Rejected**——把已完成的 spec 错标 Rejected 会丢 Done 归因（实证：#97 完结 PR #293 已合、归档欠账半月，最终靠 PR #349 人工清偿）。主题不匹配／无法确认 → 照常进 SDD（阶段 1 的 ARCHIVE-AS-DONE 裁决兜底，见 v7.1 裁决表）
3. **只填 `$SPEC_PATH`（单 spec 模式），禁填 `$QUEUE`**——批处理模式是单 session 连跑整队；无人值守循环由外部 overnight 脚本逐份新开 session 实现（干净 context + 每份独立熔断），两套批处理机制不混用
4. `.superpowers/sdd/` 下若残留已终结工作态目录（progress.md 有终态），整个目录先移入 `.superpowers/sdd-archive-<slug>/`（对齐既有先例）再新建；**停泊态禁止归档**。工作目录名 = spec 基名（`scripts/sdd-workspace` 派生，plan 基名=spec 基名映射）
5. 按单 spec 模式从阶段 0 执行到终止条件：GO 路线跑到阶段 12；REJECT 出 docs PR 完成驳斥归档、DEFER 以裁决报告终止、ARCHIVE-AS-DONE 以清偿归档 PR 终止——它们与修复合并是同等合格的交付，不硬修

## 全程纪律

- **串行**：上一份必须已 merge + main 更新；禁止并行开第二份（共享 worktree 与 `.superpowers/sdd/`）。第一步三探针就是本纪律的机制化执行，不得跳过
- **pathspec commit 保护**：worktree 常有用户未提交的 docs 修改——所有 commit 显式列文件路径，禁止 `git add -A` / `git add .`，用户 unstaged 改动全程原样保留
- **连续 REJECT 刹车**（启动时）：`git log --oneline --grep="docs(sdd): reject"` 最近两次 SDD 终态均为 REJECT → 先提示用户"注册表或 main 走向系统性漂移，建议人工抽查剩余队列"，确认后再继续
- **价值门不跳过**：命令启动 ≠ 免检；阶段 1 全查照跑（v7：freshness（含 gitignored 引用磁盘核验）/注册表＋任务级交叉引用对账/驳斥五问——含 ④解法对抗回放 ⑤替代路径）——队头 spec 可能已被 main 后续合并部分或全部实现（已发生实例：#7 的 F397 与 PR #43 的 C3 接线重叠），全查是防重复实施与次优施工的唯一防线。**v7.1 起另有立项预答义务**（INDEX 头部）：spec 缺 ④⑤ 预答栏 = 价值门首查项
- **CI 真实门禁**：合并条件 = CI 全绿（ci/codeql/security/docs workflow 按改动面触发）——本仓为 public repo，无计费豁免，CI 即权威
- **禁止直推 main（含 docs-only 收尾/归档 commit）**：一切进 main 的提交——代码、spec 修订、驳斥归档、Done 归档、清偿归档、INDEX 更新——都必须走分支 + PR + CI 全绿后合并。已发生反例（2026-08-24 SDD #4）：归档 commit 直推 main 跳过了 PR CI，specs→archive 移动产生的 4 条相对链接断裂未被拦截，main Docs workflow 变红；且无 PR 关联会被 overnight 第五重终态校验判为疑似直推而熔断。「docs-only 改动无害」不成立——docs workflow 正是对 docs-only 改动最严的门禁（mkdocs --strict 链接校验）。归档移动文件后必须检查文件内相对链接并改为同目录形式

## 完成报告（每份的终点）

阶段 12 结束（或 REJECT/DEFER/ARCHIVE-AS-DONE 终止）后，**先写 `.superpowers/sdd/progress.md` 最终状态块**（`## 最终状态` + merged PR #N / REJECTED 理由 / DEFER 依赖 / ARCHIVE-AS-DONE 清偿 PR #M），再输出最终消息。GO/REJECT/DEFER/ARCHIVE-AS-DONE 一切路线都必须写——progress.md 是唯一跨阶段状态载体（compaction 协议），overnight 批处理的五重终态校验直接依赖它；已发生反例（2026-08-24 SDD #5）：REJECT 短路线完成报告只留在会话输出、未写 progress.md，批处理熔断。最终消息必须包含：最终状态 + **审查成本行（v7.1：各阶段 audit_loop 轮数 / audit-T 计数 / 子 agent 会话数）** + 一句「本份完结——开新 session 输入 /sdd-next 跑下一份」。

分支清理是完成报告的前置闭环，不是可选收尾：凡走了分支+PR 的路线（GO 修复合并 / REJECT 驳斥归档 PR / ARCHIVE-AS-DONE 清偿 PR），合并固定 `gh pr merge --squash --delete-branch`（删远端分支硬要求，v7 阶段 10 为权威），本地 `git branch -D <branch>` + `git remote prune origin`（v7 阶段 11）——「零残留」须**远端+本地双面成立**。squash 后 `-d` 必拒（分支非 main 祖先）；不 prune 的话已删远端分支的幽灵引用留在本地 `git branch -r`，跨 session 误导本命令第一步探针 2 的分支扫描（2026-11-10 清偿实录：13 条幽灵引用 + #320-#323 四条真实残留）。

循环的驱动者是用户，不是你：一次 `/sdd-next` = 一份 spec，跑完即停；不要在同一 session 自动开始下一份，除非用户明确要求继续。
