> **Date:** 2026-09-11 | **Status:** Design · **Revised 2026-09-18**（SDD #66 价值门 REWRITE——素材源出库重定向 git 历史、truth 载体处方单块化、chapter_summaries frontmatter 裁决、locations 复用既有件；驳斥审查证据见当批 progress）| **Severity:** 🟡 P2（两 finding 均 P2 · 微修 S 量级）| **方法:** 机械替换 + 配置统一（无需 systematic-debugging——两 finding 根因与修复路径均已定案）
> **系列:** 2026-08-15 审计轮遗留收口（非 37 簇成员——F750 原属 C16 边界争议条被 spec #54 设计审查 deferred 出局、候选归宿 C15/C17 双亡；08-14 轮 F0-06 无簇 squarely 承接；归宿由 spec #40 master 维护 pass 2026-09-11 裁决登记）| **依赖:** F750 素材源 = git 历史 `d120a444^:novel-output/xinghuo-ranqiong/`（生产树已出库 PR #217；九件内容自 dd1fc629 2026-07-20 未变，与 2026-09-11 核实时点逐字节相同）+ tests/fixtures/ 既有 synthetic-sample 回退面；F0-06 无依赖 | **范围:** tests/integration/test_gate_cli.py 单文件 + pyproject.toml 一处配置值（mypy :379）+ fixtures 新增 upstream-copy 引入

# 遗留微修批：F750 集成测试真实 fixture 化 + F0-06 python 版本三元统一

## 1. F750：test_gate_cli.py 捏造项目换真实 fixture 拷贝

**根因**（转述自 Z7-b:154，2026-09-18 复核逐字成立）：`_make_worldbuilding_project`（:27-97）手写 novel.json/story_bible/rules/locations/truth 模板（占位文本 "Content here."），本测试是完整 skill 产出形态的场景（PASS 路径的 story_bible 结构即被测语义的一部分），不属 G0.9 豁免类别（gate 内部输入/接线单测豁免先例见 tests/pipeline/test_g4_directory.py:4-7、test_trigger_context.py:3-5）；手写中文占位过 gate 的方式可能与真实产物分布不同（bullet 密度、字数）。

**素材现状（2026-09-18 修订——原「全套真实产物在 novel-output/xinghuo-ranqiong/ 在盘」已失效）**：

- novel-output/ 生产树已于 PR #217（spec #63 T1504，2026-09-16）整体出库（.gitignore:93 指令、:92 注释）；spec 原文写作（09-11）时在盘、现 HEAD 已为假。
- **取材方式**：`git show d120a444^:novel-output/xinghuo-ranqiong/<path>`——素材九件（novel.json/world 三件/truth 四件/protagonist；genre-config 另复用既有 verbatim 拷贝）内容末次变更 dd1fc629（2026-07-20），与 spec 核实时点逐字节相同；其中 locations 已有既有 real-output 居件（payload 逐字节一致），git 新取八件。G0.11 无新执法面：本修复**不新增 MIRROR_MAP 条目**——novel-output 源条目已随出库移除（g0.py 头注先例：fixtures 保留作真实历史产物，不再镜像校验）；gate 对 MIRROR_MAP 缺端条目报 WARN（g0.py 要求登记或移除半死条目）、`tools/check_fixture_mirror.py` 对源缺失条目 skip——两者均不触及 git 历史源新 fixture。
- fixtures 现况：synthetic-sample 族（world-{story-bible,rules,locations,power-system}-example.md、novel-example.json、truth-current_state.md，均带载体）；upstream-copy（genre-config-example.json——真品 genre-config verbatim；truth-current_state-xinghuo.md）；real-output（world/factions/factions.md、world/locations/locations.md——**后者 payload 与 d120a444^ 真品逐字节一致**，仅前置 5 行载体块）；truth-character_matrix/emotional_arcs/chapter_summaries.md 在盘无载体。

