"""Test gate marker writing for integrity verification."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

VG = Path(__file__).resolve().parent / "validate-gate.py"


class TestGateMarkers(unittest.TestCase):
    """Test that validate-gate.py writes gate marker files on PASS."""

    def _run_vg(self, *args):
        """Run validate-gate.py as subprocess, return (stdout, stderr, returncode)."""
        result = subprocess.run(
            [os.environ.get("PYTHON", "python3"), str(VG)] + list(args),
            capture_output=True,
            text=True,
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode

    def _make_worldbuilding_project(self, base_dir):
        """Create minimal valid shenbi-worldbuilding project structure.

        Returns the path to a file that can be passed as the G4 file argument.
        """
        base = Path(base_dir)
        base.mkdir(parents=True, exist_ok=True)

        # novel.json
        (base / "novel.json").write_text(json.dumps({
            "title": "Test Novel",
            "genre": "玄幻",
            "language": "zh",
            "target_words": 100000,
        }, ensure_ascii=False))
        # genre-config.json
        (base / "genre-config.json").write_text(json.dumps({
            "chapter_word": {"default": 3000},
        }))
        # world/story_bible.md with 4+ sections and low bullet density
        sb = base / "world" / "story_bible.md"
        sb.parent.mkdir(parents=True, exist_ok=True)
        sb.write_text(
            "---\ntype: world\n---\n"
            "## 世界观基础\n这是一个宏大而复杂的世界，充满了各种神奇的元素和力量。\n"
            "## 力量体系\n在这个世界中，力量是最核心的要素，决定了每个人的命运。\n"
            "## 社会结构\n社会按照严格的等级制度运行，每个人都在自己的位置上努力生存。\n"
            "## 地理环境\n从北方的冰原到南方的沙漠，世界展现出多样的地貌和气候。\n"
        )
        # world/rules.md with a rule and testable criteria
        rp = base / "world" / "rules.md"
        rp.write_text(
            "---\ntype: rules\n---\n"
            "## 规则 一：力量守恒\n力量的使用必须遵循守恒原则。可测试标准：每次力量使用后消耗值必须记录。\n"
        )
        # world/locations.md with 3-5 locations
        lp = base / "world" / "locations.md"
        lp.write_text(
            "---\ntype: locations\n---\n"
            "## 地点：天机城\n一座古老的城池。\n"
            "## 地点：灵山\n修行者的圣地。\n"
            "## 地点：深渊裂缝\n危险的禁地。\n"
        )
        # truth/ templates with required frontmatter
        truth_dir = base / "truth"
        truth_dir.mkdir(parents=True, exist_ok=True)
        truth_frontmatter = "---\ntype: truth\ncategory: world\nstatus: active\n---\nContent here.\n"
        for tmpl in [
            "current_state.md",
            "character_matrix.md",
            "emotional_arcs.md",
            "chapter_summaries.md",
        ]:
            (truth_dir / tmpl).write_text(truth_frontmatter)
        # characters/protagonist.md
        char_dir = base / "characters"
        char_dir.mkdir(parents=True, exist_ok=True)
        (char_dir / "protagonist.md").write_text("---\nname: Test\n---\nA character.\n")
        # Return a file path in the project (G4 worldbuilding derives project_dir from file path)
        return str(base / "world" / "story_bible.md")

    def test_g4_pass_writes_marker(self):
        """G4 PASS with round_dir should write a marker file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            round_dir = Path(tmpdir) / "round-test"
            round_dir.mkdir()
            file_path = self._make_worldbuilding_project(round_dir / "project")

            stdout, stderr, rc = self._run_vg(
                "G4", "worldbuilding", file_path, str(round_dir)
            )
            result = json.loads(stdout)
            self.assertEqual(result.get("status"), "PASS", f"Expected PASS, got: {stdout}")

            marker_dir = round_dir / "gate-markers"
            self.assertTrue(marker_dir.exists(), "gate-markers directory should be created")

            # Find the marker file
            markers = list(marker_dir.glob("G4-shenbi-worldbuilding-generative.json"))
            self.assertEqual(len(markers), 1, f"Expected exactly 1 marker, found: {list(marker_dir.iterdir())}")

            marker = json.loads(markers[0].read_text())
            self.assertEqual(marker["status"], "PASS")
            self.assertIn("files_checked", marker)

    def test_g4_fail_no_marker(self):
        """G4 FAIL should not write a marker file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            round_dir = Path(tmpdir) / "round-test"
            round_dir.mkdir()
            # Create a minimal invalid project (no files = should fail)
            project_dir = round_dir / "project"
            project_dir.mkdir()
            dummy_file = project_dir / "dummy.md"
            dummy_file.write_text("just some text that is long enough")

            stdout, stderr, rc = self._run_vg(
                "G4", "worldbuilding", str(dummy_file), str(round_dir)
            )
            result = json.loads(stdout)
            # Worldbuilding should FAIL with missing required files
            self.assertEqual(result.get("status"), "FAIL", f"Expected FAIL, got: {stdout}")

            marker_dir = round_dir / "gate-markers"
            self.assertFalse(marker_dir.exists(), "gate-markers should not be created on FAIL")

    def test_g4_no_round_dir_no_marker(self):
        """G4 without round_dir should not write marker (backward compat)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            dummy_file = project_dir / "dummy.md"
            dummy_file.write_text(
                "A" * 100  # Long enough to pass generic generative check
            )

            # Call G4 without round_dir (only 2 args after G4)
            stdout, stderr, rc = self._run_vg(
                "G4", "chapter-drafting", str(dummy_file)
            )
            # Should still produce output but no marker file
            self.assertTrue(len(stdout) > 0, "Should produce output")
            # No gate-markers directory anywhere in tmpdir tree
            markers = list(Path(tmpdir).rglob("gate-markers"))
            self.assertEqual(len(markers), 0, "No gate-markers should be created without round_dir")

    def test_marker_contains_files_checked(self):
        """G2 should not write markers (negative test)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            round_dir = Path(tmpdir) / "round-test"
            round_dir.mkdir()
            # Create a minimal md file for G2
            test_file = round_dir / "test.md"
            test_file.write_text("---\ntype: chapter\n---\n" + "一些中文内容" * 50)

            stdout, stderr, rc = self._run_vg(
                "G2", str(test_file), "chapter", str(round_dir)
            )
            # G2 should not write any markers regardless of result
            marker_dir = round_dir / "gate-markers"
            self.assertFalse(marker_dir.exists(), "G2 should not create gate-markers")


SC = Path(__file__).resolve().parent / "scoring.py"


def run_py(script, args):
    """Run a Python script as subprocess, return (rc, stdout, stderr)."""
    result = subprocess.run(
        [os.environ.get("PYTHON", "python3"), str(script)] + list(args),
        capture_output=True, text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


class TestScoringMarkers(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="scoring_test_")
        self.round_dir = Path(self.tmpdir) / "round-test"
        self.round_dir.mkdir()
        (self.round_dir / "gate-markers").mkdir()
        (self.round_dir / "t1-reports").mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_rubric(self):
        rubric_dir = self.round_dir / "rubric-t1"
        rubric_dir.mkdir(exist_ok=True)
        rubric = rubric_dir / "rubric.md"
        rubric.write_text(
            "| # | Dimension | Weight |\n"
            "|---|-----------|--------|\n"
            "| 1 | Quality   | 100%   |\n"
        )
        return str(rubric)

    def _make_t1_rubric(self, skill_name):
        rubric_dir = self.round_dir / "t1-skill" / skill_name / "generative"
        rubric_dir.mkdir(parents=True, exist_ok=True)
        rubric = rubric_dir / "rubric.md"
        rubric.write_text(
            "| # | Dimension | Weight |\n"
            "|---|-----------|--------|\n"
            "| 1 | Quality   | 100%   |\n"
        )
        return str(rubric)

    def _make_scores(self, scores=None):
        scores = scores or {"1": 95}
        scores_path = self.round_dir / "test-scores.json"
        scores_path.write_text(json.dumps(scores))
        return str(scores_path)

    def _make_marker(self, gate, target, test_type="generative"):
        marker = {
            "gate": gate, "status": "PASS",
            "timestamp": "2026-06-13T00:00:00+00:00",
            "checks": [], "files_checked": ["/some/file.md"],
        }
        marker_path = self.round_dir / "gate-markers" / f"{gate}-{target}-{test_type}.json"
        marker_path.write_text(json.dumps(marker))

    def test_no_round_dir_skips_check(self):
        rubric = self._make_rubric()
        scores = self._make_scores()
        rc, stdout, stderr = run_py(SC, [rubric, scores])
        self.assertEqual(rc, 0, f"Should succeed without --round-dir. stderr: {stderr}")

    def test_missing_marker_exits_3(self):
        rubric = self._make_t1_rubric("shenbi-worldbuilding")
        scores = self._make_scores()
        rc, stdout, stderr = run_py(SC, [
            rubric, scores, "--test-type", "generative", "--round-dir", str(self.round_dir),
        ])
        self.assertEqual(rc, 3, f"Should exit 3 for missing marker. stdout: {stdout}")

    def test_present_marker_succeeds(self):
        rubric = self._make_t1_rubric("shenbi-worldbuilding")
        scores = self._make_scores()
        self._make_marker("G4", "shenbi-worldbuilding", "generative")
        rc, stdout, stderr = run_py(SC, [
            rubric, scores, "--test-type", "generative", "--round-dir", str(self.round_dir),
        ])
        self.assertEqual(rc, 0, f"Should succeed with marker present. stdout: {stdout}")


if __name__ == "__main__":
    unittest.main()
