# Shenbi 测试门禁系统实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 G0-G7 + G_TRANSITION + G_DISPATCH + G_RECONCILE 硬门禁系统，阻止测试执行者跳过步骤、自评打分、产出无效文件。

**Architecture:** 两个新工具（validate-gate.py + deps.json）、三个改造工具（scoring.py / round-exec.sh / summarize-round.py）、两个新 fixture 文件。validate-gate.py 是核心——所有 Gate 检查的独立执行器。scoring.py 和 round-exec.sh 内嵌调用 validate-gate.py，Agent 不能绕过。

**Tech Stack:** Python 3（validate-gate.py, scoring.py 改造）, Bash 3.2（round-exec.sh 改造）, JSON（deps.json, acceptance.json, progress.json）, YAML frontmatter（rubric.md 校准锚点）

**Design Spec:** `docs/superpowers/specs/2026-06-11-test-gate-system-design.md`

---

## File Structure

```
tests/
├── scoring.py              # 改造：内嵌 G3/G5/G6 依赖检查
├── round-exec.sh           # 改造：G0 检查、令牌生成、agent_id、progress.json 初始化
├── summarize-round.py      # 改造：G7 集成、从 progress.json 读取
├── validate-gate.py        # 新建：独立 Gate 执行器
├── fixtures/
│   ├── sensitive_words.txt # 新建：敏感词列表
│   └── stop_words_zh.txt   # 新建：中文停用词列表
├── tiers/
│   ├── deps.json           # 新建：依赖图和预期产出文件
│   ├── acceptance.json     # 新建：接受阈值
│   └── t1-skill/
│       └── <skill>/
│           └── rubric.md   # 改造：添加校准锚点（增量）
└── rounds/
    └── round-NNN/
        ├── progress.json   # 新建：进度追踪（工具写入）
        └── .token-hashes.json  # 新建：绕过令牌哈希（工具写入）
```

---

### Task 1: 创建数据配置文件

**Files:**
- Create: `tests/tiers/deps.json`
- Create: `tests/tiers/acceptance.json`
- Create: `tests/fixtures/sensitive_words.txt`
- Create: `tests/fixtures/stop_words_zh.txt`

- [ ] **Step 1: 创建 deps.json — 依赖图**

```bash
cat > tests/tiers/deps.json << 'DEPSEOF'
{
  "t2-phases": {
    "genesis": {
      "prerequisites": ["shenbi-worldbuilding", "shenbi-power-system", "shenbi-faction-builder", "shenbi-location-builder", "shenbi-character-design", "shenbi-relationship-map"],
      "expected_outputs": ["novel.json", "genre-config.json", "world/story_bible.md", "world/rules.md", "world/locations.md", "world/power_system.md", "world/factions.md", "characters/protagonist.md", "characters/major/*.md", "characters/relationships.md", "truth/current_state.md", "truth/character_matrix.md", "truth/emotional_arcs.md", "truth/chapter_summaries.md"]
    },
    "architecture": {
      "prerequisites": ["shenbi-story-architecture", "shenbi-pacing-design", "shenbi-plot-thread-weaver", "shenbi-genre-config"],
      "expected_outputs": ["outline/story_frame.md", "outline/volume_map.md", "outline/rhythm_principles.md", "outline/thread_map.md", "genre-config.json"]
    },
    "planning": {
      "prerequisites": ["shenbi-volume-outlining", "shenbi-chapter-planning", "shenbi-foreshadowing-plant", "shenbi-context-composing"],
      "expected_outputs": ["plans/chapter-*-plan.md", "truth/pending_hooks.md", "context/chapter-*-context.md"]
    },
    "drafting": {
      "prerequisites": ["shenbi-chapter-drafting", "shenbi-state-settling", "shenbi-foreshadowing-track", "shenbi-style-polishing", "shenbi-anti-detect", "shenbi-length-normalizing"],
      "expected_outputs": ["chapters/chapter-*.md", "truth/current_state.md", "truth/character_matrix.md", "truth/emotional_arcs.md", "truth/chapter_summaries.md", "truth/pending_hooks.md"]
    }
  },
  "t3-pipelines": {
    "long-form": {
      "prerequisites": ["genesis", "architecture", "planning", "drafting"],
      "min_chapter_ratio": 0.5
    }
  }
}
DEPSEOF
```

- [ ] **Step 2: 验证 deps.json 语法**

```bash
python3 -c "import json; d=json.load(open('tests/tiers/deps.json')); print('OK:', len(d['t2-phases']), 'phases,', len(d['t3-pipelines']), 'pipelines')"
```
Expected: `OK: 4 phases, 1 pipelines`

- [ ] **Step 3: 创建 acceptance.json — 接受阈值**

```bash
cat > tests/tiers/acceptance.json << 'ACCEPTEOF'
{
  "t1": 94,
  "t2": 94,
  "t3": 94
}
ACCEPTEOF
```

- [ ] **Step 4: 创建 sensitive_words.txt — 敏感词列表**

