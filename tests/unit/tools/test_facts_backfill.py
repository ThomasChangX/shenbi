"""spec #80 T13: facts_backfill 工具 + 验收 3 绿语料（per-chapter 前置态种子）。

R1-C3：绿断言用 per-chapter 前置态（ch9 喂 count=3、ch20 喂 副本 owner=帖木哥），
非终态种子（终态撞 F17 总数对账/F16 cp 合法性假红）。G0.9：语料=测试内构造的
结构输入（tmp mini-project 镜像 regen-vol1 形态）；真实项目只 dry-run（F947）。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.facts_backfill import derive_seeds, main, plan_memo_backfill, registry_rewrites

# ── tmp mini-project（镜像 novel-xinghuo-vol1 修复后正典形态）──

PROP_REGISTRY = """# 物象登记

| 物象 | 现持 | 经手 |
|---|---|---|
| 火纹骨哨（老驼所授·主线） | 那罕 | 贴身细绳所系；第 3 章登记桌前隔布发烫一次未吹 |
| 火纹骨哨（帖木哥所持·旧线） | 那罕 | 第20章 帖木哥从灯座底下抽出、布包交那罕 |
| 半部《鉴录》 | 林烽 | 第 9 章夜营火圈摊在膝上，第一页两个名字写得规矩，翻到第三页写第三个名字「赵三，某县，附籍」 |
| 竹笔 | 林烽 | 陆秉文遗物（对照行：backfill 不得触碰） |
"""

NAME_REGISTRY = """# 称谓字典

| 类别 | 名 | 备注 |
|---|---|---|
| 登记名 | 临 | 全卷一致（#74 项 4） |
| 别名 | 林烽 | 第一章星象局账房用名（从九品） |
| 旌名 | 那罕 | 第 3 章屯庄附籍册官给名（黑色／附籍） |
| 民夫·赵三 | 赵三 | 第 9 章路倒；夜写入《鉴录》第三个名字 |
"""

CH9 = """<!--META-BEGIN-->
## PRE_WRITE_CHECK

- 本章核心任务: 夜里在《鉴录》添第四个名字。
<!--META-END-->

那罕把《鉴录》摊在膝盖上。第一页三个名字，写得规矩。

