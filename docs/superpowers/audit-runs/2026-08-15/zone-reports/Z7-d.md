# Z7-d 段报告 — tests/fixtures + baselines + skill-behavior + skill-triggering + contracts

- 审查日期: 2026-08-15 | agent: Z7-d 初审（只读）| 编号段: F776-F799（实际使用 F776-F790，15 条）
- 文件清单: docs/superpowers/audit-runs/2026-08-15/zones/Z7-d.files（166 文件：fixtures 122 + baselines 10 + skill-behavior 22 + skill-triggering 10 + contracts 2）
- 覆盖: 机械核验 166/166（哈希/大小/命名/孤儿全量扫描）+ 深读约 22 文件 + 差分执行 8 条命令
- 上下文: 上轮 2026-08-14 已有 fixture-authenticity-design spec（状态 Design，未修复）。本轮独立复核证实其大部分 finding 仍在磁盘上成立，并新增 gate-outputs 基线漂移的量化证据。

## 总览

| 严重度 | 数量 | 编号 |
|---|---|---|
| P0 | 0 | — |
| P1 | 3 | F776, F777, F779 |
| P2 | 11 | F778, F780-F787, F789 |
| M | 1 | F790 |

P0 未触发理由: 手写 fixture 均未直接进入现行验收判定路径（calibration 锚点影响评分校准而非技能验收；伪造 drafts/manifest 零消费者或仅被 tiers 剧本引用），按严重度表归 P1（违反 AGENTS.md G0.9 显式契约）。

---

### tests/fixtures/chapter-{2..10}-draft.md + chapter-{7,8,9}-example.md + chapter-draft-example.md（13 文件）
- 处置: deep-read（机械核验 13 + 深读 4：chapter-2/3-draft 全文、chapter-draft-example 头部、哈希三连）
- 声称检查的不变量: [G0.9 fixture 为真实 skill 输出；同命名族文件应代表不同章节的真实产物；被 scenario 引用的输入应具备其声称的属性]
- findings:
  - F777 | 9 个 chapter draft 是同一文本仅改 H1 章号的复制体，且零引用 | error | P1 | 证据 tests/fixtures/chapter-2-draft.md:9 与 chapter-3-draft.md:9（difflib 全文 diff 仅 2 行差异：`# 第2章：最新章节` vs `# 第3章：最新章节`；9 文件均 150 行、4503-4504 字节；H1 标题为占位词"最新章节"非真实章节名） | 根因: 手工批量生成 fixture 冒充 9 个不同章节的真实产物，违反 G0.9；且词干级 grep（tests/src/tools/justfile/skills）零引用，兼为死文件 | 验证: `python3 -c "import difflib,pathlib; a=pathlib.Path('tests/fixtures/chapter-2-draft.md').read_text().splitlines(); b=pathlib.Path('tests/fixtures/chapter-3-draft.md').read_text().splitlines(); print([l for l in difflib.unified_diff(a,b) if l[:1] in '+-' and l[:3] not in ('+++','---')])"` → 输出仅 2 行（H1 章号）；stem grep chapter-N-draft 全 0 | 建议方向: 删除或降级为显式合成样本并标注 provenance（对齐上轮 spec R1）
  - F778 | chapter-7/8/9-example.md 三文件逐字节相同 | error | P2 | 证据 sha256 三文件均为 df81acba75e3（2494 字节）；chapter-7-example 被 tests/tiers/t1-skill/shenbi-context-composing/generative/input/scenario.md 用作"ending diversity"类输入（上轮 F762 指出多样性前提因此空转） | 根因: 复制粘贴生成三"章"；context-composing 的多样性断言建立在伪输入上 | 验证: `python3 -c "import hashlib,pathlib; print({p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:12] for p in sorted(pathlib.Path('tests/fixtures').glob('chapter-*-example.md'))})"` → 7/8/9 三键同哈希 df81acba75e3 | 建议方向: 三选一保留真本，其余删除；context-composing scenario 输入改用 multi-chapter-example/ 真实互异章节
- 验证命令: 上轮 spec R1 + 本段 difflib/sha256 脚本（见上）
- 置信度: high

