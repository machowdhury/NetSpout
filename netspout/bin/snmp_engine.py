"""
SC4SNMP & Multi-Vendor SNMP Simulation Engine (NetSpout)
Implements:
  - 300+ SC4SNMP-aligned MIB definitions (IF-MIB, SNMPv2-MIB, IP-MIB, TCP-MIB, UDP-MIB,
    BGP4-MIB, OSPF-MIB, ENTITY-MIB, CISCO-PROCESS-MIB, CISCO-MEMORY-POOL-MIB, CISCO-ENVMON-MIB,
    CISCO-BGP4-MIB, JUNIPER-MIB, ARISTA-RESOURCE-MIB, ARISTA-QUEUE-MIB)
  - SC4SNMP Metric Polling Generator (sourcetype="sc4snmp:metric", index="cisco_mdt_metrics")
  - SC4SNMP Trap Generator (linkDown, linkUp, bgpBackwardTransition, ciscoCpuThresholdExceeded, etc.)
  - Universal Multi-Pipeline Converters (Splunk HEC, OTel OTLP, Telegraf Influx/JSON, RFC 5424 Syslog)
"""

import time
import json
import random
from typing import Dict, List, Any, Optional, Tuple

try:
    from app.models import (
        Node, Edge, SNMPMibDefinition, SNMPPollingMetric, SNMPTrapEvent,
        TelemetryTransportConfig
    )
except ImportError:
    from models import (
        Node, Edge, SNMPMibDefinition, SNMPPollingMetric, SNMPTrapEvent,
        TelemetryTransportConfig
    )

