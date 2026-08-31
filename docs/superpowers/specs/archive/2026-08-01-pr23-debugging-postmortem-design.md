# 消除项目既有 test error 与 warning 根因（PR #23 调试复盘 → 实施 spec）

> **Date:** 2026-08-01
> **Status:** Design（待批准写 plan 实施）
> **Severity:** 🟠 High（既有缺陷实际阻塞开发流 + 21 条真漏洞）
> **方法:** `systematic-debugging` skill 四阶段（Root Cause → Pattern → Hypothesis → Implementation）
> **关联:** PR #23 调试复盘（postmortem 部分，见 §1）→ 本 spec 是其"另写 plan"承诺的兑现
> **Predecessors:** 原文档定位为 postmortem；本版重写为**实施 spec**——根因分析（§2-§3）保留压缩作背景，§4 起为四个独立 PR 的实施计划。

**Iron Law（systematic-debugging Phase 1）：** `NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST`。本 spec 的根因已在 PR #23 postmortem 中逐一查到机制（见 §2 索引）；本版只做"机制 → 实施"的落地，不重复归因。

**Iron Law（本 spec 专用，覆盖原 postmortem 铁律 5 的张力）：** 原铁律 5「既有技术债不夹带进 feature PR」与本 spec「一次性清掉 94 条 CodeQL」存在张力。解法：**本 spec 的所有 CodeQL 清理放独立 chore PR（Phase 4），不混入 feature/守卫 PR（Phase 1-3）**。即"既有债集中在一个 chore PR 里清，而非分散夹带进多个 feature PR"——铁律 5 反对的是后者（review 范围失焦），本 spec 遵守的是前者。

---

## 1. 背景与目标

### 1.1 为什么有这份 spec

PR #23（`1933483`，consolidate to codex single-platform）交付链路触发 7 类异常。原 postmortem（本文档前身）查清了每条的根因（§2），结论是"不产生代码改动，三个预防缺口待另写 plan"。**但那个 plan 从未写**——`git log 1933483..main` 为空，94 条 CodeQL 告警、21 条 pip-audit 漏洞、三个预防缺口全部原样保留至今。

本 spec 把"待另写"变成"已写"，把 postmortem 变成实施 spec。

### 1.2 根本目标（可量化）

| 目标 | 当前实测值 | 目标值 | 验证命令 |
|------|-----------|--------|---------|
| CodeQL open alerts（`main`） | **94** | **0** | `gh api 'repos/ThomasChangX/shenbi/code-scanning/alerts?ref=main&state=open&tool_name=CodeQL' --paginate \| jq length` |
| `pip-audit` 已知漏洞 | **21**（pillow 12.2.0 + pymdown 10.21.3） | **0** | `uv run pip-audit` |
| pre-push 与 CI 审计基准一致 | ❌ 不一致（Issue 2 根因未根治） | ✅ 一致 | pre-push 锁 `--group dev` |
| fixture 源/镜像漂移本地拦截 | ❌ 仅 G0.11 round 时才发现 | ✅ pre-commit 即时 | 编辑 `outline-example.md` 时 hook 触发 |
| mkdocs 死链本地拦截 | ❌ 仅远端 Docs CI 发现 | ✅ pre-push docs 变更时触发 | `docs/` 变更跑 `mkdocs build --strict` |
| `just check` / 全测试 | ✅ 2787 passed（基线） | ✅ 保持 | `just check` |

**非目标**：不改业务逻辑、不重构架构、不动 skill 契约。本 spec 只做"消除 warning + 装本地拦截守卫"。任何顺带发现的 bug 另开 issue，不在本 spec 处理。

---

## 2. 根因索引（来自 PR #23 postmortem，详细归因见 git 历史）

本 spec 直接引用 postmortem 已查实的根因，不重复论证。每条标注"本 spec 是否实施修复"：

