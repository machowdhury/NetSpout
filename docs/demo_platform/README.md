# PulseForge Splunk Demo Platform

## Overview
Complete, visually impressive Splunk-native synthetic telemetry demonstration platform.

## Key Features
- **End-to-end coverage** for 9 priority sourcetypes
- **9 dashboard exports** for Splunk Dashboard Studio
- **Verified generators** with realistic telemetry
- **Executable scenarios** for each source
- **SPL queries** that retrieve and interpret telemetry
- **Visualization-ready** dashboard definitions

## Priority Sourcetypes
- `sc4snmp:event`
- `sc4snmp:metric`
- `cisco:aci:fault`
- `cisco:aci:syslog`
- `cloudflare:json`
- `cloudflare:r2:json`
- `openconfig:gnmi:telemetry`
- `a10:acos:cgnat`
- `a10:acos:syslog`

## Architecture

### 1. Data Generation
- **SNMP**: 307 verified OIDs with data-type specific values
- **OpenConfig/YANG**: Realistic interface and BGP telemetry
- **SaaS/Audit**: Batch 4 sources with RAW-equality verification
- **Network Telemetry**: Cisco, Arista, and other vendor sources

### 2. Scenario Execution
- Scenario packs for different use cases
- Time-synchronized event generation
- Deterministic seed for reproducibility

### 3. Splunk Integration
- HEC-compatible event formatting
- Metric and event sourcetypes
- Proper field extraction
- CIM mapping where applicable

### 4. Visualization
- Dashboard Studio JSON exports
- Time series, categorical, and single-value visualizations
- Drilldown capabilities
- Responsive layout

## Getting Started

### 1. Generate Data
```bash
python -m netspout_core.scenario_runner --scenario <scenario_id>
```

### 2. Ingest to Splunk
- Use HEC endpoint with appropriate token
- Set sourcetype and index as defined in sourcetype catalog

### 3. Deploy Dashboards
- Import dashboard JSON files to Splunk Dashboard Studio
- Configure data sources as needed
- Adjust time ranges and filters

## Verification Evidence
All sourcetypes include verification evidence:
- Schema verification (Workstream B/C)
- Generator implementation
- Generator testing
- Splunk ingestion verification (where available)

## Extending the Platform
1. Add new sourcetype to catalog
2. Implement generator in appropriate engine
3. Create scenario pack
4. Design dashboard visualization
5. Generate verification evidence

## Files
- `dashboards/exports/` - Dashboard Studio JSON files
- `docs/verification/` - Verification evidence
- `catalog/` - Source and scenario definitions
- `src/netspout_core/` - Generator implementations
