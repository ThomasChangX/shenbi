# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| latest main | ✅ |
| < 1.0 | ❌ (pre-release) |

## Reporting a Vulnerability

Use GitHub's "Report a vulnerability" feature under the Security tab.

**Do not** open a public GitHub issue for security vulnerabilities.

**Response time**: 72 hours for initial response, 14 days for fix or disclosure timeline agreement.

## Disclosure

We follow coordinated disclosure. Once a fix is available, we publish a GitHub Security Advisory with CVE assignment (if applicable).

## Supply Chain

- All dependencies locked in `uv.lock` with hashes
- SBOM (CycloneDX format) generated per release per dependency group (prod = distributed runtime deps; dev, docs = not distributed, provenance only — spec #41/F1041) and attached to GitHub Releases
- pip-audit runs on every PR and weekly
- CodeQL static analysis runs on every PR and weekly