### tests/fixtures/snapshots/ + snapshot-dir/ + truth-*.md（16 文件）
- 处置: deep-read（机械核验 16 + 深读 manifest.md + 哈希对 4 组 + MIRROR_MAP 对照）
- 声称检查的不变量: [G0.11 镜像双向闭合；快照 fixture 应为真实快照产物；副本关系应登记可同步]
- findings:
  - F779 | chapter-025 快照 manifest 的 checksums 为占位符 | error | P1 | 证据 tests/fixtures/snapshots/chapter-025/manifest.md:7-8（`chapters/chapter-1.md: sha256:abc123`、`chapters/chapter-25.md: sha256:xyz789`）；manifest 自述第 25 章断点/累计约 125,000 字，但其 truth/ 数据实为第 1 章内容（上轮 T803/T806 已证，本轮经 truth-* 重复哈希间接印证） | 根因: 手写伪造快照，占位哈希是手工构造的直接痕迹，污染任何以其为前提的快照类测试 | 验证: `sed -n '6,8p' tests/fixtures/snapshots/chapter-025/manifest.md` → 输出含 `sha256:abc123` / `sha256:xyz789` | 建议方向: 用真实 novel-output 快照重建（snapshot-dir/ 的两份真实镜像可作模板），或显式标注合成样本
  - F780 | 4 对 truth-*.md 与 snapshots/chapter-025/truth/ 逐字节重复且未登记 MIRROR_MAP | error | P2 | 证据 sha256 相同对：truth-chapter_summaries.md==snapshots/chapter-025/truth/chapter_summaries.md（ee8b44b79dcb）、character_matrix（0b2006cb8249）、emotional_arcs（417c6a5b55e2）、pending_hooks（8faa499b28ca）；MIRROR_MAP（src/shenbi/gates/g0.py:13-22）仅登记 4 条外部源镜像，不含这 4 对 fixture 内部副本；另 6 个平铺 truth-*.md 文件名用下划线词干（truth-chapter_summaries.md），与 fixtures 顶层 kebab-case 惯例不一致 | 根因: 平铺副本供 scenario 直引，但无登记无同步守卫，快照侧一旦更新平铺侧静默漂移 | 验证: `/tmp/z7d_mech.py` 重复哈希组输出（4 组成对）+ `uv run python tools/check_fixture_mirror.py`（exit 0，绿但不覆盖此 4 对） | 建议方向: 二选一删除（保 snapshots 树或平铺族），或纳入 MIRROR_MAP 式登记
  - 镜像正面结论: MIRROR_MAP 登记的 4 条（outline-example.md、volume-map-xinghuo.md、snapshot-dir/ 两章快照）源文件均存在且哈希一致；全 fixtures 对 novel-output/ + 仓库根的内容级镜像扫描恰好命中这 4 对、无未登记外部镜像——对外部源 G0.11 双向闭合（本轮验证，非沿袭）
- 验证命令: `uv run python tools/check_fixture_mirror.py` → exit 0 无 drift 无 skip；/tmp 内容镜像扫描脚本 → 4/4 registered, 0 unregistered
- 置信度: high