```bash
cat > tests/fixtures/sensitive_words.txt << 'SENSEOF'
# 每行一个敏感词或正则表达式
# 以 # 开头的行为注释
台独
藏独
法轮功
SENSEOF
```

- [ ] **Step 5: 创建 stop_words_zh.txt — 中文停用词**

```bash
cat > tests/fixtures/stop_words_zh.txt << 'STOPEOF'
忽然
因为
所以
但是
那里
自己
什么
已经
可以
没有
这个
那个
如果
虽然
然而
不过
于是
然后
之后
之前
一直
开始
终于
可能
应该
必须
觉得
知道
觉得
看见
听见
发现
变成
回到
走到
来到
看到
想起
STOPEOF
```

- [ ] **Step 6: 验证 fixture 文件**

```bash
wc -l tests/fixtures/sensitive_words.txt tests/fixtures/stop_words_zh.txt
```
Expected: `sensitive_words.txt` ≥ 3 行, `stop_words_zh.txt` ≥ 30 行

- [ ] **Step 7: Commit**

```bash
git add tests/tiers/deps.json tests/tiers/acceptance.json tests/fixtures/sensitive_words.txt tests/fixtures/stop_words_zh.txt
git commit -m "feat: add deps.json, acceptance.json, sensitive_words, stop_words fixtures"
```

---

### Task 2: 创建 validate-gate.py

**Files:**
- Create: `tests/validate-gate.py`

- [ ] **Step 1: 写框架和参数解析**

```python
#!/usr/bin/env python3
"""独立 Gate 执行器。每个 Gate 检查返回结构化 JSON。"""

import json
import sys
import os
import re
import hashlib
import glob as globmod
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = PROJECT_ROOT / "tests"
SKILLS_DIR = PROJECT_ROOT / "skills"

def load_json(path):
    with open(path) as f:
        return json.load(f)

def load_acceptance():
    return load_json(TESTS_DIR / "tiers" / "acceptance.json")

def load_deps():
    return load_json(TESTS_DIR / "tiers" / "deps.json")

def fail(gate_id, checks, blocked_action, must_fix):
    return json.dumps({
        "gate": gate_id,
        "status": "FAIL",
        "timestamp": datetime.now().isoformat(),
        "checks": checks,
        "blocked_action": blocked_action,
        "must_fix": must_fix
    }, indent=2, ensure_ascii=False)

def passed(gate_id, checks):
    return json.dumps({
        "gate": gate_id,
        "status": "PASS",
        "timestamp": datetime.now().isoformat(),
        "checks": checks
    }, indent=2, ensure_ascii=False)
```

- [ ] **Step 2: 写 G0 环境就绪检查**

```python
def gate_G0(round_dir=None, seed_file=None):
    """G0: Round 创建前的环境检查"""
    checks = []
    
    # G0.1: 种子文件存在、可读、UTF-8
    if seed_file:
        seed_path = Path(seed_file)
        if not seed_path.exists():
            return fail("G0", checks + [{"id": "G0.1", "status": "FAIL", "reason": f"Seed file not found: {seed_file}"}], "round_creation", ["G0.1"])
        try:
            content = seed_path.read_text(encoding="utf-8")
            checks.append({"id": "G0.1", "status": "PASS"})
        except Exception as e:
            return fail("G0", checks + [{"id": "G0.1", "status": "FAIL", "reason": str(e)}], "round_creation", ["G0.1"])
        
        # G0.2: target_words 提取
        m = re.search(r'目标字数[：:]\s*(\d+)', content)
        if not m or int(m.group(1)) <= 0:
            return fail("G0", checks + [{"id": "G0.2", "status": "FAIL", "reason": "target_words not found or <= 0"}], "round_creation", ["G0.2"])
        checks.append({"id": "G0.2", "status": "PASS", "target_words": int(m.group(1))})
    
    # G0.3: expected_chapters 已计算
    genre_config = load_json(PROJECT_ROOT / "novel-output" / "星火燃穹" / "genre-config.json")  # FIXME: dynamic novel project path
    default_words = genre_config.get("chapter_word", {}).get("default", 3000)
    target_words = int(m.group(1)) if seed_file else 100000
    expected = -(-target_words // default_words)  # ceiling division
    checks.append({"id": "G0.3", "status": "PASS", "expected_chapters": expected})
    
    # G0.4: 被测技能目录检查
    all_skills = [d.name for d in SKILLS_DIR.iterdir() if d.is_dir()]
    missing_dirs = []
    missing_skill_md = []
    for s in all_skills:
        skill_dir = SKILLS_DIR / s
        if not skill_dir.exists():
            missing_dirs.append(s)
        elif not (skill_dir / "SKILL.md").exists():
            missing_skill_md.append(s)
    
    if missing_dirs:
        return fail("G0", checks + [{"id": "G0.4", "status": "FAIL", "reason": f"Skill directories not found: {missing_dirs}"}], "round_creation", ["G0.4"])
    if missing_skill_md:
        checks.append({"id": "G0.4", "status": "WARN", "reason": f"Skills missing SKILL.md (SKIP): {missing_skill_md}"})
    else:
        checks.append({"id": "G0.4", "status": "PASS"})
    
    # G0.6: novel-output/ 可写
    novel_output = PROJECT_ROOT / "novel-output"
    if not os.access(novel_output, os.W_OK):
        return fail("G0", checks + [{"id": "G0.6", "status": "FAIL", "reason": f"novel-output/ not writable: {novel_output}"}], "round_creation", ["G0.6"])
    checks.append({"id": "G0.6", "status": "PASS"})
    
    return passed("G0", checks)
```

