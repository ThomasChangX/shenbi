# 路径协议（path-layout contract）

> Spec #48 C34（F413/F407）。本文是 rd / project_dir / 输出布局的**唯一定义源**。布局探测单源 = `shenbi.paths.detect_layout`。

## 核心定义

| 术语 | 定义 | 典型内容 |
|---|---|---|
| `rd`（round_dir） | 一次 dispatch/round 的工作目录 | 输出、marker、gate 状态 |
| `project_dir`（小说项目根） | 一个小说项目的根目录 | novel.json、genre-config.json、world/、chapters/、truth/、audits/ |
| `repo_root` | 框架仓库根 | SKILL.md、fixtures、rubric |

**铁律：rd ≠ project_dir。** T2/rounds 场景下 round 目录不是项目根；任何把 `project_dir=rd` 写死的调用形态都是本协议禁止项（历史反例：cli G4 分支，F433）。

## 三布局与探测规则

| 布局 | 项目根特征 | 探测键 |
|---|---|---|
| `project-output` | 项目根含 `novel.json` | novel.json 存在 |
| `novel-output` | `<repo>/novel-output/<proj>/`，含 genre-config.json | genre-config.json + 父目录名 novel-output |
| `skill-output` | `<repo>/skill-output/<proj>/`，含 genre-config.json | genre-config.json + 父目录名 skill-output |

探测为项目目录级键控 + 父目录上溯（详见 `detect_layout` docstring）；布局根名命中仅作上溯锚，枚举**项目根**的调用方（如 G0.3/G0.cc 的 `_layout_project_roots`）必须额外要求键文件存在。

**已知分置（不在 C34 收敛）**：`dispatch_helper._load_genre_config_cached` 读 `<pd>/config/genre-config.json`（dispatch_helper.py:228），而 detect 键控项目根直置的 `genre-config.json`——新旧映射表中显式记录。

## rd/project_dir 调用矩阵

| 场景 | rd | project_dir | 说明 |
|---|---|---|---|
| T1（单目录 round，手动 CLI） | round 目录 | == rd（成文豁免：单目录即项目） | 唯一允许 rd==project_dir 的形态 |
| T2（phase_runner 阶段链） | round 目录 | detect_layout 推导的真实项目根 | phase_runner G4 调用第 4 实参 |
| G4 re-run（G7.13） | marker 所在 rd | detect_layout(rd) 推导（project-output 布局根即 rd） | 与 fresh G4 同源 |
| G2 手动（无 rd） | — | — | 相对路径 → 结构化 FAIL（不裸崩） |

## 解析入口分工

- **`shenbi.paths.RoundPaths`**：一次 dispatch/run 的三根对象（read/write/repo/backup）。`read()` 在 rd miss 时**显式**转 project_dir 并记 structlog debug 事件（`round_paths_read_fallback`）——无静默 fallthrough。
- **`shenbi.gates.shared.resolve_input_path(fp, rd)`**：G4/G2 checker 的单文件相对解析入口（相对路径必须挂 rd，无 rd 抛 ValueError 由 CLI 转 FAIL JSON）。

两者是同一协议的两个粒度（对象级 vs 单文件级），不允许第三处自行拼路径。

## `.bak` 锚定

G1.4 备份 `.bak` 锚定 = 源文件同目录（`bak_path`，gates/shared.py）；豁免裁决见 [gates.md](gates.md)。

## `git grep "skill-output" -- src/shenbi/gates/` 豁免清单

非布局探测的合法命中（成文豁免，lint 不追）：

- `g0.py:329/330/340/346/356` — G0.6 可写性检查的错误文案与注释
- `g7.py:72/88` — G7.5 语义检查引用

其余命中必须落入 `detect_layout`/`_layout_project_roots` 消费侧。
