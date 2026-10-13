# style/style_directives.md — 文风目标文件规范

> 状态：active · 引入：session31（GO①-④ 收尾批）· 消费方：`shenbi-chapter-drafting`（创作原则 6）

## 1. 它是什么，解决什么问题

`style/style_directives.md` 是**用户手写的总体文风目标文件**。在此文件之前，文风控制面有三处但都**不是目标输入**：

| 既有面 | 性质 | 局限 |
|---|---|---|
| `import/source/*.txt` 参考作品 | 目标（间接） | 仅创世期 bootstrap 生效；后续滚动画像以成书章节为准 |
| `genre-config.json → customRules` | 主题/叙事规则 | 偏内容层（show/tell 比、主题落点），不管句法节奏 |
| `style/style_profile.md` | **纯测量** | 描述「现在是什么」，每 12 章重测自我强化——环里没有目标输入，风格只能收敛不能被引导 |

`style_profile` 的反馈环是「短句→测出短句→照短句写→更短句」的收敛均衡。`style_directives` 给环加上目标项：**drafting 读取它，其目标优先于 style_profile 的统计现状**。

## 2. 位置与作用域

- 路径：`<小说项目目录>/style/style_directives.md`（每本小说独立）
- **可选文件，但不再是空白页问题**：`pipeline-init` 自动播种一份可用的**通用默认模板**（`src/shenbi/pipeline/style_seed.py` 的 `DEFAULT_STYLE_DIRECTIVES`——商业网文均衡带：叙述句 10-20 字、长短交替、对白占比 35-55%，与全部硬闸兼容）。已有项目可随时手动创建；播种只写缺失文件，永不覆盖你的修改
- 写者：只有你（人类合作者）。`shenbi-style-learning` 铁律 5 明文永不读写该文件——滚动画像不会覆盖或"纠正"你的目标
- 修改时机：随时。下一次 drafting 派发即读到新版本（无缓存）；删除整文件 = 回退纯测量画像

## 3. 标准结构

自由 markdown，drafting 读全文。推荐四节结构，**每条目标尽量量化**（LLM 对「更有文采」这类指令的执行方差远大于「叙述句目标带 12-22 字」）：

```markdown
# 文风目标

## 节奏与句法
- 叙述句目标带：12-22 字/句；对白可保持短促（5-12 字）
- 句长分布：连续 3 句短句后须出现 1 句 ≥20 字的长句收束
- 段落形态：段均 2-4 句；成段叙述与单行对白交替

## 意象与修辞
- 意象密度：每千字 2-4 处感官细节（触觉/听觉优先于视觉）
- 比喻预算：每千字 ≤2 处，取材于本卷场景物象（矿灯、绳结、潮汛），不用通用喻体

## 对白/叙述配比
- 对白占比目标：40-55%（引号内文字 / 正文总字）
- 对白必须带归属与动作拍的比例：≥70%

## 本章可微调项（可选）
- （留给章备忘段 8「不要做」承载的单章约束；此节通常留空）
```

## 4. 硬闸边界（必读）

**directives 不能松动任何硬闸**，两者冲突时硬闸赢：

- 转折词密度（然/不过/此时/突然/终于/于是 ≤ `max(5, 章字数//1000)`）
- AI 标记词（似乎/仿佛/不由得/缓缓地/微微/不禁/淡淡的…每章 ≤1 次/词）
- fatigueWords（genre-config 的禁用/慎用表）
- 篇幅契约（`genre-config.json → chapter_word`）
- 段落质量下限（任意连续 8 叙述段合计 ≥100 汉字且带对白/动作段 ≥4）

也就是说：想要长句文风，写「句长目标带 12-22 字」可以；写「解除破折号禁令」不行——那是 `anti-ai-reference.md` 的框架级红线，须走框架变更而非项目配置。

## 5. 验证它在生效

1. 文件在 `<项目>/style/style_directives.md`（拼写敏感，`style_directives.md` 不带复数不生效）
2. 任一 drafting 派发的 prompt 含该文件内容（trace.jsonl 或派发日志可见）
3. 写 2-3 章后重跑 style-learning：`style_profile.md` 的句长分布应向 directives 的目标带**漂移**——profile 是测量，目标是因，成书是果

## 6. 与既有面的协作

```
import/source/*.txt（创世期参考作品）
        │ bootstrap 提取
        ▼
style/style_profile.md ←── 每 12 章/卷界重测（描述：现在是什么）
        ▲                        │
        │ 反馈环（收敛）          │ 对照
style_directives.md ──────────────┘（目标：要什么——优先级高于 profile）
        │ drafting 创作原则 6 读取
        ▼
   chapters/chapter-N.md（成书）
```