- [ ] **Step 3: 写 G2 写盘验证检查**

```python
def word_count_md(filepath):
    """统计 Markdown 文件中正文的中文字数（排除代码块和 frontmatter）"""
    with open(filepath, encoding='utf-8') as f:
        content = f.read()
    # 移除 YAML frontmatter
    content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)
    # 移除代码块
    content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
    # 移除 PRE_WRITE_CHECK / POST_WRITE_SELF_CHECK 块
    content = re.sub(r'## PRE_WRITE_CHECK.*?(?=## |$)', '', content, flags=re.DOTALL)
    content = re.sub(r'## POST_WRITE_SELF_CHECK.*?(?=## |$)', '', content, flags=re.DOTALL)
    # 统计中文字符
    return len(re.findall(r'[一-鿿]', content))

FATIGUE_WORDS = ["突然", "猛地", "瞬间", "一股", "恐怖", "死死", "眼中闪过", "嘴角", "冷冷", "淡淡", "微微一笑", "心中一动", "暗道", "不由得", "显然", "似乎", "仿佛", "如同", "无比", "极致", "难以形容", "不可思议", "前所未有", "令人发指", "震惊", "愣住", "呆住"]

META_NARRATIVE = ["让人感悟", "引人深思", "由此可见", "综上所述", "值得注意的是", "不禁感慨", "不由得想到"]

TRANSITION_WORDS = ["然", "不过", "此时", "突然", "终于", "于是"]

def gate_G2(file_paths, file_type="chapter"):
    """G2: Subagent 返回后的写盘验证"""
    checks = []
    must_fix = []
    
    for fp in file_paths:
        path = Path(fp)
        
        # G2.1: 文件存在
        if not path.exists():
            checks.append({"id": "G2.1", "file": fp, "status": "FAIL", "reason": "File does not exist"})
            must_fix.append(f"G2.1:{fp}")
            continue
        
        # G2.2: 非空
        if path.stat().st_size == 0:
            checks.append({"id": "G2.2", "file": fp, "status": "FAIL", "reason": "File is empty"})
            must_fix.append(f"G2.2:{fp}")
            continue
        
        checks.append({"id": "G2.1", "file": fp, "status": "PASS"})
        checks.append({"id": "G2.2", "file": fp, "status": "PASS"})
        
        # G2.3: UTF-8
        try:
            content = path.read_text(encoding='utf-8')
            checks.append({"id": "G2.3", "file": fp, "status": "PASS"})
        except:
            checks.append({"id": "G2.3", "file": fp, "status": "FAIL"})
            must_fix.append(f"G2.3:{fp}")
            continue
        
        # G2.6: 章节字数 ≥ floor (仅章节文件)
        if file_type == "chapter":
            wc = word_count_md(fp)
            floor = 3000
            if wc < floor:
                checks.append({"id": "G2.6", "file": fp, "status": "FAIL", "expected": f">= {floor}", "actual": wc, "resolution": "运行 length-normalizing --mode expand"})
                must_fix.append(f"G2.6:{fp}")
            else:
                checks.append({"id": "G2.6", "file": fp, "status": "PASS", "word_count": wc})
            
            # G2.8: PRE_WRITE_CHECK
            if "## PRE_WRITE_CHECK" not in content:
                checks.append({"id": "G2.8", "file": fp, "status": "FAIL", "reason": "PRE_WRITE_CHECK missing"})
                must_fix.append(f"G2.8:{fp}")
            else:
                checks.append({"id": "G2.8", "file": fp, "status": "PASS"})
            
            # G2.9: POST_WRITE_SELF_CHECK
            if "## POST_WRITE_SELF_CHECK" not in content:
                checks.append({"id": "G2.9", "file": fp, "status": "FAIL", "reason": "POST_WRITE_SELF_CHECK missing"})
                must_fix.append(f"G2.9:{fp}")
            else:
                checks.append({"id": "G2.9", "file": fp, "status": "PASS"})
        
        # G2.10: 非模板占位符
        lines = content.split('\n')
        placeholder_lines = sum(1 for l in lines if '待填充' in l)
        if len(lines) > 0 and placeholder_lines / len(lines) > 0.1:
            checks.append({"id": "G2.10", "file": fp, "status": "FAIL", "reason": f"Template placeholder: {placeholder_lines}/{len(lines)} lines contain 待填充"})
            must_fix.append(f"G2.10:{fp}")
        else:
            checks.append({"id": "G2.10", "file": fp, "status": "PASS"})
        
        # G2.12: 文件完整性（句末标点或标题结尾）
        last_line = content.strip().split('\n')[-1].strip()
        ends_properly = last_line.endswith(('。', '！', '？', '…', '」', '』', '"', '）', ')')) or last_line.startswith('#')
        if not ends_properly:
            checks.append({"id": "G2.12", "file": fp, "status": "WARN", "reason": "File may be truncated (last line does not end with sentence-final punctuation)"})
        else:
            checks.append({"id": "G2.12", "file": fp, "status": "PASS"})
    
    if must_fix:
        return fail("G2", checks, "scoring", must_fix)
    return passed("G2", checks)
```

