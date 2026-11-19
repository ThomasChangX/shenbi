# spec #116 gate-power 负例 fixture 包（G0.9 真实章确定性变异）

- **来源**：`novel-xinghuo-vol1/chapters/chapter-1.md`（Task 3 批 F 另用 `chapter-2/3.md`；plans/卡前置物另见下）——gitignored 卷一真实运行项目，生成时一次性直读
- **生成日期**：2026-11-19/20（维护者侧一次性；确定性：同源同输出，无 RNG）
- **生成器**：`tools/gen_gate_power_fixtures.py`（spec #116 T4；变异窗口面 import Task 1 `narrative_window`——测量面=执法面，C3）

## 再生成命令

```bash
# Task 2 首批（hook/protagonist/transition）
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-hook-killed.md --mutation hook_killed
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-protagonist-vanished.md --mutation protagonist_vanished --full
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-transition-flooded.md --mutation transition_flooded --full
# Task 3 批A 散文门
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-scene-visuals-stripped.md --mutation scene_visuals_stripped
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-scene-markers-removed.md --mutation scene_markers_removed --full
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-fatigue-flooded.md --mutation fatigue_flooded
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-meta-injected.md --mutation meta_injected
# Task 3 批B 结构门（--full，NB6）
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-word-count-truncated.md --mutation word_count_truncated --full
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-post-removed.md --mutation post_removed --full
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-pre-removed.md --mutation pre_removed --full
# Task 3 批C 声口/场景钩声明门（plans 前置物＝变异产物本体）
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-voice-stripped.md --mutation voice_stripped
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/plans/chapter-1-plan.md tests/fixtures/gate-power/plans/chapter-1-plan.md --mutation hookdecl_mismatched --full
# Task 3 批D 声明对账门（--full）
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-post-quote-broken.md --mutation post_quote_broken --full
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-post-transition-lied.md --mutation post_transition_lied --full
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-golden-emptied.md --mutation golden_emptied --full
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-post-wordcount-lied.md --mutation post_wordcount_lied --full
# Task 3 批E WARN-only 组
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-surge-killed.md --mutation surge_killed
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-simile-flooded.md --mutation simile_flooded
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-ending-ledgered.md --mutation ending_ledgered
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-2.md tests/fixtures/gate-power/chapter-2-ending-ledgered.md --mutation ending_ledgered
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-3.md tests/fixtures/gate-power/chapter-3-ending-ledgered.md --mutation ending_ledgered
# Task 3 批F 跨章重复门（--donor 比对章）
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-3.md tests/fixtures/gate-power/project-output/chapters/chapter-3.md --mutation verbatim_copy --full
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/project-output/chapters/chapter-1-duplicated.md --mutation content_duplicated --full --donor novel-xinghuo-vol1/chapters/chapter-3.md
```

`characters/protagonist.md` 为手工落盘前置物（C2：`_load_protagonist_names` 非 SKIP 前提；Task 3 批C 扩 frontmatter `voice_profile.catchphrases` 四口癖原串——`G4.cd.voice_density` 计分前提），frontmatter 注明衍生自真实卡的 name 行＋catchphrases 行。`pipeline-state.json` 为手工落盘最小 hooks 台账（`declared_history` 读取形：`chapter_loop.chapter_states.0.declared.章尾钩型`＝悬念钩，供 `G4.cd.hook_type_rotation` 前一章历史）。

## 清单与算子

