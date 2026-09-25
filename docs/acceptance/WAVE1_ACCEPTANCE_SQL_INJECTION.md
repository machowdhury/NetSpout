# NETSPOUT INDEPENDENT PRODUCT ACCEPTANCE REPORT
## SCENARIO 03 — SQL INJECTION / APPLICATION BREACH

**Evaluation Date:** 2026-09-25  
**Product Version:** NetSpout Gate 9 Baseline (Wave 1 Promoted)  
**Evaluator Persona:** Senior SOC Analyst & Security Operations Engineer  
**User Goal:** *"I need to demonstrate a SQL injection/application breach investigation in Splunk using network, firewall, load-balancer and database evidence, but I don't have the infrastructure."*  
**Acceptance Determination:** **PASS**  
**Catalog Maturity Recommendation:** **`GOLDEN_PATH_CERTIFIED`** (Retained at `E2E_VALIDATED` during test per protocol)  

---

## 1. Security Semantics & Attack Reconstruction

A critical requirement of security product acceptance is ensuring accurate, defensible **Security Semantics**:

* **Precise Semantic Progression:**
  * **ATTEMPTED:** External threat actor submits an OWASP SQL injection vector (`' OR '1'='1' -- UNION SELECT`) embedded in an HTTP GET parameter.
  * **ALLOWED (Perimeter Inbound):** Cisco ASA perimeter firewall permits inbound HTTPS connection to the web tier VIP (port 443), treating the TCP session as legitimate layer-4 traffic.
  * **DETECTED (Web Tier):** NGINX web server inspects HTTP URI parameters and flags an OWASP SQL injection attack pattern.
  * **DETECTED & REJECTED (Database Tier):** PostgreSQL database audit logger records an unauthorized schema query attempt (`SELECT * FROM information_schema.tables`) and terminates query processing.
  * **BLOCKED & QUARANTINED (Active Mitigation):** Cisco ASA perimeter firewall / IPS activates inline threat prevention, denies further packets from attacker IP `198.51.100.44`, and blacklists the host.
  * **NOT EXECUTED / NO EXFILTRATION:** At no point is malicious code successfully executed to extract customer tables.
  * **RECOVERED:** Database connection pool is sanitized; legitimate application queries resume without compromise.

---

## 2. Discovery Experience

Starting from NetSpout Canvas within Splunk:

* **User-Facing Title:** **`SQL Injection / Application Breach`**
* **Category Pill:** **`Security & Zero Trust`**
* **Vendors Displayed:** `Cisco ASA`, `NGINX`, `PostgreSQL`
* **Topology Displayed:** `bypassed` (Multi-tier perimeter security topology)
* **Telemetry Displayed:** `cisco:asa`, `nginx:plus:kv`, `postgresql:audit`
* **Interactions Required:**
  1. Click category pill: `Security & Zero Trust`
  2. Select card: `SQL Injection / Application Breach`
  3. Click `Preview Selection`
* **Developer Knowledge Required:** **NO**. Discovered cleanly via standard security category filters.

![SQL Injection Discovery](/docs/acceptance/images/w1_sqli_01_discovery.png)

---

## 3. Preview & Environment Realism

In Step 2 (Preview Selection):

* **Topology Structure:** Multi-tier enterprise application environment containing an external perimeter firewall (Cisco ASA), frontend web server (NGINX), and backend production database (PostgreSQL).
* **Component Participation Breakdown:**
  * **Active Telemetry Producers:**
    1. `Perimeter Firewall (Bypassed)` (Vendor: Cisco ASA, Sourcetype: `cisco:asa`)
    2. `Vulnerable Web Server 01` (Vendor: NGINX, Sourcetype: `nginx:plus:kv`)
    3. `Production Database` (Vendor: PostgreSQL, Sourcetype: `postgresql:audit`)
  * **Topology Context:** Internal application boundary nodes.

![SQL Injection Preview](/docs/acceptance/images/w1_sqli_02_preview.png)

---

## 4. Connection Configuration

In Step 3 (Configure Connection):

* **Target Splunk Event Index:** `idx_network_ops`
* **HEC Endpoint:** `https://127.0.0.1:8888/services/collector`
* **Self-Signed TLS:** Enabled
* **Test Connection:** Successful.

![SQL Injection Connection](/docs/acceptance/images/w1_sqli_03_connection.png)

---

## 5. Scenario Execution & Runtime Phase Evidence

In Step 4 (Execute & Observe), the scenario executes across 6 distinct phases:

* **Fresh Run Correlation ID:** **`NS-20260925-024b5239`**
* **Total Events Generated:** **8**
* **Dispatch Succeeded:** **8 / 8 (100% HTTP 200)**
* **Dispatch Failed:** **0**

### 5.1. Baseline Phase
* **Observed State:** Cisco ASA permits inbound HTTPS; NGINX logs normal HTTP GET requests; PostgreSQL executes parameterized application queries.
![SQL Injection Baseline](/docs/acceptance/images/w1_sqli_04_baseline.png)

