"""T4: 散点裸崩修复(spec #38 F409/F509/F526/F608/F621/F626/F627/F517/F614)。

G0.9 说明:构造性最小输入钉边界行为(畸形形状),非 skill 产物内容。
"""

import pytest


class TestHooksNotDict:
    def test_string_hook_element_mf_not_crash(self, tmp_path) -> None:
        """F409:hooks 列表含字符串元素 → mf 计数,非 AttributeError。"""
        from shenbi.gates.g4.foreshadowing_plant import g4_foreshadowing_plant

        md = tmp_path / "foreshadowing.md"
        md.write_text("---\nhooks:\n  - 'just a string'\n---\nbody", encoding="utf-8")
        out = g4_foreshadowing_plant([str(md)])
        assert isinstance(out, str)
        assert "hook_not_dict" in out


class TestSnapshotGuards:
    def test_no_id_record_skipped_not_none_key(self) -> None:
        """F509:无 id 记录跳过 + 不落 'None' 键碰撞。"""
        from shenbi.audit.snapshot import _diff_records

        pre = [{"id": 1, "v": "a"}]
        post = [{"id": 1, "v": "a"}, {"v": "orphan"}, {"id": 2, "v": "b"}]
        new_ids, del_ids, mod = _diff_records(pre, post)
        assert "None" not in new_ids
        assert "2" in new_ids

    def test_non_utf8_file_tolerated(self, tmp_path) -> None:
        """F526:非 UTF-8 watch 文件 → None 值,非 UnicodeDecodeError。"""
        from shenbi.audit.snapshot import snapshot_tree

        (tmp_path / "x.bin").write_bytes(b"\xff\xfe\x00garbage")
        out = snapshot_tree(tmp_path, ["x.bin"])
        assert out["x.bin"] is None


class TestTraceWriterTornTail:
    def test_torn_tail_tolerated_and_repaired(self, tmp_path) -> None:
        """F608:半行 JSON 尾 → 跳过,非 JSONDecodeError;append 前修复撕裂。"""
        from shenbi.trace.writer import TraceWriter

        (tmp_path / "trace.jsonl").write_text(
            '{"seq": 1, "signature": "sig-a"}\n{"seq": 2, "sign', encoding="utf-8"
        )
        w = TraceWriter(tmp_path)
        assert w.last_signature() == "sig-a"
        assert w.next_seq() == 2
        w.append(actor="test", actor_role="SYSTEM", action="NOTE", target="t")
        lines = (tmp_path / "trace.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2  # 撕裂碎片已清除,新事件成为干净第 2 行


class TestChapterPatternNonDict:
    def test_non_dict_chapter_skipped(self) -> None:
        """F621:章节列表非 dict 元素 → 跳过 + WARN,非 AttributeError。"""
        from shenbi.skill_utils.chapter_pattern.compute_pattern import extract_patterns

        assert extract_patterns(["oops a string", {"pattern": "测试"}, 42]) == ["测试"]


class TestVersioningMissingMigration:
    def test_missing_migration_raises(self) -> None:
        """F626:缺注册迁移 → ValueError,非死循环。"""
        from shenbi.trace.versioning import migrate_to_current

        class FakeEvent:
            schema_version = 0  # 低于 CURRENT 且无注册迁移

        with pytest.raises(ValueError, match="no migration"):
            migrate_to_current(FakeEvent())  # type: ignore[arg-type]


class TestGenCodexDefaults:
    def test_missing_fields_get_defaults(self) -> None:
        """F627:config 缺 marketplace/type → 缺省值,非 KeyError。"""
        from shenbi.plugins.generate import gen_codex

        out = gen_codex(
            {"name": "x", "version": "1", "description": "d", "author": "a", "skills": []},
            {},
        )
        assert "marketplace" in out
        assert "type" in out


class TestExecutorFinallyGuard:
    def test_audit_chain_error_sets_rc2_and_reraises(self, monkeypatch, tmp_path) -> None:
        """F517:snapshot/audit 链崩溃 → 原异常上抛 + write_audit_infra_error 日志。"""
        from shenbi.dispatcher import executor

        calls = {"n": 0}

        def boom(*a, **kw):
            calls["n"] += 1
            if calls["n"] >= 2:  # pre snapshot succeeds, post snapshot crashes
                raise RuntimeError("snapshot exploded")
            return {}

        import shenbi.audit.snapshot as snap
        import shenbi.audit.write_audit as wa

        errors: list[str] = []
        monkeypatch.setattr(snap, "snapshot_tree", boom)
        monkeypatch.setattr(wa, "audit_writes", boom)
        monkeypatch.setattr(executor, "dispatch", lambda *a, **kw: 0)
        orig_error = executor.log.error

        def spy_error(event: str, **kw: object) -> None:
            errors.append(event)
            orig_error(event, **kw)

        monkeypatch.setattr(executor.log, "error", spy_error)
        with pytest.raises(RuntimeError, match="snapshot exploded"):
            executor.dispatch_with_write_audit(
                "shenbi-example", "generative", tmp_path, "chapter 1 prompt"
            )
        assert "write_audit_infra_error" in errors


class TestMaterializeRoundField:
    def test_unknown_round_dir_not_question_marks(self, tmp_path) -> None:
        """F614:无 round- 前缀目录 → 'unknown' 而非 '???'。"""
        from shenbi.trace.materialize import _round_field

        assert _round_field(tmp_path) == "unknown"
        assert _round_field(tmp_path / "round-7") == "7"


class TestParserYamlGuard:
    def test_malformed_yaml_body_value_error(self) -> None:
        """F517 第二面:畸形 YAML → ValueError(可捕获),非裸 YAMLError。"""
        from shenbi.records.parser import _parse_body

        with pytest.raises(ValueError, match="YAML invalid"):
            _parse_body("key: [unclosed")
