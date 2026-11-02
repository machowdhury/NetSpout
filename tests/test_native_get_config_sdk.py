"""Splunk SDK missing-credential behavior, without live HTTP or secrets."""
import json
import unittest
from unittest.mock import patch
import test_splunk_setup_workflow as fixtures

api = fixtures.handler


class GetConfigSDKTests(unittest.TestCase):
    setUp = fixtures.NativeSetupTests.setUp
    rest = fixtures.NativeSetupTests.rest

    def test_missing_legacy_sdk_exception_returns_unconfigured(self):
        def missing(url, **kwargs):
            if 'storage/passwords' in url:
                raise api._SplunkResourceNotFound('not exposed')
            return self.rest(url, **kwargs)
        with patch.object(api.rest, 'simpleRequest', side_effect=missing):
            self.assertEqual(api.HECCredentialStore('admin').read(''), '')
            code, response = api.execute_request(dict(action='get_config', session_key='admin'))
        self.assertEqual(code, 200)
        self.assertFalse(response['config']['hec_token_configured'])
        self.assertNotIn('not exposed', json.dumps(response))

    def test_missing_active_reference_fails_closed(self):
        reference = 'hec_token_v_' + 'a' * 32
        self.credentials['hec_token'] = 'dummy-legacy-must-not-fallback'
        original = self.rest
        def missing(url, **kwargs):
            if reference in url:
                raise api._SplunkResourceNotFound('not exposed')
            return original(url, **kwargs)
        with patch.object(api.rest, 'simpleRequest', side_effect=missing):
            with self.assertRaisesRegex(RuntimeError, '^Active HEC credential is unavailable$'):
                api.HECCredentialStore('admin').read(reference)

    def test_permissions_and_other_exceptions_remain_secret_safe_errors(self):
        for error in (PermissionError('dummy-sensitive-context'), RuntimeError('dummy-sensitive-context')):
            def unavailable(url, **kwargs):
                if 'storage/passwords' in url:
                    raise error
                return self.rest(url, **kwargs)
            with self.subTest(error=type(error).__name__), patch.object(api.rest, 'simpleRequest', side_effect=unavailable):
                with self.assertRaisesRegex(RuntimeError, '^Splunk credential store request failed$'):
                    api.HECCredentialStore('admin').read('')
                code, response = api.execute_request(dict(action='get_config', session_key='admin'))
                self.assertEqual(code, 400)
                self.assertNotIn('dummy-sensitive-context', json.dumps(response))

    def test_http_404_and_403_remain_distinct(self):
        from types import SimpleNamespace
        for status in (404, 403):
            with self.subTest(status=status), patch.object(api.rest, 'simpleRequest', return_value=(SimpleNamespace(status=status), '{}')):
                if status == 404:
                    self.assertEqual(api.HECCredentialStore('admin').read(''), '')
                else:
                    with self.assertRaisesRegex(RuntimeError, '^Cannot read NetSpout HEC credential$'):
                        api.HECCredentialStore('admin').read('')
