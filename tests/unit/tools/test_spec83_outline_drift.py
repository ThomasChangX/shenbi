"""spec #83 T3: canon 回灌对账——卷一四实证作夹具（P1-2 根因链）。

实证锚（tests/fixtures/spec83/，G0.9 真实项目片段精确拷贝）：
- outline/volume_map.md:88 第35章四件清单（红纸包、火纹骨哨、半部《鉴录》、
  私账残页）vs truth/facts/props.json 持有集——truth 持有第二把哨
  （火纹骨哨·帖木哥支 / 火纹骨哨（老驼所授·主线）），节点清单只一把；
- outline/volume_map.md:105 跨卷桥接行「火纹骨哨：老驼临终塞给他的持灯人
  信物」vs truth/prop_registry.md 事件行——实际 ch2:180 老驼存续授哨，
  双方 2+ 字词集交集为空；
- outline/volume_map.md:21 梗位复用「渡鸦局档案卡」（卷末彩蛋承诺件，
  第36章后附）正文缺件；
- chapters/chapter-1.md:43 纸坊三十文欠账行 vs
  genesis-context/chapter_outline.md:370 还账进度表（私账打卡）首批六行
  （蔗海/泡沫名单/坦波夫征粮令/抄家焚匣/断手账簿/白城夺名）——早期欠账
  不在排期。r5-M5 适配：ch36 五欠账正文行不在包内，正例取包内 ch1:43
  真实欠账行（已核对其不在进度表首批）。
"""

from __future__ import annotations

from pathlib import Path

from tools.lint_outline_truth_drift import main, run_lint

FIX = Path(__file__).resolve().parents[2] / "fixtures" / "spec83"


def test_second_whistle_missing_from_node_list():  # 双哨 canon：truth 持有、节点清单只一把
    findings = run_lint(FIX)  # volume_map:88 四件清单 vs props.json（两把哨）
    assert any("骨哨" in f.detail and "节点清单" in f.detail for f in findings)


def test_provenance_phrase_mismatch():  # 「临终塞给他」vs 实际 ch2 存续授哨——词集交集空
    findings = run_lint(FIX)
    assert any(
        "火纹骨哨" in f.detail and "临终" in f.detail and f.face == "来历短语对账" for f in findings
    )


def test_promise_item_missing():  # 渡鸦局档案卡（卷纲 L21 承诺件）正文缺件
    findings = run_lint(FIX)
    assert any("渡鸦局档案卡" in f.detail and f.face == "承诺件对账" for f in findings)


def test_new_debt_not_scheduled():  # 纸坊三十文（ch1:43）不在还账进度表首批六行
    findings = run_lint(FIX)
    assert any("纸坊三十文" in f.detail and f.face == "欠账对账" for f in findings)


def test_fixture_run_exit_1_and_read_only(capsys):  # 真实包：有 finding → exit 1；只读不写
    before = {p: p.stat().st_mtime_ns for p in FIX.rglob("*") if p.is_file()}
    assert main([str(FIX)]) == 1
    after = {p: p.stat().st_mtime_ns for p in FIX.rglob("*") if p.is_file()}
    assert before == after


def test_declarations_stub_errors_exit_2(capsys):  # Task 13 实装前的骨架：明确报错
    assert main([str(FIX), "--declarations"]) == 2


def test_missing_seed_outline_skips_debt_face(tmp_path):  # 种子文件缺失 → 欠账面 SKIP 不硬崩
    (tmp_path / "outline").mkdir()
    (tmp_path / "outline" / "volume_map.md").write_text(
        "## 第一卷：试（第 1-2 章）\n"
        "| 第1章 | a | 起：红纸包、骨哨——两件同匣。 |\n\n"
        "### 跨卷桥接\n\n"
        "| # | 钩子内容 | 类型 | 带入卷 | 预期激活章 | 当前状态 |\n"
        "|---|---|---|---|---|---|\n"
        "| 1 | 骨哨：老驼临终塞给他 | 物品 | 第二卷 | 第2章 | 已种植 |\n",
        encoding="utf-8",
    )
    (tmp_path / "truth" / "facts").mkdir(parents=True)
    (tmp_path / "truth" / "facts" / "props.json").write_text('{"facts": {}}', encoding="utf-8")
    (tmp_path / "truth" / "prop_registry.md").write_text(
        "| 实体名 | 当前owner | 经手事件 |\n|---|---|---|\n| 骨哨 | 那罕 | 第1章老驼递给他 |\n",
        encoding="utf-8",
    )
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-1.md").write_text("他欠了纸坊三十文。\n", encoding="utf-8")
    # 无 genesis-context/chapter_outline.md → 欠账面 SKIP：欠账行不产生 finding
    findings = run_lint(tmp_path)
    assert not any(f.face == "欠账对账" for f in findings)


def test_clean_project_zero_findings_exit_0(tmp_path, capsys):  # 零悬空 → exit 0
    (tmp_path / "outline").mkdir()
    (tmp_path / "outline" / "volume_map.md").write_text(
        "## 第一卷：试（第 1-1 章）\n| 第1章 | a | 他一路南行。 |\n",
        encoding="utf-8",
    )
    (tmp_path / "truth" / "facts").mkdir(parents=True)
    (tmp_path / "truth" / "facts" / "props.json").write_text('{"facts": {}}', encoding="utf-8")
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-1.md").write_text("他一路南行。\n", encoding="utf-8")
    (tmp_path / "genesis-context").mkdir()
    (tmp_path / "genesis-context" / "chapter_outline.md").write_text(
        "- 还账进度表（私账打卡）：首批六行——蔗海、泡沫名单。\n", encoding="utf-8"
    )
    assert run_lint(tmp_path) == []
    assert main([str(tmp_path)]) == 0
