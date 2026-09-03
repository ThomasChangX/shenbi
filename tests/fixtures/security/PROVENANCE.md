# fixtures/security provenance

- `req-vulnerable.txt`: 真实 `uv export --frozen --all-groups --all-extras --no-emit-project`
  产物（2026-09-03，uv 0.10.7，branch fix/spec-41-c27-supply-chain @ 88c0e990），仅将
  requests pin 行替换为 `requests==2.30.0`（已知 CVE：CVE-2023-32681 等）用于 pip-audit
  FAIL 路径回归（spec #41 R1 验收）。替换行的原 `--hash` 行随之移除，但补入
  requests 2.30.0 wheel 的真实 sha256（PyPI 官方 digest）——`--no-deps --disable-pip`
  模式要求每条 pin 带哈希，无哈希行会被 pip-audit 拒绝。