| fixture | 变异 | 面宽 | 算子（落点） | 靶向门臂 |
|---|---|---|---|---|
| `chapter-1-hook-killed.md` | `hook_killed` | 裁片（M4：叙事尾窗 11 段＝3 上下文＋8 被测窗） | 尾 8 叙事段：张力词→就、？→。、数字串→数 | `G4.cd.no_hook` |
| `chapter-1-protagonist-vanished.md` | `protagonist_vanished` | 全章 | 那罕→术赤、他→此人（全文含 META 块） | `G4.cd.protagonist_absent` |
| `chapter-1-transition-flooded.md` | `transition_flooded` | 全章 | 每叙事段首轮注 不过，/此时，/突然，/终于，/于是，（取自 `count_transition_words` 计数面 TRANSITION_SPECIFIC，I5） | `G4.transition` |
| `chapter-1-scene-visuals-stripped.md` | `scene_visuals_stripped` | 裁片 | 尾窗 11 段：视觉动词（走跑推拉抓坐站躺倒看听触/发现看到听到）→在、「」剥除 | `G4.cd.no_visual_scene` |
| `chapter-1-scene-markers-removed.md` | `scene_markers_removed` | 全章 | `<!--SCENE-->` 标记行删除（2→0） | `G4.cd.scene_count:0<2` |
| `chapter-1-fatigue-flooded.md` | `fatigue_flooded` | 裁片 | 尾窗前 9 段段尾追加「他心中暗道。」×9（FATIGUE_BASE 暗道面） | `G4.fatigue:9>8` |
| `chapter-1-meta-injected.md` | `meta_injected` | 裁片 | 末段前插 META_NARRATIVE 闭集词段（由此可见/综上所述，I1） | `G4.meta` |
| `chapter-1-word-count-truncated.md` | `word_count_truncated` | 全章 | 保 PRE/POST 块＋首 3 叙事段，余截断 | `G4.word_count:466<3000` |
| `chapter-1-post-removed.md` | `post_removed` | 全章 | POST 整块删除（H2 段→META-END 段闭区间） | `G4.post_check` |
| `chapter-1-pre-removed.md` | `pre_removed` | 全章 | PRE 整块删除（同上块手术） | `G4.pre_check` |
| `chapter-1-voice-stripped.md` | `voice_stripped` | 裁片 | 四口癖原串→中性语（这笔我先记下/折旧完了，人就自由了/此账必有还之日/行，先算账） | `G4.cd.voice_density:1<2` |
| `plans/chapter-1-plan.md` | `hookdecl_mismatched` | 全本（plan 源） | v3→v4 升（plan_format＋张力拍『』锚定＋章尾钩型行）＋场景2 收束钩改「悬念」形 | `G4.cd.scene_hook_match:场景2`（另承载 `G4.cd.quote_verbatim`/`hook_type_rotation` 负例） |
| `chapter-1-post-quote-broken.md` | `post_quote_broken` | 全章 | POST 金句位引句改一字（路通行通→路通行不通） | `G4.cd.post_quote_verbatim` |
| `chapter-1-post-transition-lied.md` | `post_transition_lied` | 全章 | 「差三文？」段首注 不过，（POST 仍报 0） | `G4.cd.post_transition_cross` |
| `chapter-1-golden-emptied.md` | `golden_emptied` | 全章 | PRE 本章金句位值→无 | `G4.cd.golden_slot` WARN |
| `chapter-1-post-wordcount-lied.md` | `post_wordcount_lied` | 全章 | POST 总计 3625→1812 | `cd.post_wordcount_precision` WARN |
| `chapter-1-surge-killed.md` | `surge_killed` | 裁片 | 尾窗 ≥35 字句内 ，→。（surge 计数面） | `G4.cd.surge` WARN |
| `chapter-1-simile-flooded.md` | `simile_flooded` | 裁片 | 尾窗追加 6 喻体句（SIMILE_MARKERS「像」面） | `G4.cd.simile_band` WARN（>4 堆叠侧） |
| `chapter-{1,2,3}-ending-ledgered.md` | `ending_ledgered` | 裁片×3 | 末段追记账目收束句（外欠 30 文/剩 17 文） | `ending_archetype_of` 三连「账目形态」（helper 级） |
| `project-output/chapters/chapter-3.md` | `verbatim_copy` | 全章 | 无变异整本拷贝（比对章前置物；G0.9 real-output copy） | —（I3 基数门槛分母） |
| `project-output/chapters/chapter-1-duplicated.md` | `content_duplicated` | 全章＋复制段 | 从 chapter-3 复制 13 段（raw 指纹成员段）append 章尾 | `G4.cd.content_overlap:42%` |

每个 fixture 头部带 `provenance: real-output-mutation (G0.9)` 注释块（源/变异/面宽/生成日期）。

**已知偏差**：pre-commit end-of-file-fixer 为裁片段 join 无源尾换行的件补尾换行（hook-killed 及批C/D 的块手术件）——内容保真，非字节级精确，同 spec83 fixture 包先例；再生成产物与提交件相差至多一个 EOF 换行。

