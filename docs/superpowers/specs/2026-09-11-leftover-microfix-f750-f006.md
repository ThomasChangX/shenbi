> **Date:** 2026-09-11 | **Status:** Design | **Severity:** 🟡 P2（两 finding 均 P2 · 微修 S 量级）| **方法:** 机械替换 + 配置统一（无需 systematic-debugging——两 finding 根因与修复路径均已定案）
> **系列:** 2026-08-15 审计轮遗留收口（非 37 簇成员——F750 原属 C16 边界争议条被 spec #54 设计审查 deferred 出局、候选归宿 C15/C17 双亡；08-14 轮 F0-06 无簇 squarely 承接；归宿由 spec #40 master 维护 pass 2026-09-11 裁决登记）| **依赖:** F750 素材已在盘（tests/fixtures/ 真实产物，见任务 1 清单）；F0-06 无依赖 | **范围:** tests/integration/test_gate_cli.py 单文件 + pyproject.toml 三处配置值

# 遗留微修批：F750 集成测试真实 fixture 化 + F0-06 python 版本三元统一

## 1. F750：test_gate_cli.py 捏造项目换真实 fixture 拷贝

**根因**（Z7-b:154 原文）：`_make_worldbuilding_project`（:27-97）手写 novel.json/story_bible/rules/locations/truth 模板（占位文本），而 tests/fixtures/ 已有真实产物；本测试是完整 skill 产出形态的场景（PASS 路径的 story_bible 结构即被测语义的一部分），不属 G0.9 豁免类别（gate 内部输入/接线单测豁免先例见 test_g4_directory.py:4-7、test_trigger_context.py:3-5）；手写中文占位过 gate 的方式可能与真实产物分布不同（bullet 密度、字数）。

**修复**（Z7-b 修复建议原样）：story_bible/rules/locations 等替换为真实 fixture 拷贝，仅保留目录组装逻辑。素材映射：

| 捏造面（现 :27-97） | 真实素材（tests/fixtures/） |
|---|---|
| novel.json | novel-example.json |
| genre-config.json | genre-config-example.json |
| world/story_bible.md | world-story-bible-example.md |
| world/rules.md | world-rules-example.md |
| world/locations.md | world-locations-example.md |
| truth/*.md 四模板 | 四面全有真实素材：truth-current_state.md / truth-character_matrix.md / truth-emotional_arcs.md / truth-chapter_summaries.md |
| characters/protagonist.md | character-profile-example.md / characters/ |

**验收：**
- `grep -n "Content here\|这是一个宏大而复杂的世界" tests/integration/test_gate_cli.py` 零命中（捏造文本清除）
- `uv run pytest tests/integration/test_gate_cli.py -v` 全绿（G4 PASS 路径在真实 fixture 拷贝下仍 PASS）
- 新引用的 fixture 均带 provenance 标注或属既有豁免白名单（G0.9/g0_purity 不新增违规）

## 2. F0-06：pyproject python 版本三元统一

**根因**（08-14 ledger F0-06）：`requires-python = ">=3.11"`（:8）vs mypy `python_version = "3.12"`（:379）vs basedpyright `pythonVersion = "3.11"`（:398）——类型检查语义基准漂移（3.11 vs 3.12 语法/API 差异可能漏报/误报）。

**裁决（spec 内定稿）**：统一为 **3.11**（对齐 requires-python 下限——工具链按支持下限校验是保守面；升 3.12 会放宽 requires-python 语义，超出微修边界）。即 mypy :379 `"3.12"` → `"3.11"`；basedpyright :398 已是 3.11 不动；:8 不动。

**验收：**
- `grep -n "python_version\|pythonVersion\|requires-python" pyproject.toml` 三处值一致（3.11 口径）
- `just check` 全绿（mypy/basedpyright 在 3.11 基准下无新报错）

## 边界

不动 src/ 生产代码；不改 ledger 状态（实施 PR 合并时由该 SDD 份回写 F750/F0-06 两行 closed）。
