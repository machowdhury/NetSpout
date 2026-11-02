#!/usr/bin/env python3
"""
Fix Palo Alto Networks catalog entries - add missing splunk_sourcetype and vendor_id fields.
Phase 4B P0 task.
"""

import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.absolute()
BACKEND_DIR = BASE_DIR / "backend"
CATALOG_PATH = BACKEND_DIR / "app" / "catalog_data" / "sourcetypes.json"

def fix_paloalto_catalog():
    """Fix incomplete Palo Alto catalog entries."""
    
    print(f"\n{'='*60}")
    print(f"🛠️  FIXING PALO ALTO CATALOG ENTRIES")
    print(f"{'='*60}")
    
    # Load catalog
    with open(CATALOG_PATH, 'r') as f:
        sourcetypes = json.load(f)
    
    print(f"📊 Total sourcetypes before: {len(sourcetypes)}")
    
    # Define Palo Alto fixes
    paloalto_fixes = {
        "paloalto-traffic": {
            "splunk_sourcetype": "paloalto:traffic",
            "vendor_id": "palo_alto_networks",
            "display_name": "Palo Alto Networks Traffic Logs",
            "data_kind": "log",
            "protocol": "syslog",
            "format": "LEEF",
            "default_index": "idx_network_ops",
            "recommended_index": "idx_network_ops",
            "generation_mode": "scenario"
        },
        "paloalto-threat": {
            "splunk_sourcetype": "paloalto:threat",
            "vendor_id": "palo_alto_networks",
            "display_name": "Palo Alto Networks Threat Logs",
            "data_kind": "log",
            "protocol": "syslog",
            "format": "LEEF",
            "default_index": "idx_security",
            "recommended_index": "idx_security",
            "generation_mode": "scenario"
        },
        "paloalto-system": {
            "splunk_sourcetype": "paloalto:system",
            "vendor_id": "palo_alto_networks",
            "display_name": "Palo Alto Networks System Logs",
            "data_kind": "log",
            "protocol": "syslog",
            "format": "syslog",
            "default_index": "idx_internal",
            "recommended_index": "idx_internal",
            "generation_mode": "scenario"
        },
        "paloalto-config": {
            "splunk_sourcetype": "paloalto:config",
            "vendor_id": "palo_alto_networks",
            "display_name": "Palo Alto Networks Configuration Logs",
            "data_kind": "audit",
            "protocol": "syslog",
            "format": "syslog",
            "default_index": "idx_audit",
            "recommended_index": "idx_audit",
            "generation_mode": "scenario"
        },
        "paloalto-userid": {
            "splunk_sourcetype": "paloalto:userid",
            "vendor_id": "palo_alto_networks",
            "display_name": "Palo Alto Networks User-ID Logs",
            "data_kind": "identity",
            "protocol": "syslog",
            "format": "LEEF",
            "default_index": "idx_security",
            "recommended_index": "idx_security",
            "generation_mode": "scenario"
        },
        "paloalto-globalprotect": {
            "splunk_sourcetype": "paloalto:globalprotect",
            "vendor_id": "palo_alto_networks",
            "display_name": "Palo Alto Networks GlobalProtect Logs",
            "data_kind": "vpn",
            "protocol": "syslog",
            "format": "LEEF",
            "default_index": "idx_network_ops",
            "recommended_index": "idx_network_ops",
            "generation_mode": "scenario"
        },
        "paloalto-wildfire": {
            "splunk_sourcetype": "paloalto:wildfire",
            "vendor_id": "palo_alto_networks",
            "display_name": "Palo Alto Networks WildFire Logs",
            "data_kind": "threat_intel",
            "protocol": "syslog",
            "format": "LEEF",
            "default_index": "idx_security",
            "recommended_index": "idx_security",
            "generation_mode": "scenario"
        },
        "paloalto-cortex": {
            "splunk_sourcetype": "paloalto:cortex",
            "vendor_id": "palo_alto_networks",
            "display_name": "Palo Alto Networks Cortex XDR Logs",
            "data_kind": "xdr",
            "protocol": "api",
            "format": "json",
            "default_index": "idx_security",
            "recommended_index": "idx_security",
            "generation_mode": "scenario"
        }
    }
    
    # Apply fixes
    fixed_count = 0
    for st in sourcetypes:
        st_id = st.get('id', '')
        if st_id in paloalto_fixes:
            fixes = paloalto_fixes[st_id]
            for key, value in fixes.items():
                if key not in st or st.get(key) in [None, '', 'N/A']:
                    st[key] = value
                    fixed_count += 1
            print(f"   ✅ Fixed {st_id}")
    
    # Save updated catalog
    with open(CATALOG_PATH, 'w') as f:
        json.dump(sourcetypes, f, indent=2)
    
    print(f"\n📊 Summary:")
    print(f"   Total sourcetypes after: {len(sourcetypes)}")
    print(f"   Fixed fields: {fixed_count}")
    print(f"   Updated file: {CATALOG_PATH}")
    
    # Verify fixes
    print(f"\n🔍 Verification:")
    with open(CATALOG_PATH, 'r') as f:
        updated = json.load(f)
    
    paloalto_entries = [st for st in updated if 'paloalto' in st.get('id', '').lower()]
    print(f"   Palo Alto entries: {len(paloalto_entries)}")
    
    for entry in paloalto_entries[:3]:  # Check first 3
        st_id = entry['id']
        splunk_st = entry.get('splunk_sourcetype', 'MISSING')
        vendor_id = entry.get('vendor_id', 'MISSING')
        print(f"   {st_id}: splunk_sourcetype={splunk_st}, vendor_id={vendor_id}")
    
    return True

