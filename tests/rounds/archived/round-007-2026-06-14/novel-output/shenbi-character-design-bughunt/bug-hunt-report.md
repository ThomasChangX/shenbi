# Bug-Hunt Report — shenbi-character-design

## 检测范围

对 `tests/rounds/round-007-2026-06-14/novel-output/shenbi-character-design-bughunt/characters/` 下全部角色档案执行 voice distinctness quality pass：
- `protagonist.md`（林烽）
- `major/old-political-commissar.md`（老政委）
- `major/a-lian.md`（阿莲）
- `major/ji-shi.md`（纪师）
- `minor/debt-collector.md`（催收员）
- `minor/young-commissar-zhou.md`（小周）
- `relationships.md`

检测维度：voice_profile 互不重叠（rubric 维度 3 "Voice distinctness" + SKILL.md 铁律 3 voice_profile 必填）、弧线完整、动机双层、关系一致。

## 检出缺陷

| # | 严重性 | 缺陷 | 文件 | 行号 | 违反的 SKILL.md 规则 | 引用证据 |
|---|--------|------|------|------|----------------------|----------|
| 1 | error | voice collision：主角 `protagonist.md` 与主要角色 `major/old-political-commissar.md` 的 voice_profile 完全相同。两者 speech_patterns 的四条逐一对应（自嘲式开场/现代口语夹杂/数字与算账/毛式辩证引用），catchphrases（"先把账算清楚"、"跪着是求不到生存的"）与 avoid_patterns（禁止中二宣言/禁止纯古风对白/禁止内心独白堆砌）一字不差。下游 audit skill（review-dialogue 等）将无法基于 voice_profile 区分二者对白。 | `characters/protagonist.md` 与 `characters/major/old-political-commissar.md` | protagonist.md voice_profile: L13-L25；old-political-commissar.md voice_profile: L13-L25 | SKILL.md 铁律 3 "voice_profile 必填——每个主要角色必须有说话风格指纹"；rubric 维度 3 "Voice distinctness"：Each major character has unique speech markers; interchangeable dialogue = fail | 两个文件的 voice_profile 字段值在 speech_patterns / catchphrases / avoid_patterns 三个子数组上完全一致；尤其 catchphrases "先把账算清楚" 在两个角色档案中同时作为口头禅出现，不可能不影响对白辨识 |

## 检测方法

1. 提取所有 `characters/**/*.md` 的 voice_profile 字段（speech_patterns、catchphrases、avoid_patterns 三个子数组）。
2. 对每对角色计算 voice 重叠度：
   - speech_patterns 完全相同 → 重叠度 100%
   - catchphrases 完全相同 → 重叠度 100%
   - avoid_patterns 完全相同 → 重叠度 100%
3. 任一子数组 100% 重叠即判定 voice collision。
4. 比对结果：林烽（protagonist）与老政委（major）的三个子数组完全相同；其他配对（林烽/阿莲、林烽/纪师、林烽/小周、阿莲/纪师等）均无 100% 重叠。
5. 跨档案交叉验证：`relationships.md` L9-L14 描述老政委"克制反问""数字配具体""梅德兰民间谚语夹杂"等独立 voice 标记，与档案中已被替换为林烽式 voice 矛盾——这进一步证明 voice_profile 被错误覆盖。

## 未检出（明确说明）

**False positives（误报）: 0** —— 本报告只列出 1 处真阳性 voice collision，未对任何合规 voice_profile 作误报。

以下配对经检查未发现 voice collision：
- 林烽 ↔ 阿莲：speech_patterns 不同（自嘲 vs 极简短句），catchphrases 不同
- 林烽 ↔ 纪师：speech_patterns 不同（现代口语 vs 学术化精确），catchphrases 不同
- 林烽 ↔ 小周：speech_patterns 不同（自嘲 vs 教条引用），catchphrases 不同
- 林烽 ↔ 催收员：speech_patterns 不同（自嘲 vs 公文化口语），catchphrases 不同
- 阿莲 ↔ 纪师：speech_patterns 不同
- 阿莲 ↔ 小周：speech_patterns 不同
- 纪师 ↔ 小周：speech_patterns 不同

## 修复建议

将 `major/old-political-commissar.md` 的 voice_profile 恢复为其应有的"梅德兰民间谚语夹杂/克制反问/数字配具体"独立风格，与 `relationships.md` 的描述保持一致；同步审查下游 review-dialogue skill 是否已基于错误 voice_profile 生成了不正确的对白。
