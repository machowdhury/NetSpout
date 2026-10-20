"""Shared-config request adapter only; no persistent credential registry.

The live TelemetryTransportConfig remains authoritative. Other mutation routes
are deliberately outside this adapter and can still overwrite its results.
"""
import json
from copy import deepcopy
from collections.abc import Mapping

try:
    from .credential_transitions import (
        CREDENTIALS, CredentialUpdateError, legacy_operations, shared_state, transition,
    )
except ImportError:  # Flat packaged modules.
    from credential_transitions import (
        CREDENTIALS, CredentialUpdateError, legacy_operations, shared_state, transition,
    )


def decode_transport_update(body):
    """Reject duplicate JSON keys before normal JSON decoding can discard them."""
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise CredentialUpdateError("Duplicate configuration field")
            result[key] = value
        return result

    try:
        payload = json.loads(body, object_pairs_hook=unique_object)
    except (ValueError, UnicodeError, TypeError):
        raise CredentialUpdateError("Invalid configuration request") from None
    if not isinstance(payload, dict):
        raise CredentialUpdateError("Expected configuration object")
    return payload


def update_shared_transport(current, payload, model_type):
    """Build a validated candidate; callers publish only on success.

    credential_updates is the explicit operation map. Legacy raw fields are
    accepted only here. Mixing raw fields with credential_updates, or supplying
    both HEC spellings, is rejected even if values agree.
    """
    if not isinstance(payload, Mapping):
        raise CredentialUpdateError("Expected configuration object")
    data = dict(payload)
    for canonical, aliases in (
        ('hec_url', ('endpoint', 'hec_endpoint')),
        ('hec_index', ('index', 'default_index')),
    ):
        supplied = [(name, data[name]) for name in (canonical,) + aliases
                    if name in data and data[name] is not None]
        if supplied:
            value = supplied[0][1]
            if any(item != value for _, item in supplied[1:]):
                raise CredentialUpdateError("Conflicting transport aliases")
            data[canonical] = value
        for alias in aliases:
            data.pop(alias, None)
    has_explicit = "credential_updates" in data
    explicit = data.pop("credential_updates", {})
    if not isinstance(explicit, Mapping):
        raise CredentialUpdateError("Expected credential operation map")
    if "token" in data:
        if "hec_token" in data:
            raise CredentialUpdateError("Conflicting HEC token aliases")
        data["hec_token"] = data.pop("token")
    raw = {name: data.pop(name) for name in CREDENTIALS if name in data}
    if raw and has_explicit:
        raise CredentialUpdateError("Conflicting credential updates")
    operations = legacy_operations(raw, allowed_fields=CREDENTIALS)
    operations.update(explicit)

    base = current if current is not None else model_type()
    # Empty existing values represent cleared runtime state, never environment
    # fallback. Snapshot backend attributes rather than public serialization.
    state = transition(shared_state(), operations)
    public = base.dict()
    if any(name not in public for name in data):
        raise CredentialUpdateError("Unknown configuration field")
    public.update(data)
    # Do not let stale stored mirror aliases override a new canonical value in
    # the runtime constructor. Null mirrors are valid and mean absent.
    if 'hec_url' in data:
        public['hec_endpoint'] = None
    if 'hec_index' in data:
        public['default_index'] = None
    try:
        candidate = model_type(**public)
    except (ValueError, TypeError):
        # Framework errors can contain raw input: return only a fixed message.
        raise CredentialUpdateError("Invalid transport configuration") from None
    secrets = {}
    for name in CREDENTIALS:
        if name not in operations or operations[name]["operation"] == "keep":
            # KEEP is not a replacement: do not revalidate existing credentials
            # against a possibly stricter replacement policy.
            secrets[name] = deepcopy(getattr(base, name))
        else:
            value = state.resolve(name)
            secrets[name] = dict(value) if name == "otel_headers" else value
    # Constructor defaults (including environment HEC fallback) must never win
    # over the validated runtime state. Copy does not invoke the constructor.
    return candidate.model_copy(update=secrets)
