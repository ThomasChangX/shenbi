# Findings Ledger — 2026-08-15

| ID | 标题 | 类别 | 严重度 | 证据 | 根因 | 验证 | 影响 | 建议方向 | 深度 | 状态 |
|---|---|---|---|---|---|---|---|---|---|---|
| D101 | pytest-cov 在 --collect-only 阶段仍写 coverage 工件并以 16.08% FAIL 污染正式覆盖率文件 | optimization | P2 | d1-11-collect-only.log 尾部（FAIL Required ... 16.08%；tests/coverage/coverage.xml 被覆写） | pyproject addopts 全局挂 --cov 无 collect-only 豁免 | `uv run pytest --co -q` 两次复现，输出在 d1/ | 非覆盖目的 pytest 调用静默污染覆盖率工件（2026-08-14 轮 2 次覆写先例） | addopts 拆分或常态 COVERAGE_FILE 隔离 | d1 | open |
| D102 | src/shenbi 内 6 处 print( 违反 AGENTS.md "No print() in framework code"（CLI 入口豁免边界待裁） | error | P1 | src/shenbi/cost/report.py:93,95; src/shenbi/pipeline/cli.py:945,947; src/shenbi/skill_utils/escalation/check.py:149; src/shenbi/skill_utils/foreshadowing_recall/recall.py:61 | CLI 输出直用 print，框架纯度例外未成文 | `git grep -n "print(" -- 'src/shenbi/*.py'`（2 处 _text_fingerprint 子串误报已剔除） | AGENTS.md 合规性；structlog 统一性 | Z3/Z5/Z6 深读裁豁免边界，豁免者降级并将豁免规则文档化 | d1 | open |
| D103 | chapter_loop.py:20 docstring 遗留 TODO 措辞（W3T4/W3T5 迁移说明未清理） | optimization | M | src/shenbi/pipeline/chapter_loop.py:20 | 历史迁移注释未清理 | `git grep -nE "TODO" -- src/shenbi/` | 误导读者以为有待办 | 清理措辞 | d1 | open |
| D104 | 2 个 meta skill（using-shenbi、shenbi-writing-skills）无 contract.kind 声明 | error | P2 | skills/using-shenbi/SKILL.md frontmatter; skills/shenbi-writing-skills/SKILL.md frontmatter | meta skill 从未纳入契约迁移范围 | d1-03-frontmatter.log（74 skill 全量解析） | 若 meta skill 应有契约则缺失；若豁免则 lint 无豁免规则（静默不对称） | Z8 语义裁决 + lint_contracts 明确 meta 豁免规则 | d1 | open |