| Issue | 根因（机制） | postmortem 的处置 | 本 spec 的处置 |
|-------|------------|-----------------|---------------|
| 1（mkdocs 14 死链） | archive 移动让 `../specs/` 相对路径基准变 | ✅ 已修（`1933483`） | **Phase 3 装本地拦截**，防复发 |
| 2（pip-audit 21 漏洞） | pre-push 裸跑 `pip-audit` 审计 venv 现状，与 CI 锁 `--group dev` 不同；venv 装过 docs 组就脏 | ⚠️ "本地环境调整非代码提交"（**沙堡修复，已复发**） | **Phase 1 合 Dependabot + Phase 2 缺口 B 锁基准** |
| 3（contract-sync hook） | hook 比工作树不比 staged，拆提交时误报 | ✅ 已澄清（合并提交即过） | 不实施（非缺陷） |
| 4（auto-fix abort） | pre-commit auto-fix 标准行为 | ✅ 已澄清（re-add 流程） | 不实施（非缺陷） |
| 5（stash 丢数据） | 混合 tracked/untracked 条目 pop 语义非显然 + 无安全锚点 | ✅ 已恢复 | 不实施（流程纪律，见 §5 铁律 4） |
| 6（94 CodeQL） | 仓库历史代码卫生债，维护性规则不阻塞 | ❌ "单独开 chore PR"（**从未开**） | **Phase 4 独立 chore PR 全清** |
| 7（G0.11 fixture 漂移） | 源/镜像两处存储，编辑源未同步镜像，无本地守卫 | ✅ 已修（`1933483`） | **Phase 2 缺口 C 装本地守卫**，防复发 |

**簇归纳**（postmortem §3 已查实）：
- **簇 A**（改源头未同步依赖方）：Issue 1 + 7 → Phase 2/3 装本地拦截根治
- **簇 B**（本地/CI 环境契约漂移）：Issue 2 + 3 + 4 → Phase 1 + Phase 2 缺口 B 根治
- **簇 C1**（流程/纪律缺口）：Issue 5 → §5 铁律 4（不实施代码）
- **簇 C2**（既有债延期）：Issue 6 → Phase 4 独立 chore PR

---

## 3. 现状证据基线（2026-08-01 实测，写 spec 时复核）

### 3.1 CodeQL 94 条——按规则与文件落点

**按规则**（`gh api ... | jq -r '.[].rule.id' | sort | uniq -c | sort -rn`）：

| 规则 | 数量 | 性质 | 清理策略 |
|------|------|------|---------|
| `py/empty-except` | 28 | bare `except:` 吞错 | 改 specific except 或加注释 `# noqa` + 理由 |
| `py/unused-local-variable` | 19 | 死变量 | 删除或加 `_` 前缀 |
| `py/import-and-import-from` | 10 | 同名既 import 又 from-import | 合并 import |
| `py/cyclic-import` | 10 | 循环依赖 | 惰性 import（函数内）或重组模块边界 |
| `py/catch-base-exception` | 10 | `except BaseException` | 改 `Exception` 或 specific |
| `py/regex/duplicate-in-character-class` | 7 | 正则字符类重复 `[aa]` | 去重 |
| `py/repeated-import` | 5 | 同名重复 import | 删重复 |
| `py/multiple-definition` | 2 | 同名多次定义 | 重命名 |
| `py/unused-import` / `py/unused-global-variable` / `py/file-not-closed` | 各 1 | 杂项 | 删 / 加 `with` |

**按文件落点**（前 5 占 43/94 = 46%）：

| 文件 | 数量 | 主要规则 | 备注 |
|------|------|---------|------|
| `novel-output/audit_script.py` | **17** | 10 catch-base + 7 empty-except | **一次性审计脚本，硬编码本地绝对路径，无人 import**（见 §4.4 裁决） |
| `tests/integration/test_gate_cli.py` | 12 | — | 测试码 |
| `src/shenbi/gates/g7.py` | 5 | — | 框架码 |
| `tests/unit/gates/g4/test_character_design.py` | 5 | — | 测试码 |
| `src/shenbi/pipeline/scr_extractor.py` | 4 | — | 框架码 |
| 其余 25 文件 | 51 | — | 每文件 1-4 条 |

### 3.2 pip-audit 21 条（实测复现）

```bash
$ uv run pip-audit
Found 21 known vulnerabilities in 2 packages
pillow             12.2.0  (20 条 PYSEC-2026-*)  → fix 12.3.0
pymdown-extensions 10.21.3 (CVE-2026-61632)      → fix 11.0.0
```

来源：仅 docs 组传递依赖（`mkdocs-material[imaging]` → `pymdown-extensions` → `pillow`）。CI 的 `uv sync --frozen --group dev` 不装 docs 组故看不到；本地装过 docs 组（复现 mkdocs）就脏。

Dependabot 已开两个 PR（**均 OPEN，未合**）：
- PR #21 `chore(deps): bump pillow 12.2.0→12.3.0`
- PR #22 `chore(deps-dev): bump pymdown-extensions 10.21.3→11.0.0`

### 3.3 三个预防缺口（postmortem §5.2 承诺，均未实施）

