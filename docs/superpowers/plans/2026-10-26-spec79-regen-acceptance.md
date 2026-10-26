# Spec #79 实施计划 — 重生成基板与验收协议

> Spec: `docs/superpowers/specs/2026-10-25-spec79-regen-acceptance.md`（rev3 GO）
> 全部 task infra → 协调者亲做；F947：全离线，零 dispatch
> 工具落点：`tools/`（purity lint 不约束 FS 变更；report_longitudinal/volume_budget 先例），src 只读侧 import

## Task 1: regen-reset CLI（tdd_red_green）

- **Create** `tools/regen_reset.py`（`python tools/regen_reset.py <dir> --tag pre-regen-2026-10 [--dry-run]`）：
  - **隔离面**：`chapters/`+`plans/`+`adjudications/`+`audits/`+`gate-markers/`+`cost/`+`pipeline-manifest.json`+`trace.jsonl`+`trace.jsonl.lockfile`+`pipeline-manifest.json.lockfile` → `_quarantine/<tag>/`（相对布局保留；shutil.move）；tag 已存在即 FAIL exit 1；`--dry-run` 只打印计划不落盘；完成后在 `_quarantine/<tag>/RESET-MANIFEST.txt` 写动作清单（取证面）
  - **游标复位**：`pipeline-state.json` 保留键集 `{genesis, config, version, project_dir, phase}`，其余顶层键（chapter_loop/checkpoint_history/closure/closure_step/closure_skills_done/closure_retry_counts/last_trigger_failure/pending_checkpoint/pending_re_dispatches/trigger_steps_done）删除后写入**框架零态 chapter_loop 壳**（复用 phase_runner/cmd_resume 的起步态构造——执行时定位 `_auto_rebuild_progress_if_stale` 同族；不重造）——genesis 块保留（不重跑付费 genesis）
  - `progress.json` 重生成为一致态（同零态构造函数出口）；`snapshots/manifest.json` 清 `last_drift_chapter` 键
  - **派生缓存**：`truth-embeddings.db`/`truth-index.json` 删除（重建：`truth_index.build_index(project_dir)` 立即重建 index；embeddings 若无独立构建入口则删除留待首章 context_assemble 惰性重建——执行时确认并记 deviations）；`context/` 目录删除；其余 `*.lockfile` 清零态（`{}`）
  - **章层 truth 重置 ~17 文件**：经 `truth_io._TABLE_HEADER_BOOTSTRAP`——文件存在→重写为 frontmatter+表头壳；缺席→跳过（bootstrap 保证首写自动建壳）。非表键控文件同族处理：`pending_hooks.md` 8 列壳（bootstrap 有）；`current_focus.md`/`state_snapshot-pre-rev.md`/`state-settling-decisions.json`（空对象 `{}`）/`audit_drift.md`（YAML create_or_overwrite 面→初始空结构）/`drift_guidance.md`；`character_matrix.md` **双表拆分**：交互总表段→表头壳，信息边界段原样保留（段落定位 `## 交互总表` 到下一 `## ` 前）
  - `outline/thread_map.md`：A/B 节章键行清零（保留节标题），C 节卷纲行保留（#74 结构）
  - **保留面不动**：book_spine/author_intent/characters//volume_summaries/name_registry/volume_map/story_frame/rhythm_principles——reset 后断言字节不变
- **Create** justfile recipe `regen-reset <dir> <tag>`（shebang 子 shell 三态传播，e2e-report 先例）
- **Test** `tests/tools/test_regen_reset.py`：tmp_path 四组断言（隔离面落位/游标差集断言——walk 后非保留前缀键必空、genesis 块原样/章层表头壳+缺席跳过+character_matrix 双表拆分/保留面字节不变）+ tag 冲突 FAIL + dry-run 零变更 + **真项目布局衍生 fixture**（`tests/fixtures/regen/`：从 novel-xinghuo-vol1 拷贝真实 pipeline-state.json、pipeline-manifest.json、character_matrix.md、thread_map.md 片段——G0.9 真实输出拷贝）跑全流程断言
- Iron Law 验证行：真项目 **--dry-run** 取证贴 progress（真落盘属运行项目入口动作，SDD 内不执行）

## Task 2: regen-accept 聚合器 + 三新增检查（tdd_red_green）