### tests/fixtures/calibration/（29 文件：README + 27 锚点 + .gitkeep）
- 处置: deep-read（机械核验 29（含 G0.14 哈希锁闭包）+ 深读 README + 4 锚点 + 语料溯源 grep）
- 声称检查的不变量: [G0.9 真实产物；README schema："excerpt 必须是真实 prose 引文，Never invented or hand-crafted"；README 描述与磁盘一致]
- findings:
  - F776 | 27 个校准锚点引文为虚构语料，违反自身 schema 且被 G0.14 锁哈希 | error | P1 | 证据 (a) 锚点核心语料"半块黑石饼/灵能催化剂/老周"经全库 grep 不存在于 novel-output/（真实已发布章节零命中，仅存在于 calibration 锚点与 tiers scenario 闭环互引）；(b) arc-payoff/期待债务结算/low.md:3 excerpt 通篇为评论体（"本卷几乎没有回答任何旧悬念…读者带着三个问题翻开本卷"），非 README.md:20 要求的 "the actual text under evaluation"；(c) resonance/场景临场感/low.md:3 为刻意写差的构造负样本，无可溯源章节 | 根因: 锚点为手工编写以填充 5×3+4×3 维度矩阵，随后被 G0.14 当作合法基准锁定（tests/tiers/deps.json `_calibration_hashes.combined`），虚构期望被固化进评分校准链 | 验证: `grep -rln "黑石饼" novel-output/` → 空；`grep -rln "老周" novel-output/` → 空；命中仅在 tests/fixtures/calibration/ 与 tests/tiers/*/scenario* | 建议方向: 按上轮 spec R4 重建锚点为真实 prose excerpt（novel-output 章节可提供语料）或显式合成标注后重锁 G0.14
  - F788 | calibration README 过期自相矛盾 + 尾部多余围栏 | error | P2 | 证据 tests/fixtures/calibration/README.md:9-11（"No anchors are authored yet … contains only this README and `.gitkeep`"）vs 磁盘实有 27 锚点（`find tests/fixtures/calibration -name "*.md" ! -name README.md | wc -l` → 27）；README.md:61 孤立 "```" 围栏未闭合 | 根因: Phase 2/3 填充锚点后未回写 README | 验证: 命令同上 + 读 README 尾行 | 建议方向: 更新 README 现状描述（锚点数、来源政策），修复围栏
- 验证命令: 见 findings 内联
- 置信度: high（虚构性由"语料零存在于真实输出"直接证明）

### tests/baselines/（10 文件）
- 处置: deep-read（机械核验 10 + 差分再生执行 5 条 shenbi-validate + 工具链阅读：regenerate-baselines.sh、compare_mutation_score.py、test_golden_parse.py）
- 声称检查的不变量: [基线反映 src 当前行为；基线可再生成；基线有消费者且语义可用]
- findings:
  - F782 | gate-outputs 7 份基线无自动化消费者且 4/7 已实质漂移，G6/G7 不可再生成 | error | P2 | 证据 (a) 唯一引用者是生成脚本 tests/regenerate-baselines.sh:7，tests/src/tools 无任何读取方；(b) 差分再生（timestamp 归一后语义对比）：G0.json 缺现行检查 G0.13/G0.14/G0.15/G0.16 且 G0.5 PASS→UNIMPLEMENTED、G0.5b PASS→WARN；G2-chapter.json G2.5 SKIP→PASS；G4-genre_config.json 整体 status FAIL→PASS（baseline 记录 G4.gc.not_found，现行新增 G4.gc.validated=PASS）；G2-internal/G2-truth 语义一致；(c) G6.json/G7.json 依赖 tests/rounds/round-001-2026-06-11（`ls tests/rounds/` → No such file or directory），脚本 `if [ -d ]` 守卫使其静默跳过，永久不可再生成 | 根因: 基线生成于 2026-06-15（PR-19 差分验证），此后 src 演进无再生成也无消费闭环，成为误导性死快照（如其设计用途被人工差分使用，G4 的 FAIL→PASS 翻转会得出错误结论） | 验证: `uv run shenbi-validate G0 outline-example.md` 等四条 + python 语义 diff（输出见 findings）；`ls tests/rounds/` → not exist | 建议方向: 要么删除 gate-outputs/（无消费者），要么建立再生成+差分的 CI 消费者并随 src 演进刷新；G6/G7 基线改用现存 round 或移除
  - F783 | mutation-score.txt 为 "BASELINE NOT YET ESTABLISHED" 占位注释，`just mutate-check` 恒失败 | error | P2 | 证据 tests/baselines/mutation-score.txt 全文为注释（"Status: BASELINE NOT YET ESTABLISHED"，mutmut 因 test_g4_fail_no_marker 子进程脆弱无法建基线）；tools/compare_mutation_score.py:42-44 空基线分支 `return 2` | 根因: PR-23/PR-35 遗留 TODO 挂起两个月，justfile:93-95 的存在性守卫通过但工具必然 exit 2，mutation 防回归通道整体不可用 | 验证: `uv run python tools/compare_mutation_score.py --baseline tests/baselines/mutation-score.txt` → "Baseline file has no parseable scores"，EXIT=2 | 建议方向: 修复 mutmut 隔离问题建立真基线，或暂从 justfile 移除 mutate-check 目标避免假可用
  - 正面结论: pending_hooks.parse.json golden 基线有效——`parse_records(truth-pending_hooks.md)` 与基线 3 条记录完全相等（MATCH），tests/unit/records/test_golden_parse.py 走真实代码路径无 mock
- 验证命令: 见 findings 内联
- 置信度: high

### tests/skill-behavior/ + tests/skill-triggering/（32 文件）
- 处置: deep-read（机械核验 32：全量与 tests/tiers 哈希比对 + ARCHIVE-MIGRATED.md 对照 + 消费者 grep）
- 声称检查的不不变量: [迁移副本与目标保持一致；测试内容真实性（这些 .md 是 tiers 场景的人工可读副本，非独立执行测试）]
- findings:
  - F781 | 32/32 全部为 tests/tiers 场景的逐字节副本，迁移记录明示保留但无同步守卫 | optimization | P2 | 证据 哈希比对：skill-behavior 22 + skill-triggering 10 共 32 文件与 tests/tiers/t1-skill/*/bug-hunt/input/* 一一逐字节相同（例：phase2-character-bug.md == shenbi-review-character/bug-hunt/input/scenario-phase2-character.md）；tests/ARCHIVE-MIGRATED.md:71 "Original files are NOT deleted — they remain in their original locations"；unit/integration/property/gates/golden 无任何同步校验测试 | 根因: T1 迁移时保留原文件作参考，形成 32 对双源，任一侧编辑即静默漂移（当前仍 32/32 一致，属风险非现实损坏） | 验证: /tmp 脚本 sha 比对输出 32 EXACT DUPLICATES + NOT-duplicated=[] | 建议方向: 删除原目录（ARCHIVE-MIGRATED.md 已有完整映射表）或加 CI 校验 32 对哈希一致
  - 测试真实性说明: 这两个目录不含可执行测试（无 .py），其"断言有效性"体现在 tiers 剧本内；上轮 F851/F852 所指剧本内部矛盾（phase3-plant-track-resolve 算术、revision-mode-routing 期望与 SKILL.md 契约冲突）位于副本对两侧同时存在，随 F781 一并处置
- 验证命令: /tmp 哈希比对脚本（32/32）
- 置信度: high

### tests/contracts/（2 文件）
- 处置: deep-read（2/2 全读 + 导入路径核验）
- 声称检查的不变量: [测试走真实代码路径；无 mock；断言有效]
- findings: 无
- 验证命令: 读 tests/contracts/test_cjk_normalization.py（9 用例直接 import shenbi.contracts.fields._normalize_ws 真函数；含 2 个精确等值断言 + 7 个特征断言；无 mock/无 monkeypatch）
- 置信度: high
- 备注: 部分用例仅断言目标字符缺席（如 test_normalizes_ideographic_space 未钉死替换结果），断言略宽但非空转，不足以立 finding

### tests/fixtures 其余顶层散件（64 文件：被引用 example 族、word lists、config json、market-data、空脚手架 .gitkeep×18、multi-chapter 目录等）
- 处置: deep-read（机械核验 64 + 深读 8：audit-report-example、qidian 榜单、genre-config 差分、sensitive/stop words、multi-chapter 五章互异性、空目录引用链）
- 声称检查的不变量: [G0.9；文件被真实消费；example fixture 与真实输出结构一致；scenario 引用的 fixture 路径存在]
- findings:
  - F784 | 19 个零引用死 fixture（词干级全库 grep 0 命中） | optimization | P2 | 证据（词干 grep tests/src/tools/justfile/pyproject/skills 全 0）: arc-example.md、book-spine-example.md、book-strata-example.md、canary-3-chapter-seed.md、market-data-example.md、multi-chapter-example.md（索引；其目录 5 章被 arc-payoff scenario 引用）、parent-canon-example.md、stop_words_zh.txt、truth-chapter_summaries.md、truth-character_matrix.md、truth-emotional_arcs.md、truth-particle_ledger.md、volume-summary-example.md、world-locations-example.md、world-power-system-example.md、world-rules-example.md、world-story-bible-example.md、chapter-8-example.md、chapter-9-example.md（后两者并入 F778 语料；上轮 F813 同口径 21 含 manifest/低锚点，本轮实测 19） | 根因: T1/T2 演进中被 scenario 弃用后未清理 | 验证: `for s in arc-example book-spine-example ...; do grep -rl "$s" tests src tools justfile pyproject.toml skills | grep -v fixtures | wc -l; done` → 全 0（sensitive_words=10、multi-chapter-example=1 除外） | 建议方向: 批量删除或归档
  - F785 | stop_words_zh.txt 违反自身格式 spec 且零消费者 | error | P2 | 证据 文件为单行 47 词逗号分隔（`忽然,因为,所以,...`），spec 要求每行一词；src/shenbi/pipeline/chapter_loop.py:2223 与 volume_align.py:31 各自硬编码停用词集，不读该文件 | 根因: 停用词逻辑内化进代码后 fixture 成孤儿且格式漂移 | 验证: `head -c 300 tests/fixtures/stop_words_zh.txt`；`grep -rn "stop_words" src/ --include="*.py"` → 仅硬编码字面量 | 建议方向: 删除，或改造为 chapter_loop/volume_align 共享数据源
  - F786 | sensitive_words.txt 仅 3 词，G6.12 敏感扫描近乎空转 | error | P2 | 证据 文件全文：台独/藏独/法轮功 三行；被 src G6.12 消费（词干 grep 10 命中） | 根因: 词表覆盖过窄，全文章节敏感词检查实际只防 3 个词 | 验证: `cat tests/fixtures/sensitive_words.txt` | 建议方向: 扩充词表或明示最小集定位
  - F787 | genre-config-example.json 与真实输出结构漂移 | error | P2 | 证据 与 novel-output/xinghuo-ranqiong/genre-config.json 键差分：fixture chapterTypes 为英文键（battle/dialogue/exposition/climax/discovery…），真实输出为中文键（战斗/对话/谋略/人物/世界观/反思…）；fixture 独有 tropeInventory 顶层键，真实输出无；其余 8 顶层键同名 | 根因: 手写示例未随真实 genre-config 产物演进，G4 校验器只验结构不验键语言，漂移静默 | 验证: python 键集合差分（fixture-only=chapterTypes.*英文, real-only=chapterTypes.*中文） | 建议方向: 改为真实输出的登记镜像（入 MIRROR_MAP）或同步键语言
  - F789 | 空脚手架目录被 scenario 当存在状态引用 | error | P2 | 证据 tests/fixtures/skill-triggering-prompts/ 仅含 .gitkeep（18 个 gitkeep-only 叶目录之一），但 tests/tiers/t1-skill/using-shenbi/bug-hunt/input/scenario.md:10 声称 "Present 10 natural language requests from the existing trigger test prompts in `tests/fixtures/skill-triggering-prompts/`"（实际 10 个 prompt 位于 tests/skill-triggering/prompts/，路径错位） | 根因: T1 迁移后 scenario 未随实际位置更新 | 验证: `ls tests/fixtures/skill-triggering-prompts/` → 仅 .gitkeep；grep 见上 | 建议方向: 修正 scenario 路径引用
  - F790 | qidian 榜单数据不可核验 | error | M | 证据 tests/fixtures/market-data/qidian-urban-fantasy-2026-06.md:8-15 作品/作者为真实知名网文（夜的命名术/会说话的肘子、万族之劫/老鹰吃小鸡 等）但 Reader Count 量级与真实不符（如我在东京当阴阳师 452,000，真实远高于此），无快照源链接 | 根因: 数据为手工编辑混合体 | 验证: 读文件 + 公开常识对照（仓库内无法独立核验——低置信度） | 建议方向: 加数据来源快照说明或降级为显式合成样本
- 结构一致性机械结论: 命名问题仅 truth-* 6 文件下划线词干（并入 F780）；空文件仅 contracts/__init__.py（包标记，正常）；multi-chapter-example/ 5 章互异（5 distinct sha，17-19KB）符合真实产物形态；覆盖清单 166/166 全在盘（磁盘多出的 3 个为 tests/contracts/__pycache__/*.pyc 非仓库对象）
- 验证命令: /tmp/z7d_mech.py + findings 内联命令
- 置信度: high（F790 medium）

---

## 汇总统计
- 机械核验: 166/166（覆盖、sha256、空文件、命名、孤儿词干扫描、副本哈希对、镜像闭包）
- 深读: 22 文件（4 calibration 锚点 + README、3 chapter drafts/examples、manifest、audit-report、qidian、genre-config 差分、word lists ×2、ARCHIVE-MIGRATED.md、regenerate-baselines.sh、compare_mutation_score.py、test_golden_parse.py、test_cjk_normalization.py、check_fixture_mirror.py、g0.py MIRROR_MAP 段）
- 执行命令: check_fixture_mirror.py（exit 0）、shenbi-validate ×5（G0/G2×3/G4 差分再生）、compare_mutation_score.py（exit 2）、parse_records golden 对比（MATCH）、/tmp 机械脚本 ×3、词干 grep ×19
- 低置信度簇: 仅 F790（qidian 数据真实性，仓库内不可核验）；multi-chapter-example/ 5 章的 LLM 产物真实性为 medium（形态自洽但无 provenance 标注，沿用上轮弱证据判断）
- 未覆盖文件: 无（166/166）
- 与上轮（2026-08-14 fixture-authenticity-design，状态 Design）关系: F776/F777/F778/F779/F780/F784/F785/F786/F787/F788/F789/F790 分别复核上轮 F807+T804/T801/T802+T802/F806+T803/F816/F813/F822+T810/F821+T811/F820/F809+T814/F761/F823 并证实**均未修复**；F781 复核 F850（32/32 副本现状）；F782/F783（gate-outputs 漂移量化 + mutation 占位）为本轮新增证据
