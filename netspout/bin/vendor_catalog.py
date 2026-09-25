# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/vendor_catalog.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""
VENDOR CATALOG: Multi-Vendor Telemetry Ecosystem Directory
Sourced directly from the Canonical Catalog (catalog/vendors.json).
Author: Mahamudul Chowdhury <machowdhury@yahoo.com>
"""

from typing import Dict, List, Any, Optional

try:
    from netspout_core.catalog import catalog
except ImportError:
    try:
        from app.catalog import catalog
    except ImportError:
        from catalog import catalog

VENDOR_CATALOG: List[Dict[str, Any]] = catalog.get_legacy_vendor_catalog()


def list_all_vendors() -> List[Dict[str, Any]]:
    return VENDOR_CATALOG


def get_all_vendors() -> List[Dict[str, Any]]:
    return VENDOR_CATALOG


def get_vendor_by_id(vendor_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves vendor details by unique catalog ID or slug."""
    vid_clean = vendor_id.lower().replace("-", "_")
    for v in VENDOR_CATALOG:
        v_id = v["id"].lower().replace("-", "_")
        v_slug = v.get("vendor_slug", "").lower().replace("-", "_")
        if v_id == vid_clean or v_slug == vid_clean or vid_clean in v_id or vid_clean in v_slug:
            return v
    return None


def get_vendor_by_slug(vendor_slug: str) -> Optional[Dict[str, Any]]:
    return next((v for v in VENDOR_CATALOG if v.get("vendor_slug") == vendor_slug), None)


def get_sourcetypes_by_vendor(vendor_id: str) -> List[str]:
    v = get_vendor_by_id(vendor_id)
    return v.get("sourcetypes", []) if v else []


def get_all_sourcetypes() -> List[str]:
    sts = set()
    for v in VENDOR_CATALOG:
        for st in v.get("sourcetypes", []):
            sts.add(st)
    return sorted(list(sts))


VENDOR_ECOSYSTEM = VENDOR_CATALOG