## 裁片与 `--full` 裁定

- **hook_killed 默认裁片**：变异落点本就在章尾 8 段窗内，裁片即被测面（frontmatter＋尾窗，M4/I7）；实测 263 字合并窗口 ≥30 CJK，门真实执法（非轻窗跳过）。
- **protagonist_vanished / transition_flooded 默认 `--full`**：二者的门判定是**全章计数**语义（主角名/他 出现总数 ≥3；转折词全章计数 > max(5, wc//1000)）——裁片截断会破坏计数分母（前文未进裁片即无所谓残留），故裁定不裁片、以全章承载（NB6）。
- **Task 3 结构类变异默认 `--full`**（NB6 落实）：`scene_markers_removed`/`word_count_truncated`/`post_removed`/`pre_removed`/`post_quote_broken`/`post_transition_lied`/`golden_emptied`/`post_wordcount_lied`/`content_duplicated`——结构面（标记行/META 块/POST 声明行/指纹占比）在裁片上要么缺席要么分母失真，红须来自变异非裁片副作用。
- **plans fixture 恒 `--full`**：plan 是声明面文件，裁片算子（narrative_window）不适用。

## 已登记裁定与伪影（Task 3）

1. **chapter-0.md 缺席**：brief 称比对章 `chapter-0.md` 在盘——实勘不存在（`find` 全 repo 无该文件）。改用真实 `chapter-3.md` 整本拷贝为比对章（指纹 20 段≥50CJK、与 ch1 事故性交集 0；ch2 仅 10 段不满足 k>2/3·m）。比对章对门只按指纹集合参与，章号身份无关。
2. **provenance 头伪影（surge）**：头块 4 行 ASCII ≥35 字会被 `segment_sentences` 计为 surge 句（`strip_narrative_body` 不剥通用 HTML 注释——设计面非门缺陷，真实章无此头）。surge WARN 红测在测试内剥头跑 tmp 副本；变异本身在裁片上已把 narrative surge 归零（基线 1/1 PASS → 变异 0<1 WARN）。
3. **quote_verbatim 负例臂**：brief 助手表写「缺『』锚定」（arm :1204），但 plans fixture 规格行要求『』锚定引句在场——单文件不可兼得。落地取锚定在场而章尾无此句的 arm :1200：引句取自真实 plan 段6 原句（该句与章尾实拍本就不同文——**真实病理**，非生造）；v3 plan 下该门未激活（v[4-9] 门），v4 化即开火（因果三查存证）。
4. **post_wordcount_precision 基线已 WARN**：真实章 POST 总计 3625 vs 门实测（含 provenance 头）4065 差 12.1%>2%——附录 A「post_wordcount WARN 行」同源。变异测试钉**改半值 1812**（差 124.6%）断言 WARN 行含变异值（值级因果）。
5. **plans fixture 共用 co-fire 面**：`plans/chapter-1-plan.md` 落盘后所有 `chapter-1-*` fixture 的 g4 实跑都会携带 plan 侧 mf（scene_hook 场景数臂（裁片无 SCENE 标记）/quote_verbatim/hook_type_rotation）——红测断言用 `any(m.startswith(靶臂))`，co-fire 不影响；各 fixture 的靶向臂因果由 /tmp 基线三查单独存证。
6. **content_duplicated 指纹口径**：门对比对章按 `_fingerprint_of` **raw 面**（无 strip_scene_markers）入集合——场景标记邻接段在裁片面拆分、raw 面合并，非 raw 指纹成员段复制后不计交集。变异取 raw 指纹成员段为复制候选（成员判定=同进程 hash 集合包含，语义=字符串等值，跨进程确定）。

## 公开 repo 内容政策声明（M4/I7）

本 repo 为 public；变异 fixture 为真实章（frontmatter＋被测窗或全章，逐 fixture 注明）的确定性变换，不脱敏——对齐 `tests/fixtures/` 既有 vol1 衍生先例（cross-chapter-regression、spec83 等）；若用户裁定需脱敏，后续批占位符替换非被测文本再生成（本 README 即该出口的登记位）。
