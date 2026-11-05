# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/ingestion_profiles.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""Ingestion profiles: how a sourcetype's raw text is framed on its way into Splunk.

Evidence: tests/fixtures/phase7_real_samples/sanitized_real_samples.json (real events from a Splunk instance whose network syslog arrives through SC4S).
A profile is chosen per request and changes ONLY the sourcetypes listed in PROFILES; nothing is stripped or added globally.

  direct  the vendor's own syslog text, exactly as the generator produces it (the default, unchanged behaviour)
  sc4s    the shape observed after Splunk Connect for Syslog:
            cisco:ios          header-less '%FAC-SEV-MNEM: text'; source 'sc4s'; host = the device address from the original header
            cisco:ise:syslog   '<local stamp> <device address> <original stamp> <node> CISE_...' with no <PRI>; source 'sc4s'

Not evidenced, deliberately not produced: the sc4s_* indexed fields (only their names were observed), SC4S timezone handling (the observed local and UTC
stamps differ by the SC4S host's offset; NetSpout renders both in UTC), and any other sourcetype.
"""
import re
from typing import Dict, List, Optional, Tuple

DEFAULT_PROFILE = "direct"
SC4S_SOURCE = "sc4s"
SC4S_DEVICE_IP_BASE = "192.0.2."          # documentation range; the address is metadata, only its position in the line is evidenced

PROFILES: Dict[str, Tuple[str, ...]] = {
    "cisco:ios": ("direct", "sc4s"),
    "cisco:ise:syslog": ("direct", "sc4s"),
}

_IOS_MSG = re.compile(r"(%[A-Z0-9_]+-\d-[A-Z0-9_]+:.*)$", re.S)
_IOS_HEADER_IP = re.compile(r"^(?:<\d{1,3}>)?[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+(\d{1,3}(?:\.\d{1,3}){3})\s")
_ISE_RAW = re.compile(r"^<\d{1,3}>([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+(CISE_.*)$", re.S)


def profiles_for(sourcetype: str) -> Tuple[str, ...]:
    return PROFILES.get(sourcetype, (DEFAULT_PROFILE,))


def validate(sourcetype: str, profile: Optional[str]) -> str:
    p = profile or DEFAULT_PROFILE
    if p not in profiles_for(sourcetype):
        raise ValueError("ingestion profile %r is not supported for %s (supported: %s); no evidence exists for it" % (p, sourcetype, ", ".join(profiles_for(sourcetype))))
    return p


def _device_ip(device_id: str) -> str:
    m = re.search(r"(\d+)$", device_id or "")
    return SC4S_DEVICE_IP_BASE + str(10 + (int(m.group(1)) % 200 if m else 0))


def convert(sourcetype: str, profile: Optional[str], raw: str, device_id: str = "") -> Optional[Tuple[str, Dict[str, str]]]:
    """(raw, metadata) for the profile, or None when this event cannot be expressed in it (never guessed).
    metadata may carry 'hec_source' and 'hec_host'. The direct profile returns the event untouched with no metadata."""
    p = validate(sourcetype, profile)
    if p == DEFAULT_PROFILE:
        return raw, {}
    if sourcetype == "cisco:ios":
        msg = _IOS_MSG.search(raw)
        if not msg:
            return None
        ip = _IOS_HEADER_IP.match(raw)
        return msg.group(1), {"hec_source": SC4S_SOURCE, "hec_host": ip.group(1) if ip else _device_ip(device_id)}
    if sourcetype == "cisco:ise:syslog":
        m = _ISE_RAW.match(raw)
        if not m:
            return None
        stamp, node, rest = m.groups()
        ip = _device_ip(device_id)
        return "%s %s %s %s %s" % (stamp, ip, stamp, node, rest), {"hec_source": SC4S_SOURCE, "hec_host": ip}
    return None


def expressible(sourcetype: str, profile: Optional[str], samples: List[str]) -> List[str]:
    """The samples that can be expressed in the profile (all of them for direct)."""
    p = validate(sourcetype, profile)
    return list(samples) if p == DEFAULT_PROFILE else [s for s in samples if convert(sourcetype, p, s) is not None]


def apply_to_entries(sourcetype: str, profile: Optional[str], entries):
    """Rewrite entries in place for the profile. Every entry must be expressible (callers filter samples with expressible() first)."""
    p = validate(sourcetype, profile)
    if p == DEFAULT_PROFILE:
        return entries
    for e in entries:
        c = convert(sourcetype, p, e.raw_log, e.device_id)
        if c is None:
            raise ValueError("%s event cannot be expressed in the %s profile" % (sourcetype, p))
        e.raw_log, meta = c
        e.ingestion_profile = p
        e.hec_source, e.hec_host = meta.get("hec_source"), meta.get("hec_host")
    return entries