| 缺口 | 现状（实测） | 实施点 |
|------|------------|--------|
| A（mkdocs 链接本地拦截） | `grep -c mkdocs tools/pre-push-check.sh` = 0 | `tools/pre-push-check.sh` 增条件块 |
| B（pre-push pip-audit 锁 dev 组） | L38 裸 `uv run pip-audit`，无 `--group dev` | `tools/pre-push-check.sh` L37-38 改 |
| C（fixture 镜像 pre-commit 守卫） | `tools/check_fixture_mirror.py` 不存在 | 新建脚本 + `.pre-commit-config.yaml` 注册 |

---

## 4. 实施计划（四个独立 PR，按此顺序）

**分 PR 原则**：每个 PR 独立可合、独立可回滚、review 范围单一。Phase 1-3 是 feature/守卫 PR（各有明确单一职责）；Phase 4 是纯 chore PR（集中清债，遵铁律 5）。

### Phase 1 · 合 Dependabot（消 21 条真漏洞）

**目标**：`pip-audit` 归零。

**Task 1.1**：合 PR #21（pillow 12.2.0→12.3.0）。
- 验证：`uv sync --group docs && uv run pip-audit` → pillow 漏洞条数归 0；`uv run mkdocs build`（非 strict，因 libcairo 本地问题）不报 pillow 相关错。

**Task 1.2**：合 PR #22（pymdown-extensions 10.21.3→11.0.0）。
- **兼容性风险**：10→11 是大版本。mkdocs-material 9.7.6 声明兼容 pymdown ≥9。验证：`uv sync --group docs && uv run mkdocs build 2>&1 | grep -i 'pymdown\|extension.*error'` 必须为空；浏览生成的 site 抽查渲染（代码块、警告框、tab）正常。
- 若不兼容：回退 PR #22，pymdown 漏洞留至 mkdocs-material 升级支持后再合；本 spec 标注部分完成。

**AC（Phase 1）**：
- `uv run pip-audit` 输出 `No known vulnerabilities found`（或仅剩 pymdown，注明回退原因）
- `uv run mkdocs build`（非 strict）成功，无 pymdown/pillow 相关错误
- `just check` 保持 2787 passed

**leaf/infra 分类**：leaf（合 PR，跑验证命令，无代码改动）。

---

### Phase 2 · 装本地拦截守卫（根治 Issue 2/7 复发）

**目标**：本地编辑/推送时即拦截环境漂移与 fixture 漂移，而非等到 CI 或 G0.11。

#### Task 2.1 · 缺口 B：pre-push pip-audit 锁 dev 组（Issue 2 根治）

**改 `tools/pre-push-check.sh`**（当前 L37-38）：
```bash
# 现状（L37-38）：
echo "--- pip-audit ---"
uv run pip-audit

# 改为：
echo "--- pip-audit (dev group, mirroring CI security.yml) ---"
uv sync --frozen --group dev >/dev/null
uv run pip-audit
```

**机制**：postmortem §2.2 已查实——CI 锁 `--group dev`，pre-push 审计 venv 现状。显式 sync dev 组后再审，基准对齐 CI，"本地绿 = CI 绿"成立。

**权衡（postmortem §5.2 缺口 B 已论证）**：每次 push 多几秒 `uv sync`。可接受（CI 模拟器的正确性 > 推送速度，符合"质量 > 速度"原则）。

#### Task 2.2 · 缺口 C：fixture 镜像 pre-commit 守卫（Issue 7 根治）

**新建 `tools/check_fixture_mirror.py`**（postmortem §5.2 给了伪码，照实现）：
```python
#!/usr/bin/env python3
"""Pre-commit guard: fixture mirrors must match source hashes (G0.11 本地版)."""

import hashlib, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# 与 src/shenbi/gates/g0.py G0.11 的 mirror_map 保持单一源（见 Task 2.3）
MIRROR_MAP = {
    "tests/fixtures/outline-example.md": "outline-example.md",
}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    drift = []
    for fixture_rel, source_rel in MIRROR_MAP.items():
        fp, sp = ROOT / fixture_rel, ROOT / source_rel
        if not sp.exists():
            continue  # source 不存在不报（可能未创建）
        if not fp.exists() or sha256(fp) != sha256(sp):
            drift.append((fixture_rel, source_rel))
    if drift:
        for f, s in drift:
            print(f"fixture mirror drift: {f} != {s}\n  fix: cp {s} {f}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**注册到 `.pre-commit-config.yaml`**（照 L73-77 contract-sync hook 格式）：
```yaml
      - id: fixture-mirror-sync
        name: fixture mirror integrity (G0.11 local)
        entry: uv run python tools/check_fixture_mirror.py
        language: system
        pass_filenames: false
