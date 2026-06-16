# Bug-Hunt Report — shenbi-worldbuilding

## 检测范围

对 `tests/rounds/round-007-2026-06-14/novel-output/shenbi-worldbuilding-bughunt/` 下全部 worldbuilding 产物执行 quality pass：
- `novel.json`
- `genre-config.json`
- `world/story_bible.md`
- `world/rules.md`
- `world/locations.md`
- `truth/current_state.md`、`character_matrix.md`、`emotional_arcs.md`、`chapter_summaries.md`

检测维度：内部一致性（rules.md 内部规则不得自相矛盾）、铁律 1（NO BULLET-POINT WORLDS）、铁律 2（前台 + 后台故事）、铁律 3（rules.md 独立存放硬性规则）、铁律 4（去重原则）。

## 检出缺陷

| # | 严重性 | 缺陷 | 文件 | 行号 | 违反的 SKILL.md 规则 | 引用证据 |
|---|--------|------|------|------|----------------------|----------|
| 1 | error | 灵能守恒律内部矛盾：规则三"灵能耗竭律"与规则七"灵能自生律"互斥，同一能量体系不能既"有限且消耗后必须等待补充事件"又"无限且自动持续回流" | `world/rules.md` | 规则三：L17；规则七：L41 | SKILL.md 铁律 3（世界铁律写在 rules.md，硬性规则独立存放，writer 和 auditor 直接引用）；rubric 维度 3「Internal consistency」zero contradictions within world rules; hard rules are mutually compatible | 规则三：`灵能储备是有限的，每次灵能运用都会消耗修炼者本人或所依托环境的灵能储备；储备耗尽即无法继续运用，必须等待明确的补充事件…才能恢复`；规则七：`任何修炼者的灵能储备会随时间自然恢复，无论此前消耗多少、无论所处环境的灵能密度如何，灵能都将持续不断地回流至修炼者体内，不存在真正的耗尽状态` |

## 检测方法

1. 顺序读 `rules.md`，对每条规则的"能量/灵能"相关陈述建立事实矩阵：
   - 规则三：能量有限、消耗后需补充事件、无补充事件不得恢复
   - 规则七：能量无限回流、不需补充事件、不存在真正耗尽
2. 事实矩阵对比：两条规则在"能量是否有限"、"是否需要补充事件"、"是否可真正耗尽"三个二元维度上完全相反，构成直接逻辑矛盾。
3. 比对 `world/story_bible.md` 第一段"天地法则"对灵能守恒律的散文陈述（"灵能守恒律贯穿一切运用：每一次分解、塑形、融合都必然对应一次等量的认知消耗或环境抽取"），确认 story_bible 的版本与规则三相容，与规则七不兼容。
4. 比对 `genre-config.json` 中 `rule-integrity-01`（"灵能守恒：任何灵能运用的描写必须在前后章节有能量来源和去向的说明"），确认 config 层面与规则三相容，与规则七不兼容。

## 未检出（明确说明）

**False positives（误报）: 0** —— 本报告只列出 1 处真阳性矛盾，未对任何合规内容作误报。

以下方面经检查未发现问题，列出以避免误报：
- `story_bible.md`：4 段散文结构完整，前台/后台线分明，bullet 密度合格
- `locations.md`：5 个核心地点，每个含地理/社会/灵能/情节支撑四要素，无重复
- `truth/` 模板：4 个文件均含 type/category/status frontmatter，body 含"待填充"标记
- `novel.json`/`genre-config.json`：JSON 合法，必填字段齐全
- 其余 8 条 rules.md 规则（一、二、四、五、六、八、九、十）之间及与 story_bible 之间未发现矛盾

## 修复建议

将规则七删除或改写为与规则三相容的形式（例如改为"灵能储备的恢复速率受修炼者知识水平与环境灵能密度共同决定，恢复过程必须消耗等量的环境灵能或修炼者生命元能，不存在无代价的自动回流"），并在 `genre-config.json` 的 `customRules` 中追加显式校验条目。
