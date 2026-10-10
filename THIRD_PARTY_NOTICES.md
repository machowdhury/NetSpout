# Third-Party Notices

NetSpout is licensed under Apache-2.0. Its build and runtime use third-party
components under their respective licenses.

The authoritative release-candidate dependency inventory is generated locally:

```bash
python3 scripts/run_phase13_release_audit.py
```

This produces a CycloneDX-format inventory under
`.artifacts/phase13-current/release/`. Package-manager lock files remain the
source of exact JavaScript transitive versions; `backend/requirements.txt`
records direct Python versions.

Major direct components include React, lucide-react, Vite, TypeScript,
Playwright, FastAPI, Uvicorn, Pydantic, gRPC, protobuf, cryptography, and
pygnmi. Docker retrieves Splunk Enterprise and collector images from their
publishers under those publishers' terms. The NetSpout repository and `.spl`
archive do not redistribute Splunk Enterprise binaries.

Phase 13A includes metadata-derived, revision-pinned catalog records from:

- Splunk Security Content (`splunk/security_content`, Apache-2.0), pinned at
  `1b2142fdd2d1358b4ac6ad3dfc47e5e455e619e8`.
- Splunk Attack Data (`splunk/attack_data`, Apache-2.0), pinned at
  `4389fa7a4e74a7c083c0fbe448fa2c7c32378981`. Dataset payloads are referenced,
  not redistributed.
- MITRE ATT&CK STIX Data (`mitre-attack/attack-stix-data`), pinned at
  `6cda5ad8462c79e14fbb872f4e09059b18e0cfc4`, under its repository terms:
  “© 2026 The MITRE Corporation. This work is reproduced and distributed with
  the permission of The MITRE Corporation.”

The Phase 13A metadata synchronization utility uses PyYAML 6.0.3 under the MIT
License. Upstream metadata may reference external files or embedded artifacts
whose rights are not established by a repository-level license. NetSpout marks
those assets reference-only pending human review and does not bundle the
Attack Data payload collection.

Automated dependency metadata is not legal clearance. License conclusions,
vendor sample redistribution rights, employer intellectual-property approval,
and publication authorization require human review before V1.0 release.