**真品过 G4 结构断言实测（2026-09-18，worldbuilding.py 同款正则）**：story_bible 恰 4 节 + 0.0% bullet ✓；rules 恰 10 条（`## 规则 N` heading 格式走 worldbuilding.py:108-119 豁免分支）✓；locations 有效计数恰 5（numbered 优先）✓；novel.json 四键齐（genre 为列表，过 :42-46 存在性+真值检查；`target_word_count` 被 :48 接受）✓；truth/current_state+character_matrix+emotional_arcs frontmatter 含 type/category/status（category: truth / status: active / filled_by / last_chapter）✓；**truth/chapter_summaries 无 frontmatter（正文直起 `## 第55章`，滚动窗形态）→ 字节保真拷贝必 FAIL G4 truth 检查**。

**修复（首选 = upstream-copy 引真实产物，回退 = synthetic-sample 拷贝）**：

首选路径从 git 历史引真实产物到 tests/fixtures/，测试内仅保留目录组装逻辑（fixture → tmp project 拷贝）。**载体形态处方（2026-09-18 裁决，三类分形）**：

| 形态 | 适用 | 构成 | 依据 |
|---|---|---|---|
| **单块合并式** | 自带 frontmatter 的 .md（truth 三件 + protagonist——真品头有 name/role 等 12 键实测） | provenance/source 两键**并入**原 frontmatter 成单块；body verbatim | yload（gates/shared.py:95-96 `split("---",3)` 取 parts[1]）只解析第一块——双块形态（truth-current_state-xinghuo.md 先例）下 G4 truth 检查读到 provenance 块、缺 type/category/status → FAIL；单块合并同时满足 load_provenance（g0_purity.py:76-79 首块内搜索）与 yload |
| **前置单块** | 无 frontmatter 的 .md（story_bible/rules——正文直起 `# 世界观圣经`/`# 世界铁律`） | 顶部前置 provenance 块（4 行 + 1 空行）；payload verbatim | world/locations/locations.md 既有 real-output 先例；G4 对 world 面纯正则检查（节数/bullet 密度/规则数），前置块不扰动（bullet 密度分母增大只会更低） |
| **sidecar** | novel.json | `novel.json.provenance.json`（**全文件名 + 后缀**——load_provenance g0_purity.py:84 取 `<完整文件名>.provenance.json`，非去扩展名；先例 genre-config-example.json.provenance.json） | genre-config-example.json 先例；G4 jload 读 payload 本体 |

**落位布局**：新 fixture 统一落 `tests/fixtures/xinghuo-ranqiong/<原项目相对路径>`（novel.json、world/story_bible.md、world/rules.md、truth/ 四件、characters/protagonist.md——镜像项目树，组装退化为机械拷贝（locations/genre-config 自既有点取用，其一随目录角色改名）；`source:` 路径自释；basename 与既有 scenario 引用 fixture 的前两段 stem 无碰撞，且带合法载体使 G0.19 变体旁路天然免疫）；`.provenance.json` sidecar 仅留在 fixtures 侧，**不拷入** tmp project（G4 只读 novel.json 本体）。locations 复用既有点 `tests/fixtures/world/locations/locations.md`、genre-config 复用既有 `tests/fixtures/genre-config-example.json`，均不新增。**前瞻注记**：`tools/check_fixture_duplicates.py` 未接 CI 且今按原始整字节哈希（合并式与双块形态字节不同，不触发）；若其日后改为剥载体哈希，`xinghuo-ranqiong/truth/current_state.md` 与既有 `truth-current_state-xinghuo.md` 的 payload 全同——届时须按该工具的登记口径处理，非本 spec 范围。

映射表：

| 捏造面（现 :27-97） | 首选素材 | 形态 |
|---|---|---|
| novel.json | `git show d120a444^:novel-output/xinghuo-ranqiong/novel.json`（830B） | sidecar |
| genre-config.json | 直接复用既有 upstream-copy fixture `genre-config-example.json`（真品 verbatim） | 既有 |
| world/story_bible.md | 同源 world/story_bible.md（10,045B） | 前置单块 |
| world/rules.md | 同源 world/rules.md（4,289B） | 前置单块 |
| world/locations.md | **直接复用既有 real-output fixture `world/locations/locations.md`**（payload 逐字节一致）——不新引入 | 既有 |
| truth/current_state.md | 同源 truth/current_state.md（10,292B） | 单块合并 |
| truth/character_matrix.md | 同源（3,711B） | 单块合并 |
| truth/emotional_arcs.md | 同源（4,566B） | 单块合并 |
| truth/chapter_summaries.md | 同源（5,955B）+ **frontmatter 重建**（见下裁决） | 重建块 |
| characters/protagonist.md | 同源（7,977B；G4 worldbuilding 不读 characters/，纯代表性） | 单块合并 |