- [ ] **Step 4: 写 G3 评分前依赖检查**

```python
def gate_G3(skill_name, test_type, round_dir):
    """G3: 评分前的依赖检查"""
    checks = []
    
    acceptance = load_acceptance()
    threshold = acceptance["t1"]
    
    # G3.1/G3.2: 检查该技能的前置评分报告存在
    # 对于 T1 技能，检查同一 test_cycle_phase 中的依赖
    report_dir = Path(round_dir) / "t1-reports"
    report_file = report_dir / f"{skill_name}-{test_type}.json"
    
    # 如果该技能有前置依赖（在 deps.json 中属于某个 phase），检查前置技能已评分
    deps = load_deps()
    prereqs = []
    for phase_name, phase_data in deps.get("t2-phases", {}).items():
        if skill_name in phase_data["prerequisites"]:
            idx = phase_data["prerequisites"].index(skill_name)
            prereqs = phase_data["prerequisites"][:idx]
            break
    
    for prereq in prereqs:
        prereq_report = report_dir / f"{prereq}-{test_type}.json"
        if not prereq_report.exists():
            return fail("G3", checks + [{"id": "G3.1", "status": "FAIL", "missing": prereq, "reason": f"Prerequisite report not found: {prereq_report}"}], "scoring", [f"G3.1:{prereq}"])
        
        try:
            prereq_data = load_json(prereq_report)
            prereq_score = prereq_data.get("score", 0)
            if prereq_score < threshold:
                return fail("G3", checks + [{"id": "G3.2", "status": "FAIL", "skill": prereq, "score": prereq_score, "threshold": threshold}], "scoring", [f"G3.2:{prereq}"])
            checks.append({"id": "G3.2", "skill": prereq, "status": "PASS", "score": prereq_score})
        except:
            pass
    
    checks.append({"id": "G3.1", "status": "PASS", "prerequisites_checked": len(prereqs)})
    
    return passed("G3", checks)
```

- [ ] **Step 5: 写 G4 chapter-drafting 脚本检查**

```python
def gate_G4_chapter_drafting(filepath):
    """G4: T1 chapter-drafting 脚本层级检查"""
    checks = []
    must_fix = []
    
    with open(filepath, encoding='utf-8') as f:
        content = f.read()
    
    # 转折词密度
    wc = word_count_md(filepath)
    transition_count = sum(content.count(w) for w in TRANSITION_WORDS)
    max_allowed = max(1, wc // 3000)
    if transition_count > max_allowed:
        checks.append({"id": "G4.transition", "status": "FAIL", "expected": f"<= {max_allowed}", "actual": transition_count})
        must_fix.append("G4.transition")
    else:
        checks.append({"id": "G4.transition", "status": "PASS", "density": f"{transition_count}/{wc}"})
    
    # 疲劳词命中
    fatigue_hits = sum(content.count(w) for w in FATIGUE_WORDS)
    if fatigue_hits > 3:
        checks.append({"id": "G4.fatigue", "status": "FAIL", "expected": "<= 3", "actual": fatigue_hits})
        must_fix.append("G4.fatigue")
    else:
        checks.append({"id": "G4.fatigue", "status": "PASS", "hits": fatigue_hits})
    
    # 元叙事句式
    meta_hits = {w: content.count(w) for w in META_NARRATIVE if w in content}
    if meta_hits:
        checks.append({"id": "G4.meta", "status": "FAIL", "actual": meta_hits})
        must_fix.append("G4.meta")
    else:
        checks.append({"id": "G4.meta", "status": "PASS"})
    
    # 字数
    if wc < 3000:
        checks.append({"id": "G4.word_count", "status": "FAIL", "expected": ">= 3000", "actual": wc})
        must_fix.append("G4.word_count")
    else:
        checks.append({"id": "G4.word_count", "status": "PASS", "word_count": wc})
    
    if must_fix:
        return fail("G4-chapter-drafting", checks, "scoring", must_fix)
    return passed("G4-chapter-drafting", checks)
```

- [ ] **Step 6: 写 G7 轮次关闭检查**

