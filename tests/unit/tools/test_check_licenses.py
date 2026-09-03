"""Spec #41 (C27) R2/R3: check_licenses.py license exception table + ignore-vuln
exemption enforcement (T1304 closure rule).
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FIX = REPO / "tests/fixtures/security"
TOOL = REPO / "tools/check_licenses.py"
EXCEPTIONS = REPO / "tools/supply_chain_exceptions.json"


def run_tool(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True)


def test_clean_sbom_passes() -> None:
    # fixture 是真实 cyclonedx environment 产物（docs 组），CairoSVG LGPL 已登记
    result = run_tool(str(FIX / "sbom-gpl-fixture.cdx.json"), "--exceptions", str(EXCEPTIONS))
    assert result.returncode == 0, result.stdout + result.stderr


def test_unregistered_gpl_fails() -> None:
    result = run_tool(str(FIX / "sbom-gpl-injected.cdx.json"), "--exceptions", str(EXCEPTIONS))
    assert result.returncode == 1
    assert "GPL-3.0-only" in result.stdout
    assert "babel" in result.stdout


def test_registered_but_mismatched_license_fails() -> None:
    # 已登记包名但许可证串与登记值不符（如 yamllint 变体许可）必须 FAIL
    import json

    tmp = FIX.parent / "security" / "sbom-mismatch-tmp.json"
    data = json.loads((FIX / "sbom-gpl-fixture.cdx.json").read_text(encoding="utf-8"))
    for c in data["components"]:
        if c["name"].lower() == "cairosvg":
            c["licenses"] = [{"license": {"id": "GPL-3.0-only"}}]
    tmp.write_text(json.dumps(data), encoding="utf-8")
    try:
        result = run_tool(str(tmp), "--exceptions", str(EXCEPTIONS))
        assert result.returncode == 1
        assert "does not match registered" in result.stdout
    finally:
        tmp.unlink()


def test_ignore_vuln_must_be_registered(tmp_path: Path) -> None:
    wf = tmp_path / "fake-workflow.yml"
    wf.write_text("run: pip-audit --ignore-vuln PYSEC-FAKE-0001\n", encoding="utf-8")
    result = run_tool(
        str(FIX / "sbom-gpl-fixture.cdx.json"),
        "--exceptions",
        str(EXCEPTIONS),
        "--workflows",
        str(wf),
    )
    assert result.returncode == 1
    assert "PYSEC-FAKE-0001" in result.stdout


def test_registered_ignore_vuln_passes(tmp_path: Path) -> None:
    import json

    wf = tmp_path / "fake-workflow.yml"
    wf.write_text("run: pip-audit --ignore-vuln PYSEC-FAKE-0001\n", encoding="utf-8")
    exc = tmp_path / "exc.json"
    data = json.loads(EXCEPTIONS.read_text(encoding="utf-8"))
    data["ignore_vulns"]["PYSEC-FAKE-0001"] = {
        "package": "requests",
        "ledger": "T1302",
        "reason": "fixture-only entry for positive-path test",
    }
    exc.write_text(json.dumps(data), encoding="utf-8")
    result = run_tool(
        str(FIX / "sbom-gpl-fixture.cdx.json"),
        "--exceptions",
        str(exc),
        "--workflows",
        str(wf),
    )
    assert result.returncode == 0, result.stdout