def create_sourcetype_resolver():
    """Create canonical sourcetype resolver module."""
    
    print(f"\n{'='*60}")
    print(f"🔧 CREATING CANONICAL SOURCETYPE RESOLVER")
    print(f"{'='*60}")
    
    resolver_code = '''"""
Canonical Sourcetype Resolver for PulseForge.
Provides bidirectional mapping between internal IDs and Splunk sourcetypes.
Phase 4B implementation.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class SourcetypeResolver:
    """Canonical sourcetype identity resolver."""
    
    def __init__(self, catalog_path: Optional[Path] = None):
        """
        Initialize resolver with catalog data.
        
        Args:
            catalog_path: Path to sourcetypes.json catalog file
        """
        if catalog_path is None:
            catalog_path = Path(__file__).parent.parent / "app" / "catalog_data" / "sourcetypes.json"
        
        self.catalog_path = catalog_path
        self._load_catalog()
    
    def _load_catalog(self):
        """Load and index catalog data."""
        try:
            with open(self.catalog_path, 'r') as f:
                self.catalog = json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load catalog from {self.catalog_path}: {e}")
        
        # Build indexes
        self.id_to_entry = {entry['id']: entry for entry in self.catalog}
        self.splunk_st_to_entry = {}
        self.splunk_st_to_id = {}
        
        for entry in self.catalog:
            splunk_st = entry.get('splunk_sourcetype')
            if splunk_st:
                self.splunk_st_to_entry[splunk_st] = entry
                self.splunk_st_to_id[splunk_st] = entry['id']
    
    def resolve_id_to_splunk_st(self, internal_id: str) -> Optional[str]:
        """
        Resolve internal ID to Splunk sourcetype.
        
        Args:
            internal_id: Internal catalog ID (e.g., 'cisco-aci-fault')
            
        Returns:
            Splunk sourcetype value (e.g., 'cisco:aci:fault') or None if not found
        """
        entry = self.id_to_entry.get(internal_id)
        return entry.get('splunk_sourcetype') if entry else None
    
    def resolve_splunk_st_to_id(self, splunk_sourcetype: str) -> Optional[str]:
        """
        Resolve Splunk sourcetype to internal ID.
        
        Args:
            splunk_sourcetype: Splunk sourcetype value (e.g., 'cisco:aci:fault')
            
        Returns:
            Internal catalog ID (e.g., 'cisco-aci-fault') or None if not found
        """
        return self.splunk_st_to_id.get(splunk_sourcetype)
    
    def get_entry_by_id(self, internal_id: str) -> Optional[Dict]:
        """Get full catalog entry by internal ID."""
        return self.id_to_entry.get(internal_id)
    
    def get_entry_by_splunk_st(self, splunk_sourcetype: str) -> Optional[Dict]:
        """Get full catalog entry by Splunk sourcetype."""
        return self.splunk_st_to_entry.get(splunk_sourcetype)
    
    def resolve_vendor(self, identifier: str, is_splunk_st: bool = False) -> Optional[str]:
        """
        Resolve vendor from identifier.
        
        Args:
            identifier: Either internal ID or Splunk sourcetype
            is_splunk_st: True if identifier is Splunk sourcetype
            
        Returns:
            Vendor ID or None if not found
        """
        if is_splunk_st:
            entry = self.get_entry_by_splunk_st(identifier)
        else:
            entry = self.get_entry_by_id(identifier)
        
        return entry.get('vendor_id') if entry else None
    
    def get_aliases(self, identifier: str, is_splunk_st: bool = False) -> List[str]:
        """
        Get all aliases for a sourcetype.
        
        Args:
            identifier: Either internal ID or Splunk sourcetype
            is_splunk_st: True if identifier is Splunk sourcetype
            
        Returns:
            List of alias strings
        """
        if is_splunk_st:
            entry = self.get_entry_by_splunk_st(identifier)
        else:
            entry = self.get_entry_by_id(identifier)
        
        if not entry:
            return []
        
        aliases = entry.get('aliases', [])
        deprecated_aliases = entry.get('deprecated_aliases', [])
        return aliases + deprecated_aliases
    
    def is_active(self, identifier: str, is_splunk_st: bool = False) -> bool:
        """
        Check if sourcetype is active (not deprecated).
        
        Args:
            identifier: Either internal ID or Splunk sourcetype
            is_splunk_st: True if identifier is Splunk sourcetype
            
        Returns:
            True if sourcetype is active
        """
        if is_splunk_st:
            entry = self.get_entry_by_splunk_st(identifier)
        else:
            entry = self.get_entry_by_id(identifier)
        
        if not entry:
            return False
        
        status = entry.get('status', 'unknown')
        return status.lower() in ['active', 'implemented', 'experimental']
    
    def validate_mapping(self, internal_id: str, splunk_sourcetype: str) -> Tuple[bool, str]:
        """
        Validate mapping between internal ID and Splunk sourcetype.
        
        Args:
            internal_id: Internal catalog ID
            splunk_sourcetype: Splunk sourcetype value
            
        Returns:
            Tuple of (is_valid, message)
        """
        entry_by_id = self.get_entry_by_id(internal_id)
        entry_by_st = self.get_entry_by_splunk_st(splunk_sourcetype)
        
        if not entry_by_id:
            return False, f"Internal ID '{internal_id}' not found in catalog"
        
        if not entry_by_st:
            return False, f"Splunk sourcetype '{splunk_sourcetype}' not found in catalog"
        
        # Check if they point to the same entry
        if entry_by_id['id'] != entry_by_st['id']:
            return False, f"ID '{internal_id}' maps to '{entry_by_id['id']}', ST '{splunk_sourcetype}' maps to '{entry_by_st['id']}'"
        
        # Check if mapping matches
        expected_st = entry_by_id.get('splunk_sourcetype')
        if expected_st != splunk_sourcetype:
            return False, f"Expected Splunk sourcetype '{expected_st}', got '{splunk_sourcetype}'"
        
        return True, "Mapping is valid"
    
    def get_all_active_sourcetypes(self) -> List[Dict]:
        """Get all active sourcetype entries."""
        return [entry for entry in self.catalog if self.is_active(entry['id'])]
    
    def get_by_vendor(self, vendor_id: str) -> List[Dict]:
        """Get all sourcetypes for a vendor."""
        return [entry for entry in self.catalog if entry.get('vendor_id') == vendor_id]

# Singleton instance for easy import
_resolver_instance = None

def get_resolver() -> SourcetypeResolver:
    """Get singleton resolver instance."""
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = SourcetypeResolver()
    return _resolver_instance

# Convenience functions
def resolve_to_splunk_st(internal_id: str) -> Optional[str]:
    """Resolve internal ID to Splunk sourcetype (convenience function)."""
    return get_resolver().resolve_id_to_splunk_st(internal_id)

def resolve_to_internal_id(splunk_sourcetype: str) -> Optional[str]:
    """Resolve Splunk sourcetype to internal ID (convenience function)."""
    return get_resolver().resolve_splunk_st_to_id(splunk_sourcetype)

def get_vendor(identifier: str, is_splunk_st: bool = False) -> Optional[str]:
    """Get vendor for identifier (convenience function)."""
    return get_resolver().resolve_vendor(identifier, is_splunk_st)

if __name__ == "__main__":
    # Test the resolver
    resolver = SourcetypeResolver()
    
    # Test cases
    test_cases = [
        ("cisco-aci-fault", "cisco:aci:fault"),
        ("cisco-dc-nexus9k-syslog", "cisco:dc:nexus9k:syslog"),
        ("paloalto-traffic", "paloalto:traffic"),
        ("paloalto-threat", "paloalto:threat"),
    ]
    
    print("🧪 Testing Sourcetype Resolver:")
    print("=" * 60)
    
    for internal_id, expected_st in test_cases:
        resolved_st = resolver.resolve_id_to_splunk_st(internal_id)
        resolved_id = resolver.resolve_splunk_st_to_id(expected_st)
        vendor = resolver.resolve_vendor(internal_id)
        
        if resolved_st == expected_st and resolved_id == internal_id:
            print(f"✅ {internal_id} ↔ {expected_st}: vendor={vendor}")
        else:
            print(f"❌ {internal_id} → {resolved_st} (expected {expected_st})")
            print(f"   {expected_st} → {resolved_id} (expected {internal_id})")
    
    # Show stats
    print(f"\n📊 Resolver Statistics:")
    print(f"   Total catalog entries: {len(resolver.catalog)}")
    print(f"   Active sourcetypes: {len(resolver.get_all_active_sourcetypes())}")
    print(f"   Unique vendors: {len(set(e.get('vendor_id') for e in resolver.catalog if e.get('vendor_id')))}")
'''
    
    resolver_path = BACKEND_DIR / "app" / "sourcetype_resolver.py"
    with open(resolver_path, 'w') as f:
        f.write(resolver_code)
    
    print(f"✅ Created resolver: {resolver_path}")
    print(f"   Includes bidirectional mapping, vendor resolution, validation")
    
    return resolver_path

def main():
    """Main entry point for Phase 4B P0 tasks."""
    print("Starting Phase 4B Priority Zero tasks...")
    
    # 1. Fix Palo Alto catalog entries
    if not fix_paloalto_catalog():
        print("❌ Failed to fix Palo Alto catalog entries")
        return 1
    
    # 2. Create canonical sourcetype resolver
    resolver_path = create_sourcetype_resolver()
    
    print(f"\n{'='*60}")
    print(f"✅ PHASE 4B P0 TASKS COMPLETED")
    print(f"{'='*60}")
    
    print(f"\n🎯 Next steps:")
    print(f"   1. Integrate resolver with scenario runner and validation tools")
    print(f"   2. Update Palo Alto generator to use authentic PAN-OS formats")
    print(f"   3. Test resolver with existing Cisco control run")
    print(f"   4. Fix SNMP OID data_type metadata")
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())