```

#### Task 2.3 · 单一源去重（避免 mirror_map 两处定义）

**问题**：Task 2.2 的 `MIRROR_MAP` 与 `src/shenbi/gates/g0.py:474` 的 `mirror_map` 重复——这正是 Issue 7 的元根因（"一个事实两处存储"）。若新增镜像条目只改一处，守卫与 gate 又会漂移。

**解法**：让 `check_fixture_mirror.py` 从 `g0.py` 动态读取 `mirror_map`，而非硬编码。实现选项：
- **选项 A（推荐，简单）**：`g0.py` 把 `mirror_map` 提到模块级常量 `MIRROR_MAP`（从函数内移出），`check_fixture_mirror.py` 用 `import` 读取。代价：g0.py 微调。
- **选项 B（零侵入）**：`check_fixture_mirror.py` 用 `ast.parse` 解析 `g0.py` 抽取 `mirror_map` 字面量。代价：脆弱，g0.py 改格式就坏。

选 A。Task 2.3 含 `g0.py` 的 `mirror_map` 提模块级 + 两处同步验证。

**已知耦合（审查 I1，非阻塞）**：选项 A 让 `tools/check_fixture_mirror.py` import `shenbi.gates.g0`，即 pre-commit hook → 框架码。这**不是新架构债务**——`tools/` 已有 12 处 import `shenbi.*`（如 `tools/audit-skill-descriptions.py` import `shenbi.gates.g0_skill_contract`），是本项目既有模式。**但** Phase 4 的 Task 4.2b（gates CodeQL 清理）和 4.3（cyclic-import）会改 g0.py，若引入 import-time 故障，会震断此 hook 阻塞所有 commit。故 Phase 4 AC 增一条：4.2b/4.3 后重跑 `pre-commit run fixture-mirror-sync` 确认 import 仍解析（见 §4 Phase 4 AC）。

#### Task 2.4 · 缺口 A：mkdocs 链接本地拦截（Issue 1 防复发）

**改 `tools/pre-push-check.sh`**，在 pip-audit 块后加（仅 docs 变更触发，避免日常推送背 docs 组）：
```bash
# 4c. mkdocs link check (only when docs change)
# 触发条件：检测【待 push 的】docs 变更。pre-push 阶段所有改动已 commit，
#   故 `git diff --cached`（round-1）和 `git diff --name-only HEAD`（round-2）都恒空——
#   前者比 index（已提交故空），后者比工作树（干净故空）。正确 idiom 是比推送范围。
#   本 repo 主分支模型用 main：`git diff --name-only main...HEAD` 列待 push 的 docs 改动。
#   （不用 @{u}...HEAD：feature 分支常无 upstream，会 fatal。）
if git diff --name-only main...HEAD 2>/dev/null | grep -qE '^(docs/|mkdocs\.yml)'; then
  echo "--- mkdocs link check (docs changed) ---"
  uv sync --group docs >/dev/null
  # 单次 build，同时捕获输出与 exit code（审查 N4：避免双 build 浪费/不一致）
  if ! out="$(uv run mkdocs build --strict 2>&1)"; then
    # build 失败。区分三类（审查 N2：libcairo 崩溃本身含 Error/Traceback，不可用宽 grep 反判）：
    #   (a) 死链 → 必失败
    #   (b) libcairo-only（良性的本地环境问题，§9 声明不处理）→ 容忍
    #   (c) 其他真错误（pymdown 不兼容、yml 语法、插件错）→ 必失败
    if echo "$out" | grep -q 'contains a link'; then
      echo "$out" | grep 'contains a link'; exit 1          # (a) 死链
    fi
    # 判 (b)：输出里的 WARNING/ERROR 行是否【全部】可归因于 libcairo？
    # 审查 C1：本脚本 L4 是 `set -euo pipefail`，`grep -vE` 全过滤时 exit 1，
    #   pipefail + set -e 会 abort 整个脚本。故 `|| true` 中和退出码。
    # libcairo 特征串：cairosvg crashed / no library called cairo / cairo-2 / libcairo
    non_cairo_problems="$(echo "$out" | grep -E '^(WARNING|ERROR)' \
      | grep -vE 'cairosvg|no library called.*cairo|cairo-2|libcairo' || true)"
    if [ -z "$non_cairo_problems" ]; then
      echo "--- mkdocs: libcairo-only warnings tolerated (§9 out-of-scope) ---"
    else
      echo "$non_cairo_problems"; exit 1                      # (c) 真错误
    fi
  fi
