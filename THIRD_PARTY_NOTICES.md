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

Automated dependency metadata is not legal clearance. License conclusions,
vendor sample redistribution rights, employer intellectual-property approval,
and publication authorization require human review before V1.0 release.
