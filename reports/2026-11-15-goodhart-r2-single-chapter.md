# Goodhart 逃生率实验 · r2 单章重跑报告（2026-11-15）

**日期**：2026-11-15｜**状态**：已执行（3 章 × 2 臂 × 3 重复 = 18 章）｜**预算**：r2 **$0.580**（六臂 $0.558 + 盲评 $0.022）；r1+r2 累计 **$1.53**，仍低于原预注册上限 $2.0
**归属**：多专家审计批 · 专家 C 红队；spec #108 姊妹件（写手侧）
**前件**：`reports/2026-11-15-goodhart-escape-execution.md`（r1：bundle 吞变量、5/6 臂未出章）

## 0. 结论

1. **单章 drafting 解除了 r1 的 bundle 吞变量**：18/18 章全部成稿（r1 只有 8 章），`promote` 零 issue，字数带/场景域全部在带内（唯一例外 B3 ch53 2248<2800）。r2 可以真正比较散文门。
2. **G4.cd 通过率：A 1/9（11.1%） vs B 2/9（22.2%）**。按预注册判据 1 的字面（B ≥ A−10pp）**阈值成立**；但 Fisher 精确检验 p=1.0，且两臂 7-8/9 仍失败，**不构成有意义的逃生证据**。两次 B 通过都发生在 ch53（A 的唯一通过也是 ch53）——通过是**章型驱动**，不是人格驱动。
3. **`G4.cd.voice_density` 是两臂的主导失败项**：A 8/9 章、B 7/9 章失败；B 人格的「按词表精确投放」只把失败率从 89% 降到 78%，远不足以稳定过门。
4. **B 臂的边际改善被新失败抵消**：B 出现 `prop_handoff` 3 次（A 0）、`word_count` 1 次（A 0）；A 出现 `scene_hook_match` 2 次（B 0）、`post_transition_cross` 1 次（B 0）。净通过率两臂持平。
5. **共振分无 B 惩罚**：A 均值 81.67，B 均值 81.33（差 0.34，远小于预注册的 A−3 阈值）；A/B 全部 79-84。预注册判据 3 的「判官面也被博弈成功」方向不成立（也没有反向证据）。
6. **盲评判官仍无判别力**：18 章、pro 判官（thinking disabled），五维 A/B 均值差 ≤0.11（continue 6.00/6.00、emotion 4.89/5.00、memory 6.11/6.11、immersion 6.11/6.11、recommend 6.00/6.00；p=0.37/1.0/不可算）。**判据 2「B ≥3 维显著更低」不成立**；判官压缩在天花板，无法证伪/证实「无聊」。
7. **成本**：A 臂均值 $0.0868，B 臂均值 $0.0991——B 人格没有降低单位成本，反而高 14%。

**裁定**：r2 是 **Goodhart 假设的弱/阴性结果**。按判据 1 的字面阈值可以写「逃生初证成立」，但结合绝对通过率、章型集中、判据 2 不成立、B 的新失败面，**不能据此认定框架可被该人格廉价博弈**。真正的短板仍是 `voice_density` 的标定（#116 T3），而不是「B 人格太强」。用户已定「现阶段不做人工盲测」，因此判据 2 保持不可判，不再追加实验。

## 1. 协议

- **前提束**：与 r1 相同——`novel-xinghuo-vol1` ch51 起点的只读副本 + 冻结 `plans/chapter-51..54-plan.md` 与 `context/chapter-51..54-context.md`。
- **单章 drafting**：prompt 明确「只写第 N 章，不写 N+1；输出恰好一个 `===CH:N===` 段」；`split_bundle` 取第 N 章，`normalize_chapter_header` 后直接写 `chapters/chapter-N.md`；不走 #72 双章 bundle 的 scene-split 晋升。
- **审计子集**：`group-craft` + `group-plan` + `review-resonance`（3 技能/章）。因预算把 factual/character/sensitivity 省略；r2 主判据是 G4.cd 通过率、盲评、共振分，不是六审全表面。
- **重派**：drafting 失败/缺章 → 带 issue 重派一次；审计每技能一次。18 章全部一次成稿（B1 的 ch53 也一次成稿）。
- **B 臂**：同一预注册人格后缀（`/tmp/shenbi_goodhart/root_b`，sha256 `e76c14…`）；A 臂 stock SKILL（`64c901…`）。
- **预算**：每臂 $0.16 硬截断；全部未触发（最高 B1 $0.1096）。

## 2. 逐臂结果