- **Modify** `tools/lint_volume_nodes.py`：`_SLOT_DEADLINES` 扩 `"灰烬◆": 12`
- **数据补丁**（#74 数据型先例：就地编辑+命令取证贴 progress）：`novel-xinghuo-vol1/outline/volume_map.md` L56 「灰烬「下辈子再见」定约」→「灰烬◆——「下辈子再见」定约」（对齐 L54/55/57 槽位记号格式）；取证 `just volume-nodes` 跑绿
- **Create** `tools/regen_accept.py`（`python tools/regen_accept.py <dir> --through N`；三态退出 0 pass/1 fail/2 data error——report_longitudinal 先例）：逐判据行 `PASS/FAIL/SKIP(RUN-PROJECT-ONLY)`：
  - 判据 1/2a-floor/2b：`pipeline-manifest.json` `gates.chapter_loop.{ch}.{skill}.G4.result` latest-wins 扫描——G4.xc/G4.cd 键零 FAIL；2a-**ceiling 离线复算**：chapters/*.md 正文字数 vs genre-config `market_params` 上限声明（键缺席→该子行 SKIP+指引）
  - 判据 3：调 lint_volume_nodes（import 或 subprocess）+ 新键灰烬◆
  - 判据 4：lint_voice_meme chapter+volume 模式聚合（subprocess 退出码）
  - 判据 5 **真章盲认**（新）：chapters/chapter-N.md 对白 span（`voice_lexicon.find_quote_spans` 同族口径）+ 归属行匹配角色名 → 对白文本按卡面标记（catchphrases_from_card+ACCOUNTING_VERBS/OPENING_VERB_FAMILIES 命中计数）argmax 归属 → 与实际归属对照；五主角各 ≥4/5 通过
  - 判据 2c **情绪代理解析**（新）：plans/chapter-N-plan.md `emotion_tone ∈{悲,喜,怒,惧,平}`——冷集 {悲,惧,平}；PASS=emotion_tone ∉ 冷集 或金句位=燃（#76 金句位声明行）；确定性正/负代查（正文级检测留运行项目）
  - 判据 6：release_split 跑临时发布目录（tmp）+ 场景原子/钩闭合断言（import producer 函数，非静态 lint）
  - 判据 7：`SKIP` 行+取数命令打印（just check 手动行）
  - 判据 8：`RUN-PROJECT-ONLY` 行（G3.4 独立评分——rubric 本批交付）
- **Create** justfile recipe `regen-accept <dir> <through>`（shebang 三态）
- **Test** `tests/tools/test_regen_accept.py`：空基线（隔离后 ch0）三态正确（0 章数据面→exit 2 data error/部分章→fail 行/全过→pass）；三新增检查各单测（灰烬◆槽位 deadline/盲认 argmax 归属含边界——冷角色标记零命中/情绪代理冷集与燃短路）；manifest latest-wins 单测（同章重跑后旧 FAIL 不计）

## Task 3: 执行协议文档 + 评分卡 rubric + 验收全量（characterization）

- **Create** `docs/regen-vol1-driver-prompt.md`：probe-vol1-driver 模式扩展——运行入口检查清单（`just regen-reset <dir> pre-regen-v1` 真落盘→`just regen-accept` 空基线绿→起步）/首个场景簇 ch1-2 人工停检点/每 10 章成本检查点（$ 上限声明+取数命令）/多会话恢复游标协议/判据 8 评分卡轴+G3.4 dispatch 配方（`--test-type generative`+独立子 agent 铁律）/复盘模板；顶部横幅「本运行在 SDD 外，由用户启动」（核心原则 8）
- **Create** `docs/regen-vol1-scoring-rubric.md`：诡秘/捞尸人开篇轴评分卡（tests/tiers/t1-skill/*/rubric.md 形态；0-100 维度表）
- **验收**：`bash tests/lock-tool-hashes.sh`（src 无改动则跳过说明）；`just check` EXIT=0；真项目 `--dry-run` 取证+`just volume-nodes` 跑绿（灰烬◆数据补丁）贴 progress

## 验收覆盖表

| spec § | task | 验证 |
|---|---|---|
| §1 隔离/游标/缓存/章层/保留 四组+fixture | T1 | pytest tmp_path+fixture；真项目 dry-run 取证 |
| §2 灰烬◆≤12 | T2 | _SLOT_DEADLINES 单测+volume_map 数据补丁跑绿 |
| §2 真章盲认 ≥4/5 | T2 | pytest argmax 归属 |
| §2 情绪代理 | T2 | pytest 冷集/燃短路 |
| §2 判据 1/2/3/4/6/7 聚合+三态 | T2 | pytest 空基线/latest-wins/exit code |
| §3 协议文档+rubric | T3 | 文件落盘+横幅断言 |
| §4 基板完成定义（全离线） | T3 | just check EXIT=0；零 dispatch 声明 |
