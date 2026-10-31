# 09 Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Explorer or Command Center shows no data | Gateway cannot reach the engine | Check `NETSPOUT_BACKEND_URL` (own line in `splunk-launch.conf`; restart splunkd), engine process, firewall; test `GET /services/netspout_gateway/api/explorer/summary` with your Splunk credentials |
| HTTP 403 starting a run | Your Splunk role lacks `admin`/`sc_admin`/`power`, or the index is not on the allowlist, or a non-lab destination without `confirm_destination` | Use a write role; pick an allowlisted index; confirm the destination |
| HTTP 409 on replay | Connection Center not configured | Save the destination and run `POST /api/setup/validate` |
| `rejected > 0` | HEC refused the events (token, disabled input, index not allowed for the token) | Fix the token's allowed indexes; re-run |
| `unknown > 0` | HEC answered with an unreadable body; nothing is re-sent | Check HEC health and logs, then re-run |
| indexed < accepted for a while | Indexing latency | Wait and verify again; only a persistent gap is a problem |
| Dashboard panels empty | Wrong run id/time range/index, or the Windows add-on rewrote `source` and you searched by it | Pick the run in the dropdown, widen the time range, search by `netspout_run_id` or `netspout_replay_session` |
| `INTERRUPTED` replay session | Engine restarted while it was active | Start a new session; it is never resumed automatically |
| Unified scenario `BLOCKED` | Native receiver or collector not running (flow scenarios need GoFlow2 and the forwarder) or search not configured | Start the collector, configure the Connection Center search credential |
| SNMP/gNMI suites fail with 0 observed | No Splunk destination configured for the tests | Export `NETSPOUT_HEC_URL`, `NETSPOUT_HEC_TOKEN`, `NETSPOUT_REST_SEARCH_URL`, `NETSPOUT_SPLUNK_USER`, `NETSPOUT_SPLUNK_PASSWORD`; create `idx_network_ops` and the metric index in your lab |
| AppInspect fails on the Enterprise app | Expected for Splunk Cloud (engine code in the app) | Use the Cloud edition ([04](04_SPLUNK_CLOUD_GUIDE.md)) |
| Index `already exists` (409) but not listed | Index created earlier, shown after a restart | Treat as existing |