蘸墨写下：赵三，某县，附籍，路倒。
"""

CH9_PLAN = "# 第9章 备忘\n\n## 6. 场景\n\n- 场景1: 1900字｜独立型\n"
CH20_PLAN = "# 第20章 备忘\n\n## 6. 场景\n\n- 场景1: 2000字｜收束型\n"
CH5_PLAN = (
    "# 第5章 备忘\n\n- 物象: 红纸包｜那罕（自持，压册页，未易主）；萤染的布｜哑姑→那罕（哑姑塞给那罕，经手成立）；"
    "火纹骨哨｜纯提及（贴身发烫，未易手）\n"
)


def _mini_project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "truth").mkdir(parents=True)
    (root / "chapters").mkdir()
    (root / "plans").mkdir()
    (root / "truth" / "prop_registry.md").write_text(PROP_REGISTRY, "utf-8")
    (root / "truth" / "name_registry.md").write_text(NAME_REGISTRY, "utf-8")
    (root / "chapters" / "chapter-9.md").write_text(CH9, "utf-8")
    for name, text in (
        ("chapter-9-plan.md", CH9_PLAN),
        ("chapter-20-plan.md", CH20_PLAN),
        ("chapter-5-plan.md", CH5_PLAN),
    ):
        (root / "plans" / name).write_text(text, "utf-8")
    return root


# ── 面1：三维种子派生 ──


def test_dry_run_default_writes_nothing(tmp_path: Path) -> None:
    root = _mini_project(tmp_path)
    rc = main(["--project", str(root)])
    assert rc == 0
    assert not (root / "truth" / "facts").exists()
    assert (root / "truth" / "prop_registry.md").read_text("utf-8") == PROP_REGISTRY
    assert (root / "truth" / "name_registry.md").read_text("utf-8") == NAME_REGISTRY
    assert (root / "plans" / "chapter-9-plan.md").read_text("utf-8") == CH9_PLAN


def test_apply_seeds_three_dims(tmp_path: Path) -> None:
    root = _mini_project(tmp_path)
    rc = main(["--project", str(root), "--apply"])
    assert rc == 0
    props = json.loads((root / "truth" / "facts" / "props.json").read_text("utf-8"))
    # audit-T13 C1：表头行（物象/现持/经手）绝不混入种子
    assert "物象" not in props["facts"] and "现持" not in props["facts"]
    assert len(props["facts"]) == 4  # 四数据行，无垃圾头行
    assert props["facts"]["火纹骨哨"]["owner"] == "那罕"
    assert props["facts"]["火纹骨哨·帖木哥支"]["owner"] == "那罕"  # 副本键约定
    assert props["facts"]["半部《鉴录》"]["owner"] == "林烽"
    assert any(
        op.get("prop") == "火纹骨哨·帖木哥支"
        and op.get("op") == "acquire"
        and op.get("chapter") == 20
        for op in props["ops_log"]
    )
    counters = json.loads((root / "truth" / "facts" / "counters.json").read_text("utf-8"))
    assert counters["facts"]["鉴录名数"]["value"] == 4  # ch9 正典：3+1
    identity = json.loads((root / "truth" / "facts" / "identity.json").read_text("utf-8"))
    assert identity["facts"]["主角"] == {
        "narration_name": "那罕",
        "from_ch": 3,
        "aliases": ["林烽"],
    }


def test_seeds_refuse_when_canon_anchor_missing(tmp_path: Path) -> None:
    root = _mini_project(tmp_path)
    (root / "chapters" / "chapter-9.md").write_text("正文无计数锚。\n", "utf-8")
    seeds = derive_seeds(root)
    assert seeds.counters is None  # 确定性守卫：锚缺席拒派生非报假值


# ── 面2：memo 声明行 backfill（幂等）──


def test_memo_backfill_and_idempotency(tmp_path: Path) -> None:
    root = _mini_project(tmp_path)
    rc = main(["--project", str(root), "--apply"])
    assert rc == 0
    ch9 = (root / "plans" / "chapter-9-plan.md").read_text("utf-8")
    assert "- 计数: 鉴录名数 3+1" in ch9 and "历史补录" in ch9
    ch20 = (root / "plans" / "chapter-20-plan.md").read_text("utf-8")
    assert "- 火纹骨哨·帖木哥支@acquire: 那罕\n" in ch20  # 值位无括注（M-1）
    assert "@acquire: 那罕（" not in ch20
    ch5 = (root / "plans" / "chapter-5-plan.md").read_text("utf-8")
    assert "- 红纸包@hold: 那罕" in ch5
    assert "- 萤染的布@transfer: 哑姑→那罕" in ch5
    # audit-T13 I-1：注记形态（纯提及）不得产出 hold 行——否则 cp.prop_decl
    # 「声明持有者『纯提及』≠ facts 现态 owner」硬败
    assert "纯提及" not in ch5.split("历史补录")[-1]
    before = {p.name: p.read_text("utf-8") for p in (root / "plans").glob("*.md")}
    rc2 = main(["--project", str(root), "--apply"])
    assert rc2 == 0
    after = {p.name: p.read_text("utf-8") for p in (root / "plans").glob("*.md")}
    assert before == after  # 幂等


def test_plan_memo_backfill_skips_existing_canonical_lines() -> None:
    memo = "# 备忘\n\n- 计数: 鉴录名数 3+1\n"
    out = plan_memo_backfill(memo, counter_line="- 计数: 鉴录名数 3+1")
    assert out == memo  # 已有规范行零追加


# ── 面3：registry 陈旧行重写（外科式，绝不整文件重生成）──


def test_registry_stale_rows_rewritten(tmp_path: Path) -> None:
    root = _mini_project(tmp_path)
    rc = main(["--project", str(root), "--apply"])
    assert rc == 0
    name_reg = (root / "truth" / "name_registry.md").read_text("utf-8")
    assert "夜写入《鉴录》第四个名字" in name_reg
    assert "全卷一致" not in name_reg  # 临 备注重写
    prop_reg = (root / "truth" / "prop_registry.md").read_text("utf-8")
    assert "第一页三个名字写得规矩" in prop_reg
    assert "写第四个名字「赵三" in prop_reg
    assert "陆秉文遗物（对照行：backfill 不得触碰）" in prop_reg  # 对照行逐字保留


def test_registry_rewrites_surgical() -> None:
    text = PROP_REGISTRY
    out = registry_rewrites(text)
    assert out.count("\n") == text.count("\n")  # 行数不变=非整档重生成
    assert "竹笔 | 林烽 | 陆秉文遗物" in out


# ── 验收 3：修复后语料全绿（per-chapter 前置态种子，R1-C3）──


@pytest.mark.unit
def test_acceptance3_ch9_green_with_pre_state(tmp_path: Path) -> None:
    from shenbi.gates.g4.chapter_drafting import check_counter_reconciliation

    root = _mini_project(tmp_path)
    main(["--project", str(root), "--apply"])
    memo = (root / "plans" / "chapter-9-plan.md").read_text("utf-8")
    counters = {"鉴录名数": {"value": 3}}  # 前置态：ch8 后、ch9 前
    issues = check_counter_reconciliation(CH9, memo, counters)
    assert issues == []


@pytest.mark.unit
def test_acceptance3_ch20_green_with_pre_state(tmp_path: Path) -> None:
    from shenbi.gates.g4.chapter_drafting import check_prop_handoffs
    from shenbi.gates.g4.cross_chapter import check_narration_name

    green = Path("tests/fixtures/invariant-mutants/ch20-fixed-green.md").read_text("utf-8")
    root = _mini_project(tmp_path)
    main(["--project", str(root), "--apply"])
    memo = (root / "plans" / "chapter-20-plan.md").read_text("utf-8")
    # 前置态：主线=那罕；副本=帖木哥（交付前夜）
    props = {
        "火纹骨哨": {"owner": "那罕"},
        "火纹骨哨·帖木哥支": {"owner": "帖木哥"},
    }
    assert check_prop_handoffs(green, memo_text=memo, props=props) == []
    identity = {"narration_name": "那罕", "from_ch": 3, "aliases": ["林烽"]}
    assert check_narration_name(green, identity, memo, chapter=20) == []
