# License Attribution Report

**Date:** 2025-07-17
**Milestone:** M9 — OSS Integration Layer

---

## License Summary

| Adapter | Upstream Project | License | SPDX ID | Commercial Use | Modifications | Distribution |
|---------|-----------------|---------|---------|---------------|---------------|-------------|
| OpenJarvis | openjarvis | MIT | MIT | Yes | Yes | Yes |
| OpenHands | openhands | MIT | MIT | Yes | Yes | Yes |
| OpenInterpreter | open-interpreter | MIT | MIT | Yes | Yes | Yes |
| AnythingLLM | anythingllm | MIT | MIT | Yes | Yes | Yes |
| LibreChat | librechat | MIT | MIT | Yes | Yes | Yes |
| Open WebUI | open-webui | BSD-2-Clause | BSD-2-Clause | Yes | Yes | Yes |
| Continue | continue | Apache-2.0 | Apache-2.0 | Yes | Yes | Yes |
| Jan | jan | AGPL-3.0 | AGPL-3.0 | Yes* | Yes | Yes* |

*AGPL-3.0 requires source distribution for network use. Consult legal for SaaS deployment.

## License Details

### MIT License (5 adapters)
- **Permission:** Commercial use, modification, distribution, private use
- **Condition:** License and copyright notice must be included
- **Limitation:** No liability, no warranty

### BSD-2-Clause (1 adapter)
- **Permission:** Commercial use, modification, distribution, private use
- **Condition:** License and copyright notice must be included, no endorsement
- **Limitation:** No liability, no warranty

### Apache-2.0 (1 adapter)
- **Permission:** Commercial use, modification, distribution, patent grant, private use
- **Condition:** License and copyright notice, state changes, include NOTICE file if provided
- **Limitation:** No liability, no warranty, patent retaliation

### AGPL-3.0 (1 adapter)
- **Permission:** Commercial use, modification, distribution, private use
- **Condition:** Source distribution required, state changes, network use triggers disclosure
- **Limitation:** No liability, no warranty

## Attribution Requirements

AIOS preserves upstream licenses through:

1. **`UPSTREAM_LICENSES` dict** — each adapter's license is documented in `oss/__init__.py`
2. **Adapter docstrings** — each adapter file includes license header
3. **Test coverage** — `TestLicensePreservation` verifies all licenses are documented
4. **`upstream_version` property** — each adapter exposes the upstream version for traceability

## Compliance Notes

- AIOS adapters call upstream APIs; they do not embed or vendor upstream source code
- When upstream packages are installed, their own license files are present in site-packages
- AIOS distribution should include a THIRD_PARTY_LICENSES file aggregating all upstream licenses
- AGPL-3.0 (Jan) requires special attention for SaaS deployments — consult legal counsel