# =========================================================================
# 300+ Comprehensive MIB Catalog
# =========================================================================
RAW_MIB_DEFINITIONS: List[Dict[str, Any]] = [
    # ---------------------------------------------------------------------
    # 1. IF-MIB (RFC 2863 / RFC 1213) - 40 MIBs
    # ---------------------------------------------------------------------
    {"name": "ifIndex", "oid": "1.3.6.1.2.1.2.2.1.1", "module": "IF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Unique interface index number", "is_table": True},
    {"name": "ifDescr", "oid": "1.3.6.1.2.1.2.2.1.2", "module": "IF-MIB", "type": "OctetString", "vendor": "RFC", "desc": "Interface description or name", "is_table": True},
    {"name": "ifType", "oid": "1.3.6.1.2.1.2.2.1.3", "module": "IF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "IANA interface network type (e.g. 6 = ethernetCsmacd)", "is_table": True},
    {"name": "ifMtu", "oid": "1.3.6.1.2.1.2.2.1.4", "module": "IF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Maximum transmission unit size in octets", "is_table": True},
    {"name": "ifSpeed", "oid": "1.3.6.1.2.1.2.2.1.5", "module": "IF-MIB", "type": "Gauge32", "vendor": "RFC", "desc": "Estimated current interface bandwidth in bits per second", "is_table": True},
    {"name": "ifPhysAddress", "oid": "1.3.6.1.2.1.2.2.1.6", "module": "IF-MIB", "type": "OctetString", "vendor": "RFC", "desc": "Physical MAC address of the interface", "is_table": True},
    {"name": "ifAdminStatus", "oid": "1.3.6.1.2.1.2.2.1.7", "module": "IF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Administrative status: 1=up, 2=down, 3=testing", "is_table": True},
    {"name": "ifOperStatus", "oid": "1.3.6.1.2.1.2.2.1.8", "module": "IF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Operational status: 1=up, 2=down, 3=testing, 4=unknown, 5=dormant", "is_table": True},
    {"name": "ifLastChange", "oid": "1.3.6.1.2.1.2.2.1.9", "module": "IF-MIB", "type": "TimeTicks", "vendor": "RFC", "desc": "Value of sysUpTime when interface entered its current operational state", "is_table": True},
    {"name": "ifInOctets", "oid": "1.3.6.1.2.1.2.2.1.10", "module": "IF-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total inbound octets received on the interface", "is_table": True},
    {"name": "ifInUcastPkts", "oid": "1.3.6.1.2.1.2.2.1.11", "module": "IF-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Subnetwork-unicast packets delivered to higher layer", "is_table": True},
    {"name": "ifInNUcastPkts", "oid": "1.3.6.1.2.1.2.2.1.12", "module": "IF-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Inbound non-unicast (broadcast/multicast) packets", "is_table": True},
    {"name": "ifInDiscards", "oid": "1.3.6.1.2.1.2.2.1.13", "module": "IF-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Inbound valid packets discarded due to buffer exhaustion", "is_table": True},
    {"name": "ifInErrors", "oid": "1.3.6.1.2.1.2.2.1.14", "module": "IF-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Inbound packets containing formatting errors or CRC faults", "is_table": True},
    {"name": "ifInUnknownProtos", "oid": "1.3.6.1.2.1.2.2.1.15", "module": "IF-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Inbound packets discarded due to unsupported higher-layer protocol", "is_table": True},
    {"name": "ifOutOctets", "oid": "1.3.6.1.2.1.2.2.1.16", "module": "IF-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total outbound octets transmitted out of the interface", "is_table": True},
    {"name": "ifOutUcastPkts", "oid": "1.3.6.1.2.1.2.2.1.17", "module": "IF-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Subnetwork-unicast packets requested to be transmitted", "is_table": True},
    {"name": "ifOutNUcastPkts", "oid": "1.3.6.1.2.1.2.2.1.18", "module": "IF-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Outbound non-unicast (broadcast/multicast) packets transmitted", "is_table": True},
    {"name": "ifOutDiscards", "oid": "1.3.6.1.2.1.2.2.1.19", "module": "IF-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Outbound packets discarded due to buffer overflow", "is_table": True},
    {"name": "ifOutErrors", "oid": "1.3.6.1.2.1.2.2.1.20", "module": "IF-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Outbound packets that could not be transmitted due to errors", "is_table": True},
    {"name": "ifOutQLen", "oid": "1.3.6.1.2.1.2.2.1.21", "module": "IF-MIB", "type": "Gauge32", "vendor": "RFC", "desc": "Current length of output packet queue", "is_table": True},
    {"name": "ifSpecific", "oid": "1.3.6.1.2.1.2.2.1.22", "module": "IF-MIB", "type": "OctetString", "vendor": "RFC", "desc": "Reference to MIB definition specific to physical medium", "is_table": True},
    {"name": "ifName", "oid": "1.3.6.1.2.1.31.1.1.1.1", "module": "IF-MIB", "type": "OctetString", "vendor": "RFC", "desc": "Textual name of the interface (e.g. GigabitEthernet0/1)", "is_table": True},
    {"name": "ifInMulticastPkts", "oid": "1.3.6.1.2.1.31.1.1.1.2", "module": "IF-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Multicast packets delivered to higher-layer protocol", "is_table": True},
    {"name": "ifInBroadcastPkts", "oid": "1.3.6.1.2.1.31.1.1.1.3", "module": "IF-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Broadcast packets delivered to higher-layer protocol", "is_table": True},
    {"name": "ifOutMulticastPkts", "oid": "1.3.6.1.2.1.31.1.1.1.4", "module": "IF-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Multicast packets transmitted out of the interface", "is_table": True},
    {"name": "ifOutBroadcastPkts", "oid": "1.3.6.1.2.1.31.1.1.1.5", "module": "IF-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Broadcast packets transmitted out of the interface", "is_table": True},
    {"name": "ifHCInOctets", "oid": "1.3.6.1.2.1.31.1.1.1.6", "module": "IF-MIB", "type": "Counter64", "vendor": "RFC", "desc": "64-bit high-capacity counter of total inbound octets", "is_table": True},
    {"name": "ifHCInUcastPkts", "oid": "1.3.6.1.2.1.31.1.1.1.7", "module": "IF-MIB", "type": "Counter64", "vendor": "RFC", "desc": "64-bit high-capacity counter of inbound unicast packets", "is_table": True},
    {"name": "ifHCInMulticastPkts", "oid": "1.3.6.1.2.1.31.1.1.1.8", "module": "IF-MIB", "type": "Counter64", "vendor": "RFC", "desc": "64-bit high-capacity counter of inbound multicast packets", "is_table": True},
    {"name": "ifHCInBroadcastPkts", "oid": "1.3.6.1.2.1.31.1.1.1.9", "module": "IF-MIB", "type": "Counter64", "vendor": "RFC", "desc": "64-bit high-capacity counter of inbound broadcast packets", "is_table": True},
    {"name": "ifHCOutOctets", "oid": "1.3.6.1.2.1.31.1.1.1.10", "module": "IF-MIB", "type": "Counter64", "vendor": "RFC", "desc": "64-bit high-capacity counter of total outbound octets", "is_table": True},
    {"name": "ifHCOutUcastPkts", "oid": "1.3.6.1.2.1.31.1.1.1.11", "module": "IF-MIB", "type": "Counter64", "vendor": "RFC", "desc": "64-bit high-capacity counter of outbound unicast packets", "is_table": True},
    {"name": "ifHCOutMulticastPkts", "oid": "1.3.6.1.2.1.31.1.1.1.12", "module": "IF-MIB", "type": "Counter64", "vendor": "RFC", "desc": "64-bit high-capacity counter of outbound multicast packets", "is_table": True},
    {"name": "ifHCOutBroadcastPkts", "oid": "1.3.6.1.2.1.31.1.1.1.13", "module": "IF-MIB", "type": "Counter64", "vendor": "RFC", "desc": "64-bit high-capacity counter of outbound broadcast packets", "is_table": True},
    {"name": "ifLinkUpDownTrapEnable", "oid": "1.3.6.1.2.1.31.1.1.1.14", "module": "IF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Whether linkUp/linkDown traps are enabled (1=enabled, 2=disabled)", "is_table": True},
    {"name": "ifHighSpeed", "oid": "1.3.6.1.2.1.31.1.1.1.15", "module": "IF-MIB", "type": "Gauge32", "vendor": "RFC", "desc": "Estimate of interface current bandwidth in megabits/sec", "is_table": True},
    {"name": "ifPromiscuousMode", "oid": "1.3.6.1.2.1.31.1.1.1.16", "module": "IF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Whether interface is in promiscuous mode (1=true, 2=false)", "is_table": True},
    {"name": "ifConnectorPresent", "oid": "1.3.6.1.2.1.31.1.1.1.17", "module": "IF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Whether interface has physical connector (1=true, 2=false)", "is_table": True},
    {"name": "ifAlias", "oid": "1.3.6.1.2.1.31.1.1.1.18", "module": "IF-MIB", "type": "OctetString", "vendor": "RFC", "desc": "User configured interface alias string", "is_table": True},
    {"name": "ifCounterDiscontinuityTime", "oid": "1.3.6.1.2.1.31.1.1.1.19", "module": "IF-MIB", "type": "TimeTicks", "vendor": "RFC", "desc": "sysUpTime timestamp of most recent counter reset", "is_table": True},

    # ---------------------------------------------------------------------
    # 2. SNMPv2-MIB (RFC 3418) - 35 MIBs
    # ---------------------------------------------------------------------
    {"name": "sysDescr", "oid": "1.3.6.1.2.1.1.1.0", "module": "SNMPv2-MIB", "type": "OctetString", "vendor": "RFC", "desc": "Hardware and software version description", "is_table": False},
    {"name": "sysObjectID", "oid": "1.3.6.1.2.1.1.2.0", "module": "SNMPv2-MIB", "type": "OctetString", "vendor": "RFC", "desc": "Vendor authoritative identification of network subsystem", "is_table": False},
    {"name": "sysUpTime", "oid": "1.3.6.1.2.1.1.3.0", "module": "SNMPv2-MIB", "type": "TimeTicks", "vendor": "RFC", "desc": "Time in hundredths of a second since agent initialized", "is_table": False},
    {"name": "sysContact", "oid": "1.3.6.1.2.1.1.4.0", "module": "SNMPv2-MIB", "type": "OctetString", "vendor": "RFC", "desc": "Contact person for this managed node", "is_table": False},
    {"name": "sysName", "oid": "1.3.6.1.2.1.1.5.0", "module": "SNMPv2-MIB", "type": "OctetString", "vendor": "RFC", "desc": "Fully qualified administrative node name", "is_table": False},
    {"name": "sysLocation", "oid": "1.3.6.1.2.1.1.6.0", "module": "SNMPv2-MIB", "type": "OctetString", "vendor": "RFC", "desc": "Physical location of this device node", "is_table": False},
    {"name": "sysServices", "oid": "1.3.6.1.2.1.1.7.0", "module": "SNMPv2-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Value indicating OSI layers served (e.g. 78)", "is_table": False},
    {"name": "sysORLastChange", "oid": "1.3.6.1.2.1.1.8.0", "module": "SNMPv2-MIB", "type": "TimeTicks", "vendor": "RFC", "desc": "sysUpTime value when object resource table last changed", "is_table": False},
    {"name": "snmpInPkts", "oid": "1.3.6.1.2.1.11.1.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total SNMP packets delivered to SNMP entity", "is_table": False},
    {"name": "snmpOutPkts", "oid": "1.3.6.1.2.1.11.2.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total SNMP packets passed from SNMP entity to transport", "is_table": False},
    {"name": "snmpInBadVersions", "oid": "1.3.6.1.2.1.11.3.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "SNMP packets with unsupported version number", "is_table": False},
    {"name": "snmpInBadCommunityNames", "oid": "1.3.6.1.2.1.11.4.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "SNMP packets with unknown community name", "is_table": False},
    {"name": "snmpInBadCommunityUses", "oid": "1.3.6.1.2.1.11.5.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "SNMP packets with operation not allowed by community", "is_table": False},
    {"name": "snmpInASNParseErrs", "oid": "1.3.6.1.2.1.11.6.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "SNMP packets discarded due to ASN.1 or BER errors", "is_table": False},
    {"name": "snmpInTooBigs", "oid": "1.3.6.1.2.1.11.8.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "SNMP PDUs received with tooBig error status", "is_table": False},
    {"name": "snmpInNoSuchNames", "oid": "1.3.6.1.2.1.11.9.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "SNMP PDUs received with noSuchName error status", "is_table": False},
    {"name": "snmpInBadValues", "oid": "1.3.6.1.2.1.11.10.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "SNMP PDUs received with badValue error status", "is_table": False},
    {"name": "snmpInReadOnlys", "oid": "1.3.6.1.2.1.11.11.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "SNMP PDUs received with readOnly error status", "is_table": False},
    {"name": "snmpInGenErrs", "oid": "1.3.6.1.2.1.11.12.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "SNMP PDUs received with genErr error status", "is_table": False},
    {"name": "snmpInTotalReqVars", "oid": "1.3.6.1.2.1.11.13.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total MIB objects successfully retrieved in requests", "is_table": False},
    {"name": "snmpInTotalSetVars", "oid": "1.3.6.1.2.1.11.14.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total MIB objects successfully altered in set requests", "is_table": False},
    {"name": "snmpInGetRequests", "oid": "1.3.6.1.2.1.11.15.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total Get-Request PDUs accepted and processed", "is_table": False},
    {"name": "snmpInGetNexts", "oid": "1.3.6.1.2.1.11.16.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total Get-Next PDUs accepted and processed", "is_table": False},
    {"name": "snmpInSetRequests", "oid": "1.3.6.1.2.1.11.17.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total Set-Request PDUs accepted and processed", "is_table": False},
    {"name": "snmpInGetResponses", "oid": "1.3.6.1.2.1.11.18.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total Get-Response PDUs accepted and processed", "is_table": False},
    {"name": "snmpInTraps", "oid": "1.3.6.1.2.1.11.19.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total SNMP Trap PDUs accepted and processed", "is_table": False},
    {"name": "snmpOutTooBigs", "oid": "1.3.6.1.2.1.11.20.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "SNMP PDUs generated with tooBig error status", "is_table": False},
    {"name": "snmpOutNoSuchNames", "oid": "1.3.6.1.2.1.11.21.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "SNMP PDUs generated with noSuchName error status", "is_table": False},
    {"name": "snmpOutBadValues", "oid": "1.3.6.1.2.1.11.22.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "SNMP PDUs generated with badValue error status", "is_table": False},
    {"name": "snmpOutGenErrs", "oid": "1.3.6.1.2.1.11.24.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "SNMP PDUs generated with genErr error status", "is_table": False},
    {"name": "snmpOutGetRequests", "oid": "1.3.6.1.2.1.11.25.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total Get-Request PDUs generated", "is_table": False},
    {"name": "snmpOutGetNexts", "oid": "1.3.6.1.2.1.11.26.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total Get-Next PDUs generated", "is_table": False},
    {"name": "snmpOutSetRequests", "oid": "1.3.6.1.2.1.11.27.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total Set-Request PDUs generated", "is_table": False},
    {"name": "snmpOutGetResponses", "oid": "1.3.6.1.2.1.11.28.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total Get-Response PDUs generated", "is_table": False},
    {"name": "snmpOutTraps", "oid": "1.3.6.1.2.1.11.29.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total SNMP Trap PDUs generated", "is_table": False},
    {"name": "snmpSilentDrops", "oid": "1.3.6.1.2.1.11.31.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "SNMP packets silently discarded due to authentication failure", "is_table": False},
    {"name": "snmpProxyDrops", "oid": "1.3.6.1.2.1.11.32.0", "module": "SNMPv2-MIB", "type": "Counter32", "vendor": "RFC", "desc": "SNMP packets silently discarded by proxy", "is_table": False},

    # ---------------------------------------------------------------------
    # 3. IP-MIB & RFC1213-MIB - 45 MIBs
    # ---------------------------------------------------------------------
    {"name": "ipForwarding", "oid": "1.3.6.1.2.1.4.1.0", "module": "IP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "1=forwarding gateway, 2=not-forwarding host", "is_table": False},
    {"name": "ipDefaultTTL", "oid": "1.3.6.1.2.1.4.2.0", "module": "IP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Default value inserted into IP header TTL field", "is_table": False},
    {"name": "ipInReceives", "oid": "1.3.6.1.2.1.4.3.0", "module": "IP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total input datagrams received from interfaces", "is_table": False},
    {"name": "ipInHdrErrors", "oid": "1.3.6.1.2.1.4.4.0", "module": "IP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Input datagrams discarded due to IP header errors", "is_table": False},
    {"name": "ipInAddrErrors", "oid": "1.3.6.1.2.1.4.5.0", "module": "IP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Input datagrams discarded due to invalid destination IP", "is_table": False},
    {"name": "ipForwDatagrams", "oid": "1.3.6.1.2.1.4.6.0", "module": "IP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Input datagrams forwarded to another entity", "is_table": False},
    {"name": "ipInUnknownProtos", "oid": "1.3.6.1.2.1.4.7.0", "module": "IP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Input datagrams discarded due to unknown protocol", "is_table": False},
    {"name": "ipInDiscards", "oid": "1.3.6.1.2.1.4.8.0", "module": "IP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Input datagrams discarded due to lack of buffers", "is_table": False},
    {"name": "ipInDelivers", "oid": "1.3.6.1.2.1.4.9.0", "module": "IP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Input datagrams successfully delivered to protocols", "is_table": False},
    {"name": "ipOutRequests", "oid": "1.3.6.1.2.1.4.10.0", "module": "IP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total IP datagrams supplied by local protocols", "is_table": False},
    {"name": "ipOutDiscards", "oid": "1.3.6.1.2.1.4.11.0", "module": "IP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Output IP datagrams discarded due to memory exhaustion", "is_table": False},
    {"name": "ipOutNoRoutes", "oid": "1.3.6.1.2.1.4.12.0", "module": "IP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Output datagrams discarded because no route was found", "is_table": False},
    {"name": "ipReasmTimeout", "oid": "1.3.6.1.2.1.4.13.0", "module": "IP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Maximum seconds received fragments are held awaiting reassembly", "is_table": False},
    {"name": "ipReasmReqds", "oid": "1.3.6.1.2.1.4.14.0", "module": "IP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Number of IP fragments received requiring reassembly", "is_table": False},
    {"name": "ipReasmOKs", "oid": "1.3.6.1.2.1.4.15.0", "module": "IP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Number of IP datagrams successfully reassembled", "is_table": False},
    {"name": "ipReasmFails", "oid": "1.3.6.1.2.1.4.16.0", "module": "IP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Failures detected by IP reassembly algorithm", "is_table": False},
    {"name": "ipFragOKs", "oid": "1.3.6.1.2.1.4.17.0", "module": "IP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "IP datagrams successfully fragmented at this node", "is_table": False},
    {"name": "ipFragFails", "oid": "1.3.6.1.2.1.4.18.0", "module": "IP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "IP datagrams discarded because fragmentation failed (DF bit)", "is_table": False},
    {"name": "ipFragCreates", "oid": "1.3.6.1.2.1.4.19.0", "module": "IP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total IP datagram fragments generated at this node", "is_table": False},
    {"name": "ipRoutingDiscards", "oid": "1.3.6.1.2.1.4.23.0", "module": "IP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Valid routing entries discarded due to memory limit", "is_table": False},
    {"name": "ipAdEntAddr", "oid": "1.3.6.1.2.1.4.20.1.1", "module": "IP-MIB", "type": "IpAddress", "vendor": "RFC", "desc": "The IPv4 address to which this entry relates", "is_table": True},
    {"name": "ipAdEntIfIndex", "oid": "1.3.6.1.2.1.4.20.1.2", "module": "IP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Interface index identifying corresponding subnetwork", "is_table": True},
    {"name": "ipAdEntNetMask", "oid": "1.3.6.1.2.1.4.20.1.3", "module": "IP-MIB", "type": "IpAddress", "vendor": "RFC", "desc": "Subnet mask associated with the IPv4 address", "is_table": True},
    {"name": "ipAdEntBcastAddr", "oid": "1.3.6.1.2.1.4.20.1.4", "module": "IP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Value of least significant bit in IP broadcast address", "is_table": True},
    {"name": "ipAdEntReasmMaxSize", "oid": "1.3.6.1.2.1.4.20.1.5", "module": "IP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Size of largest IP datagram this entity can reassemble", "is_table": True},
    {"name": "ipRouteDest", "oid": "1.3.6.1.2.1.4.21.1.1", "module": "IP-MIB", "type": "IpAddress", "vendor": "RFC", "desc": "Destination IPv4 address of this route", "is_table": True},
    {"name": "ipRouteIfIndex", "oid": "1.3.6.1.2.1.4.21.1.2", "module": "IP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Index of local interface through which next hop is reached", "is_table": True},
    {"name": "ipRouteMetric1", "oid": "1.3.6.1.2.1.4.21.1.3", "module": "IP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Primary routing metric for this route", "is_table": True},
    {"name": "ipRouteMetric2", "oid": "1.3.6.1.2.1.4.21.1.4", "module": "IP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Alternate routing metric 2", "is_table": True},
    {"name": "ipRouteMetric3", "oid": "1.3.6.1.2.1.4.21.1.5", "module": "IP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Alternate routing metric 3", "is_table": True},
    {"name": "ipRouteMetric4", "oid": "1.3.6.1.2.1.4.21.1.6", "module": "IP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Alternate routing metric 4", "is_table": True},
    {"name": "ipRouteNextHop", "oid": "1.3.6.1.2.1.4.21.1.7", "module": "IP-MIB", "type": "IpAddress", "vendor": "RFC", "desc": "IPv4 address of next hop router", "is_table": True},
    {"name": "ipRouteType", "oid": "1.3.6.1.2.1.4.21.1.8", "module": "IP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Route type: 1=other, 2=invalid, 3=direct, 4=indirect", "is_table": True},
    {"name": "ipRouteProto", "oid": "1.3.6.1.2.1.4.21.1.9", "module": "IP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Routing protocol: 1=other, 2=local, 3=netmgmt, 4=icmp, 13=ospf, 14=bgp", "is_table": True},
    {"name": "ipRouteAge", "oid": "1.3.6.1.2.1.4.21.1.10", "module": "IP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Number of seconds since route was last updated or verified", "is_table": True},
    {"name": "ipRouteMask", "oid": "1.3.6.1.2.1.4.21.1.11", "module": "IP-MIB", "type": "IpAddress", "vendor": "RFC", "desc": "Subnet mask to apply to destination address before comparison", "is_table": True},
    {"name": "ipRouteMetric5", "oid": "1.3.6.1.2.1.4.21.1.12", "module": "IP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Alternate routing metric 5", "is_table": True},
    {"name": "ipRouteInfo", "oid": "1.3.6.1.2.1.4.21.1.13", "module": "IP-MIB", "type": "OctetString", "vendor": "RFC", "desc": "Reference to MIB definition specific to routing protocol", "is_table": True},
    {"name": "ipNetToMediaIfIndex", "oid": "1.3.6.1.2.1.4.22.1.1", "module": "IP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Interface index for ARP address mapping entry", "is_table": True},
    {"name": "ipNetToMediaPhysAddress", "oid": "1.3.6.1.2.1.4.22.1.2", "module": "IP-MIB", "type": "OctetString", "vendor": "RFC", "desc": "Media-dependent physical MAC address", "is_table": True},
    {"name": "ipNetToMediaNetAddress", "oid": "1.3.6.1.2.1.4.22.1.3", "module": "IP-MIB", "type": "IpAddress", "vendor": "RFC", "desc": "IPv4 address corresponding to physical address", "is_table": True},
    {"name": "ipNetToMediaType", "oid": "1.3.6.1.2.1.4.22.1.4", "module": "IP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Mapping type: 1=other, 2=invalid, 3=dynamic, 4=static", "is_table": True},
    {"name": "ipSystemStatsInReceives", "oid": "1.3.6.1.2.1.4.31.1.1.3.1", "module": "IP-MIB", "type": "Counter64", "vendor": "RFC", "desc": "High capacity 64-bit total input datagrams received", "is_table": True},
    {"name": "ipSystemStatsInOctets", "oid": "1.3.6.1.2.1.4.31.1.1.4.1", "module": "IP-MIB", "type": "Counter64", "vendor": "RFC", "desc": "High capacity 64-bit total inbound IP octets received", "is_table": True},
    {"name": "ipSystemStatsOutOctets", "oid": "1.3.6.1.2.1.4.31.1.1.34.1", "module": "IP-MIB", "type": "Counter64", "vendor": "RFC", "desc": "High capacity 64-bit total outbound IP octets transmitted", "is_table": True},

    # ---------------------------------------------------------------------
    # 4. TCP-MIB (RFC 4022) - 20 MIBs
    # ---------------------------------------------------------------------
    {"name": "tcpRtoAlgorithm", "oid": "1.3.6.1.2.1.6.1.0", "module": "TCP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Algorithm used to determine retransmission timeout (e.g. 4=vanj)", "is_table": False},
    {"name": "tcpRtoMin", "oid": "1.3.6.1.2.1.6.2.0", "module": "TCP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Minimum retransmission timeout value in milliseconds", "is_table": False},
    {"name": "tcpRtoMax", "oid": "1.3.6.1.2.1.6.3.0", "module": "TCP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Maximum retransmission timeout value in milliseconds", "is_table": False},
    {"name": "tcpMaxConn", "oid": "1.3.6.1.2.1.6.4.0", "module": "TCP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Limit on total TCP connections the entity can support", "is_table": False},
    {"name": "tcpActiveOpens", "oid": "1.3.6.1.2.1.6.5.0", "module": "TCP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Direct transitions from CLOSED state to SYN-SENT state", "is_table": False},
    {"name": "tcpPassiveOpens", "oid": "1.3.6.1.2.1.6.6.0", "module": "TCP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Direct transitions from LISTEN state to SYN-RCVD state", "is_table": False},
    {"name": "tcpAttemptFails", "oid": "1.3.6.1.2.1.6.7.0", "module": "TCP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Transitions directly from SYN-SENT or SYN-RCVD to CLOSED", "is_table": False},
    {"name": "tcpEstabResets", "oid": "1.3.6.1.2.1.6.8.0", "module": "TCP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Direct transitions from ESTABLISHED or CLOSE-WAIT to CLOSED", "is_table": False},
    {"name": "tcpCurrEstab", "oid": "1.3.6.1.2.1.6.9.0", "module": "TCP-MIB", "type": "Gauge32", "vendor": "RFC", "desc": "TCP connections currently in ESTABLISHED or CLOSE-WAIT state", "is_table": False},
    {"name": "tcpInSegs", "oid": "1.3.6.1.2.1.6.10.0", "module": "TCP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total TCP segments received, including those with errors", "is_table": False},
    {"name": "tcpOutSegs", "oid": "1.3.6.1.2.1.6.11.0", "module": "TCP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total TCP segments sent, including retransmissions", "is_table": False},
    {"name": "tcpRetransSegs", "oid": "1.3.6.1.2.1.6.12.0", "module": "TCP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "TCP segments retransmitted containing one or more bytes", "is_table": False},
    {"name": "tcpInErrs", "oid": "1.3.6.1.2.1.6.14.0", "module": "TCP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total TCP segments received in error (bad checksums)", "is_table": False},
    {"name": "tcpOutRsts", "oid": "1.3.6.1.2.1.6.15.0", "module": "TCP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "TCP segments sent containing the RST reset flag", "is_table": False},
    {"name": "tcpHCInSegs", "oid": "1.3.6.1.2.1.6.17.0", "module": "TCP-MIB", "type": "Counter64", "vendor": "RFC", "desc": "64-bit high-capacity counter of total TCP segments received", "is_table": False},
    {"name": "tcpHCOutSegs", "oid": "1.3.6.1.2.1.6.18.0", "module": "TCP-MIB", "type": "Counter64", "vendor": "RFC", "desc": "64-bit high-capacity counter of total TCP segments transmitted", "is_table": False},
    {"name": "tcpConnState", "oid": "1.3.6.1.2.1.6.13.1.1", "module": "TCP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "State of TCP connection: 1=closed, 2=listen, 5=established", "is_table": True},
    {"name": "tcpConnLocalAddress", "oid": "1.3.6.1.2.1.6.13.1.2", "module": "TCP-MIB", "type": "IpAddress", "vendor": "RFC", "desc": "Local IPv4 address for this TCP connection", "is_table": True},
    {"name": "tcpConnLocalPort", "oid": "1.3.6.1.2.1.6.13.1.3", "module": "TCP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Local port number for this TCP connection", "is_table": True},
    {"name": "tcpConnRemAddress", "oid": "1.3.6.1.2.1.6.13.1.4", "module": "TCP-MIB", "type": "IpAddress", "vendor": "RFC", "desc": "Remote IPv4 address for this TCP connection", "is_table": True},

    # ---------------------------------------------------------------------
    # 5. UDP-MIB (RFC 4113) - 10 MIBs
    # ---------------------------------------------------------------------
    {"name": "udpInDatagrams", "oid": "1.3.6.1.2.1.7.1.0", "module": "UDP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total UDP datagrams delivered to application users", "is_table": False},
    {"name": "udpNoPorts", "oid": "1.3.6.1.2.1.7.2.0", "module": "UDP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Received UDP datagrams for which no application existed", "is_table": False},
    {"name": "udpInErrors", "oid": "1.3.6.1.2.1.7.3.0", "module": "UDP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Received UDP datagrams that could not be delivered", "is_table": False},
    {"name": "udpOutDatagrams", "oid": "1.3.6.1.2.1.7.4.0", "module": "UDP-MIB", "type": "Counter32", "vendor": "RFC", "desc": "UDP datagrams sent from this entity", "is_table": False},
    {"name": "udpHCInDatagrams", "oid": "1.3.6.1.2.1.7.8.0", "module": "UDP-MIB", "type": "Counter64", "vendor": "RFC", "desc": "64-bit high capacity counter of delivered UDP datagrams", "is_table": False},
    {"name": "udpHCOutDatagrams", "oid": "1.3.6.1.2.1.7.9.0", "module": "UDP-MIB", "type": "Counter64", "vendor": "RFC", "desc": "64-bit high capacity counter of transmitted UDP datagrams", "is_table": False},
    {"name": "udpLocalAddress", "oid": "1.3.6.1.2.1.7.5.1.1", "module": "UDP-MIB", "type": "IpAddress", "vendor": "RFC", "desc": "Local IPv4 address for this UDP listener", "is_table": True},
    {"name": "udpLocalPort", "oid": "1.3.6.1.2.1.7.5.1.2", "module": "UDP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Local port number for this UDP listener", "is_table": True},
    {"name": "udpEndpointProcess", "oid": "1.3.6.1.2.1.7.7.1.8", "module": "UDP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "PID of the process that opened this UDP socket", "is_table": True},
    {"name": "udpEndpointInstance", "oid": "1.3.6.1.2.1.7.7.1.7", "module": "UDP-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Index identifying multiple sockets bound to same address", "is_table": True},

    # ---------------------------------------------------------------------
    # 6. BGP4-MIB (RFC 4273) - 25 MIBs
    # ---------------------------------------------------------------------
    {"name": "bgpVersion", "oid": "1.3.6.1.2.1.15.1.0", "module": "BGP4-MIB", "type": "OctetString", "vendor": "RFC", "desc": "Vector of supported BGP protocol version numbers", "is_table": False},
    {"name": "bgpLocalAs", "oid": "1.3.6.1.2.1.15.2.0", "module": "BGP4-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Autonomous system number of local BGP speaker", "is_table": False},
    {"name": "bgpIdentifier", "oid": "1.3.6.1.2.1.15.4.0", "module": "BGP4-MIB", "type": "IpAddress", "vendor": "RFC", "desc": "BGP Identifier router ID of local BGP speaker", "is_table": False},
    {"name": "bgpPeerIdentifier", "oid": "1.3.6.1.2.1.15.3.1.1", "module": "BGP4-MIB", "type": "IpAddress", "vendor": "RFC", "desc": "BGP Identifier of remote BGP peer router", "is_table": True},
    {"name": "bgpPeerState", "oid": "1.3.6.1.2.1.15.3.1.2", "module": "BGP4-MIB", "type": "Integer32", "vendor": "RFC", "desc": "BGP peer FSM state: 1=idle, 2=connect, 3=active, 4=opensent, 5=openconfirm, 6=established", "is_table": True},
    {"name": "bgpPeerAdminStatus", "oid": "1.3.6.1.2.1.15.3.1.3", "module": "BGP4-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Desired state: 1=stop, 2=start", "is_table": True},
    {"name": "bgpPeerNegotiatedVersion", "oid": "1.3.6.1.2.1.15.3.1.4", "module": "BGP4-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Negotiated BGP version with this peer (e.g. 4)", "is_table": True},
    {"name": "bgpPeerLocalAddr", "oid": "1.3.6.1.2.1.15.3.1.5", "module": "BGP4-MIB", "type": "IpAddress", "vendor": "RFC", "desc": "Local IP address of local end of BGP TCP connection", "is_table": True},
    {"name": "bgpPeerLocalPort", "oid": "1.3.6.1.2.1.15.3.1.6", "module": "BGP4-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Local TCP port of BGP connection (typically 179)", "is_table": True},
    {"name": "bgpPeerRemoteAddr", "oid": "1.3.6.1.2.1.15.3.1.7", "module": "BGP4-MIB", "type": "IpAddress", "vendor": "RFC", "desc": "Remote IP address of BGP peer", "is_table": True},
    {"name": "bgpPeerRemotePort", "oid": "1.3.6.1.2.1.15.3.1.8", "module": "BGP4-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Remote TCP port of BGP peer connection", "is_table": True},
    {"name": "bgpPeerRemoteAs", "oid": "1.3.6.1.2.1.15.3.1.9", "module": "BGP4-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Autonomous system number of remote BGP peer", "is_table": True},
    {"name": "bgpPeerInUpdates", "oid": "1.3.6.1.2.1.15.3.1.10", "module": "BGP4-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total BGP UPDATE messages received from this peer", "is_table": True},
    {"name": "bgpPeerOutUpdates", "oid": "1.3.6.1.2.1.15.3.1.11", "module": "BGP4-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total BGP UPDATE messages transmitted to this peer", "is_table": True},
    {"name": "bgpPeerInTotalMessages", "oid": "1.3.6.1.2.1.15.3.1.12", "module": "BGP4-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total BGP messages received from this peer", "is_table": True},
    {"name": "bgpPeerOutTotalMessages", "oid": "1.3.6.1.2.1.15.3.1.13", "module": "BGP4-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Total BGP messages transmitted to this peer", "is_table": True},
    {"name": "bgpPeerLastError", "oid": "1.3.6.1.2.1.15.3.1.14", "module": "BGP4-MIB", "type": "OctetString", "vendor": "RFC", "desc": "Last error code and subcode received or sent in NOTIFICATION", "is_table": True},
    {"name": "bgpPeerFsmEstablishedTransitions", "oid": "1.3.6.1.2.1.15.3.1.15", "module": "BGP4-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Number of times peer transitioned into ESTABLISHED state", "is_table": True},
    {"name": "bgpPeerFsmEstablishedTime", "oid": "1.3.6.1.2.1.15.3.1.16", "module": "BGP4-MIB", "type": "Gauge32", "vendor": "RFC", "desc": "Elapsed seconds peer has been in ESTABLISHED state", "is_table": True},
    {"name": "bgpPeerConnectRetryInterval", "oid": "1.3.6.1.2.1.15.3.1.17", "module": "BGP4-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Time interval in seconds for ConnectRetry timer", "is_table": True},
    {"name": "bgpPeerHoldTime", "oid": "1.3.6.1.2.1.15.3.1.18", "module": "BGP4-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Time interval in seconds for HoldTimer configured with peer", "is_table": True},
    {"name": "bgpPeerKeepAlive", "oid": "1.3.6.1.2.1.15.3.1.19", "module": "BGP4-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Time interval in seconds for KeepAlive timer", "is_table": True},
    {"name": "bgpPeerHoldTimeConfigured", "oid": "1.3.6.1.2.1.15.3.1.20", "module": "BGP4-MIB", "type": "Integer32", "vendor": "RFC", "desc": "HoldTime locally configured for this peer", "is_table": True},
    {"name": "bgpPeerKeepAliveConfigured", "oid": "1.3.6.1.2.1.15.3.1.21", "module": "BGP4-MIB", "type": "Integer32", "vendor": "RFC", "desc": "KeepAlive locally configured for this peer", "is_table": True},
    {"name": "bgpPeerInUpdateElapsedTime", "oid": "1.3.6.1.2.1.15.3.1.24", "module": "BGP4-MIB", "type": "Gauge32", "vendor": "RFC", "desc": "Elapsed seconds since last UPDATE message was received", "is_table": True},

    # ---------------------------------------------------------------------
    # 7. OSPF-MIB (RFC 4750) - 35 MIBs
    # ---------------------------------------------------------------------
    {"name": "ospfRouterId", "oid": "1.3.6.1.2.1.14.1.1.0", "module": "OSPF-MIB", "type": "IpAddress", "vendor": "RFC", "desc": "32-bit router ID of this OSPF router", "is_table": False},
    {"name": "ospfAdminStat", "oid": "1.3.6.1.2.1.14.1.2.0", "module": "OSPF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Administrative status: 1=enabled, 2=disabled", "is_table": False},
    {"name": "ospfVersionNumber", "oid": "1.3.6.1.2.1.14.1.3.0", "module": "OSPF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Current version number of OSPF protocol (e.g. 2)", "is_table": False},
    {"name": "ospfAreaBdrRtrStatus", "oid": "1.3.6.1.2.1.14.1.4.0", "module": "OSPF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "1=true (area border router ABR), 2=false", "is_table": False},
    {"name": "ospfASBdrRtrStatus", "oid": "1.3.6.1.2.1.14.1.5.0", "module": "OSPF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "1=true (autonomous system boundary router ASBR), 2=false", "is_table": False},
    {"name": "ospfExternLsaCount", "oid": "1.3.6.1.2.1.14.1.6.0", "module": "OSPF-MIB", "type": "Gauge32", "vendor": "RFC", "desc": "Number of external (type-5) LSAs in link-state database", "is_table": False},
    {"name": "ospfExternLsaCksumSum", "oid": "1.3.6.1.2.1.14.1.7.0", "module": "OSPF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "32-bit sum of external LSA checksums", "is_table": False},
    {"name": "ospfTOSSupport", "oid": "1.3.6.1.2.1.14.1.8.0", "module": "OSPF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Whether router supports TOS routing metrics (1=true, 2=false)", "is_table": False},
    {"name": "ospfOriginateNewLsas", "oid": "1.3.6.1.2.1.14.1.9.0", "module": "OSPF-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Number of new LSAs originated by this router", "is_table": False},
    {"name": "ospfRxNewLsas", "oid": "1.3.6.1.2.1.14.1.10.0", "module": "OSPF-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Number of new LSAs received by this router", "is_table": False},
    {"name": "ospfExtLsdbLimit", "oid": "1.3.6.1.2.1.14.1.11.0", "module": "OSPF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Maximum number of non-default AS-external-LSAs allowed", "is_table": False},
    {"name": "ospfExitOverflowInterval", "oid": "1.3.6.1.2.1.14.1.13.0", "module": "OSPF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Seconds router waits after overflow before leaving state", "is_table": False},
    {"name": "ospfDemandExtensions", "oid": "1.3.6.1.2.1.14.1.14.0", "module": "OSPF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Whether demand routing extensions are supported", "is_table": False},
    {"name": "ospfAreaId", "oid": "1.3.6.1.2.1.14.2.1.1", "module": "OSPF-MIB", "type": "IpAddress", "vendor": "RFC", "desc": "32-bit identifier of this OSPF area (e.g. 0.0.0.0)", "is_table": True},
    {"name": "ospfAuthType", "oid": "1.3.6.1.2.1.14.2.1.2", "module": "OSPF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Authentication scheme: 0=none, 1=simplePassword, 2=md5", "is_table": True},
    {"name": "ospfImportAsExtern", "oid": "1.3.6.1.2.1.14.2.1.3", "module": "OSPF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "1=importExternal, 2=importNoExternal (stub area)", "is_table": True},
    {"name": "ospfSpfRuns", "oid": "1.3.6.1.2.1.14.2.1.4", "module": "OSPF-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Number of times Dijkstra SPF algorithm has run on area", "is_table": True},
    {"name": "ospfAreaBdrRtrCount", "oid": "1.3.6.1.2.1.14.2.1.5", "module": "OSPF-MIB", "type": "Gauge32", "vendor": "RFC", "desc": "Number of reachable ABR routers in this area", "is_table": True},
    {"name": "ospfASBdrRtrCount", "oid": "1.3.6.1.2.1.14.2.1.6", "module": "OSPF-MIB", "type": "Gauge32", "vendor": "RFC", "desc": "Number of reachable ASBR routers in this area", "is_table": True},
    {"name": "ospfAreaLsaCount", "oid": "1.3.6.1.2.1.14.2.1.7", "module": "OSPF-MIB", "type": "Gauge32", "vendor": "RFC", "desc": "Total number of link-state advertisements in this area", "is_table": True},
    {"name": "ospfNbrIpAddr", "oid": "1.3.6.1.2.1.14.10.1.1", "module": "OSPF-MIB", "type": "IpAddress", "vendor": "RFC", "desc": "IPv4 address of OSPF neighbor", "is_table": True},
    {"name": "ospfNbrAddressLessIndex", "oid": "1.3.6.1.2.1.14.10.1.2", "module": "OSPF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Interface index for unnumbered point-to-point interface", "is_table": True},
    {"name": "ospfNbrRtrId", "oid": "1.3.6.1.2.1.14.10.1.3", "module": "OSPF-MIB", "type": "IpAddress", "vendor": "RFC", "desc": "Router ID of neighbor router in dotted decimal notation", "is_table": True},
    {"name": "ospfNbrOptions", "oid": "1.3.6.1.2.1.14.10.1.4", "module": "OSPF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Bit mask of OSPF options negotiated with neighbor", "is_table": True},
    {"name": "ospfNbrPriority", "oid": "1.3.6.1.2.1.14.10.1.5", "module": "OSPF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Priority of neighbor in Designated Router election", "is_table": True},
    {"name": "ospfNbrState", "oid": "1.3.6.1.2.1.14.10.1.6", "module": "OSPF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "OSPF neighbor state: 1=down, 2=attempt, 3=init, 4=2Way, 5=exStart, 6=exchange, 7=loading, 8=full", "is_table": True},
    {"name": "ospfNbrEvents", "oid": "1.3.6.1.2.1.14.10.1.7", "module": "OSPF-MIB", "type": "Counter32", "vendor": "RFC", "desc": "Number of state transitions of this OSPF neighbor", "is_table": True},
    {"name": "ospfNbrLsRetransQLen", "oid": "1.3.6.1.2.1.14.10.1.8", "module": "OSPF-MIB", "type": "Gauge32", "vendor": "RFC", "desc": "Length of LSA retransmission queue for neighbor", "is_table": True},
    {"name": "ospfIfIpAddress", "oid": "1.3.6.1.2.1.14.7.1.1", "module": "OSPF-MIB", "type": "IpAddress", "vendor": "RFC", "desc": "IP address of this OSPF interface", "is_table": True},
    {"name": "ospfIfAreaId", "oid": "1.3.6.1.2.1.14.7.1.3", "module": "OSPF-MIB", "type": "IpAddress", "vendor": "RFC", "desc": "OSPF Area to which interface connects", "is_table": True},
    {"name": "ospfIfType", "oid": "1.3.6.1.2.1.14.7.1.4", "module": "OSPF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Interface type: 1=broadcast, 2=nbma, 3=pointToPoint", "is_table": True},
    {"name": "ospfIfAdminStat", "oid": "1.3.6.1.2.1.14.7.1.5", "module": "OSPF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Administrative status of OSPF interface", "is_table": True},
    {"name": "ospfIfState", "oid": "1.3.6.1.2.1.14.7.1.12", "module": "OSPF-MIB", "type": "Integer32", "vendor": "RFC", "desc": "OSPF interface state: 1=down, 2=loopback, 3=waiting, 4=pointToPoint, 5=drOther, 6=backupDesignatedRouter, 7=designatedRouter", "is_table": True},
    {"name": "ospfIfDesignatedRouter", "oid": "1.3.6.1.2.1.14.7.1.13", "module": "OSPF-MIB", "type": "IpAddress", "vendor": "RFC", "desc": "IP address of Designated Router for interface", "is_table": True},
    {"name": "ospfIfBackupDesignatedRouter", "oid": "1.3.6.1.2.1.14.7.1.14", "module": "OSPF-MIB", "type": "IpAddress", "vendor": "RFC", "desc": "IP address of Backup Designated Router for interface", "is_table": True},

    # ---------------------------------------------------------------------
    # 8. ENTITY-MIB (RFC 6933 / RFC 2737) - 20 MIBs
    # ---------------------------------------------------------------------
    {"name": "entPhysicalIndex", "oid": "1.3.6.1.2.1.47.1.1.1.1.1", "module": "ENTITY-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Unique index of physical hardware component", "is_table": True},
    {"name": "entPhysicalDescr", "oid": "1.3.6.1.2.1.47.1.1.1.1.2", "module": "ENTITY-MIB", "type": "OctetString", "vendor": "RFC", "desc": "Textual description of physical entity (e.g. Supervisor 4)", "is_table": True},
    {"name": "entPhysicalVendorType", "oid": "1.3.6.1.2.1.47.1.1.1.1.3", "module": "ENTITY-MIB", "type": "OctetString", "vendor": "RFC", "desc": "Vendor specific hardware identification OID", "is_table": True},
    {"name": "entPhysicalContainedIn", "oid": "1.3.6.1.2.1.47.1.1.1.1.4", "module": "ENTITY-MIB", "type": "Integer32", "vendor": "RFC", "desc": "entPhysicalIndex of parent container component", "is_table": True},
    {"name": "entPhysicalClass", "oid": "1.3.6.1.2.1.47.1.1.1.1.5", "module": "ENTITY-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Physical class: 3=chassis, 6=powerSupply, 7=fan, 9=module, 10=port", "is_table": True},
    {"name": "entPhysicalParentRelPos", "oid": "1.3.6.1.2.1.47.1.1.1.1.6", "module": "ENTITY-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Relative position within parent hardware container", "is_table": True},
    {"name": "entPhysicalName", "oid": "1.3.6.1.2.1.47.1.1.1.1.7", "module": "ENTITY-MIB", "type": "OctetString", "vendor": "RFC", "desc": "Textual name of physical entity", "is_table": True},
    {"name": "entPhysicalHardwareRev", "oid": "1.3.6.1.2.1.47.1.1.1.1.8", "module": "ENTITY-MIB", "type": "OctetString", "vendor": "RFC", "desc": "Hardware revision level string", "is_table": True},
    {"name": "entPhysicalFirmwareRev", "oid": "1.3.6.1.2.1.47.1.1.1.1.9", "module": "ENTITY-MIB", "type": "OctetString", "vendor": "RFC", "desc": "Firmware revision level string", "is_table": True},
    {"name": "entPhysicalSoftwareRev", "oid": "1.3.6.1.2.1.47.1.1.1.1.10", "module": "ENTITY-MIB", "type": "OctetString", "vendor": "RFC", "desc": "Software revision level string", "is_table": True},
    {"name": "entPhysicalSerialNum", "oid": "1.3.6.1.2.1.47.1.1.1.1.11", "module": "ENTITY-MIB", "type": "OctetString", "vendor": "RFC", "desc": "Vendor specific serial number string", "is_table": True},
    {"name": "entPhysicalMfgName", "oid": "1.3.6.1.2.1.47.1.1.1.1.12", "module": "ENTITY-MIB", "type": "OctetString", "vendor": "RFC", "desc": "Name of manufacturer of this physical component", "is_table": True},
    {"name": "entPhysicalModelName", "oid": "1.3.6.1.2.1.47.1.1.1.1.13", "module": "ENTITY-MIB", "type": "OctetString", "vendor": "RFC", "desc": "Vendor specific model name string", "is_table": True},
    {"name": "entPhysicalAlias", "oid": "1.3.6.1.2.1.47.1.1.1.1.14", "module": "ENTITY-MIB", "type": "OctetString", "vendor": "RFC", "desc": "User configured alias for physical component", "is_table": True},
    {"name": "entPhysicalAssetID", "oid": "1.3.6.1.2.1.47.1.1.1.1.15", "module": "ENTITY-MIB", "type": "OctetString", "vendor": "RFC", "desc": "Asset tracking identifier string", "is_table": True},
    {"name": "entPhysicalIsFRU", "oid": "1.3.6.1.2.1.47.1.1.1.1.16", "module": "ENTITY-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Whether field replaceable unit: 1=true, 2=false", "is_table": True},
    {"name": "entPhysicalMfgDate", "oid": "1.3.6.1.2.1.47.1.1.1.1.17", "module": "ENTITY-MIB", "type": "OctetString", "vendor": "RFC", "desc": "Manufacturing date string in DateAndTime format", "is_table": True},
    {"name": "entPhysicalUris", "oid": "1.3.6.1.2.1.47.1.1.1.1.18", "module": "ENTITY-MIB", "type": "OctetString", "vendor": "RFC", "desc": "URIs providing more info on physical component", "is_table": True},
    {"name": "entLastStatusChange", "oid": "1.3.6.1.2.1.47.1.4.1.0", "module": "ENTITY-MIB", "type": "TimeTicks", "vendor": "RFC", "desc": "sysUpTime when any physical table entry changed", "is_table": False},
    {"name": "entPhysicalContainsTable", "oid": "1.3.6.1.2.1.47.1.3.3.1.1", "module": "ENTITY-MIB", "type": "Integer32", "vendor": "RFC", "desc": "Mapping of container to contained physical entities", "is_table": True},

    # ---------------------------------------------------------------------
    # 9. CISCO-PROCESS-MIB - 20 MIBs
    # ---------------------------------------------------------------------
    {"name": "cpmCPUTotalIndex", "oid": "1.3.6.1.4.1.9.9.109.1.1.1.1.1", "module": "CISCO-PROCESS-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "Index of CPU instance", "is_table": True},
    {"name": "cpmCPUTotalPhysicalIndex", "oid": "1.3.6.1.4.1.9.9.109.1.1.1.1.2", "module": "CISCO-PROCESS-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "entPhysicalIndex of corresponding physical entity", "is_table": True},
    {"name": "cpmCPUTotal5sec", "oid": "1.3.6.1.4.1.9.9.109.1.1.1.1.3", "module": "CISCO-PROCESS-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "CPU utilization percentage over last 5 seconds", "is_table": True},
    {"name": "cpmCPUTotal1min", "oid": "1.3.6.1.4.1.9.9.109.1.1.1.1.4", "module": "CISCO-PROCESS-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "CPU utilization percentage over last 1 minute", "is_table": True},
    {"name": "cpmCPUTotal5min", "oid": "1.3.6.1.4.1.9.9.109.1.1.1.1.5", "module": "CISCO-PROCESS-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "CPU utilization percentage over last 5 minutes", "is_table": True},
    {"name": "cpmCPUTotal5secRev", "oid": "1.3.6.1.4.1.9.9.109.1.1.1.1.6", "module": "CISCO-PROCESS-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "Accurate revised CPU load in percent over last 5 seconds", "is_table": True},
    {"name": "cpmCPUTotal1minRev", "oid": "1.3.6.1.4.1.9.9.109.1.1.1.1.7", "module": "CISCO-PROCESS-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "Accurate revised CPU load in percent over last 1 minute", "is_table": True},
    {"name": "cpmCPUTotal5minRev", "oid": "1.3.6.1.4.1.9.9.109.1.1.1.1.8", "module": "CISCO-PROCESS-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "Accurate revised CPU load in percent over last 5 minutes", "is_table": True},
    {"name": "cpmCPUMonInterval", "oid": "1.3.6.1.4.1.9.9.109.1.1.1.1.9", "module": "CISCO-PROCESS-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "Sampling interval duration in seconds", "is_table": True},
    {"name": "cpmCPUTotalMonIntervalValue", "oid": "1.3.6.1.4.1.9.9.109.1.1.1.1.10", "module": "CISCO-PROCESS-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "CPU load percentage in monitoring interval", "is_table": True},
    {"name": "cpmCPUInterruptMonIntervalValue", "oid": "1.3.6.1.4.1.9.9.109.1.1.1.1.11", "module": "CISCO-PROCESS-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "CPU interrupt percentage in monitoring interval", "is_table": True},
    {"name": "cpmCPUCoreIndex", "oid": "1.3.6.1.4.1.9.9.109.1.1.2.1.1", "module": "CISCO-PROCESS-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "Physical processor core index", "is_table": True},
    {"name": "cpmCPUCore5sec", "oid": "1.3.6.1.4.1.9.9.109.1.1.2.1.2", "module": "CISCO-PROCESS-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "Core CPU load percentage over 5 seconds", "is_table": True},
    {"name": "cpmCPUCore1min", "oid": "1.3.6.1.4.1.9.9.109.1.1.2.1.3", "module": "CISCO-PROCESS-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "Core CPU load percentage over 1 minute", "is_table": True},
    {"name": "cpmCPUCore5min", "oid": "1.3.6.1.4.1.9.9.109.1.1.2.1.4", "module": "CISCO-PROCESS-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "Core CPU load percentage over 5 minutes", "is_table": True},
    {"name": "cpmProcessPID", "oid": "1.3.6.1.4.1.9.9.109.1.2.1.1.1", "module": "CISCO-PROCESS-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "IOS process identifier (PID)", "is_table": True},
    {"name": "cpmProcessName", "oid": "1.3.6.1.4.1.9.9.109.1.2.1.1.2", "module": "CISCO-PROCESS-MIB", "type": "OctetString", "vendor": "Cisco", "desc": "Process name (e.g. BGP Router, IP Input)", "is_table": True},
    {"name": "cpmProcessAverageUSecs", "oid": "1.3.6.1.4.1.9.9.109.1.2.1.1.4", "module": "CISCO-PROCESS-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "Average elapsed CPU microseconds per invocation", "is_table": True},
    {"name": "cpmProcessTimeCreated", "oid": "1.3.6.1.4.1.9.9.109.1.2.1.1.5", "module": "CISCO-PROCESS-MIB", "type": "TimeTicks", "vendor": "Cisco", "desc": "sysUpTime when this process was instantiated", "is_table": True},
    {"name": "cpmProcessType", "oid": "1.3.6.1.4.1.9.9.109.1.2.1.1.10", "module": "CISCO-PROCESS-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "Process type: 1=posix, 2=ios_process", "is_table": True},

    # ---------------------------------------------------------------------
    # 10. CISCO-MEMORY-POOL-MIB - 15 MIBs
    # ---------------------------------------------------------------------
    {"name": "ciscoMemoryPoolType", "oid": "1.3.6.1.4.1.9.9.48.1.1.1.1", "module": "CISCO-MEMORY-POOL-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "Memory pool type: 1=processor, 2=io, 3=pci, 4=fast", "is_table": True},
    {"name": "ciscoMemoryPoolName", "oid": "1.3.6.1.4.1.9.9.48.1.1.1.2", "module": "CISCO-MEMORY-POOL-MIB", "type": "OctetString", "vendor": "Cisco", "desc": "Textual name of memory pool (e.g. Processor, I/O)", "is_table": True},
    {"name": "ciscoMemoryPoolAlternate", "oid": "1.3.6.1.4.1.9.9.48.1.1.1.3", "module": "CISCO-MEMORY-POOL-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "Type of alternate memory pool if this pool exhausts", "is_table": True},
    {"name": "ciscoMemoryPoolValid", "oid": "1.3.6.1.4.1.9.9.48.1.1.1.4", "module": "CISCO-MEMORY-POOL-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "1=pool is valid and usable, 2=invalid", "is_table": True},
    {"name": "ciscoMemoryPoolUsed", "oid": "1.3.6.1.4.1.9.9.48.1.1.1.5", "module": "CISCO-MEMORY-POOL-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "Bytes of memory allocated and currently in use", "is_table": True},
    {"name": "ciscoMemoryPoolFree", "oid": "1.3.6.1.4.1.9.9.48.1.1.1.6", "module": "CISCO-MEMORY-POOL-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "Bytes of memory unallocated and free for use", "is_table": True},
    {"name": "ciscoMemoryPoolLargestFree", "oid": "1.3.6.1.4.1.9.9.48.1.1.1.7", "module": "CISCO-MEMORY-POOL-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "Size in bytes of largest contiguous free chunk (fragmentation indicator)", "is_table": True},
    {"name": "ciscoMemoryPoolHCUsed", "oid": "1.3.6.1.4.1.9.9.48.1.1.1.8", "module": "CISCO-MEMORY-POOL-MIB", "type": "Counter64", "vendor": "Cisco", "desc": "64-bit high capacity bytes of used memory", "is_table": True},
    {"name": "ciscoMemoryPoolHCFree", "oid": "1.3.6.1.4.1.9.9.48.1.1.1.9", "module": "CISCO-MEMORY-POOL-MIB", "type": "Counter64", "vendor": "Cisco", "desc": "64-bit high capacity bytes of free memory", "is_table": True},
    {"name": "ciscoMemoryPoolHCLargestFree", "oid": "1.3.6.1.4.1.9.9.48.1.1.1.10", "module": "CISCO-MEMORY-POOL-MIB", "type": "Counter64", "vendor": "Cisco", "desc": "64-bit high capacity size of largest contiguous free memory", "is_table": True},
    {"name": "ciscoMemoryPoolUtilization1Min", "oid": "1.3.6.1.4.1.9.9.48.1.2.1.1.1", "module": "CISCO-MEMORY-POOL-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "Memory utilization percentage averaged over 1 minute", "is_table": True},
    {"name": "ciscoMemoryPoolUtilization5Min", "oid": "1.3.6.1.4.1.9.9.48.1.2.1.1.2", "module": "CISCO-MEMORY-POOL-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "Memory utilization percentage averaged over 5 minutes", "is_table": True},
    {"name": "ciscoMemoryPoolUtilization10Min", "oid": "1.3.6.1.4.1.9.9.48.1.2.1.1.3", "module": "CISCO-MEMORY-POOL-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "Memory utilization percentage averaged over 10 minutes", "is_table": True},
    {"name": "ciscoMemoryPoolAllocFails", "oid": "1.3.6.1.4.1.9.9.48.1.3.1.1.1", "module": "CISCO-MEMORY-POOL-MIB", "type": "Counter32", "vendor": "Cisco", "desc": "Count of times memory allocation failed due to OOM", "is_table": True},
    {"name": "ciscoMemoryPoolAllocSuccess", "oid": "1.3.6.1.4.1.9.9.48.1.3.1.1.2", "module": "CISCO-MEMORY-POOL-MIB", "type": "Counter32", "vendor": "Cisco", "desc": "Count of successful memory allocations", "is_table": True},

    # ---------------------------------------------------------------------
    # 11. CISCO-ENVMON-MIB - 20 MIBs
    # ---------------------------------------------------------------------
    {"name": "ciscoEnvMonVoltageStatusIndex", "oid": "1.3.6.1.4.1.9.9.13.1.2.1.1", "module": "CISCO-ENVMON-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "Voltage test point index", "is_table": True},
    {"name": "ciscoEnvMonVoltageStatusDescr", "oid": "1.3.6.1.4.1.9.9.13.1.2.1.2", "module": "CISCO-ENVMON-MIB", "type": "OctetString", "vendor": "Cisco", "desc": "Description of voltage point (e.g. +12V Core)", "is_table": True},
    {"name": "ciscoEnvMonVoltageStatusValue", "oid": "1.3.6.1.4.1.9.9.13.1.2.1.3", "module": "CISCO-ENVMON-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "Current voltage in millivolts", "is_table": True},
    {"name": "ciscoEnvMonVoltageState", "oid": "1.3.6.1.4.1.9.9.13.1.2.1.7", "module": "CISCO-ENVMON-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "Voltage state: 1=normal, 2=warning, 3=critical, 4=shutdown", "is_table": True},
    {"name": "ciscoEnvMonTemperatureStatusIndex", "oid": "1.3.6.1.4.1.9.9.13.1.3.1.1", "module": "CISCO-ENVMON-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "Temperature sensor index", "is_table": True},
    {"name": "ciscoEnvMonTemperatureStatusDescr", "oid": "1.3.6.1.4.1.9.9.13.1.3.1.2", "module": "CISCO-ENVMON-MIB", "type": "OctetString", "vendor": "Cisco", "desc": "Sensor description (e.g. Ingress ASICs, Exhaust)", "is_table": True},
    {"name": "ciscoEnvMonTemperatureStatusValue", "oid": "1.3.6.1.4.1.9.9.13.1.3.1.3", "module": "CISCO-ENVMON-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "Current temperature in degrees Celsius", "is_table": True},
    {"name": "ciscoEnvMonTemperatureThreshold", "oid": "1.3.6.1.4.1.9.9.13.1.3.1.4", "module": "CISCO-ENVMON-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "Thermal shutdown threshold in degrees Celsius", "is_table": True},
    {"name": "ciscoEnvMonTemperatureState", "oid": "1.3.6.1.4.1.9.9.13.1.3.1.6", "module": "CISCO-ENVMON-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "State: 1=normal, 2=warning, 3=critical, 4=shutdown", "is_table": True},
    {"name": "ciscoEnvMonFanStatusIndex", "oid": "1.3.6.1.4.1.9.9.13.1.4.1.1", "module": "CISCO-ENVMON-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "Cooling fan tray index", "is_table": True},
    {"name": "ciscoEnvMonFanStatusDescr", "oid": "1.3.6.1.4.1.9.9.13.1.4.1.2", "module": "CISCO-ENVMON-MIB", "type": "OctetString", "vendor": "Cisco", "desc": "Cooling fan description (e.g. Fan Tray 1)", "is_table": True},
    {"name": "ciscoEnvMonFanState", "oid": "1.3.6.1.4.1.9.9.13.1.4.1.3", "module": "CISCO-ENVMON-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "Fan state: 1=normal, 2=warning, 3=critical, 4=shutdown, 5=notFunctioning", "is_table": True},
    {"name": "ciscoEnvMonSupplyStatusIndex", "oid": "1.3.6.1.4.1.9.9.13.1.5.1.1", "module": "CISCO-ENVMON-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "Power supply unit index", "is_table": True},
    {"name": "ciscoEnvMonSupplyStatusDescr", "oid": "1.3.6.1.4.1.9.9.13.1.5.1.2", "module": "CISCO-ENVMON-MIB", "type": "OctetString", "vendor": "Cisco", "desc": "Power supply description (e.g. Redundant PSU 2)", "is_table": True},
    {"name": "ciscoEnvMonSupplyState", "oid": "1.3.6.1.4.1.9.9.13.1.5.1.3", "module": "CISCO-ENVMON-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "Supply state: 1=normal, 2=warning, 3=critical, 4=shutdown, 5=notFunctioning", "is_table": True},
    {"name": "ciscoEnvMonSupplySource", "oid": "1.3.6.1.4.1.9.9.13.1.5.1.4", "module": "CISCO-ENVMON-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "Power source: 1=unknown, 2=ac, 3=dc, 4=externalPowerSupply", "is_table": True},
    {"name": "ciscoEnvMonAlarmContactIndex", "oid": "1.3.6.1.4.1.9.9.13.1.6.1.1", "module": "CISCO-ENVMON-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "External alarm contact point index", "is_table": True},
    {"name": "ciscoEnvMonAlarmContactDescr", "oid": "1.3.6.1.4.1.9.9.13.1.6.1.2", "module": "CISCO-ENVMON-MIB", "type": "OctetString", "vendor": "Cisco", "desc": "External contact description (e.g. Door Sensor)", "is_table": True},
    {"name": "ciscoEnvMonAlarmContactSeverity", "oid": "1.3.6.1.4.1.9.9.13.1.6.1.3", "module": "CISCO-ENVMON-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "Contact severity: 1=critical, 2=major, 3=minor", "is_table": True},
    {"name": "ciscoEnvMonAlarmContactState", "oid": "1.3.6.1.4.1.9.9.13.1.6.1.4", "module": "CISCO-ENVMON-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "Contact state: 1=normal, 2=alarmActive", "is_table": True},

    # ---------------------------------------------------------------------
    # 12. CISCO-BGP4-MIB - 15 MIBs
    # ---------------------------------------------------------------------
    {"name": "cbgpPeer2RemoteAs", "oid": "1.3.6.1.4.1.9.9.187.1.2.5.1.11", "module": "CISCO-BGP4-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "4-byte autonomous system number of BGP peer", "is_table": True},
    {"name": "cbgpPeer2State", "oid": "1.3.6.1.4.1.9.9.187.1.2.5.1.3", "module": "CISCO-BGP4-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "BGP peer FSM state: 1=idle, 6=established", "is_table": True},
    {"name": "cbgpPeer2AdminStatus", "oid": "1.3.6.1.4.1.9.9.187.1.2.5.1.4", "module": "CISCO-BGP4-MIB", "type": "Integer32", "vendor": "Cisco", "desc": "Administrative status: 1=stop, 2=start", "is_table": True},
    {"name": "cbgpPeer2PrefixAccepted", "oid": "1.3.6.1.4.1.9.9.187.1.2.8.1.1", "module": "CISCO-BGP4-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "Prefixes accepted from peer after inbound route-maps", "is_table": True},
    {"name": "cbgpPeer2PrefixAdvertised", "oid": "1.3.6.1.4.1.9.9.187.1.2.8.1.2", "module": "CISCO-BGP4-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "Prefixes announced to peer after outbound route-maps", "is_table": True},
    {"name": "cbgpPeer2PrefixSuppressed", "oid": "1.3.6.1.4.1.9.9.187.1.2.8.1.3", "module": "CISCO-BGP4-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "Prefixes suppressed due to route flapping penalties", "is_table": True},
    {"name": "cbgpPeer2PrefixWithdrawn", "oid": "1.3.6.1.4.1.9.9.187.1.2.8.1.4", "module": "CISCO-BGP4-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "Prefixes withdrawn from peer", "is_table": True},
    {"name": "cbgpPeer2InUpdates", "oid": "1.3.6.1.4.1.9.9.187.1.2.5.1.14", "module": "CISCO-BGP4-MIB", "type": "Counter32", "vendor": "Cisco", "desc": "Total UPDATE messages received from peer", "is_table": True},
    {"name": "cbgpPeer2OutUpdates", "oid": "1.3.6.1.4.1.9.9.187.1.2.5.1.15", "module": "CISCO-BGP4-MIB", "type": "Counter32", "vendor": "Cisco", "desc": "Total UPDATE messages sent to peer", "is_table": True},
    {"name": "cbgpPeer2InTotalMessages", "oid": "1.3.6.1.4.1.9.9.187.1.2.5.1.16", "module": "CISCO-BGP4-MIB", "type": "Counter32", "vendor": "Cisco", "desc": "Total messages received from peer", "is_table": True},
    {"name": "cbgpPeer2OutTotalMessages", "oid": "1.3.6.1.4.1.9.9.187.1.2.5.1.17", "module": "CISCO-BGP4-MIB", "type": "Counter32", "vendor": "Cisco", "desc": "Total messages sent to peer", "is_table": True},
    {"name": "cbgpPeer2LastError", "oid": "1.3.6.1.4.1.9.9.187.1.2.5.1.18", "module": "CISCO-BGP4-MIB", "type": "OctetString", "vendor": "Cisco", "desc": "Last BGP error notification bytes", "is_table": True},
    {"name": "cbgpPeer2FsmEstablishedTransitions", "oid": "1.3.6.1.4.1.9.9.187.1.2.5.1.19", "module": "CISCO-BGP4-MIB", "type": "Counter32", "vendor": "Cisco", "desc": "FSM transitions to established", "is_table": True},
    {"name": "cbgpPeer2FsmEstablishedTime", "oid": "1.3.6.1.4.1.9.9.187.1.2.5.1.20", "module": "CISCO-BGP4-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "Seconds in established state", "is_table": True},
    {"name": "cbgpPeer2InUpdateElapsedTime", "oid": "1.3.6.1.4.1.9.9.187.1.2.5.1.25", "module": "CISCO-BGP4-MIB", "type": "Gauge32", "vendor": "Cisco", "desc": "Seconds elapsed since last UPDATE", "is_table": True},

    # ---------------------------------------------------------------------
    # 13. JUNIPER-MIB & JUNIPER-ALARM-MIB - 15 MIBs
    # ---------------------------------------------------------------------
    {"name": "jnxOperatingTemp", "oid": "1.3.6.1.4.1.2636.3.1.13.1.7", "module": "JUNIPER-MIB", "type": "Gauge32", "vendor": "Juniper", "desc": "Temperature in degrees Celsius of Juniper hardware module", "is_table": True},
    {"name": "jnxOperatingCPU", "oid": "1.3.6.1.4.1.2636.3.1.13.1.8", "module": "JUNIPER-MIB", "type": "Gauge32", "vendor": "Juniper", "desc": "CPU utilization percentage (0..100) of Routing Engine", "is_table": True},
    {"name": "jnxOperatingBuffer", "oid": "1.3.6.1.4.1.2636.3.1.13.1.11", "module": "JUNIPER-MIB", "type": "Gauge32", "vendor": "Juniper", "desc": "Packet memory buffer utilization percentage (0..100)", "is_table": True},
    {"name": "jnxOperatingState", "oid": "1.3.6.1.4.1.2636.3.1.13.1.6", "module": "JUNIPER-MIB", "type": "Integer32", "vendor": "Juniper", "desc": "State: 1=unknown, 2=running, 3=ready, 4=reset, 5=runningAtFullSpeed", "is_table": True},
    {"name": "jnxRedundancyState", "oid": "1.3.6.1.4.1.2636.3.1.14.1.5", "module": "JUNIPER-MIB", "type": "Integer32", "vendor": "Juniper", "desc": "Routing Engine redundancy state: 1=unknown, 2=master, 3=backup, 4=disabled", "is_table": True},
    {"name": "jnxOperating1MinLoadAvg", "oid": "1.3.6.1.4.1.2636.3.1.13.1.20", "module": "JUNIPER-MIB", "type": "Gauge32", "vendor": "Juniper", "desc": "1 minute load average of Juniper OS kernel", "is_table": True},
    {"name": "jnxOperating5MinLoadAvg", "oid": "1.3.6.1.4.1.2636.3.1.13.1.21", "module": "JUNIPER-MIB", "type": "Gauge32", "vendor": "Juniper", "desc": "5 minute load average of Juniper OS kernel", "is_table": True},
    {"name": "jnxOperating15MinLoadAvg", "oid": "1.3.6.1.4.1.2636.3.1.13.1.22", "module": "JUNIPER-MIB", "type": "Gauge32", "vendor": "Juniper", "desc": "15 minute load average of Juniper OS kernel", "is_table": True},
    {"name": "jnxAlarmRelayState", "oid": "1.3.6.1.4.1.2636.4.1.2.0", "module": "JUNIPER-ALARM-MIB", "type": "Integer32", "vendor": "Juniper", "desc": "Hardware alarm relay state: 1=other, 2=pass, 3=fail", "is_table": False},
    {"name": "jnxYellowAlarmCount", "oid": "1.3.6.1.4.1.2636.4.1.3.1.1.2", "module": "JUNIPER-ALARM-MIB", "type": "Gauge32", "vendor": "Juniper", "desc": "Count of active minor yellow alarms", "is_table": True},
    {"name": "jnxRedAlarmCount", "oid": "1.3.6.1.4.1.2636.4.1.3.1.1.3", "module": "JUNIPER-ALARM-MIB", "type": "Gauge32", "vendor": "Juniper", "desc": "Count of active major red alarms", "is_table": True},
    {"name": "jnxFruState", "oid": "1.3.6.1.4.1.2636.3.1.15.1.5", "module": "JUNIPER-MIB", "type": "Integer32", "vendor": "Juniper", "desc": "FRU state: 1=unknown, 2=empty, 3=present, 4=ready, 5=online, 6=offline", "is_table": True},
    {"name": "jnxFruType", "oid": "1.3.6.1.4.1.2636.3.1.15.1.6", "module": "JUNIPER-MIB", "type": "Integer32", "vendor": "Juniper", "desc": "FRU type: 1=other, 2=clockGenerator, 3=flexiblePicConcentrator, 4=routingEngine", "is_table": True},
    {"name": "jnxFruSlot", "oid": "1.3.6.1.4.1.2636.3.1.15.1.7", "module": "JUNIPER-MIB", "type": "Integer32", "vendor": "Juniper", "desc": "Physical chassis slot number of FRU", "is_table": True},
    {"name": "jnxCosIfTxPkts", "oid": "1.3.6.1.4.1.2636.3.15.1.1.3", "module": "JUNIPER-MIB", "type": "Counter64", "vendor": "Juniper", "desc": "High capacity Class-of-Service queue transmit packets", "is_table": True},

    # ---------------------------------------------------------------------
    # 14. ARISTA-RESOURCE-MIB & ARISTA-QUEUE-MIB - 15 MIBs
    # ---------------------------------------------------------------------
    {"name": "aristaResourceUtilization", "oid": "1.3.6.1.4.1.30065.3.1.1.1.1.1", "module": "ARISTA-RESOURCE-MIB", "type": "Gauge32", "vendor": "Arista", "desc": "Resource utilization percentage (TCAM, LPM, LEM)", "is_table": True},
    {"name": "aristaResourceType", "oid": "1.3.6.1.4.1.30065.3.1.1.1.1.2", "module": "ARISTA-RESOURCE-MIB", "type": "Integer32", "vendor": "Arista", "desc": "Type of resource: 1=tcam, 2=routingTable, 3=macTable, 4=hostTable", "is_table": True},
    {"name": "aristaResourceDescription", "oid": "1.3.6.1.4.1.30065.3.1.1.1.1.3", "module": "ARISTA-RESOURCE-MIB", "type": "OctetString", "vendor": "Arista", "desc": "Descriptive text of hardware resource pool", "is_table": True},
    {"name": "aristaIngressQueueDropPkts", "oid": "1.3.6.1.4.1.30065.3.2.1.1.1.1", "module": "ARISTA-QUEUE-MIB", "type": "Counter64", "vendor": "Arista", "desc": "Packets dropped in ingress VOQ buffer queue", "is_table": True},
    {"name": "aristaEgressQueueDropPkts", "oid": "1.3.6.1.4.1.30065.3.2.1.1.1.2", "module": "ARISTA-QUEUE-MIB", "type": "Counter64", "vendor": "Arista", "desc": "Packets dropped in egress port buffer queue", "is_table": True},
    {"name": "aristaQueueBufferBytes", "oid": "1.3.6.1.4.1.30065.3.2.1.1.1.3", "module": "ARISTA-QUEUE-MIB", "type": "Gauge32", "vendor": "Arista", "desc": "Total buffer bytes currently consumed by queue", "is_table": True},
    {"name": "aristaVoqMaxBufferBytes", "oid": "1.3.6.1.4.1.30065.3.2.1.1.1.4", "module": "ARISTA-QUEUE-MIB", "type": "Gauge32", "vendor": "Arista", "desc": "Maximum buffer watermark recorded by queue", "is_table": True},
    {"name": "aristaEcnMarkedPkts", "oid": "1.3.6.1.4.1.30065.3.2.1.1.1.5", "module": "ARISTA-QUEUE-MIB", "type": "Counter64", "vendor": "Arista", "desc": "Total packets marked with Explicit Congestion Notification (ECN)", "is_table": True},
    {"name": "aristaPfcPriorityFramesRx", "oid": "1.3.6.1.4.1.30065.3.2.1.1.1.6", "module": "ARISTA-QUEUE-MIB", "type": "Counter64", "vendor": "Arista", "desc": "PFC pause frames received on traffic class", "is_table": True},
    {"name": "aristaPfcPriorityFramesTx", "oid": "1.3.6.1.4.1.30065.3.2.1.1.1.7", "module": "ARISTA-QUEUE-MIB", "type": "Counter64", "vendor": "Arista", "desc": "PFC pause frames transmitted on traffic class", "is_table": True},
    {"name": "aristaInternalTempSensor", "oid": "1.3.6.1.4.1.30065.3.3.1.1.1.2", "module": "ARISTA-RESOURCE-MIB", "type": "Gauge32", "vendor": "Arista", "desc": "Internal ASIC temperature in degrees Celsius", "is_table": True},
    {"name": "aristaPowerSupplyWatts", "oid": "1.3.6.1.4.1.30065.3.3.1.2.1.3", "module": "ARISTA-RESOURCE-MIB", "type": "Gauge32", "vendor": "Arista", "desc": "Current power draw in Watts", "is_table": True},
    {"name": "aristaFanTrayRpm", "oid": "1.3.6.1.4.1.30065.3.3.1.3.1.4", "module": "ARISTA-RESOURCE-MIB", "type": "Gauge32", "vendor": "Arista", "desc": "Current fan rotational speed in RPM", "is_table": True},
    {"name": "aristaAclRuleCount", "oid": "1.3.6.1.4.1.30065.3.4.1.1.1.2", "module": "ARISTA-RESOURCE-MIB", "type": "Gauge32", "vendor": "Arista", "desc": "Number of ACL rules programmed in hardware", "is_table": True},
    {"name": "aristaVlanCount", "oid": "1.3.6.1.4.1.30065.3.4.1.1.1.3", "module": "ARISTA-RESOURCE-MIB", "type": "Gauge32", "vendor": "Arista", "desc": "Total active VLAN interfaces configured", "is_table": True},
]


# =========================================================================
# Trap Catalog
# =========================================================================
TRAP_DEFINITIONS = {
    "linkDown": {
        "oid": "1.3.6.1.6.3.1.1.5.3",
        "enterprise": "1.3.6.1.4.1",
        "severity": "critical",
        "desc": "Signifies that the SNMP entity, acting in an agent role, has detected that the ifOperStatus object for one of its communication links is about to enter the down state.",
        "varbind_keys": ["ifIndex", "ifAdminStatus", "ifOperStatus", "ifDescr"]
    },
    "linkUp": {
        "oid": "1.3.6.1.6.3.1.1.5.4",
        "enterprise": "1.3.6.1.4.1",
        "severity": "informational",
        "desc": "Signifies that the SNMP entity has detected that the ifOperStatus object for one of its communication links has transitioned out of the down state into the up state.",
        "varbind_keys": ["ifIndex", "ifAdminStatus", "ifOperStatus", "ifDescr"]
    },
    "coldStart": {
        "oid": "1.3.6.1.6.3.1.1.5.1",
        "enterprise": "1.3.6.1.4.1",
        "severity": "warning",
        "desc": "Signifies that the sending protocol entity is reinitializing itself such that configuration or protocol state may have been altered.",
        "varbind_keys": ["sysUpTime", "sysDescr"]
    },
    "warmStart": {
        "oid": "1.3.6.1.6.3.1.1.5.2",
        "enterprise": "1.3.6.1.4.1",
        "severity": "informational",
        "desc": "Signifies that the sending protocol entity is reinitializing itself without alteration to configuration.",
        "varbind_keys": ["sysUpTime", "sysDescr"]
    },
    "authenticationFailure": {
        "oid": "1.3.6.1.6.3.1.1.5.5",
        "enterprise": "1.3.6.1.4.1",
        "severity": "warning",
        "desc": "Signifies that the sending protocol entity received a protocol message not properly authenticated.",
        "varbind_keys": ["snmpInBadCommunityNames"]
    },
    "bgpBackwardTransition": {
        "oid": "1.3.6.1.2.1.15.7.2",
        "enterprise": "1.3.6.1.2.1.15",
        "severity": "major",
        "desc": "Generated when the BGP FSM moves from a higher numbered state to a lower numbered state (e.g. ESTABLISHED -> IDLE).",
        "varbind_keys": ["bgpPeerLastError", "bgpPeerState", "bgpPeerRemoteAddr"]
    },
    "bgpEstablished": {
        "oid": "1.3.6.1.2.1.15.7.1",
        "enterprise": "1.3.6.1.2.1.15",
        "severity": "informational",
        "desc": "Generated when the BGP FSM enters the ESTABLISHED state.",
        "varbind_keys": ["bgpPeerLastError", "bgpPeerState", "bgpPeerRemoteAddr"]
    },
    "ospfNbrStateChange": {
        "oid": "1.3.6.1.2.1.14.16.2.2",
        "enterprise": "1.3.6.1.2.1.14",
        "severity": "major",
        "desc": "Signifies that there has been a change in the state of a non-virtual OSPF neighbor.",
        "varbind_keys": ["ospfRouterId", "ospfNbrIpAddr", "ospfNbrState"]
    },
    "ciscoEnvMonTemperatureNotification": {
        "oid": "1.3.6.1.4.1.9.9.13.3.0.2",
        "enterprise": "1.3.6.1.4.1.9.9.13",
        "severity": "critical",
        "desc": "Generated when chassis temperature reaches critical or warning thermal threshold.",
        "varbind_keys": ["ciscoEnvMonTemperatureStatusValue", "ciscoEnvMonTemperatureState", "ciscoEnvMonTemperatureThreshold"]
    },
    "ciscoEnvMonFanNotification": {
        "oid": "1.3.6.1.4.1.9.9.13.3.0.3",
        "enterprise": "1.3.6.1.4.1.9.9.13",
        "severity": "critical",
        "desc": "Generated when cooling fan state changes from normal to warning or shutdown.",
        "varbind_keys": ["ciscoEnvMonFanStatusDescr", "ciscoEnvMonFanState"]
    },
    "ciscoCpuThresholdExceeded": {
        "oid": "1.3.6.1.4.1.9.9.109.2.0.1",
        "enterprise": "1.3.6.1.4.1.9.9.109",
        "severity": "major",
        "desc": "Generated when CPU utilization exceeds the configured high-water threshold.",
        "varbind_keys": ["cpmCPUTotal5minRev", "cpmCPUTotal5secRev"]
    },
    "ciscoMemoryThresholdExceeded": {
        "oid": "1.3.6.1.4.1.9.9.48.2.0.1",
        "enterprise": "1.3.6.1.4.1.9.9.48",
        "severity": "major",
        "desc": "Generated when free pool memory drops below warning threshold.",
        "varbind_keys": ["ciscoMemoryPoolUsed", "ciscoMemoryPoolFree", "ciscoMemoryPoolLargestFree"]
    },
    "jnxPowerSupplyFailure": {
        "oid": "1.3.6.1.4.1.2636.4.1.1",
        "enterprise": "1.3.6.1.4.1.2636",
        "severity": "critical",
        "desc": "Generated when Juniper redundant power supply drops offline or experiences voltage fault.",
        "varbind_keys": ["jnxOperatingState", "jnxRedAlarmCount"]
    },
    "aristaQueueDropExceeded": {
        "oid": "1.3.6.1.4.1.30065.3.1.1",
        "enterprise": "1.3.6.1.4.1.30065",
        "severity": "warning",
        "desc": "Generated when egress buffer queue drop rate exceeds microburst watermark.",
        "varbind_keys": ["aristaEgressQueueDropPkts", "aristaQueueBufferBytes"]
    }
}


class SNMPEngine:
    """
    Carrier-grade SNMP & SC4SNMP Engine for Network Simulation
    """
    def __init__(self):
        self._mibs = [
            SNMPMibDefinition(
                name=m["name"],
                oid=m["oid"],
                mib_module=m["module"],
                data_type=m["type"],
                description=m["desc"],
                is_table=m["is_table"],
                vendor=m["vendor"]
            )
            for m in RAW_MIB_DEFINITIONS
        ]
        self._mibs_by_name = {m.name: m for m in self._mibs}
        self._mibs_by_oid = {m.oid: m for m in self._mibs}

    def list_mibs(
        self,
        vendor: Optional[str] = None,
        module: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[SNMPMibDefinition]:
        results = self._mibs
        if vendor and vendor.lower() != "all":
            results = [m for m in results if m.vendor.lower() == vendor.lower()]
        if module and module.lower() != "all":
            results = [m for m in results if m.mib_module.lower() == module.lower()]
        if search:
            q = search.lower()
            results = [
                m for m in results
                if q in m.name.lower() or q in m.oid or q in m.description.lower()
            ]
        return results

    def simulate_snmp_poll(
        self,
        node: Node,
        module: str = "IF-MIB"
    ) -> List[Dict[str, Any]]:
        """
        Simulate an SC4SNMP poll walk for a given device and MIB module.
        Outputs compliant Splunk HEC metric payloads formatted for cisco_mdt_metrics.
        """
        now = time.time()
        hostname = node.name or node.id
        results = []

        mibs = [m for m in self._mibs if m.mib_module == module or module == "ALL"]
        if not mibs:
            mibs = [m for m in self._mibs if m.mib_module == "IF-MIB"]

        hw = node.hardware
        cpu_val = hw.cpu_utilization_pct if hw else 22.4
        mem_val = hw.memory_utilization_pct if hw else 38.0
        temp_val = hw.temperature_celsius if hw else 42.0

        intf_name = node.interface or "GigabitEthernet0/0/1"
        is_down = (node.status in ("degraded", "breached", "stopped"))

        for m in mibs:
            val = 0.0
            dimensions = {
                "oid": m.oid,
                "mib_module": m.mib_module,
                "vendor": node.vendor or "cisco",
                "device": hostname,
                "host": f"{hostname}.corp.internal",
                "source": "sc4snmp",
                "sourcetype": "sc4snmp:metric"
            }

            # Generate realistic values based on metric name & data type
            if "Octets" in m.name:
                val = float(random.randint(15000000, 99000000))
                dimensions["ifIndex"] = "1"
                dimensions["ifDescr"] = intf_name
            elif "Pkts" in m.name:
                val = float(random.randint(12000, 95000))
                dimensions["ifIndex"] = "1"
                dimensions["ifDescr"] = intf_name
            elif "Errors" in m.name or "Discards" in m.name:
                val = float(random.randint(0, 5) if is_down else 0)
                dimensions["ifIndex"] = "1"
                dimensions["ifDescr"] = intf_name
            elif m.name == "ifOperStatus":
                val = 2.0 if is_down else 1.0  # 1=up, 2=down
                dimensions["ifIndex"] = "1"
                dimensions["ifDescr"] = intf_name
            elif m.name == "ifAdminStatus":
                val = 1.0
                dimensions["ifIndex"] = "1"
                dimensions["ifDescr"] = intf_name
            elif "CPU" in m.name or "cpmCPUTotal" in m.name:
                val = float(cpu_val)
            elif "Memory" in m.name or "ciscoMemoryPoolUsed" in m.name:
                val = float(mem_val * 10485760.0)  # bytes
            elif "ciscoMemoryPoolFree" in m.name:
                val = float((100.0 - mem_val) * 10485760.0)
            elif "Temp" in m.name:
                val = float(temp_val)
            elif "sysUpTime" in m.name:
                val = float(8640000)
            elif "bgpPeerState" in m.name:
                val = 1.0 if is_down else 6.0  # 1=idle, 6=established
                dimensions["bgpPeerRemoteAddr"] = "10.255.0.2"
            elif "ospfNbrState" in m.name:
                val = 1.0 if is_down else 8.0  # 1=down, 8=full
                dimensions["ospfNbrIpAddr"] = "10.255.0.2"
            else:
                val = float(random.randint(1, 100))

            # Strictly compliant Splunk HEC metric event payload:
            hec_metric_event = {
                "time": now,
                "event": "metric",
                "source": "sc4snmp",
                "sourcetype": "sc4snmp:metric",
                "host": f"{hostname}.corp.internal",
                "index": "cisco_mdt_metrics",
                "fields": {
                    f"metric_name:{m.name}": val,
                    "_value": val,
                    **dimensions
                }
            }
            results.append(hec_metric_event)

        return results

    def generate_trap(
        self,
        trap_name: str,
        node: Node,
        varbind_overrides: Optional[Dict[str, Any]] = None
    ) -> SNMPTrapEvent:
        """
        Synthesize an authentic SC4SNMP SNMP Trap Event.
        """
        now = time.time()
        hostname = node.name or node.id
        trap_info = TRAP_DEFINITIONS.get(trap_name, TRAP_DEFINITIONS["linkDown"])
        
        varbinds = {}
        for k in trap_info["varbind_keys"]:
            if k == "ifIndex":
                varbinds["ifIndex"] = 1
            elif k == "ifAdminStatus":
                varbinds["ifAdminStatus"] = 1
            elif k == "ifOperStatus":
                varbinds["ifOperStatus"] = 2 if "Down" in trap_name else 1
            elif k == "ifDescr":
                varbinds["ifDescr"] = node.interface or "GigabitEthernet0/0/1"
            elif k == "sysUpTime":
                varbinds["sysUpTime"] = 8640000
            elif k == "sysDescr":
                varbinds["sysDescr"] = f"{node.vendor or 'Cisco'} Internetwork Operating System Software"
            elif k == "bgpPeerState":
                varbinds["bgpPeerState"] = 1 if "Backward" in trap_name else 6
            elif k == "bgpPeerRemoteAddr":
                varbinds["bgpPeerRemoteAddr"] = "10.255.0.2"
            elif k == "bgpPeerLastError":
                varbinds["bgpPeerLastError"] = "0602" if "Backward" in trap_name else "0000"
            elif k == "ospfNbrState":
                varbinds["ospfNbrState"] = 1 if "Down" in trap_name or "Change" in trap_name else 8
            elif k == "ospfNbrIpAddr":
                varbinds["ospfNbrIpAddr"] = "10.255.0.2"
            elif k == "ospfRouterId":
                varbinds["ospfRouterId"] = node.ip_address or "10.0.1.1"
            elif k == "ciscoEnvMonTemperatureStatusValue":
                varbinds["ciscoEnvMonTemperatureStatusValue"] = 82
            elif k == "ciscoEnvMonTemperatureThreshold":
                varbinds["ciscoEnvMonTemperatureThreshold"] = 75
            elif k == "ciscoEnvMonTemperatureState":
                varbinds["ciscoEnvMonTemperatureState"] = 3  # critical
            elif k == "cpmCPUTotal5minRev":
                varbinds["cpmCPUTotal5minRev"] = 98.4
            elif k == "cpmCPUTotal5secRev":
                varbinds["cpmCPUTotal5secRev"] = 99.1
            elif k == "ciscoMemoryPoolUsed":
                varbinds["ciscoMemoryPoolUsed"] = 950000000
            elif k == "ciscoMemoryPoolFree":
                varbinds["ciscoMemoryPoolFree"] = 1200000
            elif k == "ciscoMemoryPoolLargestFree":
                varbinds["ciscoMemoryPoolLargestFree"] = 4096
            else:
                varbinds[k] = 1

        if varbind_overrides:
            varbinds.update(varbind_overrides)

        trap_event = SNMPTrapEvent(
            timestamp=now,
            host=f"{hostname}.corp.internal",
            trap_oid=trap_info["oid"],
            trap_name=trap_name,
            enterprise=trap_info["enterprise"],
            generic_trap=6,
            specific_trap=1,
            varbinds=varbinds,
            severity=trap_info["severity"],
            sourcetype="sc4snmp:event",
            index="idx_network_ops"
        )
        return trap_event

    def to_sc4snmp_hec_trap_payload(self, trap: SNMPTrapEvent) -> Dict[str, Any]:
        """
        Formats SNMPTrapEvent as an authentic SC4SNMP log event for Splunk HEC.
        """
        raw_event_text = (
            f"SNMP-COMMUNITY=public TRAP-TYPE={trap.trap_name} OID={trap.trap_oid} "
            f"SEVERITY={trap.severity.upper()} "
            + " ".join(f"{k}={v}" for k, v in trap.varbinds.items())
        )
        payload = {
            "time": trap.timestamp,
            "host": trap.host,
            "source": "sc4snmp:trap",
            "sourcetype": trap.sourcetype,
            "index": trap.index,
            "event": {
                "snmp_trap_name": trap.trap_name,
                "snmp_trap_oid": trap.trap_oid,
                "enterprise": trap.enterprise,
                "severity": trap.severity,
                "varbinds": trap.varbinds,
                "raw_event": raw_event_text
            },
            "fields": {
                "snmp_trap_name": trap.trap_name,
                "snmp_trap_oid": trap.trap_oid,
                "severity": trap.severity
            }
        }
        return payload

    def to_rfc5424_syslog_trap(self, trap: SNMPTrapEvent) -> str:
        """
        Format trap as RFC 5424 structured syslog message.
        """
        pri_map = {"informational": 134, "warning": 132, "major": 130, "critical": 129}
        pri = pri_map.get(trap.severity.lower(), 132)
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(trap.timestamp))
        clean_host = trap.host.split(".")[0]
        
        # Structured data element [snmp@41888 trap_name="..." trap_oid="..."]
        varbind_sd = " ".join(f'{k}="{v}"' for k, v in trap.varbinds.items())
        sd = f'[snmpTrap@41888 name="{trap.trap_name}" oid="{trap.trap_oid}" {varbind_sd}]'
        msg = f"SNMP TRAP {trap.trap_name} (OID: {trap.trap_oid}) - Severity: {trap.severity.upper()}"
        return f"<{pri}>1 {now_iso} {clean_host} snmpd - - {sd} {msg}"

    def to_otel_metric_payload(self, metric_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert SC4SNMP metric to OTLP JSON /v1/metrics payload format.
        """
        fields = metric_event.get("fields", {})
        host = metric_event.get("host", "unknown-host")
        now_nano = int(metric_event.get("time", time.time()) * 1e9)

        data_points = []
        for k, v in fields.items():
            if k.startswith("metric_name:") and isinstance(v, (int, float)):
                m_name = k.replace("metric_name:", "")
                data_points.append({
                    "name": m_name,
                    "gauge": {
                        "dataPoints": [{
                            "asDouble": float(v),
                            "timeUnixNano": str(now_nano),
                            "attributes": [
                                {"key": "host.name", "value": {"stringValue": host}},
                                {"key": "service.name", "value": {"stringValue": "sc4snmp-poller"}}
                            ]
                        }]
                    }
                })

        return {
            "resourceMetrics": [{
                "resource": {
                    "attributes": [
                        {"key": "host.name", "value": {"stringValue": host}},
                        {"key": "service.name", "value": {"stringValue": "sc4snmp-poller"}}
                    ]
                },
                "scopeMetrics": [{
                    "scope": {"name": "netspout.sc4snmp", "version": "2.0.0"},
                    "metrics": data_points
                }]
            }]
        }

    def to_telegraf_influx_line(self, metric_event: Dict[str, Any]) -> str:
        """
        Convert SC4SNMP metric to Influx Line Protocol for Telegraf HTTP listener.
        Format: measurement,tag1=val,tag2=val field1=val,field2=val timestamp_nano
        """
        fields = metric_event.get("fields", {})
        host = metric_event.get("host", "unknown-host")
        timestamp_nano = int(metric_event.get("time", time.time()) * 1e9)
        
        tags = [f"host={host}", "source=sc4snmp"]
        if "device" in fields:
            tags.append(f"device={fields['device']}")
        if "vendor" in fields:
            tags.append(f"vendor={fields['vendor']}")
        if "ifDescr" in fields:
            tags.append(f"interface={fields['ifDescr']}")

        field_assignments = []
        for k, v in fields.items():
            if k.startswith("metric_name:") and isinstance(v, (int, float)):
                clean_name = k.replace("metric_name:", "").replace(".", "_")
                field_assignments.append(f"{clean_name}={float(v)}")

        if not field_assignments:
            field_assignments.append("value=1.0")

        return f"sc4snmp_metrics,{','.join(tags)} {','.join(field_assignments)} {timestamp_nano}"


# Global singleton instance
snmp_engine = SNMPEngine()
