# 08 Security content, TA and CIM

## What is implemented
- Security scenarios (56 dashboard-backed) with Overview / Investigation / Evidence views: events, progression by phase, affected hosts, users where the telemetry exposes them, and the raw evidence.
- A reference universe of Splunk Security Content: 365 Analytic Stories and 2,181 detections are cataloged (`catalog/phase13a_*`). They are **reference content, not 365 executable scenarios**. Curated stories carry their original `research.splunk.com` link (HTTP 200 verified).
- Original analytic links on a dashboard are exact: a detection is listed only if its published test data is a dataset the scenario replays.
- One detection workflow is runtime-approved and one detection has stored positive-case validation (React2Shell); see the Explorer's Security view.

## What is not verified
| Claim | Status |
|---|---|
| Detection executed by Splunk on generated data | **Not verified** except the one stored React2Shell positive case |
| Enterprise Security notable events or risk | **Not verified** (ES not installed) |
| CIM data model mapping | **Not validated** (Splunk_SA_CIM not installed in any lab) |
| TA parsing | Verified only for Windows (TA 10.0.1) and Sysmon (5.0.1) in an isolated lab: field extraction, timestamps, tags/event types, and the add-on's source/sourcetype rewrite |

## Requirements to verify a detection
Install the official add-ons that declare the scenario's sourcetypes (see `required_ta` and the TA matrix `docs/verification/pulseforge_ta_validation_matrix.md`), `Splunk_SA_CIM`, the Security Content app/ESCU with its macros and lookups, then: generate or replay the scenario, verify the indexed run, enable the detection, and read its actual result. Install only official, correctly identified Splunkbase packages; 37 Cisco sourcetypes now carry a verified add-on (declared by Splunkbase), 63 remain unverified.

## TA and parsing contracts
Parsing add-ons, API collectors (modular inputs) and native protocol collectors are different things; PulseForge replays or generates data, it does not replace the add-on that parses it. Sourcetype-name equality is never reported as TA validation.
