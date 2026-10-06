import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from netspout_core.scenario_studio import (
    ClassificationAuthority,
    CorrelationMapping,
    CreationPath,
    CustomSourceDraft,
    FieldClassification,
    PrivacyStatus,
    RedistributionStatus,
    SampleAnalysisRequest,
    SampleProvenance,
    ScenarioStage,
    ScenarioStudioService,
    StudioDraftRequest,
    StudioParameter,
    StudioStateValue,
    StudioTransition,
)
from netspout_core.native_runtime import build_shared_enterprise_state_plan
from netspout_core.unified_generation import UnifiedGenerationService


CLEAN_SAMPLE = json.dumps(
    {
        "event_type": "interface_health",
        "device": "router-01.example",
        "src_ip": "192.0.2.10",
        "loss_pct": 8.0,
        "timestamp": "2026-10-06T18:00:00Z",
    }
)


class ScenarioStudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.generation = UnifiedGenerationService()
        self.service = ScenarioStudioService(
            catalog=self.generation.catalog,
            generation_service=self.generation,
            storage_dir=self.temp.name,
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_starting_home_keeps_creation_paths_separate(self):
        home = self.service.home()
        self.assertEqual(
            [item["id"] for item in home["creation_paths"]],
            [
                "EXISTING_SOURCES",
                "IMPORT_SANITIZED_SAMPLE",
                "CLONE_SCENARIO",
            ],
        )
        self.assertIn("authorized", home["import_notice"])

    def test_clean_documentation_sample_is_analyzed_locally(self):
        result = self.service.analyze_sample(
            SampleAnalysisRequest(
                sample=CLEAN_SAMPLE,
                authorization_acknowledged=True,
            )
        )
        self.assertFalse(result.blocked)
        self.assertEqual(result.privacy_status, PrivacyStatus.SANITIZED)
        self.assertEqual(result.format, "JSON")
        fields = {item.name: item for item in result.fields}
        self.assertEqual(
            fields["event_type"].classification,
            FieldClassification.STRUCTURAL,
        )
        self.assertEqual(
            fields["loss_pct"].classification,
            FieldClassification.MODELED,
        )
        self.assertEqual(
            fields["timestamp"].classification,
            FieldClassification.DERIVED,
        )

    def test_sensitive_sample_is_blocked_without_echoing_values(self):
        synthetic_value = "credential-shaped-" + ("x" * 28)
        sample = "username=fictional-admin password={}".format(synthetic_value)
        result = self.service.analyze_sample(
            SampleAnalysisRequest(
                sample=sample,
                authorization_acknowledged=True,
            )
        )
        self.assertTrue(result.blocked)
        self.assertEqual(
            result.privacy_status, PrivacyStatus.FINDINGS_REQUIRE_REVIEW
        )
        serialized = result.model_dump_json()
        self.assertNotIn(synthetic_value, serialized)
        self.assertIn("[REDACTED]", serialized)
        self.assertTrue(
            all(item.redacted_preview.endswith("[REDACTED]") for item in result.findings)
        )

    def test_scanner_blocks_required_sensitive_identifier_classes(self):
        fixtures = {
            "email": "owner=fictional.user@customer.internal",
            "uuid": "tenant=11111111-2222-4333-8444-555555555555",
            "token": "Authorization: Bearer TESTTOKENVALUE123456789",
            "account": "account_id=fictional-account-123",
            "serial": "serial_number=TESTSERIAL123",
            "mac": "mac=02:00:5e:10:00:01",
            "ipv6": "src=2001:4860:4860::8888",
            "certificate": "-----BEGIN CERTIFICATE-----\\nTEST-ONLY\\n-----END CERTIFICATE-----",
            "private-key": "-----BEGIN PRIVATE KEY-----\\nTEST-ONLY\\n-----END PRIVATE KEY-----",
        }
        for label, sample in fixtures.items():
            with self.subTest(label=label):
                result = self.service.analyze_sample(
                    SampleAnalysisRequest(
                        sample=sample,
                        authorization_acknowledged=True,
                    )
                )
                self.assertTrue(result.blocked)
                self.assertNotIn("TESTTOKENVALUE", result.model_dump_json())

    def test_import_requires_authorization_acknowledgement(self):
        with self.assertRaisesRegex(ValueError, "acknowledgement"):
            SampleAnalysisRequest(
                sample=CLEAN_SAMPLE,
                authorization_acknowledged=False,
            )

    def test_existing_source_pack_saves_reloads_and_stays_private(self):
        draft = self.service.create_draft(
            StudioDraftRequest(
                creation_path=CreationPath.EXISTING_SOURCES,
                source_ids=["ietf-syslog-rfc5424"],
                title="Branch Link Recovery",
            )
        )
        saved = self.service.save_pack(draft)
        self.assertEqual(saved.redistribution, RedistributionStatus.PRIVATE)
        self.assertEqual(saved.maturity.value, "STRUCTURE VALIDATED")
        path = Path(self.temp.name) / "{}.json".format(saved.pack_id)
        self.assertTrue(path.exists())
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

        reloaded_generation = UnifiedGenerationService()
        reloaded = ScenarioStudioService(
            catalog=reloaded_generation.catalog,
            generation_service=reloaded_generation,
            storage_dir=self.temp.name,
        )
        loaded = reloaded.get_pack(saved.pack_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.timeline, saved.timeline)
        self.assertEqual(loaded.relationships, saved.relationships)
        self.assertEqual(loaded.contract_fingerprints, saved.contract_fingerprints)

        self.assertTrue(self.service.delete_pack(saved.pack_id))
        scenario_ids = {
            item["scenario_id"]
            for item in self.generation.capabilities(
                include_runtime_health=False
            )["scenarios"]
        }
        self.assertNotIn(saved.scenario_id, scenario_ids)

    def test_clone_preserves_contract_fingerprint_while_values_change(self):
        clone = self.service.clone_scenario(
            "test-correlated-interface-degradation"
        )
        original = dict(clone.contract_fingerprints)
        clone.timeline[0].title = "Modified modeled baseline"
        clone.entities[0].attributes["address"] = "198.51.100.44"
        report = self.service.validate_pack(clone)
        self.assertTrue(report.valid)
        self.assertEqual(clone.contract_fingerprints, original)

        clone.contract_fingerprints["ietf-snmpv2c-ifmib"] = "tampered"
        blocked = self.service.validate_pack(clone)
        self.assertFalse(blocked.valid)
        self.assertIn(
            "Verified source contracts must remain unchanged.",
            blocked.errors,
        )

    def test_studio_native_plan_reuses_verified_profile_with_studio_identity(self):
        plan = build_shared_enterprise_state_plan(
            run_id="phase6-test-run",
            scenario_id="studio-correlated-private",
            entity_id="cisco-asr9k-pe1",
            seed=606,
            state_profile_scenario_id="test-correlated-interface-degradation",
        )
        self.assertEqual(plan.state_store.scenario_id, "studio-correlated-private")
        self.assertTrue(
            all(
                item.scenario_id == "studio-correlated-private"
                for item in plan.snapshots
            )
        )
        self.assertEqual(
            [
                item.interfaces[plan.interface_id].oper_status
                for item in plan.snapshots
            ],
            ["UP", "DOWN", "DOWN", "UP"],
        )

    def test_custom_source_pack_is_not_vendor_verified(self):
        analysis = self.service.analyze_sample(
            SampleAnalysisRequest(
                sample=CLEAN_SAMPLE,
                authorization_acknowledged=True,
            )
        )
        custom = CustomSourceDraft(
            source_id="private-interface-health",
            display_name="Private Interface Health",
            sanitized_sample=CLEAN_SAMPLE,
            analyzed_fingerprint=analysis.sample_fingerprint,
            privacy_status=PrivacyStatus.SANITIZED,
            provenance=SampleProvenance.LAB_SAMPLE_SANITIZED,
            fields=[
                item.model_copy(
                    update={"authority": ClassificationAuthority.USER_PROVIDED}
                )
                for item in analysis.fields
            ],
            format=analysis.format,
            source_description="Synthetic private test telemetry.",
            netspout_sourcetype="netspout:custom:interface_health",
            netspout_sourcetype_acknowledged=True,
        )
        valid = self.service.validate_custom_source(custom)
        self.assertTrue(valid["valid"])
        self.assertEqual(
            valid["splunk_contract"]["authority"], "NETSPOUT_DEFINED"
        )
        self.assertEqual(
            valid["splunk_contract"]["integration"], "NOT ESTABLISHED"
        )
        self.assertEqual(valid["splunk_contract"]["cim"], "CIM NOT ESTABLISHED")

        draft = self.service.create_draft(
            StudioDraftRequest(
                creation_path=CreationPath.IMPORT_SANITIZED_SAMPLE,
                source_ids=[],
                title="Private Interface Health",
            )
        )
        draft.source_ids = [custom.source_id]
        draft.custom_sources = [custom]
        draft.provenance = custom.provenance
        draft.timeline = [
            StudioTransition(
                transition_id="baseline",
                stage=ScenarioStage.BASELINE,
                offset_seconds=0,
                title="Baseline",
                state_changes=[
                    StudioStateValue(
                        state_key="loss_pct",
                        entity_id=draft.entities[0].entity_id,
                        value=0.1,
                        unit="percent",
                    )
                ],
                source_ids=[custom.source_id],
            ),
            StudioTransition(
                transition_id="incident",
                stage=ScenarioStage.INCIDENT,
                offset_seconds=60,
                title="Loss increase",
                state_changes=[
                    StudioStateValue(
                        state_key="loss_pct",
                        entity_id=draft.entities[0].entity_id,
                        value=8.0,
                        unit="percent",
                    )
                ],
                source_ids=[custom.source_id],
            ),
        ]
        draft.correlation_mappings = [
            CorrelationMapping(
                source_id=custom.source_id,
                source_field="device",
                entity_id=draft.entities[0].entity_id,
                identity_type="device",
            )
        ]
        saved = self.service.save_pack(draft)
        definition, _ = self.service.compile_pack(saved)
        source = definition.sources[0].source
        self.assertNotEqual(source.verification_state.value, "VERIFIED")
        self.assertNotIn("VENDOR_DOCUMENTED", [item.value for item in source.provenance])
        self.assertEqual(
            source.splunk_contract.sourcetypes[0].authority.value,
            "NETSPOUT_DEFINED",
        )

    def test_structural_parameter_fails_closed(self):
        analysis = self.service.analyze_sample(
            SampleAnalysisRequest(
                sample=CLEAN_SAMPLE,
                authorization_acknowledged=True,
            )
        )
        custom = CustomSourceDraft(
            source_id="private-structural-test",
            display_name="Private Structural Test",
            sanitized_sample=CLEAN_SAMPLE,
            analyzed_fingerprint=analysis.sample_fingerprint,
            privacy_status=PrivacyStatus.SANITIZED,
            provenance=SampleProvenance.LAB_SAMPLE_SANITIZED,
            fields=analysis.fields,
            format=analysis.format,
            source_description="Synthetic private test telemetry.",
        )
        draft = self.service.create_draft(
            StudioDraftRequest(
                creation_path=CreationPath.IMPORT_SANITIZED_SAMPLE,
                title="Structural Protection",
            )
        )
        draft.source_ids = [custom.source_id]
        draft.custom_sources = [custom]
        draft.timeline = []
        draft.parameters = [
            StudioParameter(
                parameter_id="event-kind",
                state_key="event_type",
                value_type="string",
                default="different",
            )
        ]
        report = self.service.validate_pack(draft)
        self.assertFalse(report.valid)
        self.assertTrue(
            any("structural field" in item for item in report.errors)
        )

    def test_unsupported_source_and_public_export_fail_closed(self):
        draft = self.service.create_draft(
            StudioDraftRequest(
                creation_path=CreationPath.EXISTING_SOURCES,
                source_ids=["missing-source"],
                title="Blocked Draft",
            )
        )
        report = self.service.validate_pack(draft)
        self.assertFalse(report.valid)

        valid_draft = self.service.create_draft(
            StudioDraftRequest(
                creation_path=CreationPath.EXISTING_SOURCES,
                source_ids=["ietf-syslog-rfc5424"],
                title="Private Export Gate",
            )
        )
        saved = self.service.save_pack(valid_draft)
        gate = self.service.export_gate(saved.pack_id, public=True)
        self.assertFalse(gate["allowed"])
        self.assertTrue(
            any("redistribution" in item for item in gate["blockers"])
        )


if __name__ == "__main__":
    unittest.main()
