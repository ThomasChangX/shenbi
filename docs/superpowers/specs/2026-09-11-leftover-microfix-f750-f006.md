> **Date:** 2026-09-11 | **Status:** Design | **Severity:** 🟡 P2（两 finding 均 P2 · 微修 S 量级）| **方法:** 机械替换 + 配置统一（无需 systematic-debugging——两 finding 根因与修复路径均已定案）
> **系列:** 2026-08-15 审计轮遗留收口（非 37 簇成员——F750 原属 C16 边界争议条被 spec #54 设计审查 deferred 出局、候选归宿 C15/C17 双亡；08-14 轮 F0-06 无簇 squarely 承接；归宿由 spec #40 master 维护 pass 2026-09-11 裁决登记）| **依赖:** F750 素材源在盘（novel-output/xinghuo-ranqiong/ 真实产物全套 + tests/fixtures/ 既有 synthetic-sample 回退面，见任务 1 映射）；F0-06 无依赖 | **范围:** tests/integration/test_gate_cli.py 单文件 + pyproject.toml 三处配置值 + fixtures 新增 upstream-copy 引入（如走首选路径）

# 遗留微修批：F750 集成测试真实 fixture 化 + F0-06 python 版本三元统一

## 1. F750：test_gate_cli.py 捏造项目换真实 fixture 拷贝

**根因**（转述自 Z7-b:154）：`_make_worldbuilding_project`（:27-97）手写 novel.json/story_bible/rules/locations/truth 模板（占位文本 "Content here."），本测试是完整 skill 产出形态的场景（PASS 路径的 story_bible 结构即被测语义的一部分），不属 G0.9 豁免类别（gate 内部输入/接线单测豁免先例见 test_g4_directory.py:4-7、test_trigger_context.py:3-5）；手写中文占位过 gate 的方式可能与真实产物分布不同（bullet 密度、字数）。

**素材现状（2026-09-11 核实，audit-T2 修正）**：审计轮所称「真实 world fixtures 已存在」在 C16（spec #54，PR #174）落地 provenance 标注后不再成立——tests/fixtures/ 的 world-{story-bible,rules,locations,power-system}-example.md 与 novel-example.json 均为 `synthetic-sample`（hand-authored example structure），truth-character_matrix/emotional_arcs/chapter_summaries.md 三者无 provenance 载体；唯一 upstream-copy 真材是 genre-config-example.json。**全套真实产物在 `novel-output/xinghuo-ranqiong/`**（world/story_bible.md、rules.md、locations.md、truth/character_matrix.md、chapter_summaries.md 等，经 C18 清洗）。

**修复（首选路径 = upstream-copy 引真实产物，回退路径 = synthetic-sample 拷贝）**：

首选（满足 F750 分布真实性立论）：从 `novel-output/xinghuo-ranqiong/` 按既有 upstream-copy 模式（对齐 genre-config-example.json 的 `.provenance.json` sidecar 形态）引入真实产物到 tests/fixtures/，测试内仅保留目录组装逻辑：

| 捏造面（现 :27-97） | 首选素材（novel-output/xinghuo-ranqiong/ → upstream-copy 入 fixtures/） |
|---|---|
| novel.json / genre-config.json | genre-config 已有 upstream-copy fixture；novel 元数据面若无对应产物则以既有 novel-example.json（synthetic-sample）回退并注记 |
| world/story_bible.md | world/story_bible.md |
| world/rules.md | world/rules.md |
| world/locations.md | world/locations.md |
| truth/*.md 四模板 | truth/character_matrix.md、truth/chapter_summaries.md（在盘真实产物）；缺口面（current_state/emotional_arcs 如需）允许回退 synthetic-sample 并注记 |
| characters/protagonist.md | 以真实产物如可得则引入；否则 character-profile-example.md（synthetic-sample）回退并注记 |

回退面：既有 synthetic-sample fixtures（world-*-example.md、truth-current_state.md 等 provenance 已标注者）可作拷贝源——结构真实但分布非真实，须在测试注记其局限；无 provenance 载体的三个 truth fixture（character_matrix/emotional_arcs/chapter_summaries）引用前须先补 provenance 标注或以 upstream-copy 真实产物替代。

**验收：**
- `grep -n "Content here\|这是一个宏大而复杂的世界" tests/integration/test_gate_cli.py` 零命中（捏造文本清除）
- `uv run pytest tests/integration/test_gate_cli.py -v` 全绿（G4 PASS 路径在 fixture 拷贝下仍 PASS）
- 首选路径下新增的 fixtures 均带 `.provenance.json`（upstream-copy, source 指明 novel-output 路径）；回退路径的 synthetic-sample 引用在测试内注记局限——g0_purity 不新增违规

## 2. F0-06：pyproject python 版本三元统一

**根因**（08-14 ledger F0-06）：`requires-python = ">=3.11"`（:8）vs mypy `python_version = "3.12"`（:379）vs basedpyright `pythonVersion = "3.11"`（:398）——类型检查语义基准漂移（3.11 vs 3.12 语法/API 差异可能漏报/误报）。

**裁决（spec 内定稿）**：统一为 **3.11**（对齐 requires-python 下限——工具链按支持下限校验是保守面；升 3.12 会放宽 requires-python 语义，超出微修边界）。即 mypy :379 `"3.12"` → `"3.11"`；basedpyright :398 已是 3.11 不动；:8 不动。

**验收：**
- `grep -n "python_version\|pythonVersion\|requires-python" pyproject.toml` 三处值一致（3.11 口径）
- `just check` 全绿（mypy/basedpyright 在 3.11 基准下无新报错）

## 边界

不动 src/ 生产代码；不改 ledger 状态（实施 PR 合并时由该 SDD 份回写 F750/F0-06 两行 closed）。
