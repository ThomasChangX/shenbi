# Bug-Hunt Report — shenbi-story-architecture

## 检测范围

对 `tests/rounds/round-007-2026-06-14/novel-output/shenbi-story-architecture-bughunt/outline/` 下全部 architecture 产物执行 OKR executability quality pass：
- `story_frame.md`
- `volume_map.md`
- `rhythm_principles.md`

检测维度：所有 KR 必须可测量（measurable）且映射到具体章节范围（chapter ranges）；前台故事 + 后台故事双线必写；三层冲突互为支撑。

## 检出缺陷

| # | 严重性 | 缺陷 | 文件 | 行号 | 违反的 SKILL.md 规则 | 引用证据 |
|---|--------|------|------|------|----------------------|----------|
| 1 | error | 不可测量的 KR：第二卷（"根据地的锤炼"）的 Objective 2 下的 KR-3（KR2.3）违反 OKR executability 要求——既无可测量标准（measurable criteria）也无章节范围映射（chapter range mapping） | `outline/volume_map.md` | L46-L48（原 KR2.3 整段） | SKILL.md 铁律 2 "OKR 递归分解——全书 Objective → 每卷 Key Results → planner 据此分解章节任务"；rubric 维度 5 "OKR executability: KRs are measurable and map to chapter ranges; 'protagonist grows' = fail" | KR2.3 整段内容：`3. KR2.3 主角成长与变强 / - 主角在第二卷中持续成长，变得更强 / - 主角的能力与影响力都比第一卷有所提升`——无任何可量化指标（人员数、地理范围、灵能等级、组织规模等），无具体章节范围（其他 KR 均标注"第 X-Y 章完成"，此 KR 完全缺失章节范围），无法被 chapter-planning 锚定章节节点 |

## 检测方法

1. 提取所有卷的所有 KR 条目（共 6 卷 × 3 KR = 18 条 KR）。
2. 对每条 KR 检查两个必要属性：
   - 章节范围标注：KR 标题或紧随的元数据必须包含"第 X-Y 章"或类似明确章节范围
   - 可测量标准：KR 描述必须含至少一项可量化指标（人数、地理范围、组织规模、灵能等级、文献数量、关系状态变化等）
3. 检查结果：除 KR2.3 外，其余 17 条 KR 均同时具备两个属性。
4. KR2.3 反例对照：
   - KR2.1："梵光教训批判性吸收"——可测量（3 次辩论、复仇清单提及），章节范围（第 13-18 章）
   - KR2.2："第一次反扫荡战"——可测量（清剿名单、战斗胜利），章节范围（第 19-22 章）
   - KR2.3："主角成长与变强"——无任何可测量标准；无章节范围
5. 与 rhythm_principles.md 交叉验证：rhythm_principles.md L9-L11 规定"每卷必须包含至少 1 个高张力高潮章节（决战、转折、牺牲）"，第二卷的其他 KR 均有对应高潮节点，但 KR2.3 因无章节范围无法被验证是否兑现了高潮。

## 未检出（明确说明）

**False positives（误报）: 0** —— 本报告只列出 1 处真阳性不可测量 KR，未对其他 17 条合规 KR 作误报。

以下 KR 经检查未发现问题（节选）：
- 第一卷 KR1.1（穿越落地与种姓压迫呈现，第 1-3 章）：可测量（种姓第一课、垃圾场救人、空袭），章节范围明确
- 第三卷 KR3.1（第一次大捷，第 25-30 章）：可测量（运动战调动、商标发现、大捷），章节范围明确
- 第五卷 KR5.2（史诗级决战，第 55-58 章）：可测量（决战三日三夜、3 层级视角、投降），章节范围明确
- 全部 18 条 KR 中除 KR2.3 外均合规

## 修复建议

将 KR2.3 改写为可测量版本，例如：`3. KR2.3 "梅德兰军事思想"萌芽（第 23-24 章完成）：- 第 23 章节点：林烽与老政委第二次深度对话，确立"实事求是+群众路线+独立自主"的三原则；- 第 24 章节点：林烽被任命为根据地的中队长，开始独立指挥（成长里程碑）`。修复后必须保证可被 chapter-planning skill 锚定章节节点。