### 5.2. Attack Phase
* **Observed State:** Threat actor submits SQL injection payload. NGINX emits critical alert: `OWASP SQL Injection Attempt Detected in URI`.
![SQL Injection Attack](/docs/acceptance/images/w1_sqli_05_attack.png)

### 5.3. Propagation Phase
* **Observed State:** Malicious query reaches database audit layer; PostgreSQL audit logs: `PostgreSQL Security Audit: Unauthorized Schema Query Attempt`.
![SQL Injection Propagation](/docs/acceptance/images/w1_sqli_06_propagation.png)

### 5.4. Mitigation Phase
* **Observed State:** Cisco ASA perimeter firewall / IPS drops connection: `%ASA-4-106023: Deny tcp src outside:198.51.100.44/54122 dst inside:10.0.1.10/443 by access-group`.
![SQL Injection Mitigation](/docs/acceptance/images/w1_sqli_07_mitigation.png)

### 5.5. Recovery Phase
* **Observed State:** PostgreSQL connection pool sanitized and verified; Cisco ASA enforces IP blacklist; legitimate application transactions resume.
![SQL Injection Recovery](/docs/acceptance/images/w1_sqli_08_recovery.png)

---

## 6. Splunk Observation & Investigation

The user investigates the breach within Splunk Search:

```spl
search index=idx_network_ops netspout_run_id="NS-20260925-024b5239"
```

* **Splunk Event Count Observed:** **8 of 8 (100.0% completeness)**
* **Sourcetypes Observed in Splunk:**
  * 3x `cisco:asa`
  * 2x `nginx:plus:kv`
  * 3x `postgresql:audit`

![SQL Injection Splunk Evidence](/docs/acceptance/images/w1_sqli_09_splunk_evidence.png)

### Operational SOC Investigation Questions Answered Purely via Evidence:

1. **What was the attacker/source?**
   External IP `198.51.100.44` on port `54122`.
2. **What target was attacked?**
   Web application VIP `10.0.1.10` on port `443` and backend database `10.0.2.20`.
3. **What request/payload indicates SQL injection?**
   OWASP vector: `' OR '1'='1' -- UNION SELECT username, password FROM users`.
4. **Which security controls observed it?**
   Cisco ASA firewall (`cisco:asa`), NGINX web server (`nginx:plus:kv`), and PostgreSQL database audit logger (`postgresql:audit`).
5. **Was it allowed or blocked?**
   Initially allowed through perimeter as valid HTTPS traffic, detected by NGINX and PostgreSQL, then actively blocked by Cisco ASA IPS.
6. **Did it reach the application?**
   Yes. NGINX received the malicious HTTP URI parameter.
7. **Is database impact modeled?**
   Yes. PostgreSQL logged an unauthorized schema query attempt, but parameterized query protection prevented unauthorized data return.
8. **What mitigation occurred?**
   Cisco ASA denied further packets from attacker IP `198.51.100.44` and added the address to the dynamic threat blacklist.
9. **Did service recover?**
   Yes. PostgreSQL connection pool sanitized; legitimate parameterized catalog queries resumed.
10. **Which evidence proves each stage?**
    Correlated records across `cisco:asa`, `nginx:plus:kv`, and `postgresql:audit` under `netspout_run_id="NS-20260925-024b5239"`.

---

## 7. Multi-Source Validation & Negative Tampering Integrity

In Step 5 (Prove Expected Condition):

* **Observation Completeness:** **100.0% (8 / 8)**
* **Destination Status:** **`PASS`**
* **Overall Contract Validation:** **`PASS`**

| Rule ID | Rule Name | Criteria | Outcome | Detail |
| :--- | :--- | :--- | :---: | :--- |
| `sqli-val-01` | SQL Injection Attack Vector Detected | Signature matches SQLi pattern | **PASS** | Count 3 >= 1 |
| `sqli-val-02` | Multi-Tier Perimeter Security Present | Multi-tier security presence | **PASS** | Count 3 >= 1 |
| `sqli-val-03` | Attack Mitigation / Drop Enforced | `action == "blocked"` | **PASS** | Observed 2 events matching criteria |
| `sqli-val-04` | Database Operations Restored | `status == "normal"` post-mitigation | **PASS** | Observed 2 events matching criteria |

![SQL Injection Validation](/docs/acceptance/images/w1_sqli_10_validation.png)

* **Negative Tampering Verification:** Unit and integration tests confirm that stripping any tier's evidence (e.g. mutating blocked actions or deleting database audit events) causes immediate validation failure.

---

## 8. Final Acceptance Determination

* **Determination:** **`PASS`**
* **Developer Knowledge Required:** **`NO`**
* **Maturity Recommendation:** **`GOLDEN_PATH_CERTIFIED`** (Maintained at `E2E_VALIDATED` during test per protocol)
