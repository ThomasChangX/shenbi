# 不变量普查（13 维 × 四槽契约）

> spec #80 §2。每维四槽：**载体**（命实文件/机制——非 13 维全 facts 承载）/ **声明**（memo 结构化行）/ **门检**（check id 或工具）/ **审计**（审计契约 reads）。**任何维度缺槽 = 文档化的已知洞**，不是失职隐瞒——期相列声明该洞何时到期补齐。

**期相语义（lint 机制）**：`期相 ≤ 当前期` 而缺槽 = `tools/lint_invariant_coverage.py` 红（进 `just check`）；`期相 > 当前期` 的缺槽 = 已排期的已知洞。**当前期由 lint 内 `CURRENT_PHASE` 常量定义**（随批次 bump，离线确定性），现行 **CURRENT_PHASE = P1**。

**字面量权威层级**（只引用不定义）：facts op/dim 枚举值集的唯一权威 = `src/shenbi/facts/` Python StrEnum → `docs/framework/status-vocab.md` 域清单注册行 → 本表**只引用不定义**（doc↔code 双源漂移由 `lint_status_strings` 红）。

**mutant 义务谓词**（spec rev4 R3-I1）：义务只挂「F15+ 族新引入 check id 的维度或 facts 承载维」——P1 到期 = 恒等/持有与经手/枚举计数三行，P2 到期 = 能力活性（F18）。既有 XC 门控维度（时间/叙事纪律等普查行内维度）由既有红测文档化覆盖（该行注记红测文件）；未入普查面的 XC 检查族（卡属性等）同由其红测覆盖、不占行。**13 维 ≠ 13 mutant**。

| # | 维度 | 载体 | 声明 | 门检 | 审计 | 期相 | mutant 义务 |
|---|------|------|------|------|------|------|-------------|
| 1 | 恒等 identity | `truth/facts/identity.json`（narration_name+别名集；facts 缺席降级载体=`truth/name_registry.md`） | settle `facts_ops.identity`（op 值集见 status-vocab.md 域清单）+ 备忘 `[旧名回溯]` 闪回豁免标记 | `XC.narration_name`（F15）+ `ss.identity_row_match`（G4.ss 对账） | shenbi-review-pov reads（character_matrix/current_state 切片；P2 F19 起 continuity/foreshadowing 增 facts 查询面） | P1 | Yes（name-swap） |
| 2 | 时间 | `truth/timeline.md`（时间锚） | 备忘 `- 时间锚: [回拨]…` 闪回豁免行 | XC 时间锚单调（`check_cross_chapter`，`XC.registry` 降级先例） | shenbi-review-continuity reads（current_state/chapter_summaries 切片） | P1 | No（红测 `test_xc_timeline.py`） |
| 3 | 空间 | `world/locations.md`（registered world 文件） | —（无备忘结构化声明面） | —（无门检） | —（无审计 reads） | P3 | No |
| 4 | 持有与经手 props | `truth/facts/props.json`（facts 缺席降级载体=`truth/prop_registry.md`，XC 不变量 4 回退层全 severity） | 备忘 `物件@op` 声明行（planning 段 6 模板）+ settle `facts_ops.props` | `cp.prop_decl` + `cd.prop_handoff`（F16）+ `ss.prop_row_match` + `ss.facts_ops`（F16s simulate） | shenbi-review-continuity reads（P2 F19 增 facts 查询面） | P1 | Yes（prop-chain-break；P2 增 settle-illegal-op） |
| 5 | 枚举计数 counters | `truth/facts/counters.json` | 备忘 `计数: 名 N+1` 声明行 + settle `facts_ops.counters` | `cd.counter`（F17 三方对账：prose 总数族 ≡ facts 现值 ≡ memo N+1） | shenbi-review-continuity reads（P2 F19 增 facts 查询面） | P1 | Yes（counter-dup） |
| 6 | 知识态 who-knows-what | —（无载体） | — | — | — | P3 | No |
| 7 | 承诺与债务（钩） | `truth/pending_hooks.md`（钩总览+详情；归档面=pending_hooks_archive.md；P3 迁 facts） | 备忘 §7 钩账行（MH-ID+生命周期列） | `cd.chapter_end_hook`（SOFT）+ `cd.hook_fulfillment` + foreshadowing-lifecycle 检查 | shenbi-review-foreshadowing reads（pending_hooks.md/subplot_board.md） | P1 | No（红测 `test_hook_fulfillment.py`/`test_foreshadowing_lifecycle.py`） |
| 8 | 情绪节奏 | `genre-config.json`（pacing/emotion_band）+ 备忘 §1（P3 迁 facts） | 备忘 `emotion_tone` / `payoff 拍` / `留存锚` 行 | `cp.emotion_tone` + `cp.payoff_beat` + `cp.retention_anchor`（商业三硬闸） | shenbi-review-pacing reads（genre-config pacing 切片）+ shenbi-review-highpoint（蓄压-释放比对 payoff 拍） | P1 | No（红测 `test_chapter_planning_craft_fields.py`） |
| 9 | 能力活性 | `genre-config.json` `pacing.core_motif_touch`（P2 F18 新增键，现为洞） | 备忘体感触点拍（P2 volume_outlining 卷级分解步，现为洞） | G4.cp 滑窗 max_gap 检查（P2 F18，现为洞） | —（P2 随 F18 接线） | P2 | Yes（motif-dormant，P2 落地） |
| 10 | 叙事纪律（POV/声口） | `truth/name_registry.md`（禁用保留名/登记名）+ `genre-config.json` 声口纪律 | 备忘 `POV:` 行 | XC 主角称谓/POV 基线（protagonist_binding/reserved_name_hijack）+ voice 引用检查 | shenbi-review-pov reads（character_matrix/current_state 切片） | P1 | No（红测 `test_xc_pov_name.py`/`test_spec76_voice_quote.py`） |
| 11 | 字量结构 | 章节正文 + `genre-config.json` 平台字数带（default/min/max per platform） | 备忘 `场景N: N字｜…` 行 | G2.6（章字数）+ volume-budget 护栏（卷级 ±3 漂移/保量 floor） | shenbi-review-pacing reads（chapter+genre-config 切片） | P1 | No（红测 G2 字数族 + volume-budget） |
| 12 | 发布卫生 | `publish/<platform>/` 档位更（release-split 产物，spec #70） | —（档位派生自 genre-config 平台带，无备忘声明面） | `just release-split` 约束窗口选择（工具级校验） | — | P3 | No |
| 13 | 防剧透 | —（无载体） | — | — | — | P3 | No |

## 维护规约

- **改表即改 lint**：门检 check id 增删（新 G4/G2 检查、XC 检查）必须同批反映到本表门检列——`lint_invariant_coverage`（T12）扫全仓 check id 对照本表，表内不存在的 check id = 未登记面红；本表声明而代码不存在的 check id = 幽灵红。
- **期相 bump**：P2 批次开工时 `CURRENT_PHASE` 常量 P1→P2（能力活性行四槽到期）。
- **mutant 名归一**：本表与 `tests/gates/test_invariant_mutants.py` 的 mutant 名互查时按 hyphen↔underscore 归一（`name-swap` ↔ `test_mutant_name_swap_killed_by_`）——lint_invariant_coverage 的义务面即按此归一 grep。
