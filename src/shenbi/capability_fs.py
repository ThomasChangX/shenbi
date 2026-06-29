"""CapabilityFS：in-process 只读 FS 句柄（spec 支柱五；判据 4/14）。

把可写 Path 换成只读句柄注入门/测试：读允许，任意写/删/改抛 PermissionError。
是「门纯度」的运行时兜底（AST lint 禁 FS 原语在支柱六）。

v5 命名分离（I1）：本模块仅 in-process；codex subprocess 的 read-provenance
（需 FUSE/ptrace）是 future work / 已知盲点，不由本模块承担。
"""

from __future__ import annotations

from pathlib import Path


class CapabilityFS:
    """只读文件系统句柄。读经 allow_root 沙箱；写一律拒绝。"""

    def __init__(self, allow_root: Path) -> None:
        """Bind the read-only handle to an allow_root directory (resolved)."""
        self._root = Path(allow_root).resolve()

    def _sandbox(self, path: Path) -> Path:
        p = Path(path)
        try:
            resolved = p.resolve(strict=False)
            resolved.relative_to(self._root)
        except ValueError as exc:
            raise PermissionError(f"path outside allow_root: {p}") from exc
        return resolved

    def exists(self, path: Path) -> bool:
        return self._sandbox(path).exists()

    def read_text(self, path: Path, encoding: str = "utf-8") -> str:
        # newline="" disables universal-newline translation so read_text is a
        # faithful inverse of write_text(newline="")（\r 等控制字符原样保留）。
        return self._sandbox(path).read_text(encoding=encoding, newline="")

    def read_bytes(self, path: Path) -> bytes:
        return self._sandbox(path).read_bytes()

    def list_dir(self, path: Path) -> list[str]:
        return [p.name for p in self._sandbox(path).iterdir()]

    # --- 写侧：全部拒绝（纯度兜底） ---
    def write_text(self, path: Path, data: str, encoding: str = "utf-8") -> None:
        raise PermissionError("CapabilityFS is read-only")

    def write_bytes(self, path: Path, data: bytes) -> None:
        raise PermissionError("CapabilityFS is read-only")

    def unlink(self, path: Path) -> None:
        raise PermissionError("CapabilityFS is read-only")

    def mkdir(self, path: Path, parents: bool = False, exist_ok: bool = False) -> None:
        raise PermissionError("CapabilityFS is read-only")
