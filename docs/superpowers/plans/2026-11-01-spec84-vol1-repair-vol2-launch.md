# Spec #84 卷一清偿与卷二开卷 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地 spec #84 r11——章头注入器参数化适配 + 卷一 13 项内容修复（含 G3.4 无主 P2 外科批）+ 卷二开卷协议（驱动 prompt 实例化 + ch37-44 实弹）。

**Architecture:** 三层交付——①repo 面（注入器 `chapter_header_style` 参数化 + genre-config 契约同步 + 卷二驱动 prompt 文档，走 git/CI）；②运行项目面（novel-xinghuo-vol1/ 内容定点手术 13 项 + truth/声明面同步 + 台账，gitignored，验收=gates CLI 真门 + grep 断言）；③生产面（ch37-44 经管线实弹，用户门控）。T0 内容批执行前提=**用户确认启动修复轮**（spec §0）；卷二实弹=**用户独立决策**（vol1-ledger :159）。

**Tech Stack:** Python 3.11+/pathlib/json（框架）；pytest（测试）；`shenbi-validate G4`（真门取证，不走管线——管线内 shadow 键缺席默认降 WARN）；`just regen-accept`（判据聚合）。

## Global Constraints（每 task 隐含包含）

- 单章改动面 **≤15% 正文**，超限即停手上报（spec §4）；修章头等机械面**不碰正文内容**
- 修复纪律（R1-R4 沿用）：内容定点改 → plan/PRE/POST 声明面同步 → G4 真门重跑 PASS → truth 同步（涉及处）→ 台账记录
- **手工通道纪律**：任何章文件写路径（含熔断后手工束派生）必须复用同一章头规范化入口
- **T0 执行前提=用户确认启动修复轮**；G3.4 复评=可选用户令；禁止为「验证」目的触发真实 dispatch（生产 dispatch 是交付物不是验证）
- 取证一律 `shenbi-validate`/`just`/`uv run`（与 CI 同构）；pathspec commit（禁 `git add -A`）；novel-xinghuo-vol1/ 全部 gitignored——内容 task 无 git commit，验收证据贴 progress.md `## 验收证据` + 台账
- 章头目标形钉死：章号行 `^# 第[0-9]+章$`（阿码）+ `# 章题`；断言=chapters/chapter-{1..36}.md（排 -pre-rev）无 `^# Chapter [0-9]+:` 行且每文件恰含 1 行章号行
- 「渡口那夜」完成判据：`grep -rn "渡口那夜" novel-xinghuo-vol1/ --include="*.md"` 除冻结类（snapshots/audits/diagnostics/reviews/_quarantine/）与 vol1-ledger.md 及 *-pre-rev* 外**零命中**
- 「这笔我先记下」≤12 分子=正文面计数（G3.4 同口径）；「…呢？」≤4 分子=按 ch13:132/ch23:65 两处逐字引文剔除后的叙述形计数

---

### Task 0: 章头注入器 chapter_header_style 参数化（infra · 协调者亲自 TDD）

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py`（:1846 `ensure_chapter_header` + 调用点 :2826-2827 + 新 helper）
- Modify: `skills/shenbi-genre-config/SKILL.md`（chapter_word 块描述加 chapter_header_style 子键）
- Modify (gitignored): `novel-xinghuo-vol1/genre-config.json`（chapter_word 块加 `"chapter_header_style": "two_line_zh"`）
- Test: `tests/unit/pipeline/test_dispatch_helper.py`（:934 既有两测试旁扩展）

**Interfaces:**
- Produces: `ensure_chapter_header(content: str, chapter_num: int, style: str = "english") -> str`；`_chapter_header_style(project_root: Path) -> str`（'english'（缺省，z11 F1301 零变化）|'two_line_zh'）；`_insert_zh_header(content: str, chapter_num: int) -> str`

- [ ] **Step 1: 写红测**（tests/unit/pipeline/test_dispatch_helper.py，加在既有 ensure_chapter_header 测试后）

```python
def test_chapter_header_style_default_english_on_missing_config(tmp_path: Path) -> None:
    assert _chapter_header_style(tmp_path) == "english"