**chapter_summaries 裁决（2026-09-18 定稿）**：真品无 frontmatter，字节保真拷贝必 FAIL（missing_type/category/status 三 must_fix）。三选一中取 **frontmatter 重建**：按同族真品 frontmatter 契约重建（title: 章节摘要 / project: 星火燃穹 / type: chapter_summaries / category: truth / status: active + provenance/source 键 + source 注记「frontmatter reconstructed per template contract; body verbatim」，**注记值整体加引号**——防御性要求（裸标量含 `: ` 会致 yload yaml_error；本值现不含该序列，加引号防后续措辞漂移引入）），body 逐字节保真。**有意省略**同族四键：version/last_updated（版本戳属其他三件的快照时刻，移植即捏造）、filled_by（state-settling 的 SKILL.md Updates 行虽列 chapter_summaries，但该件自身无实证 frontmatter 契约——保守省略，不替写入方断言）、last_chapter（滚动窗文件的语义属滚动写入方，非本件可静态断言）。理由：F750 反对的是 body 内容分布失真（bullet 密度/字数）；元数据层按有实证的同族契约（三件真品 frontmatter 实测形态）重建不属捏造。另两选均劣——synthetic 回退（分布失真正是 F750 指控本体）、放弃该件 PASS 主张（测试目标残缺）。

