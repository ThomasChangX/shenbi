---
name: shenbi-style-learning
description: "Use when extracting a style fingerprint from existing chapters for style imitation, computing sentence/paragraph length statistics, or generating a statistical style profile"
contract:
  kind: artifact
  reads:
    - chapters/*.md              # normal mode (exists after ch1)
    - import/source/*.txt        # optional reference works
    - novel.json                 # bootstrap mode
    - genre-config.json          # bootstrap mode
  writes:
    - style/style_profile.md
  updates: []
---
<!-- AUTO-CHECK-START -->

## auto-check (generated -- do not edit)

<!-- AUTO-CHECK-END -->

<!-- AUTO-GENERATED from frontmatter — do not edit -->

## 数据契约

- **Reads:** chapters/*.md, import/source/*.txt, novel.json, genre-config.json
- **Writes:** style/style_profile.md
- **Updates:** none

<!-- END AUTO-GENERATED -->

# 风格学习

从现有章节提取风格指纹。负责句长/段长统计、TTR、高频模式、修辞特征。

**统计计算由 `compute_stats.py` 执行（确定性），LLM 只负责将统计结果转化为散文描述。**

## 流程

```dot
digraph style_learning {
    "Read source chapters" -> "Run compute_stats.py on chapter files";
    "Run compute_stats.py on chapter files" -> "LLM reads JSON stats output";
    "LLM reads JSON stats output" -> "LLM writes style_profile.md (stats + prose)";
    "LLM writes style_profile.md (stats + prose)" -> "Done";
}
```

**第一步必须运行** `python -m shenbi.skill_utils.style_learning <chapter_files> --output /tmp/style-stats.json`。**禁止跳过此步直接用 LLM 估算统计值。**

## Bootstrap 模式 (Genesis 阶段)

Genesis 阶段尚无章节正文 (`chapters/*.md`)。bootstrap 模式在不依赖正文的条件下生成初始风格指纹。

```dot
digraph style_bootstrap {
    "import/source/*.txt 存在?" [shape=diamond];
    "import/source/*.txt 存在?" -> "正常提取 (参考作品)" [label="是"];
    "import/source/*.txt 存在?" -> "种子指纹 (novel.json + genre-config.json)" [label="否"];
    "正常提取 (参考作品)" -> "style/style_profile.md";
    "种子指纹 (novel.json + genre-config.json)" -> "style/style_profile.md\n(bootstrap: true, confidence: low)";
}
```

- **有参考文件** (`import/source/*.txt`): 运行正常流程，从参考作品提取风格指纹
- **无参考文件**: 从以下来源生成**种子风格指纹**:
  1. `novel.json` 的 genre/era — 题材惯例（句长、节奏、修辞偏好）
  2. `genre-config.json` 的 `show_tell_ratio`（展示/讲述比例）与 `deep_themes`（深层主题）
  3. 输出 `style/style_profile.md`，标注 `bootstrap: true`、`confidence: low`

> 种子指纹无法由 `compute_stats.py` 计算（无正文样本）。它仅作为后续写作的临时参照，必须在首次正式提取时被真实统计覆盖。

### 首次正式提取

前 3 章完成后，pipeline 重新运行 style-learning（非 bootstrap）覆盖 bootstrap 指纹:

- 读取 `chapters/chapter-1.md` 到 `chapters/chapter-3.md`
- 运行 `compute_stats.py` 获取真实统计
- 用真实统计结果覆盖 bootstrap 指纹（移除 `bootstrap: true` 标记）
- 样本 < 10 章时按铁律 #3 标注「样本不足」（3 章统计仍优于无数据的种子指纹）

### 定期更新

每 `style_learning_interval` 章（默认 12）或卷边界时重新运行:

- 周期性更新（`N % style_learning_interval == 0`）
- 卷级更新（`is_volume_boundary(N)`）
- 每次更新重新运行 `compute_stats.py`，纳入最新章节统计

## 铁律

1. **统计由脚本执行** — 所有指标由 `compute_stats.py` 计算，禁止 LLM 估算统计值。LLM 仅负责将脚本输出的 JSON 转为散文描述
2. **统计而非评判** — 输出"是什么"，不输出"好不好"
3. **样本量要求** — 至少 10 章有效样本；不足 10 章时明确标注"样本不足"
4. **可重现** — 相同输入必须产生相同输出（无随机性）

## 统计指标

### 1. 句长分布

```
均值 / 中位数 / 标准差 / P25 / P50 / P75 / P95
变异系数 = std / mean
```

输出：直方图 + 关键统计量

### 2. 段长分布

按"句数/段"统计，与"字数/段"双口径。

### 3. TTR（Type-Token Ratio）

- 词表大小 / 总词数
- 按窗口滑动的局部 TTR
- 实词 TTR（去虚词）

### 4. 高频 n-gram

| 维度 | n | 阈值 |
|------|---|------|
| 词性二元 | 2 | 出现 ≥ 50 次 |
| 词性三元 | 3 | 出现 ≥ 20 次 |
| 词性四元 | 4 | 出现 ≥ 10 次 |

按词性标注过滤停用词。

### 5. 修辞模式

通过规则模式匹配检测：
- 对仗（A + B + A' + B' 结构）
- 排比（连续 3+ 句同结构）
- 反复（同一短语在邻近出现）
- 设问（"为何..."）
- 反问

### 6. 标点密度

每千字的：
- 句号数
- 逗号数
- 感叹号数
- 问号数
- 破折号 / 省略号数

### 7. 连接词密度

- 时间连接：然后 / 接着 / 之后 / 忽然
- 转折连接：但是 / 然而 / 不过 / 可是
- 因果连接：因为 / 所以 / 因此 / 既然
- 顺序连接：首先 / 其次 / 最后 / 终于

每千字出现次数。

## 输出格式

写入 `style/style_profile.md`：

```markdown
# 风格画像

**样本来源**: [路径]
**样本章节数**: N
**样本总字数**: X
**生成时间**: YYYY-MM-DD
**生成方式**: 纯统计（零 LLM）

---

## 1. 句长分布

| 统计量 | 值 |
|--------|-----|
| 均值 | N 字/句 |
| 中位数 | N 字/句 |
| 标准差 | N |
| P25 | N |
| P50 | N |
| P75 | N |
| P95 | N |
| 变异系数 | N |

直方图: ...

## 2. 段长分布

| 统计量 | 值 |
|--------|-----|
| 句/段（均值） | N |
| 字/段（均值） | N |
| 句/段（标准差） | N |

## 3. TTR

- 全局 TTR: N
- 实词 TTR: N
- 局部 TTR (滑动窗口 1000 词): N (均值) ± N (标准差)

## 4. 高频 n-gram

### 二元

| 模式 | 频次 |
|------|------|
| ... | N |

### 三元

| 模式 | 频次 |
|------|------|
| ... | N |

## 5. 修辞模式

| 模式 | 出现章节 | 频次 |
|------|---------|------|
| 排比 | ... | N |
| 对仗 | ... | N |
| 反复 | ... | N |
| 设问 | ... | N |

## 6. 标点密度（每千字）

| 标点 | 数量 |
|------|------|
| 句号 | N |
| 逗号 | N |
| 感叹号 | N |
| 问号 | N |
| 破折号 | N |
| 省略号 | N |

## 7. 连接词密度（每千字）

| 类型 | 连接词 | 数量 |
|------|--------|------|
| 时间 | 然后 | N |
| 时间 | 接着 | N |
| ... | ... | ... |

## 8. 综合画像

[1 段散文：基于上述统计的客观风格描述]

> 注意：这是统计画像，不是优劣判断。后续写作以此为参考，但不是必须严格复制。
```

## 汇总

```markdown
## 风格学习汇总

**写入文件**: `style/style_profile.md`
**样本章节数**: N
**总字数**: X
**生成时间**: YYYY-MM-DD

### 关键发现

- 句长: 平均 N 字，变异系数 N（高/中/低变异）
- 段长: 平均 N 句/段
- TTR: N（词表丰富度）
- 主导修辞: [排比/对话/...]

### 风格指纹摘要

[1 段简短描述，供下游 skill 快速参考]

### 局限性

- 样本 < 30 章时统计稳定性下降
- 修辞模式检测基于规则，可能漏检非典型修辞
- 不评估"质量"，只统计"是什么"
```

## Anti-Rationalization

| Excuse | Reality |
|--------|---------|
| "统计太麻烦，让 LLM 总结" | LLM 总结 = 不可重现 + 不可验证 = 无意义的"风格画像" |
| "样本 5 章就够了" | 5 章统计的均值/标准差都是噪声 |
| "画像就是给后续 skill 参考" | 参考 = 必须可验证；统计可验证，LLM 总结不可 |
| "字数不到 1 万不用画像" | 1 万字 = 5-7 章，足够产生有效 TTR |