def test_chapter_header_style_two_line_zh(tmp_path: Path) -> None:
    (tmp_path / "genre-config.json").write_text(
        '{"chapter_word": {"chapter_header_style": "two_line_zh"}}', encoding="utf-8")
    assert _chapter_header_style(tmp_path) == "two_line_zh"

def test_chapter_header_style_invalid_value_falls_back(tmp_path: Path) -> None:
    (tmp_path / "genre-config.json").write_text(
        '{"chapter_word": {"chapter_header_style": "bogus"}}', encoding="utf-8")
    assert _chapter_header_style(tmp_path) == "english"

def test_ensure_chapter_header_zh_meta_first_insert() -> None:
    content = "<!--META-BEGIN-->\n## PRE_WRITE_CHECK\n\n- x\n<!--META-END-->\n\n旧残头行\n\n正文首句。"
    out = ensure_chapter_header(content, 37, style="two_line_zh")
    # 零动作判据：META-END 后存在 ^# 第N章$ 才零动作；此处插入
    assert "# 第37章\n" in out
    assert out.index("<!--META-END-->") < out.index("# 第37章") < out.index("旧残头行")

def test_ensure_chapter_header_zh_zero_action_header_after_end() -> None:
    content = "<!--META-BEGIN-->\n- x\n<!--META-END-->\n\n# 第1章\n\n# 雪夜账房\n\n正文。"
    assert ensure_chapter_header(content, 1, style="two_line_zh") == content

def test_ensure_chapter_header_zh_bare_end_with_tail_paired_block_zero_action() -> None:
    # ch17/18 形态：裸 END@头部（无配对 BEGIN）+ 尾部完整配对 POST 块——配对式 META_BLOCK_RE 会误判，判据必须按首个字面 END
    content = "\n<!--META-END-->\n\n# 第17章\n\n# 章题\n\n正文。\n\n<!--META-BEGIN-->\n- post\n<!--META-END-->\n"
    assert ensure_chapter_header(content, 17, style="two_line_zh") == content

def test_ensure_chapter_header_zh_no_marker_inserts_at_head() -> None:
    content = "\n# 第11章\n\n正文。"  # 章头已在：零动作
    assert ensure_chapter_header(content, 11, style="two_line_zh") == content
    out = ensure_chapter_header("正文无头。", 11, style="two_line_zh")
    assert out.startswith("# 第11章\n\n")

def test_ensure_chapter_header_english_default_unchanged() -> None:
    # F1301 回归：无 style 参数行为与旧版逐字一致
    assert ensure_chapter_header("正文。", 5) == "# Chapter 5:\n\n正文。"
    assert ensure_chapter_header("# Chapter 5:\n正文。", 5) == "# Chapter 5:\n正文。"

def test_ensure_chapter_header_zh_marker_at_eof_without_newline() -> None:
    # 边界：META-END 恰在文件尾且无尾换行——region 不得回卷全文
    content = "<!--META-BEGIN-->\n- x\n<!--META-END-->"
    out = ensure_chapter_header(content, 3, style="two_line_zh")
    assert out == "<!--META-BEGIN-->\n- x\n<!--META-END-->\n# 第3章\n"
```

- [ ] **Step 2: 跑红**——`uv run pytest tests/unit/pipeline/test_dispatch_helper.py -q -k "zh or header_style"` → **7 failed**（TypeError/NameError；第 8 个 english_default 回归测试不匹配 -k、本来就过）
- [ ] **Step 3: 实现**（dispatch_helper.py，`ensure_chapter_header` 就地扩展）

```python
_ZH_CHAPTER_LINE_RE = re.compile(r"^# 第[0-9]+章$", re.MULTILINE)
_META_END_MARKER = "<!--META-END-->"


