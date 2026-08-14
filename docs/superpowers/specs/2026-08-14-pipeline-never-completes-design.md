> **Date:** 2026-08-14 | **Status:** Design | **Severity:** 🟥 P0 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查 | **依赖:** 无 | **范围:** src/shenbi/pipeline/ + contracts/paths.py | **核心洞察:** 5 个独立根因叠加使长篇小说 pipeline 永不进入 CLOSURE

# Pipeline 永不完成（5 独立根因）

## 症状
真实项目 novel-output/xinghuo-ranqiong（56 章）停在 chapter-loop、closure_step=0、novel.json.total_chapters=None；任何长篇小说无法通过 pipeline 完成。

## 根因与证据
### R1 · volume_map 中文格式 vs 英文解析器（F324, P0）
- `_shared.py:35-42` `_END_RE`/`_RANGE_RE` 只匹配英文 "Chapter End:"/"Chapters N-M"
- 生产格式（SKILL 模板 + 真实产物一致）：`**章节范围**: 第1章 - 第15章（共15章）`
- 实证：`read_volume_boundaries(production) → set()`；`is_volume_boundary(15) → False`（第 15 章是第 1 卷末章应为 True）
- 影响链：卷边界触发全家失效 → total_chapters 永不写入 → `if total > 0:` 守卫（cli.py:219）跳过全部章间触发 → book_closure 永不触发

### R2 · total_chapters 写点自锁（F353, P0）
- 全仓仅两个 `_update_total_chapters` 写点（cli.py:748、triggers.py:623），均位于依赖 `total > 0` 守卫或 volume_boundary 触发的路径内
- total 初始 0 → 守卫永不进 → 写点永不执行 → 自锁。**即使修复 R1 仍无法完成**

### R3 · closure step 10 目录 G4（F371, P0）
- step 10 output_path=`final-snapshot/`（目录），`_resolve_closure_g4_path` 原样返回
- generic G4 对目录 `p.read_text()` → IsADirectoryError → G4.gen.read_error FAIL → 重试×3 → ESCALATION

### R4 · N 型触发步骤 G4 未解析路径（F373, P0）
- triggers.py 5 个触发步骤 output_path 含字面 N（`audits/arc-N-score.md` 等），G4 校验未解析路径 → not_found 恒 FAIL
- dispatch 侧写解析后路径（`arc-5-score.md`）——同一内容两路径 FAIL/PASS（G4 CLI 实证）

### R5 · closure prompt 构建期失败（F379, P0）
- closure 5/10 步（2/4/5/6/10）契约 writes 含 N/NNN 占位符，prompt 无 "chapter N" → `extract_chapter`→None → `resolve_chapter_path(None)` 抛 UnresolvedPathError → prompt build 失败
- 从属：F313（closure G4 卷号替换章号）、F380（genesis anchor 恒跳过）、F3B5（escalation 升级恒失败）、F245（volume-N 按章号解析）

## 影响
- 长篇小说无法完成（P0 级产品功能缺失）
- 卷级特性全家静默失效（foreshadowing-resolve/volume-consolidation/score-volume 等）
- 章节节点数据污染（`| 1 |` 误中跨卷桥接表）

## 假设 + 验证命令
- H1: 修复 R1 后 `read_volume_boundaries(production)` 返回正确边界集 → `uv run python -c "from shenbi.pipeline._shared import read_volume_boundaries; print(read_volume_boundaries(Path('novel-output/xinghuo-ranqiong')))"`
- H2: 修复 R2 后 genesis 完成后 total_chapters 被写入 → 检查 novel.json
- H3: 修复 R3/R4/R5 后 closure 全步骤 G4 PASS → G4 CLI 全步骤实测

## 修复方向（数值化标准）
1. R1: `_shared` 增加中文格式解析（`第N章 - 第M章`/`（共K章）`/`| 第N章 |`）；补真实中文 volume_map fixture 测试；**验收：真实项目边界集非空、is_volume_boundary(15)=True**
2. R2: genesis step 6 完成后由代码固化 total_chapters（不依赖 LLM）；统一两写点口径（read_volume_boundaries 唯一来源）；**验收：novel.json.total_chapters=56（真实项目）**
3. R3: `_resolve_closure_g4_path` 对目录输出返回空串（跳过 G4）或改校验目录内容；**验收：closure step 10 不再 FAIL**
4. R4: 触发步骤 G4 校验用解析后路径（extract_chapter + resolve_chapter_path）；**验收：arc-5-score.md 场景 PASS**
5. R5: closure prompt 构造时对 N 占位提供卷/章上下文（或 resolve 后传入）；**验收：closure 10 步 prompt-build 全通过**
6. 回归：`just check` 全绿 + 新增上述验收测试

## 相关流程缺陷（同批次修复）
- **F340（P1）**：cmd_review REJECT 全类型无重做/回退语义（spec §2.7）；genesis-complete reject 后 resume 恒 True → pipeline 永久卡死
- **F341（P1）**：--auto 模式并行 post-draft 无条件设 STATE_SETTLE checkpoint（state_settle_review_required 未检查）→ 自动化每章必停
- **F303（P1）**：快照子系统生产未接线（create/restore/prune 无调用方，last_snapshot 永不写入）
- **F304（P1）**：RetryExhaustedError 无 except → crash-resume 预算耗尽 CLI 裸崩
