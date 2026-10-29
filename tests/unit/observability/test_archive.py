"""Spec #81 §1 archive layer unit tests (offline, tmp_path structural corpora)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shenbi.observability import archive as ar


class TestBlobStore:
    def test_put_blob_content_addressed_idempotent(self, tmp_path: Path):
        d1 = ar.put_blob(tmp_path, "同内容")
        d2 = ar.put_blob(tmp_path, "同内容")
        assert d1 == d2 and d1.startswith("sha256:")
        blob = tmp_path / "observability" / "blobs" / d1.split(":", 1)[1]
        assert blob.read_text(encoding="utf-8") == "同内容"

    def test_quota_breaker_skips_blob_keeps_hash_and_counts(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SHENBI_ARCHIVE_QUOTA_BYTES", "200")  # KB 级实测形态（spec §7.5 离线）
        d1 = ar.put_blob(tmp_path, "x" * 150)  # 150B 落盘
        d2 = ar.put_blob(tmp_path, "y" * 400)  # 150+400 > 200 → 跳内容写
        assert d2.startswith("sha256:")  # 哈希照返（spec §1「档与哈希照写」）
        blob2 = tmp_path / "observability" / "blobs" / d2.split(":", 1)[1]
        assert not blob2.exists()  # 内容确实没写
        assert (tmp_path / "observability" / "blobs" / d1.split(":", 1)[1]).exists()
        stats = json.loads((tmp_path / "observability" / "archive-stats.json").read_text())
        assert stats["archive_quota_skip"] == 1

    def test_archive_disabled_env(self, monkeypatch):
        monkeypatch.setenv("SHENBI_ARCHIVE_DISPATCH", "0")
        assert ar.archive_enabled() is False


class TestSeq:
    def test_next_seq_monotonic_across_files(self, tmp_path: Path):
        d = tmp_path / "observability" / "dispatches"
        d.mkdir(parents=True)
        (d / "00003-x-ch001-a1.json").write_text("{}", encoding="utf-8")
        assert ar.next_seq(tmp_path) == 4  # 跨重启续号


class TestWriteArchive:
    def _frame(self, **kw):
        base: dict[str, Any] = {
            "skill": "shenbi-chapter-drafting",
            "chapter": 20,
            "attempt": 1,
            "model": "m",
            "system_prompt": "SYS",
            "user_prompt": "USER",
            "reads_manifest": [
                {
                    "path": "truth/current_state.md",
                    "mode": "fields",
                    "fields": ["系统演化阶段"],
                    "resolved_fields": [],
                    "matched_all": False,
                }
            ],
            "raw_reads": {"truth/current_state.md": "# 原文"},
            "skill_contract_sha256": "sha256:abc",
            "loop_id": 3,
            "feedback_ref": None,
        }
        base.update(kw)
        return ar.ArchiveFrame(**base)

    def test_success_record_shape_and_dereference(self, tmp_path: Path):
        path = ar.write_dispatch_archive(
            tmp_path,
            self._frame(),
            finish_reason="stop",
            response_text="RESP",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
        )
        assert path is not None and path.exists()
        rec = json.loads(path.read_text(encoding="utf-8"))
        assert rec["seq"] == 1 and rec["skill_contract_sha256"] == "sha256:abc"
        assert rec["user_prompt_blob"] == ar.sha256_of("USER")
        # 字节级复现：解引用 == 原文（spec §6 P1 离线验收）
        blob = tmp_path / "observability" / "blobs" / rec["user_prompt_blob"].split(":", 1)[1]
        assert blob.read_text(encoding="utf-8") == "USER"
        assert rec["reads"][0]["resolved_fields"] == []  # 未命中如实记空
        assert rec["reads"][0]["blob"] == ar.sha256_of("# 原文")  # 磁盘原文（非过滤视图）
        assert "00001-shenbi-chapter-drafting-ch020-a1" in path.name

    def test_genesis_ch000_and_failure_nullable(self, tmp_path: Path):
        path = ar.write_dispatch_archive(
            tmp_path, self._frame(chapter=None), finish_reason=None, response_text=None, usage=None
        )
        assert path is not None
        assert "ch000" in path.name
        rec = json.loads(path.read_text(encoding="utf-8"))
        assert rec["response_blob"] is None and rec["finish_reason"] is None

    def test_write_failure_never_raises_counts_stats(self, tmp_path: Path, monkeypatch):
        from shenbi.safe_write import safe_write as _real_safe_write

        def _selective_boom(path: Path, data, **kw):
            if "dispatches" in str(path):  # 只炸档写；stats/blob 照写
                raise RuntimeError("disk full")
            return _real_safe_write(path, data, **kw)

        monkeypatch.setattr("shenbi.observability.archive.safe_write", _selective_boom)
        path = ar.write_dispatch_archive(
            tmp_path, self._frame(), finish_reason="stop", response_text="R", usage=None
        )
        assert path is None  # fail-safe：不抛
        stats = json.loads((tmp_path / "observability" / "archive-stats.json").read_text())
        assert stats["archive_write_failed"] == 1

    def test_disabled_env_writes_nothing(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SHENBI_ARCHIVE_DISPATCH", "0")
        path = ar.write_dispatch_archive(
            tmp_path, self._frame(), finish_reason="stop", response_text="R", usage=None
        )
        assert path is None
        assert not (tmp_path / "observability").exists()


class TestConcurrentStats:
    def test_thread_hammer_no_lost_update(self, tmp_path: Path):
        """audit-T1 I-1: parallel waves must not lose counter/byte updates."""
        import threading

        def _worker(i: int) -> None:
            ar.put_blob(tmp_path, f"content-{i}")
            if i % 3 == 0:
                ar.bump_stats(tmp_path, "archive_quota_skip")

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(24)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        stats = json.loads((tmp_path / "observability" / "archive-stats.json").read_text())
        assert stats["_puts"] == 24  # 字节账无丢失
        assert stats["archive_quota_skip"] == 8  # 计数无互吞（24 中 i%3==0 者 8 个）

    def test_calibration_path_resets_bytes(self, tmp_path: Path, monkeypatch):
        """audit-T1 M-4: every-N calibration resets the tally to du ground truth."""
        monkeypatch.setattr(ar, "_CALIBRATE_EVERY", 5)
        for i in range(5):
            ar.put_blob(tmp_path, f"unique-{i}-" + "z" * 10)  # 唯一内容：物理 5 blob
        stats = json.loads((tmp_path / "observability" / "archive-stats.json").read_text())
        assert stats["_bytes"] == 5 * (len("unique-0-") + 10)  # du 校准 = 实存字节