def _chapter_header_style(project_root: Path) -> str:
    """chapter_word.chapter_header_style — 'english'（缺省，z11 F1301 零变化）
    |'two_line_zh'（spec #84 §0 r6-r10 形态钉死）。缺文件/缺键/非法值一律回退 english。"""
    try:
        cfg = json.loads((Path(project_root) / "genre-config.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "english"
    block = cfg.get("chapter_word")
    style = block.get("chapter_header_style", "english") if isinstance(block, dict) else "english"
    return style if style in {"english", "two_line_zh"} else "english"


def _insert_zh_header(content: str, chapter_num: int) -> str:
    """spec #84 r6-r7 判据：以首个字面 <!--META-END--> 行为界（整文件缺席则全文
    扫描、插入位=文件首），其扫描域内存在 ^# 第N章$ 行即零动作；补全只插章号行、
    插入位=META-END 行后首个空行。禁用配对式 META_BLOCK_RE 定位（ch17/18 裸 END+
    尾部配对 POST 块形态会把扫描域误解到文件尾——r7 实测误插重复章号行）。"""
    marker = content.find(_META_END_MARKER)
    if marker == -1:
        if _ZH_CHAPTER_LINE_RE.search(content):
            return content
        return f"# 第{chapter_num}章\n\n" + content
    nl = content.find("\n", marker)
    if nl == -1:  # END 行即文件尾（无尾换行）——region 为空，紧跟其后补行
        return content + f"\n# 第{chapter_num}章\n"
    region_start = nl + 1
    region = content[region_start:]
    if _ZH_CHAPTER_LINE_RE.search(region):
        return content
    m = re.search(r"^\s*$", region, re.MULTILINE)
    if m is None:  # END 后无空行：紧跟 END 行插入
        return content[:region_start] + f"# 第{chapter_num}章\n" + region
    insert_at = region_start + m.start()
    return content[:insert_at] + f"# 第{chapter_num}章\n" + content[insert_at:]
```

`ensure_chapter_header` 头部加 `style: str = "english"` 参数与 docstring 增补；函数体首行 `if style == "two_line_zh": return _insert_zh_header(content, chapter_num)`，其余不动。调用点 :2826-2827 改：

```python
            if _is_chapter_prose_write(rel_path):
                content = ensure_chapter_header(
                    content,
                    int(Path(rel_path).stem.split("-")[1]),
                    style=_chapter_header_style(project_root),
                )
```

- [ ] **Step 4: 跑绿**——`uv run pytest tests/unit/pipeline/test_dispatch_helper.py -q`（含既有 :934/:942 两测试与 tests/pipeline/test_dispatch_helper_* 8 文件族全绿）
- [ ] **Step 5: 契约同步（两处，防叙述与模板不一致）**——skills/shenbi-genre-config/SKILL.md ①:334 附近键集叙述加一句：`chapter_word 可选子键 chapter_header_style：english（缺省，z11 F1301 契约头形不变）|two_line_zh（spec #84——章文件两行式中文章头，注入器按首个字面 META-END 感知判据）`；②:138-144 chapter_word 模板范式加子键行（`"chapter_header_style": "english"` 缺省示例行＋注释）；novel-xinghuo-vol1/genre-config.json chapter_word 块加 `"chapter_header_style": "two_line_zh"`
- [ ] **Step 6: 门禁**——`uv run pytest tests/unit/gates/test_g2_chapter_contract.py tests/unit/gates/test_chapter_contract_re.py -q` + `just check` exit 0
- [ ] **Step 7: Commit**——`git add src/shenbi/pipeline/dispatch_helper.py tests/unit/pipeline/test_dispatch_helper.py skills/shenbi-genre-config/SKILL.md && git commit -m "feat: chapter_header_style 参数化——章头注入器 two_line_zh 形态（spec #84 §0 框架面适配）"`

---

### Task 1: 卷二驱动 prompt 实例化（docs · tracked）

**Files:**
- Create: `docs/regen-vol2-driver-prompt.md`
- 参照: `docs/regen-vol1-continue-prompt.md`（结构母版）+ `docs/probe-vol1-driver-prompt.md`（上游协议 v2.2）

**Interfaces:** Produces 卷二开卷的驱动侧执法载体（Task 9/10 消费）。

- [ ] **Step 1: 写文档**，必含节（每节硬约束取自 spec §2 r4-r7 文本）：
  1. 使用方式与上游协议（新 session、工作目录=本仓、上游沿用 probe-vol1 v2.2 监控/裁决分级/断点协议）
  2. 卷二定位：KR1 斡脱钱庄→驿站站户→渡3；卷界 ch37-86；「卷一是立足卷低温合法，卷二是冲突卷——开卷必须把卷一欠的追读债还给读者」
  3. **首四束（ch37-44）三件套逐束全量检查**（非每 10 章抽样）：热开篇（危机/对手动作开场，非工序低温）/主角自选目标出口（那罕亲口说出要什么+倒计时锚承接 ch36「船开在清明前」——**按引文重锚不按行号**，T0-9 压缩后行号必漂移）/章尾危机型热钩——**声明温度 vs 正文温度背离→blocking，当章 revision**
  4. **断供钩清偿表**（每钩付息或显式挂起）：七三一编号卡→前 6 章内一次实质推进（哪怕一句：档案房换卡/卡被取走）；老驼纸条（灯-横线-小圈）→与骨哨路线图并轨付息；帖木哥归否→前 12 章一句交代；「我见过另一支」第三哨→挂起声明至卷二后段或前 12 章触（挂起必带清偿锚，#82 T2 口径）；萤饼债/春天之约→KR 目标本体不挂起；**笔迹链三处同钩（ch13:309-311/ch14:333/ch26:169-173）→挂起带清偿锚（r5 升格自 G3.4 P2-9）**
  5. 金手指进度条首片：前 10 章内一次「记起来」实质碎片（新规则/新代价/前世画面——非机制解释）
  6. 完颜嫂罚单 ch37-38 内即付（T0-11 选转卷二）
  7. **shadow 促转检查点**：`uv run python tools/lint_shadow_promotion.py novel-xinghuo-vol1 --ledger novel-xinghuo-vol1/vol1-ledger.md`——连续 2 束 WARN 零误伤才转正（#82 协议，非首束即转）；转正=genre-config 键 shadow:false+台账记录
  8. 检查点四行必答（温度谱/胜利账/钩龄表/挂起清单——spec #82 T5）+ 驱动侧每 10 章抽读 ≥2 章沿用
  9. 成本护栏（累计 >$10 先分析再继续；硬顶 $25）+ 判据 5 预期保持 FAIL 挂账口径（docs/regen-vol1-continue-prompt.md:60）
  10. **章头形态断言**（每束收尾跑）：ch37+ 无 `^# Chapter [0-9]+:` 行且每文件恰含 1 行 `^# 第[0-9]+章$`
  11. **修后章 clobber 防线**：T0 修过的章若再修订，diff 复核 -pre-rev 备份（备份是恢复非阻断）
- [ ] **Step 2: Commit**——`git add docs/regen-vol2-driver-prompt.md && git commit -m "docs: 卷二开卷驱动 prompt 实例化（spec #84 T1 执法载体）"`

---

### Task 2: T0-1 ch28 计数链回退 + 声明面四处 + 真门取证（内容 · **用户门 T0 启动后**）

**Files (全 gitignored):** novel-xinghuo-vol1/chapters/chapter-28.md :208-214；truth/timeline.md :31；plans/chapter-28-plan.md :100/:102/:110

- [ ] **Step 1: 正文回退**——ch28:210-214「写完，名数改成五。五字写得比四字实。他数了数这一页的名字。五个，最后一个墨还新。」段改写为不添第五名的收束（张五行「添一行：张五，附籍，诸王之乱点丁，未归。」转为名册侧登记不进《鉴录》或整段删——**单章改动 ≤15%**，取最小面；「名数停在四」保留并与 ch29:145/ch30:154/ch32:260 四口径一致）
- [ ] **Step 2: 声明面四处同步**——timeline.md:31 删「《鉴录》添张五、名数四改五」；plan:100 `- 计数: 鉴录名数 4 +1` → `- 计数: 鉴录名数 4+0`；plan:102 blockquote 计数说明段整段删；plan:110 MH05 行 advance→同栏改「名数保持四；『记了也没人看，账也在』」（hook 语义保留、计数主张移除）
- [ ] **Step 3: 取证**——`uv run shenbi-validate G4 chapter-drafting novel-xinghuo-vol1/chapters/chapter-28.md novel-xinghuo-vol1/plans/chapter-28-plan.md` → cd.counter PASS（真门 CLI，不走管线）；输出贴 progress.md 验收证据
- [ ] **Step 4: 台账**——vol1-ledger.md 追加 `### T0-1` 行（改动面+取证输出摘要）

### Task 3: T0-2/T0-3 双哨补登记 + 骨哨来历归位（内容）

**Files (gitignored):** chapters/chapter-35.md :109-111；truth/prop_registry.md :65/:17；truth/current_state.md :48/:49；truth/character_matrix.md :14/:755；truth/particle_ledger.md :148；style/anchors.md :9；characters/relationships.md :51；chapters/chapter-36.md :58/:208；ch35:255（POST 引文）

- [ ] **Step 1: 双哨补登记**——ch35:109-111 清点段「火纹骨哨一枚，渡口那夜得，经手人老驼」改两行分记「火纹骨哨两枚：老驼所授·主线（城破那夜·门洞得）／帖木哥所持·旧线（ch20 交付）」形（措辞按清点段账目体例，改动 ≤15%）；prop_registry:65 旧线哨行补「第 35 章入匣」事件
- [ ] **Step 2: 来历归位**——「渡口那夜」→「城破那夜」（授物语境）：ch35:111/:168、ch36:58/:208、ch35:255 POST 引文、prop_registry:17、current_state:48（两处）/:49、character_matrix:14/:755（两处）、particle_ledger:148、style/anchors.md:9（few-shot 范文逐字同步）、relationships.md:51；纯地理引用（「东边是渡口」「第29章渡口骨哨自烫」）不动
- [ ] **Step 3: 判据**——`grep -rn "渡口那夜" novel-xinghuo-vol1/ --include="*.md" | grep -vE "snapshots/|audits/|diagnostics/|reviews/|_quarantine/|vol1-ledger|pre-rev"` → **零输出**；贴 progress.md
- [ ] **Step 4: 台账** `### T0-2/T0-3` 行

### Task 4: T0-4 章头/卷名规范化（内容 · 依赖 Task 0 已落）

- [ ] **Step 1: 逐章修头**——ch25-36：删 `# Chapter N:`（ch25/29/31:1）；中文数字形归一阿码（ch25 `# 第二十五章`/ch26/ch31/ch32）；`# 星火` 占位行移除+补章号（ch27/28/29/30/33/34 六处）；ch35/36:20 错贴串 `# 星台雪夜饼初分` 移除+补章号——全部两行式 `# 第N章`+`# 章题`（章题取各章既有题或按正文一句提炼；**不碰正文**）；ch11 补 META 块（章号行之上，文件首 canon 位）
- [ ] **Step 2: 断言**——`for f in novel-xinghuo-vol1/chapters/chapter-{1..36}.md; do echo "$f $(grep -cE '^# 第[0-9]+章$' $f) $(grep -cE '^# Chapter [0-9]+:' $f)"; done` → 每行 `1 0`
- [ ] **Step 3: 台账** `### T0-4`

### Task 5: T0-5..8 连续性四项（内容）

- [ ] **Step 1: T0-5**——ch26:26「纸包里剩一百零三文，十文一摞，压得平。」→「纸包里剩一百一十三文…」（付工本前；:177 付后 103 不动）
- [ ] **Step 2: T0-6（二择一已裁：入账方案）**——ch30:130-131 后补一句「桑伽给的三十文脚钱，他记在私账空栏」（账房腔，≤2 句）；余额链同步**五处正文**：ch30:144「余额一百零三文…剩四十三文」→ 133/七十三文（:145 派生句「四十三文，到不了蔗海」随改）＋ch31:282/ch32:268/ch35:139/ch36:173「一百零三文」→「一百三十三文」；**ch35:139 差数句改写**：「值一百一十五，剩一百零三，中间差的十二文，是这半年吃掉的」在 133 下推导断裂（133>115 方向翻转）——改写为与 133 自洽的账房自审（保留 G3.4 最强样本声口，差数语义重述执行时定，**禁机械换数**）；truth 镜像同步点名：current_state:48（ch35 行页脚+差十二文短语）/:49（ch36 行页脚「一百零三文」）、character_matrix:755、particle_ledger:134（ch30 行自算句）/:146/:151（ch35 行差十二文）**＋新增第 30 章脚钱收入行（+30 文）**、timeline:38（差十二文短句随重述）、subplot_board:112（payoff 列「四十三文到不了蔗海」）、arc-3:25（ch30 自算句）/:56（「后未再动」断言改述：补 ch30 脚钱入账至 133）/:76、pending_hooks.md:116/:118 证据段引用行；**decisions 侧车处置声明**：chapters/chapter-31-revision-decisions.json:139 引「余额一百零三文一文未动」系当时决策时点证词——历史记录保留不改，台账注记口径；**兜底 grep `一百零三文\|四十三文` 核 ch30 付脚钱后各面**（按章节行归属过滤：ch1-29 历史行含「一百四十三文」子串者不动）
- [ ] **Step 3: T0-7**——ch31:268 引述改与 :157-159 原话对齐（「粮借出去叫私放，粮烂在仓里叫折耗」→引述形复述「借出去是罪，烂在仓里是德」语义，引述人称语气保留）
- [ ] **Step 4: T0-8**——ch33 开场（:20-40 区）加一句回收：墨管事三倍价做市=皮帽人收粮前奏（31/32/33 焊接；不展开、一句锚）
- [ ] **Step 5: 台账** `### T0-5..8`

### Task 6: T0-9..11 收束三项（内容）

- [ ] **Step 1: T0-9**——删 ch35:161「开春他要替她把一整张饼吃回来；这话他对谁都没说全过，今夜对着匣子说全了。」整句（饼之约留 ch36 独享首兑）；ch36:240 誓言后至 :270 约 27 行日常压缩至 ≤10 行（调三音 :246/数滴水 :254-256/剪灯花 :262 **合并成段保留**——ch36 正文须 ≥chapter_word.min 2800 字，删而不并会破下限）；末拍序列=誓言→南下第一步实写→卷二钩；**truth 镜像同步**：被删句逐字镜像 truth/current_state.md:48（随删）＋**truth/pending_hooks.md:71 春天之约钩证据段**（逐字引该句并断「L161 约定第一次说全」——非机械删：钩重裁=证据锚迁 ch36（首兑拍）、lifecycle 语义保留、裁定过程记台账）；truth/character_matrix.md:755 为压缩镜像（不含「这话他对谁都没说全过」从句）——压缩面随删；压缩涉及的 ch35/36 摘要行（current_state:48-49/character_matrix:755/particle_ledger/prop_registry:17/relationships.md:51）逐面核对涉及处同步
- [ ] **Step 2: T0-10（T0-9 压缩后 ch36 行号已漂移——按引文内容重锚，不按行号）**——「听说公司贸易船正在测绘新航道」二道转述改实写（**信源已裁：周二船工带信登门**——ch29:141 既有声口；含具体威胁指向「新航道废驿路→站籍饭碗」+ 一句画面（港口/船可见））；保留「船开在清明前」倒计时锚；**truth 信源镜像同步四处**：current_state.md:49 环境列、truth/chapter_summaries.md:45（出场列「章末驿卒在院里喊了一声」＋钩列逐字引）、truth/arcs/arc-3.md:37（章末句）、truth/emotional_arcs.md:51（末拍「听驿卒喊」）——全部改周二船工带信登门
- [ ] **Step 3: T0-9/T0-10 判据 grep**——`grep -rn "这话他对谁都没说全过" novel-xinghuo-vol1/chapters/ novel-xinghuo-vol1/truth/ | grep -v pre-rev` → 0；`grep -rn "港口来了信\|驿卒喊\|驿卒在喊" novel-xinghuo-vol1/truth/ | grep -v pre-rev` → 0（新信源措辞不复用驿卒短语；ch36 正文面按引文重锚核）
- [ ] **Step 4: T0-11（二择一已裁：转卷二）**——ch35 清点段不加认罚行；罚单处置=卷二 ch37-38 内即付（Task 1 驱动 prompt 第 6 节已载）
- [ ] **Step 5: 台账** `### T0-9..11`

### Task 7: T0-12/13 清扫批 + P2 外科批 + 档案卡登记（内容）

- [ ] **Step 1: 清扫**——引号体例统一「」（弯引号残留定位用 U+201C/U+201D 码点 `grep -n $'\u201c' chapters/chapter-N.md`——ASCII `"` 零命中会静默空转）；双结尾段去重（ch1:218-224/ch3:238-256/ch6:197-199 保留首拍删复述）；ch29:119 幽灵黑鸟行删+**chapters/chapter-29.md 的** PRE :19/POST :176/:177 声明同步（**PRE 锚一律指 chapters/ 章文件声明块，非 plans/ 目录**）；ch11 META 块（Task 4 已落则核）；**ch5/6（裸 PRE）/ch17/18（META-END 无 BEGIN）围栏不完整形态记台账备查行（spec T0-12 交付物）**；口癖「这笔我先记下」正文面 26→≤12（留关键拍：ch1 首记/ch24 复利课/ch36 誓言前等关键拍优先保留）；「…呢？」按两处逐字引文剔除后计数 14→≤4
- [ ] **Step 2: P2 外科**——ch2:256 旁白预支「落款只有一句：此账必有还之日」改悬账收束不含誓言句；ch25:235「昨日」→「前日」+**chapters/chapter-25.md 的** PRE :19 锚记号修正（以行内 prose 尾注「同日清晨，同日回拨开篇」为准）；**chapters/chapter-32.md 的** PRE:8 钩声明「指向第 35 章」改指实际回收章或删（执行时核对小账本在 ch35/36 实况后定向）；timeline.md:26 ch23 行删「章末认出欠条之印与城破降表同印」尾注
- [ ] **Step 3: 档案卡登记**——vol1-ledger T0 节注明「渡鸦局档案卡卷末彩蛋拆出 release-split 扩展子任务另立项（release_split 零附录槽位 r3 坐实）」＝该项落地
- [ ] **Step 4: 计数断言**——`grep -c "这笔我先记下"`（正文面，G3.4 口径）≤12；「…呢？」剔除两引文后 ≤4；贴 progress.md
- [ ] **Step 5: 台账** `### T0-12/13`

### Task 8: T0 收口验收（门禁批）

- [ ] **Step 1: G4 真门全量**——`uv run shenbi-validate G4 chapter-drafting novel-xinghuo-vol1/chapters/chapter-{1..36}.md`（shell 展开通读全部）→ PASS；state-settling/chapter-revision 面按改动文件补跑
- [ ] **Step 2: regen-accept**——`just regen-accept novel-xinghuo-vol1 --through 36` → 判据 5 按挂账口径豁免记录（预期 7 绿 1 红挂账），其余全绿
- [ ] **Step 3: 断言三件**——章头（Task 4 形态）/渡口那夜（Task 3 判据）/口癖计数（Task 7）复跑贴证
- [ ] **Step 4: 台账 T0 收口节** + progress.md `## 验收证据` 汇总
- [ ] **Step 5: memory 断点更新**——`卷一 T0 修复轮完成（spec #84）`

### Task 9: ch37 staged 计划实审与重规划（内容 · T0 完成后）

- [ ] **Step 1: 实审驳回**——staging/plans/chapter-37-plan.md 按三件套审：`emotion_tone: 平`/`金句位: 静`/`章尾张力拍: 微`＝冷三连，违反 T1-1 热开篇+危机热钩 → REJECT（台账记录驳回依据）
- [ ] **Step 2: 重规划**——按 T1-1 重写 ch37 计划：热开篇（灰烬线或斡脱债主任一上门）、那罕亲口说出南下第一步+清明前船期倒计时、章尾危机型热钩；断供钩表首排（七三一/纸条并轨/罚单即付 ch37-38）；plan_format v3 合规
- [ ] **Step 3: 台账** `### T1 实审` 行

### Task 10: ch37-44 实弹生产（生产 · **用户门：卷二启动属用户独立决策**）

- [ ] **Step 1: 用户确认后启动**——前置一行可证伪检查（#82/#83 门在位）：`grep -c "hot_hook_floor" src/shenbi/gates/g4/chapter_planning.py` ≥1 且 `ls tools/lint_shadow_promotion.py` 存在；`export SHENBI_LLM_API_KEY` → `nohup ./run_pipeline.sh novel-xinghuo-vol1 > /tmp/vol2-open-run.log 2>&1 & disown`（断点协议沿用）
- [ ] **Step 2: 逐束监控**——按 docs/regen-vol2-driver-prompt.md 执行（三件套逐束全量/裁决分级/断供钩清偿表推进/shadow 促转检查点每束跑 lint_shadow_promotion/章头断言每束收尾/修后章 -pre-rev diff 复核）
- [ ] **Step 3: 收口验收（spec 验收 3）**——三件套全中+断供钩清偿表全勾（含笔迹链挂起行）+新门零误伤（促转记录在案）+ch37-44 章头断言
- [ ] **Step 4: 台账卷二开卷节** + memory 断点「卷二开卷协议就位」

### Task 11: G3.4 复评（可选 · 用户令）

- [ ] 独立 fresh-context 子 agent（G3.4，无生成上下文）评 ch1-36 → P1=0、P2≤3、总分 ≥88（冲 90）；裁决书落 reviews/rubric-score-36-r4.md；台账记录

---

## 验收覆盖表（spec §3 → task → 命令）

| spec 验收 | task | 验证 |
|---|---|---|
| 1. T0 13 项全落+G4 真门+regen-accept+章头断言+cd.counter 取证 | T2-T8 | shenbi-validate G4 / just regen-accept --through 36 / grep 断言三件 |
| 2. G3.4 复评（可选） | T11 | 独立子 agent 裁决书 |
| 3. 卷二实弹三件套+清偿表+新门零误伤+章头断言 | T9-T10 | 驱动 prompt 逐束检查记录+lint_shadow_promotion |
| 4. 台账+memory 断点 | T2-T10 | vol1-ledger 各节+memory 更新 |

## 执行顺序与用户门

Task 0 → Task 1 → **[用户门 1：确认启动 T0 修复轮]** → Task 2-8（串行）→ Task 9 → **[用户门 2：确认卷二启动]** → Task 10 →（可选 T11）。spec §0 推荐顺序「适配→T0→T1」已满足（#82/#83 框架面先落地）。

## Self-Review 记录

- 覆盖：spec §0 适配（T0）/§1 十三项（T2-T7 逐项）/§2 T1 五条（T1 prompt+T9+T10）/§3 四验收（覆盖表）/§4 非目标（Global Constraints）——无缺口
- 占位扫描：内容二择一项（T0-6/T0-10/T0-11）已裁并写明理由；创作面（T0-8/9/10 措辞）以硬约束 brief 形式给全（锚点/字数/声口/不动面），非 TBD
- 类型一致：Task 0 签名与调用点/测试一致；内容 task 无跨 task 代码依赖