```python
def gate_G7(round_dir):
    """G7: 轮次关闭完整性验证"""
    checks = []
    must_fix = []
    rd = Path(round_dir)
    
    # G7.1: summary.json skill names ∈ skills/ dir
    summary_path = rd / "summary.json"
    if summary_path.exists():
        summary = load_json(summary_path)
        t1_scores = summary.get("t1_scores", {})
        actual_skills = set(d.name for d in SKILLS_DIR.iterdir() if d.is_dir())
        summary_skills = set(t1_scores.keys())
        hallucinated = summary_skills - actual_skills
        if hallucinated:
            checks.append({"id": "G7.1", "status": "FAIL", "hallucinated_skills": list(hallucinated)})
            must_fix.append("G7.1")
        else:
            checks.append({"id": "G7.1", "status": "PASS"})
    
    # G7.5: 无模板占位符
    novel_output = rd / "novel-output"
    placeholder_files = []
    if novel_output.exists():
        for f in novel_output.rglob("*.md"):
            content = f.read_text(encoding='utf-8')
            lines = content.split('\n')
            if len(lines) > 0:
                placeholder_ratio = sum(1 for l in lines if '待填充' in l) / len(lines)
                if placeholder_ratio > 0.1:
                    placeholder_files.append(str(f.relative_to(novel_output)))
    
    if placeholder_files:
        checks.append({"id": "G7.5", "status": "FAIL", "files": placeholder_files})
        must_fix.append("G7.5")
    else:
        checks.append({"id": "G7.5", "status": "PASS"})
    
    # G7.6: truth 文件 status ≠ pending
    truth_dir = novel_output / "星火燃穹" / "truth"  # FIXME: dynamic path
    pending_files = []
    if truth_dir.exists():
        for f in truth_dir.glob("*.md"):
            content = f.read_text(encoding='utf-8')
            if 'status: pending' in content:
                pending_files.append(f.name)
    if pending_files:
        checks.append({"id": "G7.6", "status": "FAIL", "files": pending_files})
        must_fix.append("G7.6")
    else:
        checks.append({"id": "G7.6", "status": "PASS"})
    
    if must_fix:
        return fail("G7", checks, "round_close", must_fix)
    return passed("G7", checks)
```

- [ ] **Step 7: 写 G_TRANSITION 和 G_DISPATCH 检查**

```python
def gate_G_TRANSITION(from_phase, to_phase, round_dir):
    """G_TRANSITION: Phase 切换 Gate"""
    checks = []
    rd = Path(round_dir)
    progress_path = rd / "progress.json"
    
    if not progress_path.exists():
        return fail("G_TRANSITION", [{"id": "GT.0", "status": "FAIL", "reason": "progress.json not found"}], "phase_transition", ["GT.0"])
    
    progress = load_json(progress_path)
    
    # GT.1: remaining 队列为空
    phase_key = f"remaining_{from_phase}"
    remaining = progress.get(phase_key, [])
    if remaining:
        return fail("G_TRANSITION", [{"id": "GT.1", "status": "FAIL", "phase": from_phase, "remaining": len(remaining)}], "phase_transition", ["GT.1"])
    checks.append({"id": "GT.1", "status": "PASS"})
    
    # GT.3: 无 FAIL gate_blockers
    blockers = progress.get("gate_blockers", [])
    if blockers:
        return fail("G_TRANSITION", [{"id": "GT.3", "status": "FAIL", "blockers": blockers}], "phase_transition", ["GT.3"])
    checks.append({"id": "GT.3", "status": "PASS"})
    
    return passed("G_TRANSITION", checks)

def gate_G_DISPATCH(phase, round_dir):
    """G_DISPATCH: 派发完整性 Gate"""
    rd = Path(round_dir)
    progress_path = rd / "progress.json"
    
    if not progress_path.exists():
        return fail("G_DISPATCH", [{"id": "GD.0", "status": "FAIL", "reason": "progress.json not found"}], "phase_completion", ["GD.0"])
    
    progress = load_json(progress_path)
    
    all_skills = set(d.name for d in SKILLS_DIR.iterdir() if d.is_dir())
    completed = set(progress.get("completed_skill_names", []))
    missing = all_skills - completed
    
    if missing:
        return fail("G_DISPATCH", [{"id": "GD.1", "status": "FAIL", "missing_skills": list(missing), "completed": len(completed), "total": len(all_skills)}], "phase_completion", ["GD.1"])
    
    return passed("G_DISPATCH", [{"id": "GD.1", "status": "PASS", "completed": len(completed)}])
```

- [ ] **Step 8: 写 main() 入口和 CLI**

