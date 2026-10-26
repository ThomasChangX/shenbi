# Spec #79 · 重生成基板与验收协议（regen-acceptance）

> **Date:** 2026-10-25（rev2 2026-10-26 价值门 REWRITE；rev3 2026-10-26 复审五 I 清偿——保留面拆分/派生缓存/原则式游标/灰烬◆前置） | **Status:** Active | **Severity:** 🟠 P1（收口） | **方法:** 隔离/重置 CLI + 判据聚合器 + 执行协议文档 | **系列:** 市场适配层（novel-market-overhaul） | **依赖:** #72-#78 全部 | **范围:** regen-reset CLI / regen-accept 聚合器（三缺口补齐）/ 执行协议文档+评分卡 rubric / **范围外：重生成运行本体（用户启动的独立执行项目——核心原则 8）**

> 源自总设计 §3/§4。用户决策：旧九章全部丢弃，根治后删除重新生成。**价值门裁定（2026-10-26）**：原 spec 完成定义（八项判据全过+物理清理+复盘）依赖前 24 章真实重生成——付费多会话 chapter_loop 运行，SDD 核心原则 8 禁止且 F947 必然阻塞。本 spec 重写为**基板（substrate）交付**：删除/重置工具 + 判据机器可查聚合器 + 执行协议；运行本体委托给用户启动的独立执行项目（probe-vol1-driver-prompt 先例）。

## 1. regen-reset CLI（`just regen-reset <dir> --tag pre-regen-2026-10`）

一次性幂等工具（`--dry-run`；tag 已存在即 FAIL 不覆盖——_quarantine 已有零散 drafting dump）：
- **隔离面**：`chapters/`+`plans/`+`adjudications/`+`audits/`+`gate-markers/` → `_quarantine/<tag>/`（相对布局保留）；`pipeline-manifest.json`/`trace.jsonl`/`cost/` 归档同目录（manifest 陈旧行会让 release_split 打包已隔离章）
- **游标复位**：`pipeline-state.json` **原则式：除 genesis/config 块外全键零态复位**（chapter_loop 归 ch0 含 current/chapter_states/retry_budget_consumed/retry_counts/soft_fail_trackers/modify_feedback/retry_feedback/checkpoint_history/pending_checkpoint，顶层 pending_re_dispatches/trigger_steps_done/closure*/last_trigger_failure 同清——单测对真实 state 键集做差集断言：复位后非 genesis/config 键必须为初始零态；**genesis 块保留**——不重跑付费 genesis）；`progress.json` 重生成为一致态（现文件 stale——不可拷贝）；`snapshots/manifest.json` 清 last_drift_chapter
- **派生缓存清理**：`truth-embeddings.db` 删除重建（Route B 余弦检索的旧章 chunk 会注入每章重生成上下文——恰毒化重生成目的）、`truth-index.json` 删除重建（hooks 采集自 pending_hooks）、`context/` 旧章上下文删除、`*.lockfile` 清零态
- **章层 truth 重置**：~16 章键控文件（pending_hooks 8 列壳/current_focus/current_state/character_matrix 交互总表/chapter_summaries/emotional_arcs/subplot_board/bridge_tracker/particle_ledger/resonance_anchors/resonance_trend/drift_guidance/audit_drift/state_snapshot-pre-rev/state-settling-decisions + #75 两表 timeline/prop_registry——经 truth_io._TABLE_HEADER_BOOTSTRAP 表头引导，填充态与缺席态都处理）。character_matrix **双表拆分**：交互总表（章键滚动——现含旧运行第10章行）重置，**信息边界段保留**（角色层）。current_state 现含旧运行第 1-4 章状态行——#74 重锚后章号语义全错，必须重置。
- **outline/thread_map.md** 章键行重置（C 节跨度保留卷纲行——#74 重锚不动）
- **保留面**：世界/角色/卷层（book_spine/author_intent/characters/ 角色卡/volume_summaries/name_registry/volume_map/story_frame/rhythm_principles——#74 已修复）

## 2. regen-accept 聚合器（`just regen-accept <dir> --through N`）

三态退出（report_longitudinal 先例），逐判据行输出 PASS/FAIL/SKIP(run-project-only)：
- 判据 1/2a-floor/2b：manifest 扫描（G4.xc/G4.cd 键 latest-wins 零 FAIL）；2a-ceiling 离线复算（G4 只查地板）
- 判据 3：lint_volume_nodes + **灰烬利害冲突首现 ≤12 检查**（本批新增——_SLOT_DEADLINES 扩「灰烬」键；**前置数据补丁：volume_map 第 6 章行现无 ◆ 槽位标记，本批就地补「灰烬◆」**（L56 行文本已有「利害冲突形态出场」语义，只缺槽位记号——_check_slots 按 ◆ 子串匹配且零行即 FAIL，不补标记则新检查恒 FAIL），#74 数据型 spec 先例：就地编辑+命令取证贴 progress）
- 判据 4：lint_voice_meme chapter+volume 模式聚合
- 判据 5：**真章盲认模式**（本批新增——真章对白按卡面标记 argmax 归属，五角色 ≥4/5；构造语料分类器测试保留为 CI 面）
- 判据 2c 情绪高点：**代理解析**（memo emotion_tone ∉ 冷集 或 金句位=燃——确定性正/负代查，正文级检测留运行项目）
- 判据 6：release_split 跑临时发布目录 + 场景原子/钩闭合断言（producer 非静态 lint）
- 判据 7：just check 手动行标注
- 判据 8：RUN-PROJECT-ONLY 行（G3.4 独立评分——评分卡 rubric 文件本批交付，执行在运行项目）

## 3. 执行协议文档（docs/regen-vol1-driver-prompt.md）

probe-vol1-driver 模式扩展：运行入口检查清单（reset 完成+聚合器空基线绿）/首个场景簇（ch1-2）人工停检点/每 10 章成本检查点（$ 上限声明）/多会话恢复游标/判据 8 评分卡轴+G3.4 dispatch 配方/复盘模板；显式横幅「本运行在 SDD 外，由用户启动」。评分卡 rubric 独立文件（诡秘/捞尸人开篇轴）。

## 4. 验收（基板完成定义——重写）

- regen-reset：tmp_path 结构用例全绿（隔离面/游标/章层 truth/保留面四组断言）+ 真项目布局衍生 fixture 用例
- regen-accept：空基线（隔离后 ch0）三态正确；三新增检查（灰烬截止/真章盲认/情绪代理）各有单测
- 协议文档+rubric 落盘；`just check` EXIT=0
- **范围外（委托运行项目）**：重生成运行、判据 8 评分执行、验收后旧章物理清理（quarantine 目录）、复盘内容
