# Spec #77 实施计划 — 文体指纹 WARN 闸

> Spec: `docs/superpowers/specs/2026-10-25-spec77-style-fingerprint-warn.md`（rev2 GO）
> 阶段 3 附注折入：缺省阈值为临时档——验收时以旧九章实测分布定档（问号缺省 12 系全文口径换算，对白域分母上实测可能 ~2×；ch8+ch9 双章连续态缺省不中则调档）；指标 4 动词统一为「超标 WARN」（#78 消费）；问号验收配对 = ch8+ch9 或任一连续对；audit_drift 行 = 仅追加（_append_audit 纪律，无重复计数——schema 不入 count_drift_alerts）

## Task 1: 词表 + style_fingerprint 模块 + 阈值定档（infra · tdd_red_green）

- **Modify** `src/shenbi/text/voice_lexicon.py`：`SIMILE_DOMAINS`（五域封闭词表：纸账册/粮食物/器物/自然/身体——版本化注释 v1）+ `OPENING_VERB_FAMILIES`（清点/数数/拆包/量取/翻检/归置…书 tic 词表）
- **Create** `src/shenbi/text/style_fingerprint.py`：
  - `DEFAULTS = {question_per_k: 12, simile_share: 0.70, simile_min_n: 5, opener_run: 3, opener_share: 0.50, dialogue_min_chars: 300, window: 3, opener_min_chapters: 6}`（临时档，注释实测定档条款）
  - `question_density(body) -> (per_k, denominator_ok)`（find_quote_spans 对白域，含半角 ?）
  - `simile_domains(body) -> dict[域, n]`（SIMILE_MARKERS → 一样/般/似的 名词窗；好像/像是 非比喻用例钉测试）
  - `classify_opener(body) -> str | None`（strip 后首条非对白句动词族）
  - `fingerprints(project, chapter) -> list[WarnRow]`（近 N 章窗口重算；**文件谓词 = helper_injection 过滤器同款**——`chapter-(\d+).md` fullmatch，排除 `*pre-rev*`/快照，#74 教训三站点同款；四指标 + INFO 其他>70% + 连续 k 章态）
  - CLI `python -m shenbi.text.style_fingerprint <dir> --chapter N`（打印行；--write 落 audit_drift）
- **Modify** `src/shenbi/contracts/skills/genre_config.py`：`market_params.styleFingerprint` **嵌套子块**（真 #76 同款——voice_density_min/meme_quota 同层；不动 GENRE_KEYS 顶层闭集/无需 SKILL 四站同步）三态校验，键域表：

  | 键 | 域 | 缺省 |
  |---|---|---|
  | question_per_k | [1,40] | 12 |
  | simile_share | [0.5,1.0] | 0.70 |
  | simile_min_n | [1,20] | 5 |
  | opener_run | [2,6] | 3 |
  | opener_share | [0.2,1.0] | 0.50 |
  | dialogue_min_chars | [50,2000] | 300 |

  （window=3/opener_min_chapters=6 为模块常量不入 config）
- **Test**：`tests/unit/text/test_style_fingerprint.py`（四指标构造用例/窗口连续态/样本下限/对话域下限/好像像是反例/**像词素反例（影像/画像——降级其他域 INFO）**/pre-rev 排除/其他域 INFO）
- F947 合规：全部离线（pytest/CLI/just check），零 LLM dispatch

## Task 2: chapter_loop 审计边界接线（infra · characterization）

- **Modify** `src/shenbi/pipeline/chapter_loop.py`：`_run_audit_close_for_chapter` **重试循环退出后**（收束点，每章一次——非 :392 循环体内，防审计重试期重复追加）调 `style_fingerprint.fingerprints` → 行 append-only 写 truth/audit_drift（`- [style-warn:<名>] chN <detail>`；不进 count_drift_alerts——结构性排除已验证；重跑幂等性 = 行可重复但计数器结构性免疫）
- **Test**：接线面单测（构造项目两章超限 → 行落盘 + 幂等重跑不重复计数）

## Task 3: 验收全量（旧九章复跑）

- 真阳性（语料 = novel-xinghuo-vol1/ ch1-9，gitignored——本地取证贴 progress，CI 用构造用例）：问号 ch8+ch9（或任一连续对）连续态 WARN；喻体域窗口样本≥5 且同域>70% WARN；开头同构 ≥3 连续 WARN；数数开头 7/9>50% WARN
- 对照：问号密度在事件高密度章不误报（实测选取）
- `just check` EXIT=0；实测分布贴 progress（缺省调档记录）

## 验收覆盖表

| spec §3 | task | 验证 |
|---|---|---|
| 旧九章三项 WARN 真阳性+指标4 报值 | T3 | CLI 对 ch9 跑 + 窗口重算输出贴 progress |
| 对照不误报 | T3 | 事件章实测 |
| WARN 只进 audit_drift/不入 count/G 硬闸 | T1+T2 | pytest（schema 排除断言）+ 接线单测 |
| just check 全绿 | T3 | EXIT=0 |