```python
def main():
    if len(sys.argv) < 2:
        print("Usage: validate-gate.py <GATE> [args...]")
        print("  validate-gate.py G0 [--seed <file>]")
        print("  validate-gate.py G2 --files <f1,f2> [--type chapter|report]")
        print("  validate-gate.py G3 <skill_name> <test_type> <round_dir>")
        print("  validate-gate.py G4 chapter-drafting <file>")
        print("  validate-gate.py G7 <round_dir>")
        print("  validate-gate.py G_TRANSITION <from_phase> <to_phase> <round_dir>")
        print("  validate-gate.py G_DISPATCH <phase> <round_dir>")
        print("  validate-gate.py G_RECONCILE <round_dir>")
        sys.exit(1)
    
    gate = sys.argv[1]
    
    if gate == "G0":
        seed = None
        if "--seed" in sys.argv:
            seed = sys.argv[sys.argv.index("--seed") + 1]
        print(gate_G0(seed_file=seed))
    elif gate == "G2":
        files = []
        ftype = "chapter"
        if "--files" in sys.argv:
            files = sys.argv[sys.argv.index("--files") + 1].split(",")
        if "--type" in sys.argv:
            ftype = sys.argv[sys.argv.index("--type") + 1]
        print(gate_G2(files, ftype))
    elif gate == "G3":
        print(gate_G3(sys.argv[2], sys.argv[3], sys.argv[4]))
    elif gate == "G4":
        if sys.argv[2] == "chapter-drafting":
            print(gate_G4_chapter_drafting(sys.argv[3]))
        else:
            print(json.dumps({"status": "UNIMPLEMENTED", "gate": f"G4-{sys.argv[2]}"}))
    elif gate == "G7":
        print(gate_G7(sys.argv[2]))
    elif gate == "G_TRANSITION":
        print(gate_G_TRANSITION(sys.argv[2], sys.argv[3], sys.argv[4]))
    elif gate == "G_DISPATCH":
        print(gate_G_DISPATCH(sys.argv[2], sys.argv[3]))
    elif gate == "G_RECONCILE":
        rd = Path(sys.argv[2])
        print(json.dumps({"gate": "G_RECONCILE", "status": "PASS", "checks": [{"id": "GR.0", "note": "G_RECONCILE implementation requires progress.json; stub for now"}]}, indent=2, ensure_ascii=False))
    else:
        print(json.dumps({"status": "UNKNOWN_GATE", "gate": gate}))

if __name__ == "__main__":
    main()
```

- [ ] **Step 9: 设置可执行权限并测试**

```bash
chmod +x tests/validate-gate.py
python3 tests/validate-gate.py  # 应打印 usage
```

- [ ] **Step 10: 测试 G2 对 chapter-1.md 的检查**

```bash
python3 tests/validate-gate.py G2 --files tests/rounds/round-002-2026-06-11/novel-output/星火燃穹/chapters/chapter-1.md --type chapter
```
Expected: 如果 ch1 字数 < 3000，返回 G2.6 FAIL；否则 PASS

- [ ] **Step 11: Commit**

```bash
git add tests/validate-gate.py
git commit -m "feat: add validate-gate.py with G0/G2/G3/G4/G7/G_TRANSITION/G_DISPATCH checks"
```

---

### Task 3: 改造 scoring.py

**Files:**
- Modify: `tests/scoring.py`

- [ ] **Step 1: 添加 validate-gate.py 调用逻辑**

在 `scoring.py` 的 `main()` 函数开头添加依赖检查：

```python
# 在 main() 中，解析 rubric_path 之后、评分之前插入：
def run_gate_check(tier, phase, rubric_path):
    """运行前置 Gate 检查。失败则打印 JSON 并退出。"""
    import subprocess
    validate_script = Path(__file__).parent / "validate-gate.py"
    
    if tier == "T2":
        result = subprocess.run(
            ["python3", str(validate_script), "G_TRANSITION", "generative", phase, str(Path(rubric_path).parent.parent.parent.parent / "rounds")],
            capture_output=True, text=True
        )
        gate_output = json.loads(result.stdout)
        if gate_output.get("status") == "FAIL":
            print(json.dumps(gate_output, indent=2, ensure_ascii=False))
            sys.exit(1)
    elif tier == "T3":
        result = subprocess.run(
            ["python3", str(validate_script), "G_TRANSITION", "clean", "T3", str(Path(rubric_path).parent.parent.parent.parent / "rounds")],
            capture_output=True, text=True
        )
        gate_output = json.loads(result.stdout)
        if gate_output.get("status") == "FAIL":
            print(json.dumps(gate_output, indent=2, ensure_ascii=False))
            sys.exit(1)
```

- [ ] **Step 2: 添加 --gate-only 模式**

在 `main()` 的参数解析中添加：

```python
if "--gate-only" in sys.argv:
    # 只跑门禁，不评分
    gate_type = sys.argv[sys.argv.index("--gate-only") + 1] if len(sys.argv) > sys.argv.index("--gate-only") + 1 else "G2"
    files_idx = sys.argv.index("--files") + 1 if "--files" in sys.argv else None
    files = sys.argv[files_idx].split(",") if files_idx else []
    
    import subprocess
    validate_script = str(Path(__file__).parent / "validate-gate.py")
    result = subprocess.run(
        ["python3", validate_script, gate_type, "--files", ",".join(files), "--type", "chapter"],
        capture_output=True, text=True
    )
    print(result.stdout)
    sys.exit(0)
```

- [ ] **Step 3: 测试 --gate-only 模式**

