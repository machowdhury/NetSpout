# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/credential_transitions.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""Pure runtime credential transitions; no environment, persistence, or API wiring.

Omitted operations KEEP state. Node INHERIT resolves shared state at use time;
CLEAR always resolves empty, including for SNMP. Callers must never add fallback
credentials after resolution. Clearing here does not revoke a remote credential
or prevent environment initialization after a process restart.
"""

from types import MappingProxyType
from collections.abc import Collection, Mapping


CREDENTIALS = ("hec_token", "otel_headers", "native_snmp_community")


class CredentialUpdateError(ValueError):
    """Validation failure whose message never includes supplied values."""


def _empty(name):
    return MappingProxyType({}) if name == "otel_headers" else ""


def _replacement(name, value):
    if name == "otel_headers":
        if not isinstance(value, Mapping) or not value:
            raise CredentialUpdateError("Replacement requires a nonempty header map")
        headers = {}
        seen = set()
        for key, item in value.items():
            if (not isinstance(key, str) or not key
                    or any(c not in "!#$%&'*+-.^_`|~0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ" for c in key)
                    or key.lower() in seen
                    or not isinstance(item, str) or not item.strip()
                    or any(ord(c) < 32 or ord(c) > 126 for c in item)):
                raise CredentialUpdateError("Invalid replacement header map")
            seen.add(key.lower())
            headers[key] = item
        return MappingProxyType(headers)
    if (not isinstance(value, str) or not value.strip()
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise CredentialUpdateError("Replacement requires a nonempty credential string")
    return value


class CredentialState:
    """Backend-only state, immutable through its supported public interface.

    Use shared_state()/node_state() to construct and transition() to update.
    resolve() is explicit backend access, never a response serializer.
    There is no public serialization of secret values. Immutability is not a
    security boundary against arbitrary in-process Python code.
    """

    __slots__ = ("_node", "_modes", "_values")

    def __init__(self, *, node=False):
        object.__setattr__(self, "_node", node)
        object.__setattr__(self, "_modes", MappingProxyType({
            name: "inherit" if node else "clear" for name in CREDENTIALS
        }))
        object.__setattr__(self, "_values", MappingProxyType({
            name: _empty(name) for name in CREDENTIALS
        }))

    def __setattr__(self, name, value):
        raise AttributeError("CredentialState is immutable")

    def __delattr__(self, name):
        raise AttributeError("CredentialState is immutable")

    def __repr__(self):
        return "CredentialState(node=%r, credentials=<redacted>)" % self._node

    def mode(self, name):
        if name not in CREDENTIALS:
            raise CredentialUpdateError("Unknown credential")
        return self._modes[name]

    def resolve(self, name, *, shared=None):
        """Return immutable effective value; cleared values never inherit."""
        if self.mode(name) == "inherit":
            if not isinstance(shared, CredentialState) or shared._node:
                raise CredentialUpdateError("Inheritance requires shared credential state")
            return shared.resolve(name)
        return self._values[name]


def shared_state():
    """Start empty; trusted initialization can supply explicit REPLACE operations."""
    return CredentialState()


def node_state():
    """New nodes inherit without copying shared secrets. No node registry is kept."""
    return CredentialState(node=True)


def transition(current, updates):
    """Validate a complete operation map, then return new state atomically.

    Each entry is {operation: keep|replace|clear|inherit, value?: ...}.
    Only REPLACE accepts/requires value; INHERIT is node-only. Inputs and current
    state are never mutated, even if a later operation fails validation.
    """
    if not isinstance(current, CredentialState) or not isinstance(updates, Mapping):
        raise CredentialUpdateError("Expected credential state and operation map")
    if any(name not in CREDENTIALS for name in updates):
        raise CredentialUpdateError("Unknown credential")
    modes = dict(current._modes)
    values = dict(current._values)
    for name, spec in updates.items():
        if not isinstance(spec, Mapping):
            raise CredentialUpdateError("Expected explicit credential operation")
        operation = spec.get("operation")
        if not isinstance(operation, str) or operation not in ("keep", "replace", "clear", "inherit"):
            raise CredentialUpdateError("Invalid credential operation")
        expected = {"operation", "value"} if operation == "replace" else {"operation"}
        if set(spec) != expected:
            raise CredentialUpdateError("Invalid or contradictory operation fields")
        if operation == "inherit" and not current._node:
            raise CredentialUpdateError("Shared credentials cannot inherit")
        if operation == "keep":
            continue
        values[name] = _replacement(name, spec["value"]) if operation == "replace" else _empty(name)
        modes[name] = "override" if operation == "replace" else operation
    result = CredentialState(node=current._node)
    object.__setattr__(result, "_modes", MappingProxyType(modes))
    object.__setattr__(result, "_values", MappingProxyType(values))
    return result


def legacy_operations(raw, *, allowed_fields):
    """Normalize explicitly allowlisted legacy fields at a compatibility boundary.

    No routes are implicitly allowed. Blank strings mean KEEP only here. Aliases
    must be normalized by the boundary, which must also reject conflicts with
    explicit operations before combining inputs. This helper validates values
    but never applies state. allowed_fields must be a collection of credential
    names, not a string, binary value, mapping, or one-shot iterator.
    """
    if (not isinstance(allowed_fields, Collection)
            or isinstance(allowed_fields, (str, bytes, bytearray, memoryview, Mapping))):
        raise CredentialUpdateError("Invalid legacy credential allowlist")
    if any(not isinstance(name, str) or name not in CREDENTIALS
           for name in allowed_fields):
        raise CredentialUpdateError("Invalid legacy credential allowlist")
    try:
        allowed = set(allowed_fields)
    except TypeError:
        raise CredentialUpdateError("Invalid legacy credential allowlist") from None
    if (not isinstance(raw, Mapping)
            or any(name not in allowed for name in raw)):
        raise CredentialUpdateError("Legacy credential field is not allowed")
    result = {}
    for name, value in raw.items():
        if isinstance(value, str) and value == "":
            result[name] = {"operation": "keep"}
        else:
            value = _replacement(name, value)
            result[name] = {"operation": "replace", "value": value}
    return result
