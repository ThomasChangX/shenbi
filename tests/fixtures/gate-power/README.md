# spec #116 gate-power 负例 fixture 包（G0.9 真实章确定性变异）

- **来源**：`novel-xinghuo-vol1/chapters/chapter-1.md`（gitignored 卷一真实运行项目，生成时一次性直读）
- **生成日期**：2026-11-19（维护者侧一次性；确定性：同源同输出，无 RNG）
- **生成器**：`tools/gen_gate_power_fixtures.py`（spec #116 T4；变异窗口面 import Task 1 `narrative_window`——测量面=执法面，C3）

## 再生成命令

```bash
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-hook-killed.md --mutation hook_killed
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-protagonist-vanished.md --mutation protagonist_vanished --full
uv run python tools/gen_gate_power_fixtures.py novel-xinghuo-vol1/chapters/chapter-1.md tests/fixtures/gate-power/chapter-1-transition-flooded.md --mutation transition_flooded --full
```

`characters/protagonist.md` 为手工落盘前置物（C2：`_load_protagonist_names` 非 SKIP 前提），frontmatter 注明衍生自真实 `novel-xinghuo-vol1/characters/protagonist.md` 的 name 行。

## 清单与算子

| fixture | 变异 | 面宽 | 算子（落点） | 靶向门臂 |
|---|---|---|---|---|
| `chapter-1-hook-killed.md` | `hook_killed` | 裁片（M4：叙事尾窗 11 段＝3 上下文＋8 被测窗） | 尾 8 叙事段：张力词→就、？→。、数字串→数 | `G4.cd.no_hook` |
| `chapter-1-protagonist-vanished.md` | `protagonist_vanished` | 全章 | 那罕→术赤、他→此人（全文含 META 块） | `G4.cd.protagonist_absent` |
| `chapter-1-transition-flooded.md` | `transition_flooded` | 全章 | 每叙事段首轮注 不过，/此时，/突然，/终于，/于是，（取自 `count_transition_words` 计数面 TRANSITION_SPECIFIC，I5） | `G4.transition` |

每个 fixture 头部带 `provenance: real-output-mutation (G0.9)` 注释块（源/变异/面宽/生成日期）。

**已知偏差**：pre-commit end-of-file-fixer 为 `chapter-1-hook-killed.md` 补尾换行（裁片段 join 无源尾换行；两份 `--full` fixture 继承源章尾换行不受影响）——内容保真，非字节级精确，同 spec83 fixture 包先例；再生成产物与提交件相差至多一个 EOF 换行。

## 裁片与 `--full` 裁定

- **hook_killed 默认裁片**：变异落点本就在章尾 8 段窗内，裁片即被测面（frontmatter＋尾窗，M4/I7）；实测 263 字合并窗口 ≥30 CJK，门真实执法（非轻窗跳过）。
- **protagonist_vanished / transition_flooded 默认 `--full`**：二者的门判定是**全章计数**语义（主角名/他 出现总数 ≥3；转折词全章计数 > max(5, wc//1000)）——裁片截断会破坏计数分母（前文未进裁片即无所谓残留），故裁定不裁片、以全章承载（NB6）。
- Task 3 若新增结构类变异（frontmatter/块级手术），默认同样 `--full`（裁片会切掉被测结构）。

## 公开 repo 内容政策声明（M4/I7）

本 repo 为 public；变异 fixture 为真实章（frontmatter＋被测窗或全章，逐 fixture 注明）的确定性变换，不脱敏——对齐 `tests/fixtures/` 既有 vol1 衍生先例（cross-chapter-regression、spec83 等）；若用户裁定需脱敏，后续批占位符替换非被测文本再生成（本 README 即该出口的登记位）。