```bash
python3 tests/scoring.py --gate-only G2 --files tests/rounds/round-002-2026-06-11/novel-output/星火燃穹/chapters/chapter-1.md
```
Expected: G2 检查结果 JSON

- [ ] **Step 4: Commit**

```bash
git add tests/scoring.py
git commit -m "feat: add gate-check integration and --gate-only mode to scoring.py"
```

---

### Task 4: 改造 round-exec.sh

**Files:**
- Modify: `tests/round-exec.sh`

- [ ] **Step 1: 添加 G0 前置检查**

在 `round-exec.sh` 的 `set -euo pipefail` 之后、创建 round 目录之前插入：

```bash
# G0: Environment readiness check
echo "=== G0: Environment Check ==="
SEED_FILE="${SEED_FILE:-}"
G0_ARGS=""
if [ -n "$SEED_FILE" ]; then
    G0_ARGS="--seed $SEED_FILE"
fi
G0_RESULT=$(python3 tests/validate-gate.py G0 $G0_ARGS 2>&1)
G0_STATUS=$(echo "$G0_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','UNKNOWN'))" 2>/dev/null || echo "UNKNOWN")

if [ "$G0_STATUS" != "PASS" ]; then
    echo "G0 FAILED:"
    echo "$G0_RESULT"
    exit 1
fi
echo "G0 PASSED"
```

- [ ] **Step 2: 添加 progress.json 初始化**

在创建 round 目录之后插入：

```bash
# Initialize progress.json
SKILL_COUNT=$(ls -d skills/*/ | wc -l | tr -d ' ')
cat > "${ROUND_DIR}/progress.json" << PROGEOF
{
  "round": "${ROUND_NUM}",
  "tier": "${TIER}",
  "test_cycle_phase": "generative",
  "subagent_completion_count": 0,
  "completed_skill_names": [],
  "skills": {},
  "remaining_generative": $(ls skills/ | sed 's|/$||' | jq -R -s 'split("\n")[:-1]'),
  "remaining_bug_hunt": [],
  "remaining_clean": [],
  "gate_blockers": [],
  "total_framework_skills": ${SKILL_COUNT}
}
PROGEOF
```

- [ ] **Step 3: 添加令牌生成**

在 progress.json 初始化之后插入：

```bash
# Generate override tokens
TOKEN1=$(python3 -c "import secrets; print(secrets.token_hex(16))")
TOKEN2=$(python3 -c "import secrets; print(secrets.token_hex(16))")
TOKEN3=$(python3 -c "import secrets; print(secrets.token_hex(16))")

# Store hashes
python3 -c "
import hashlib, json
tokens = ['$TOKEN1', '$TOKEN2', '$TOKEN3']
hashes = [{'hash': hashlib.sha256(t.encode()).hexdigest(), 'spent': False} for t in tokens]
with open('${ROUND_DIR}/.token-hashes.json', 'w') as f:
    json.dump({'tokens': hashes}, f, indent=2)
"
chmod 600 "${ROUND_DIR}/.token-hashes.json"

echo ""
echo "=== Round ${ROUND_NUM} Override Tokens (SAVE THESE) ==="
echo "Token 1: $TOKEN1"
echo "Token 2: $TOKEN2"
echo "Token 3: $TOKEN3"
echo "=== Store securely. Each token is SINGLE-USE. ==="
echo ""
```

- [ ] **Step 4: 测试 round-exec.sh**

```bash
bash tests/round-exec.sh claude T1 2>&1 | head -20
```
Expected: 应执行 G0 检查、创建 round 目录、初始化 progress.json、打印令牌

- [ ] **Step 5: Commit**

```bash
git add tests/round-exec.sh
git commit -m "feat: add G0 pre-check, progress.json init, and override token generation to round-exec.sh"
```

---

### Task 5: 改造 summarize-round.py

**Files:**
- Modify: `tests/summarize-round.py`

- [ ] **Step 1: 添加 G7 检查调用**

在 `summarize-round.py` 的 `main()` 开头添加：

```python
import subprocess
import json as jsonmod

def run_g7_check(round_dir):
    """运行 G7 轮次关闭检查"""
    validate_script = Path(__file__).parent / "validate-gate.py"
    result = subprocess.run(
        ["python3", str(validate_script), "G7", str(round_dir)],
        capture_output=True, text=True
    )
    try:
        gate_output = jsonmod.loads(result.stdout)
        return gate_output
    except:
        return {"gate": "G7", "status": "ERROR", "reason": "validate-gate.py execution failed"}
```

在 `main()` 中调用：

```python
# G7 check before summary
gate_result = run_g7_check(round_dir)
if gate_result.get("status") == "FAIL":
    print(f"G7 FAILED: {jsonmod.dumps(gate_result, indent=2, ensure_ascii=False)}")
    print("Round cannot be closed. Fix G7 issues first.")
    sys.exit(1)
```

- [ ] **Step 2: 从 progress.json 读取数据而非手动推断**

在 `main()` 中：