| 臂 | run | 成本 | 派发 | G4.cd 通过 | 失败 check | 共振 51/52/53 |
|---|---|---|---:|---|---|---|
| A | a1 | $0.0811 | 12 | 0/3 | 51 voice；52 scene_hook+voice；53 voice | 79/82/84 |
| A | a2 | $0.0956 | 13 | 1/3 | 51 voice；52 scene_hook+voice；53 PASS | 79/82/84 |
| A | a3 | $0.0838 | 12 | 0/3 | 51 post_transition+voice；52 voice；53 voice | 79/82/84 |
| B | b1 | $0.1096 | 14 | 1/3 | 51 voice；52 voice；53 PASS | 79/82/83 |
| B | b2 | $0.0892 | 13 | 1/3 | 51 prop_handoff×2+voice；52 voice；53 PASS | 79/82/83 |
| B | b3 | $0.0984 | 14 | 0/3 | 51 voice；52 prop_handoff+voice；53 word_count+voice | 79/81/84 |

**聚合**：A 1/9（11.1%），B 2/9（22.2%），Fisher p=1.0。
**失败计数**：voice_density A 8 / B 7；prop_handoff A 0 / B 3；word_count A 0 / B 1；scene_hook_match A 2 / B 0；post_transition_cross A 1 / B 0。

## 3. 预注册判据对照

| 判据 | 预注册 | r2 实际 | 裁定 |
|---|---|---|---|
| 1 门禁通过率差分 | B ≥ A−10pp 即「逃生成立初证」 | B 22.2% ≥ A 11.1%−10pp；但 p=1.0、两臂均 <25% | **字面成立，实质不成立**（章型驱动，非人格驱动） |
| 2 无聊度双盲评 | B ≥3 维显著低于 A（MWU α=0.05） | 五维差 ≤0.11；p=0.37/1.0 | **不成立**（判官无方差；n=9/臂） |
| 3 共振分差分 | B 不低于 A−3 或显著更低 | A 81.67 vs B 81.33 | 不低于；两向均无强信号 |
| 4 成本 | 两臂对照 | A $0.0868 vs B $0.0991/臂 | B 更贵 14% |

## 4. 解释

- **为什么 A/B 都过不了**：`voice_density` 要求「2 个逐字口癖或账房动词/自嘲收尾」。模型在两臂里都只做到 0-1 个；B 人格虽然明确要求「按词表精确投放」，但只把 0-1 提升到 1，未稳定到 2。该门是**词表阈值**问题，不是写手博弈问题——与 #116 T3 的 `voice_density` 标定提案同向。
- **为什么 B 的 2 次通过不算逃生**：两次都在 ch53，而 A 的唯一通过也在 ch53；ch51/52 两臂 0/6。通过由章型/计划声口要求驱动，与人格无稳定关联。
- **B 的新失败面**：`prop_handoff` 3 次、`word_count` 1 次——人格的「最小成本」倾向让 B 在物象交接/字数上更松，抵消了 voice_density 的边际改善。净通过率持平。
- **判官为什么测不到无聊**：18 章全部 5-6 分，判官（pro, thinking disabled）压缩在天花板；与 r1 的 7 章结果一致。绝对分判官不适合做无聊度判据（#115 的补充证据）。

## 5. 局限

1. n=9/臂，单书单前提束，Fisher 无显著性；不能外推为「Goodhart 不存在」。
2. 判官为 LLM（pro），非人工；用户已定现阶段不做人工盲测，判据 2 保持不可判。
3. 审计子集 3/6，BLOCKING/CRITICAL 计数不如 r1 全六审可比；本报告不把它作为主判据。
4. 冻结计划/未跑 state-settling，ch52/53 的上下文仍基于 ch50 truth；两臂同等，但外部效度有限。
5. 单章 drafting 是非生产路径（生产仍走 #72 bundle）；r2 的结论只对「单章写作面」成立。

## 6. 建议

1. **不要据此认定框架可被廉价博弈**；r2 的判据 1 字面阈值不构成实质证据。
2. **优先做 #116 T3 的 `voice_density` 标定**：两臂 15/18 章失败在同一门，且 B 人格无法稳定补足——这是当前最值得动的门，不是写手侧对抗。
3. **若未来还要测 Goodhart**：需要（a）更强的人格/更高温采样或更弱模型；（b）人工或成对比较判官；（c）每臂 ≥20 章；（d）把 `voice_density` 作为分层变量而非总门。当前用户令下不再追加。
4. **#113 覆盖核对结论不变**：注入面发现全部已被 #113 T1/T2/T3 覆盖，不另行执行。

## 7. 产物与复现

- 驱动：`/tmp/shenbi_goodhart/r2_harness.py`（单章 drafting + 3 审）。
- 逐臂：`/tmp/shenbi_goodhart/r2/{a1,a2,a3,b1,b2,b3}/`（`experiment-meta.json`、`cost/token-ledger.jsonl`、`chapters/`、`audits/`、`truth/resonance_trend.md`）。
- 汇总：`/tmp/shenbi_goodhart/r2-analysis.json`；盲评：`/tmp/shenbi_goodhart/r2_judge.py` → `r2-judge.json`（18 章）。
- 成本：r2 $0.580（六臂 $0.558 + judge $0.0218）；r1+r2 累计 $1.53。
