"""Standalone SEC-2B tests: dummy values, no application startup or networking."""
import json
import os
import unittest
from unittest.mock import patch

from netspout_core.credential_transitions import (
    CREDENTIALS, CredentialUpdateError, legacy_operations, node_state,
    shared_state, transition,
)


VALUES = {"hec_token": "dummy-hec", "otel_headers": {"Authorization": "dummy-header"},
          "native_snmp_community": "dummy-community"}


def populated():
    return transition(shared_state(), {
        key: {"operation": "replace", "value": value} for key, value in VALUES.items()
    })


class CredentialTransitionsTests(unittest.TestCase):
    def test_shared_keep_replace_clear_for_each_credential(self):
        for name in CREDENTIALS:
            with self.subTest(name=name):
                original = populated()
                self.assertEqual(transition(original, {}).resolve(name), VALUES[name])
                kept = transition(original, {name: {"operation": "keep"}})
                self.assertEqual(kept.resolve(name), VALUES[name])
                cleared = transition(original, {name: {"operation": "clear"}})
                self.assertFalse(cleared.resolve(name))
                self.assertEqual(cleared.mode(name), "clear")
                self.assertFalse(transition(cleared, {}).resolve(name))
                replaced = transition(cleared, {name: {"operation": "replace", "value": VALUES[name]}})
                self.assertEqual(replaced.resolve(name), VALUES[name])
                self.assertEqual(original.resolve(name), VALUES[name])
                for other in CREDENTIALS:
                    if other != name:
                        self.assertEqual(cleared.resolve(other), VALUES[other])

    def test_new_nodes_inherit_live_shared_values_without_copying(self):
        node = node_state()
        shared = populated()
        for name in CREDENTIALS:
            self.assertEqual(node.mode(name), "inherit")
            self.assertEqual(node.resolve(name, shared=shared), VALUES[name])
            cleared = transition(shared, {name: {"operation": "clear"}})
            self.assertFalse(node.resolve(name, shared=cleared))

    def test_node_override_clear_keep_and_return_to_inherit(self):
        shared = populated()
        for name in CREDENTIALS:
            node = transition(node_state(), {name: {"operation": "replace", "value": VALUES[name]}})
            self.assertEqual(node.mode(name), "override")
            self.assertEqual(node.resolve(name, shared=shared_state()), VALUES[name])
            cleared = transition(node, {name: {"operation": "clear"}})
            self.assertFalse(cleared.resolve(name, shared=shared))
            self.assertFalse(transition(cleared, {name: {"operation": "keep"}}).resolve(name, shared=shared))
            inherited = transition(cleared, {name: {"operation": "inherit"}})
            self.assertEqual(inherited.resolve(name, shared=shared), VALUES[name])
            self.assertEqual(node_state().mode(name), "inherit")

    def test_rejects_invalid_or_ambiguous_operations_atomically(self):
        bad_specs = [None, "", {}, {"operation": "unknown"},
                     {"operation": "replace"}, {"operation": "replace", "value": None},
                     {"operation": "replace", "value": ""},
                     {"operation": "replace", "value": "   "},
                     {"operation": "clear", "value": "dummy-secret"},
                     {"operation": "keep", "value": ""},
                     {"operation": "inherit", "value": "dummy-secret"},
                     {"operation": "clear", "extra": True}]
        original = populated()
        for spec in bad_specs:
            with self.subTest(spec=spec):
                with self.assertRaises(CredentialUpdateError):
                    transition(original, {"hec_token": {"operation": "clear"},
                                          "native_snmp_community": spec})
                for name in CREDENTIALS:
                    self.assertEqual(original.resolve(name), VALUES[name])
        for updates in (None, {"unknown": {"operation": "clear"}},
                        {"hec_token": {"operation": "inherit"}}):
            with self.assertRaises(CredentialUpdateError):
                transition(original, updates)

    def test_header_validation_and_input_isolation(self):
        for value in ({}, {"Authorization": ""}, {"Bad Header": "dummy"},
                      {"Authorization": "dummy\r\nInjected: value"},
                      {"A": "dummy", "a": "other"}, {"A": 1}, [], "dummy"):
            with self.assertRaises(CredentialUpdateError):
                transition(shared_state(), {"otel_headers": {"operation": "replace", "value": value}})
        headers = {"Authorization": "dummy-header"}
        spec = {"otel_headers": {"operation": "replace", "value": headers}}
        state = transition(shared_state(), spec)
        self.assertEqual(spec["otel_headers"]["value"], headers)
        headers["Authorization"] = "changed"
        self.assertEqual(state.resolve("otel_headers")["Authorization"], "dummy-header")
        with self.assertRaises(TypeError):
            state.resolve("otel_headers")["Authorization"] = "changed"
        with self.assertRaises(AttributeError):
            state._node = True

    def test_legacy_requires_allowlist_and_blank_keep_is_separate(self):
        for name in CREDENTIALS:
            ops = legacy_operations({name: ""}, allowed_fields=[name])
            self.assertEqual(transition(populated(), ops).resolve(name), VALUES[name])
            ops = legacy_operations({name: VALUES[name]}, allowed_fields=[name])
            self.assertEqual(transition(shared_state(), ops).resolve(name), VALUES[name])
            with self.assertRaises(CredentialUpdateError):
                legacy_operations({name: VALUES[name]}, allowed_fields=[])
            with self.assertRaises(CredentialUpdateError):
                legacy_operations({name: None}, allowed_fields=[name])

    def test_legacy_rejects_malformed_allowlists_without_echoing_values(self):
        secret = "dummy-private-allowlist-value"

        class UnhashableName(str):
            __hash__ = None

        malformed = [None, True, 42, 1.5, secret, "", b"", bytearray(),
                     memoryview(b""), {}, {"hec_token": secret},
                     iter(["hec_token"]), [None], [42], [secret],
                     [[secret]], [{secret: secret}], [{secret}],
                     ["hec_token", [secret]], [UnhashableName("hec_token")]]
        for index, allowlist in enumerate(malformed):
            with self.subTest(case=index):
                with self.assertRaises(CredentialUpdateError) as caught:
                    legacy_operations({}, allowed_fields=allowlist)
                self.assertEqual(str(caught.exception), "Invalid legacy credential allowlist")
                self.assertNotIn(secret, str(caught.exception))
                self.assertTrue(caught.exception.__suppress_context__
                                or caught.exception.__context__ is None)

    def test_legacy_accepts_valid_allowlist_collections(self):
        for allowlist in (["hec_token"], ("hec_token",), {"hec_token"},
                          frozenset({"hec_token"}), {"hec_token": None}.keys()):
            with self.subTest(collection_type=type(allowlist).__name__):
                self.assertEqual(legacy_operations({"hec_token": ""}, allowed_fields=allowlist),
                                 {"hec_token": {"operation": "keep"}})
        for allowlist in ([], (), set(), frozenset()):
            self.assertEqual(legacy_operations({}, allowed_fields=allowlist), {})

    def test_clear_never_reads_or_changes_environment_or_restores_snmp(self):
        with patch.dict(os.environ, {"NETSPOUT_HEC_TOKEN": "dummy-environment"}):
            before = dict(os.environ)
            state = transition(populated(), {name: {"operation": "clear"} for name in CREDENTIALS})
            self.assertEqual(state.resolve("hec_token"), "")
            self.assertEqual(state.resolve("native_snmp_community"), "")
            self.assertEqual(dict(os.environ), before)

    def test_no_default_secret_serialization_or_secret_error_messages(self):
        state = populated()
        for value in VALUES.values():
            if isinstance(value, str):
                self.assertNotIn(value, repr(state))
        with self.assertRaises(TypeError):
            json.dumps(state)
        with self.assertRaises(TypeError):
            vars(state)
        secret = "dummy-secret-that-must-not-be-echoed"
        with self.assertRaises(CredentialUpdateError) as caught:
            transition(state, {"hec_token": {"operation": "clear", "value": secret}})
        self.assertNotIn(secret, str(caught.exception))
        with self.assertRaises(CredentialUpdateError):
            node_state().resolve("hec_token")
        with self.assertRaises(CredentialUpdateError):
            node_state().resolve("hec_token", shared=node_state())


if __name__ == "__main__":
    unittest.main()