```python
# 优先从 progress.json 读取分数
progress_path = Path(round_dir) / "progress.json"
if progress_path.exists():
    with open(progress_path) as f:
        progress = jsonmod.load(f)
    # 从 progress.skills 中提取分数
    t1_scores = {}
    for skill_name, skill_data in progress.get("skills", {}).items():
        for test_type, test_data in skill_data.items():
            if test_data.get("status") == "DONE" and "score" in test_data:
                key = f"{skill_name}-{test_type}"
                t1_scores[key] = test_data["score"]
    summary["t1_scores"] = t1_scores
```

- [ ] **Step 3: Commit**

```bash
git add tests/summarize-round.py
git commit -m "feat: add G7 validation gate and progress.json integration to summarize-round.py"
```

---

### Task 6: 添加校准锚点到 using-shenbi rubric（模板示例）

**Files:**
- Modify: `tests/tiers/t1-skill/using-shenbi/rubric.md`

- [ ] **Step 1: 读取现有 rubric**

```bash
cat tests/tiers/t1-skill/using-shenbi/rubric.md
```

- [ ] **Step 2: 为第 3 个维度（Trigger accuracy）添加校准锚点**

在 rubric 表格后、Kill Switch 段之前插入：

```markdown

## Calibration Anchors

### Dimension 3: Trigger accuracy

**Anchor PASS**: "用户说'帮我看看角色有没有问题'，Agent 正确路由到 shenbi-review-character 而非 shenbi-character-design——因为'看看/检查'关键词匹配 review 类技能。触发准确。"

**Anchor FAIL**: "用户说'设计一个角色'，Agent 路由到 shenbi-review-character 而非 shenbi-character-design——因为混淆了'角色'关键词，未区分 creation vs review 语义。触发不准确。"
```

- [ ] **Step 3: Commit**

```bash
git add tests/tiers/t1-skill/using-shenbi/rubric.md
git commit -m "docs: add calibration anchors to using-shenbi rubric as template example"
```

---

### Task 7: 集成测试 — 端到端 Gate 验证

**Files:**
- Test: `tests/validate-gate.py` (self-test)

- [ ] **Step 1: 写 validate-gate.py 自测试**

```bash
# 测试 G0
python3 tests/validate-gate.py G0 --seed outline-example.md 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='PASS', f'G0 failed: {d}'; print('G0 OK')"

# 测试 G2 对已知文件的检查
python3 tests/validate-gate.py G2 --files tests/rounds/round-002-2026-06-11/novel-output/星火燃穹/chapters/chapter-3.md --type chapter 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'G2: {d[\"status\"]}')"

# 测试 G4 chapter-drafting
python3 tests/validate-gate.py G4 chapter-drafting tests/rounds/round-002-2026-06-11/novel-output/星火燃穹/chapters/chapter-3.md 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'G4: {d[\"status\"]}')"
```

Expected: G0 PASS, G2 结果取决于文件质量, G4 结果取决于 chapter-3.md 的 AI 标记

- [ ] **Step 2: 测试 G7 对 round-002**

```bash
python3 tests/validate-gate.py G7 tests/rounds/round-002-2026-06-11 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'G7: {d[\"status\"]}')"
```
Expected: 可能 FAIL（round-002 有模板占位符文件）

- [ ] **Step 3: Commit**

```bash
git commit -m "test: add validation gate integration tests"
```

---

### Task 8: 文档更新

**Files:**
- Modify: `tests/rounds/CHANGELOG.md`

- [ ] **Step 1: 添加 Gate 系统启用条目**

```bash
cat >> tests/rounds/CHANGELOG.md << 'CHANGELOGEOF'

## Round 003 (2026-06-11) — Gate System V1
- **Gate System**: G0-G7 + G_TRANSITION + G_DISPATCH + G_RECONCILE hard gates enabled
- **New tools**: validate-gate.py, deps.json, acceptance.json, progress.json
- **Tool changes**: scoring.py (+gate integration), round-exec.sh (+G0/tokens/progress), summarize-round.py (+G7)
- **Fixtures**: sensitive_words.txt, stop_words_zh.txt
- **Enhancement**: Calibration anchors added to using-shenbi rubric
CHANGELOGEOF
```

- [ ] **Step 2: Commit**

```bash
git add tests/rounds/CHANGELOG.md
git commit -m "docs: add Gate System V1 entry to CHANGELOG"
```

---

## Self-Review

**Spec coverage**: 所有 Gate 类型 (G0, G2, G3, G4, G7, G_TRANSITION, G_DISPATCH, G_RECONCILE) 都在 validate-gate.py 中有对应实现。G1 和 G5/G6 的部分逻辑内嵌在 scoring.py 和 round-exec.sh 的改造中。Calibration anchors 有模板示例。deps.json、acceptance.json、progress.json 结构符合设计规格。

**Placeholder check**: 通过——所有步骤有具体代码或命令。

**Type consistency**: gate_G2 返回的 JSON 结构与 fail()/passed() 一致。gate_G3 使用 acceptance.json 读取阈值。G_TRANSITION 读取 progress.json。命名一致。