**不可直接复用 truth-current_state-xinghuo.md 于 truth/**：其为双块形态，拷入 project 后 yload 读第一块（provenance/source）→ G4 FAIL；须按单块合并式新立 fixture。该既有件的 ~8 处消费面（4 文件：tests/unit/contracts/test_fields.py、scripts/lint_contract_fields.py、2 个 bug-hunt scenario）不受本 spec 影响。

**高敏感点注记（实施约束）**：真品 locations=5（压 3-5 上界）、rules=10（压 1-10 上界且靠 heading 豁免分支）、story_bible=4 节（压 ≥4 下界）——均为边界压线，实施时**不得对 payload 做任何内容扰动**（仅允许上述载体层操作），否则 G4 PASS 崩溃。另注：chapter_summaries 真品尾部含生产 LLM 残留（未闭合 ``` 围栏 + 英文收尾语）——body verbatim 铁律下如实保留，G4 truth 检查纯 frontmatter 无碍；未来消费方若将其当干净 truth 范例（字数测试/格式 lint）须知悉。

回退面（不变）：既有 synthetic-sample fixtures（world-*-example.md、truth-current_state.md 等载体已标注者）可作拷贝源——结构真实但分布非真实，须在测试注记其局限；三个无载体 truth fixture（character_matrix/emotional_arcs/chapter_summaries）引用前须先补载体或以 upstream-copy 真实产物替代。

**验收：**
- `grep -n "Content here\|这是一个宏大而复杂的世界\|name: Test\|天机城" tests/integration/test_gate_cli.py` 零命中（捏造文本清除——模式覆盖 helper 全部自造字符串面：占位/世界观句/角色 frontmatter/地点名）
- `uv run pytest tests/integration/test_gate_cli.py -v` 全绿（G4 PASS 路径在 fixture 拷贝下仍 PASS）
- 新增 fixtures 载体合规且 g0_purity 不新增违规：truth 类为**单块合并式** frontmatter（`provenance: upstream-copy` 与原键同块；g0_purity `load_provenance` 对 `.md` 只读 frontmatter——sidecar 对 `.md` 无效）、无 frontmatter `.md` 为前置单块、novel.json 为 `.provenance.json` sidecar；验证命令（**真树断言**——test_g0_purity*.py 为 tmp_path 合成树，对本声明 vacuous）`uv run python -c "from pathlib import Path; from shenbi.gates.g0_purity import load_provenance; ps=[p for p in Path('tests/fixtures/xinghuo-ranqiong').rglob('*') if p.is_file() and p.suffix in ('.md','.json') and not p.name.endswith('.provenance.json')]; assert ps and all(load_provenance(p) for p in ps), ps"`（后缀白名单防杂散文件如 .DS_Store 误炸断言；本条与下条 python -c 命令均以 repo 根为 CWD——相对路径约定） 通过；**基线注记**：main 现存 G0.19 既有 +2 违规（tests/fixtures/production-config/genre-config.json、tests/fixtures/write-audit-glob/genre-config.json 无载体）——与本改动无关，勿误判回归、不在本 spec 范围；回退路径的 synthetic-sample 引用在测试内注记局限
- 新增 fixture 与 `git show d120a444^:...` 取回内容的保真度可执行验证（payload 逐字节一致；偏离仅限处方内载体操作——chapter_summaries 重建 frontmatter 为其中唯一 frontmatter 级新造，truth 三件与 protagonist 为原键 + 2 合并键、story_bible/rules 为前置块、novel.json 本体不变）。**空行约定**：前置块/重建块与 payload 间空一行（对齐 locations.md 先例）；验证命令的 `body()` 剥载体时对缝部空行稳健（lstrip，空行 0/1 均过）：
  ```
  uv run python -c "
  import re, subprocess, sys
  from pathlib import Path
  def body(t):
      m = re.match(r'^---\r?\n.*?\r?\n---\r?\n', t, re.DOTALL)
      return t[m.end():].lstrip('\r\n') if m else t
  ok = True
  for rel in ['world/story_bible.md','world/rules.md','truth/current_state.md','truth/character_matrix.md','truth/emotional_arcs.md','truth/chapter_summaries.md','characters/protagonist.md','novel.json']:
      fx = Path('tests/fixtures/xinghuo-ranqiong', rel).read_text(encoding='utf-8')
      src = subprocess.run(['git','show',f'd120a444^:novel-output/xinghuo-ranqiong/{rel}'],capture_output=True,text=True,encoding='utf-8').stdout
      if rel.endswith('.json'):
          ok &= fx == src; continue
      same = body(fx) == body(src)  # chapter_summaries 源无 frontmatter，body(src)==src，同一比较即 body 级
      print(rel, 'body-bytes:', same)
      ok &= same
  # 既有复用件 locations 的 payload 锁（前置块 4 行 + 空行，剥后应等于 git 源）
  fx = Path('tests/fixtures/world/locations/locations.md').read_text(encoding='utf-8')
  src = subprocess.run(['git','show','d120a444^:novel-output/xinghuo-ranqiong/world/locations.md'],capture_output=True,text=True,encoding='utf-8').stdout
  print('world/locations.md (existing fixture) body-bytes:', body(fx) == body(src))
  ok &= body(fx) == body(src)
  sys.exit(0 if ok else 1)"
  ```

## 2. F0-06：pyproject python 版本三元统一

**根因**（08-14 ledger F0-06）：`requires-python = ">=3.11"`（:8）vs mypy `python_version = "3.12"`（:379）vs basedpyright `pythonVersion = "3.11"`（:398）——类型检查语义基准漂移（3.11 vs 3.12 语法/API 差异可能漏报/误报）。2026-09-18 复核：三处行号零漂移、值未变；src/ 静态扫描零 PEP 695 泛型、零 `type X =` 别名、零 3.12+ stdlib API——降基准无新增报错风险。

**裁决（spec 内定稿）**：统一为 **3.11**（对齐 requires-python 下限——工具链按支持下限校验是保守面；升 3.12 会放宽 requires-python 语义，超出微修边界）。即 mypy :379 `"3.12"` → `"3.11"`；basedpyright :398 已是 3.11 不动；:8 不动。

**验收：**
- `grep -n "python_version\|pythonVersion\|requires-python" pyproject.toml` 三处一致于 3.11 基准（:8 为下限 `>=3.11`，:379/:398 为字面 `"3.11"`）
- `just check` 全绿（mypy/basedpyright 在 3.11 基准下无新报错）

## 边界

不动 src/ 生产代码；不改 ledger 状态（实施 PR 合并时由该 SDD 份回写 F750/F0-06 两行 closed）。