fi
```

**决策表（审查 N2 要求的完整追踪，三路径不可重叠）**：

| 情形 | mkdocs exit | `contains a link` | 非 libcairo 的 WARNING/ERROR 行 | 判定 |
|------|-------------|-------------------|--------------------------------|------|
| (a) 死链 | ≠0 | 有 | — | **FAIL** |
| (b) 仅 libcairo（本地 cairo 缺失） | ≠0 | 无 | 无（全部 cairosvg/no library called cairo/cairo-2/libcairo） | **容忍** |
| (c) 真错误（pymdown 不兼容/yml/插件） | ≠0 | 无 | 有 | **FAIL** |
| (d) 干净 | 0 | — | — | PASS |

**机制**：postmortem §5.2 缺口 A 已论证——`contains a link` 是死链特征串。但单纯 `|| true`（早期方案）会吞掉**非链接**的 build 失败（如 Task 1.2 pymdown 10→11 不兼容、mkdocs.yml 语法错、插件错），重蹈"在 CI 才发现"覆辙。而宽 grep 反判（`grep Error|Traceback`）会误杀 libcairo（其崩溃本身带 Error/Traceback，见审查 N2）。故用**排除法**：build 失败时，剥离所有 libcairo 归因行后，若仍有 WARNING/ERROR 行则真失败，否则容忍。libcairo 是本地渲染库缺失问题，非仓库缺陷（§9 已声明不处理）。

**`set -euo pipefail` 兼容性（审查 C1）**：本脚本 L4 启用 `set -euo pipefail`。决策表 row (b) 中 `grep -vE` 把所有行过滤光时 exit 1，`pipefail` 传播 + `set -e` 会 abort 脚本——使"容忍"分支反而阻塞推送。故 `grep -vE` 末尾加 `|| true` 中和（L241）。`if ! out="$(...)"` 和 `if git diff ... | grep -q` 在 `if` 条件内不受 `set -e` 影响（POSIX 豁免）。

**与缺口 B 的张力（postmortem 已论证解法）**：B 先 `uv sync --group dev`，A 又 `uv sync --group docs`。两者顺序：B 先（审计基准），A 后（docs 链接，按需）。A 的 sync 不影响 B 已完成的审计。

**AC（Phase 2）**：
- `tools/pre-push-check.sh` 改动后，`bash -n` 语法检查过
- 故意改 `outline-example.md` 不改 fixture → `pre-commit run fixture-mirror-sync` FAIL
- `pre-commit run --all-files` 全绿（含新 hook）
- `just check` 保持 2787 passed（g0.py 改动后 G0.11 仍 PASS，证明 Task 2.3 提常量未破坏 gate）

**leaf/infra 分类**：
- Task 2.1（pre-push L38 改 2 行）：leaf
- Task 2.2（新脚本 + hook 注册）：leaf
- Task 2.3（g0.py mirror_map 提模块级）：**infra**（触及 gate 源码，跨 task 影响 G0.11 + 守卫，协调者亲实现）
- Task 2.4（pre-push docs 块）：leaf

---

### Phase 3 · 验证守卫真的工作（回归测试）

**目标**：证明 Phase 2 的守卫能拦截它们对应根因，而非装了摆设。**Issue 2 是"沙堡修复，已复发"的最高风险根因——其守卫（Task 2.1）必须有 negative test，不可只靠读文件验证。**

**Task 3.0**：negative test——证明 pre-push 的 `--group dev` 锁有效（守 Task 2.1 / Issue 2）。**必需方法**（审查 N5：只验证锁真生效，非只验字符串存在）：

**关键语义**（审查 I1 纠正）：`pip-audit` 审计的是**已安装**包。Issue 2 的真实症状是——开发者本地装过 docs 组（`uv sync --group docs` 复现 mkdocs），venv 变脏含漏洞包，裸 `pip-audit` 此时**误判失败**（exit 1，报 21 漏洞），而非误判通过。`--group dev` 锁的作用是 push 前 `uv sync --frozen --group dev` 把 venv ** reconcil 回 dev 组**（卸载 docs 组的漏洞包），使审计基准 = CI。

**测试步骤**（须在 Phase 1 合并 Dependabot **之前**跑，否则 docs 组已修补，测试空洞化——见时序约束）：
1. 确认当前在 Phase 1 之前的基线（pillow 12.2.0 / pymdown 10.21.3 仍有漏洞）。
2. `uv sync --group docs` 把脏 venv 复现出来（装漏洞包）。
3. 临时把 pre-push 的 `uv sync --frozen --group dev` 注释掉（模拟 Issue 2 复发），跑 pre-push → 必须**误判失败**（报 21 漏洞，因为审脏 venv）。
4. 改回正确版本（`--group dev`），跑 pre-push → 必须报 0 漏洞（锁把 venv reconcil 回 dev 组）。
5. 还原：`uv sync --frozen --group dev` 清理 venv + 恢复 pre-push 文件。

**时序约束**：此测试依赖 docs 组含漏洞包，**必须在 Phase 1（合 Dependabot）之前执行**。若 Phase 1 已先合，改用注入法：临时在**非 dev 组**（如新建 `test-injection` 组或临时加到 docs 组）pin 一个已知漏洞包，验证 `--group dev` 锁能把它排除在审计外（pin 在 dev 组内反而会被 `uv sync --group dev` 装上，测不出过滤）。plan 须把 Task 3.0 排在 Phase 1 之前，或用注入法去耦。

**辅助断言**（可选，不可替代必需方法）：pre-push-check.sh 加 grep 自检 `[ "$(grep -c 'uv sync --frozen --group dev' tools/pre-push-check.sh)" -ge 1 ]` 防字符串被误删——但此断言不能替代上面的语义测试（typo `--group docs` 仍会过 grep）。
**Task 3.1**：negative test——本地造一个 fixture 漂移（改 `outline-example.md` 加一行空格，不改 fixture），跑 `pre-commit run fixture-mirror-sync`，必须 FAIL 并提示 cp 命令。还原。
**Task 3.2**：negative test——本地造一个死链（在某个 `docs/superpowers/specs/*.md` 加一段形如 `](../nonexistent.md)` 的 markdown 链接文本），**commit** 后跑 pre-push 的 docs 块，必须 FAIL。（审查 I2：触发器是 `git diff --name-only main...HEAD`，只看 committed-not-on-main；staged-but-uncommitted 不触发，故必须 commit。）还原（amend 掉该 commit 或 reset）。
**Task 3.3**：positive test——干净树跑 `pre-commit run --all-files` + `pre-push-check.sh`（手动 bash 调用），全绿。

**AC（Phase 3）**：4 个测试均符合预期，输出记录在 PR 描述。**缺 Task 3.0 = 违铁律 6（Issue 2 的守卫无 negative test）。**

**leaf/infra 分类**：leaf（测试，不改源码）。

---

### Phase 4 · 清 94 条 CodeQL（独立 chore PR，遵铁律 5）

**目标**：`gh api ... | jq length` = 0。

**前置裁决（§4.4）**：`novel-output/audit_script.py`（17 条，占 18%）的处置决定 Phase 4 工作量。

#### Task 4.1 · `novel-output/audit_script.py` 裁决

**证据**：
- 硬编码绝对路径 `/Users/xiaotiac/Documents/GitHub/shenbi/novel-output/xinghuo-ranqiong`（`head -15` 已证实）——**换机器即坏**，不可移植。
- 无任何模块 import 它（`grep -rn audit_script src/ tests/` 为空）——**独立脚本，非框架依赖**。
- 在 `git ls-files` 内（受版本控制）但属一次性审计产物。

**裁决选项**（plan 阶段定，本 spec 列证据供决策）：
- **选项 A（推荐，省 17 条工作量）**：仅 `git rm novel-output/audit_script.py`，**不改 `.gitignore`**。理由：硬编码本地路径的一次性脚本不该进版本控制；CodeQL 扫它是误伤。**关键约束**：`.gitignore` 的 `!novel-output/` + `!novel-output/**`（L93-94）negation lines 是**承重线**——`novel-output/` 下有 1261 个受版本控制文件（其中 `xinghuo-ranqiong/` 1229 个，且被 `tests/unit/config/test_production_config_coherence.py` 守卫）。删 negation 不影响已 tracked 文件（gitignore 不 untrack），但会让**未来新增**的 `novel-output/` 文件静默 untracked，破坏"可审计 pipeline 验证"初衷。故只 `git rm` 单文件，negation lines 原样保留。
- **选项 B**：保留并修 17 条（10 catch-base 改 `Exception`、7 empty-except 改 specific 或加注释）。代价：修一个不可移植脚本的价值可疑。

**推荐 A**（纯 `git rm`，零 `.gitignore` 改动）。若用户裁决 B，则 Task 4.2 含此文件。

#### Task 4.2 · 按文件分批清理（剩 77 条，或 94 条若选 B）

**分批策略**（避免单 PR 过大，每批独立可合）：

| 批次 | 范围 | 条数 | 规则集中度 |
|------|------|------|-----------|
| 4.2a | `tests/` 下全部（test_gate_cli 12 + test_character_design 5 + 其余散落） | 36 | empty-except / unused-local 为主，机械修 |
| 4.2b | `src/shenbi/gates/`（g7 5 + g5 4 + g6_checks 2 + g0 2 + shared 1 + g6 1 + g4/chapter_drafting 1 + g3 1 + g1 1） | 18 | 框架码，需谨慎（gate 逻辑） |
| 4.2c | `src/shenbi/pipeline/`（scr_extractor 4 + crash_recovery 3 + dispatch_helper 2 + 其余） | 14 | 含 cyclic-import（Task 4.3） |
| 4.2d | `src/shenbi/` 其余 + `novel-output/`（若选 B） | 9（+17 若选 B） | 杂项 |

**每批的修复模式（按规则）**：
- `empty-except`（28）：bare `except:` → specific exception；确实需宽范围则 `except Exception` + 注释理由。禁止保留 bare `except:`。
- `catch-base-exception`（10）：`except BaseException` → `except Exception`（除非明确要捕 `KeyboardInterrupt`，加注释）。
- `unused-local-variable`（19）：删除，或前缀 `_` 若有意保留。
- `import-and-import-from`（10）/ `repeated-import`（5）：合并/删重复 import。
- `cyclic-import`（10）：**见 Task 4.3**，非机械修。
- `regex/duplicate-in-character-class`（7）：正则字符类去重 `[aa]`→`[a]`。
- `multiple-definition`（2）/ `unused-import`（1）/ `unused-global-variable`（1）/ `file-not-closed`（1）：逐案修。

**批次 4.2b 特别警示（审查 I4）**：gates 的 `except BaseException` / bare `except:` 是**语义负载的**——`except BaseException` 通常意在捕 `KeyboardInterrupt`/`SystemExit` 以做清理，收窄为 `except Exception` 会改变哪些异常传播。AGENTS.md 规定"gate checkers idempotent—pure validation, no side effects"。故 4.2b 的每个 except 收窄点**必须逐 site 审查**原意图（是否在捕 KeyboardInterrupt 做清理），**禁止 bulk sed**。即便分类为"机械修"的 empty-except，在 gates 内也按 infra 处理（逐 site 判断）。

#### Task 4.3 · cyclic-import 专项（10 条，非机械）

**根因（postmortem 视角）**：循环依赖是设计气味，非单纯代码风格。需逐个判断：
- **若惰性 import（函数内）可解**：改函数内 import（如 `dispatch_helper.py:688` 已是此模式，可能告警已存在但合理——评估是否加 `# noqa` + 注释说明）。
- **若模块边界设计问题**：记录为 spec-deviation，**本 spec 不重构**（非目标），加 `# noqa` 抑制并注释指向 follow-up issue。
- `dispatch_helper.py` 的 cyclic-import（L688）涉及 `plan_skeleton`——postmortem 已核实此惰性 import 在 PR #23 前就存在，非新引入。处置：评估能否重组；若不能，`# noqa` + 注释 + 开 follow-up issue。

**抑制预算（审查 I5）**：`# noqa` 可让告警数归 0 但不消根因。为防"告警归 0 耦合留存"，规则：**每个 `# noqa` 的 cyclic-import 必须附 follow-up issue 链接**（注释内）；PR 描述必须列"已修复 X / 已抑制 Y"比例。若无软上限可设（10 条全可能合理），则至少强制可见性——reviewer 能看到抑制 vs 真修的比例，而非被"告警 0"误导。本 spec 不重构（§9），故接受合理抑制，但拒绝静默抑制。

**AC（Phase 4）**：
- `gh api '.../alerts?ref=main&state=open&tool_name=CodeQL' --paginate | jq length` = **0**
- `just check` 保持绿（每批 commit 后跑，cyclic-import 改动易触发 import error）
- 每批 PR 描述附改前/改后告警数 + 抑制/修复比例
- **跨 Phase AC（审查 I1）**：4.2b/4.3 改 g0.py 后，重跑 `pre-commit run fixture-mirror-sync` 确认 Task 2.3 引入的 `shenbi.gates.g0` import 仍解析（Phase 4 改 gate 可能震断 Phase 2 的 hook）
- **g0.py 双触警示（审查 M6）**：g0.py 在 Phase 2（Task 2.3 提 mirror_map 模块级）和 Phase 4（4.2b 清 2 条告警）都被改——plan 必须排序，避免两 PR 冲突

**leaf/infra 分类**：
- 4.2a/4.2d（tests + 杂项）：leaf（机械修）
- 4.2b/4.2c（gates + pipeline 框架码）：**infra**（触及 gate/核心逻辑，协调者亲实现）
- 4.3（cyclic-import）：**infra**（设计决策）

---

## 5. 铁律（从 postmortem 继承 + 本 spec 新增）

继承自 PR #23 postmortem（措辞精炼，机制不重复）：

1. **本地工具链必须与 CI 环境契约一致。**（Phase 2 缺口 B 兑现）
2. **改了源头，必须遍历所有引用该源头的依赖方。**（Phase 2 缺口 A/C + Task 2.3 单一源兑现）
3. **"在 CI 才发现"是工具链的失败。**（Phase 2/3 全部兑现）
4. **诊断性事务变更前先建安全锚点。**（Issue 5，流程纪律，本 spec 不实施代码）
5. **既有技术债集中在一个 chore PR 清，不分散夹带进 feature PR。**（Phase 4 兑现——修订原铁律 5 的表述，本质不变：反对范围失焦，不反对集中清理）

本 spec 新增：

6. **守卫装完必须 negative test 证明它能拦。**（Phase 3 兑现——装了不验证 = 摆设，违 Iron Law）
7. **single source of truth：mirror_map 一处定义，gate 与守卫同源读取。**（Task 2.3 兑现——否则守卫与 gate 漂移就是下一个 Issue 7）

---

## 6. 验证标准（Pass criteria）

| 判据 | 阈值 | 验证命令 | Phase |
|------|------|---------|-------|
| CodeQL open alerts | **0** | `gh api ... \| jq length` | 4 |
| `pip-audit` 漏洞 | **0**（或注明 pymdown 回退） | `uv run pip-audit` | 1 |
| pre-push 审计基准 = CI | `--group dev` 锁定 | negative test（Task 3.0，证明锁语义生效非只验字符串） | 3 |
| fixture 漂移本地拦截 | pre-commit 触发 | negative test | 3 |
| mkdocs 死链本地拦截 | docs 变更触发 | negative test | 3 |
| `just check` | 2787 passed（基线保持） | `just check` | 每 Phase |
| `mkdocs build --strict` 死链（基线，非守卫） | 0（既有 libcairo 告警除外） | `uv run mkdocs build --strict 2>&1 \| grep 'contains a link'` | 基线（非 Phase，现状已 0） |

---

## 7. 实施顺序与 PR 路线图

```
Phase 1 (PR-A): 合 Dependabot #21/#22      [leaf, ~30min, 消 21 漏洞]
   │
   ▼
Phase 2 (PR-B): 装三个守卫 + g0 单一源      [含 infra Task 2.3, ~半天]
   │
   ▼
Phase 3 (PR-B 内或独立 PR-C): negative test  [leaf, ~1h]
   │
   ▼
Phase 4 (PR-D…PR-G, 4 个 chore): 清 94 CodeQL [含 infra 4.2b/c/4.3, ~1-2天]
```

**依赖关系**：Phase 1 独立可先行；Phase 2/3 顺序（3 验证 2）；Phase 4 与 1-3 独立（可并行开 chore PR，但建议在 2/3 后，避免清理时守卫未就位反复触发）。**例外**：Phase 3 Task 3.0 须排在 Phase 1 **之前**（依赖 docs 组含漏洞包；Phase 1 合 Dependabot 后测试空洞化，见 Task 3.0 时序约束）。

**预估总工作量**：Phase 1-3 约 1 天；Phase 4 约 1-2 天（取决 Task 4.1 裁决）。

---

## 8. 依赖与前置

```
PR #23 postmortem（根因已查实，本 spec 引用不复述）
        │
        ├──► Dependabot PR #21/#22（Phase 1 合）
        │
        ├──► G0.11 实现（src/shenbi/gates/g0.py，Task 2.3 改单一源）
        │
        ├──► tools/pre-push-check.sh（Phase 2 缺口 A/B 改）
        │
        ├──► .pre-commit-config.yaml（Phase 2 缺口 C 注册）
        │
        └──► CodeQL 94 条（Phase 4 清，§3.1 分布）
```

**前置条件**：无。所有 Phase 可立即开始（证据已齐，无待查项）。

**对应 plan**：本 spec 即 Design；批准后写 plan 拆 task（按 Phase × Task 粒度），plan 路径建议 `docs/superpowers/plans/2026-08-01-eliminate-existing-warnings-plan.md`。

---

## 9. 范围纪律声明

本 spec 只做"消除既有 warning + 装本地守卫"。不顺带：
- 不重构 skill 契约
- 不动业务逻辑（cyclic-import 若需重构才解，本 spec 选 `# noqa` + follow-up issue，不在此重构）
- 不改进 CodeQL 规则配置（如调 query suite）——仅清告警，不改扫描配置
- 不处理 libcairo 本地渲染问题（环境问题，非仓库缺陷）

任何清理中发现的真 bug，记录到 spec-deviations，另开 issue，不在本 spec 修。
