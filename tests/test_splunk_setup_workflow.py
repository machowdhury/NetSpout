"""Offline native setup tests. No Splunk instance or live HTTP is used."""
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'netspout/bin'))
import datablaster_rest as handler

OLD = 'dummy-legacy-token'
NEW = 'dummy-new-token'
REPLACEMENT = 'dummy-replacement-token'


class NativeSetupTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.env = patch.dict(os.environ, {'SPLUNK_HOME': folder.name})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.app = Path(folder.name, 'app')
        self.app.mkdir()
        self.app_patch = patch.object(handler, 'APP_DIR', str(self.app))
        self.app_patch.start()
        self.addCleanup(self.app_patch.stop)
        self.credentials = {}
        self.calls = []
        self.fail_write = False
        self.fail_read = False
        self.uncertain_write = False
        self.mock = patch.object(handler.rest, 'simpleRequest', self.rest, create=True)
        self.mock.start()
        self.addCleanup(self.mock.stop)
        handler.get_active_run_dir()
        self.path = Path(handler.CONFIG_FILE)

    def rest(self, url, sessionKey='', method='GET', postargs=None, **kwargs):
        self.calls.append((method, url, postargs))
        if 'current-context' in url:
            caps = ['netspout_admin'] if sessionKey == 'admin' else []
            return types.SimpleNamespace(status=200), json.dumps({'entry': [{'content': {'capabilities': caps}}]})
        final = unquote(urlsplit(url).path.rsplit('/', 1)[-1])
        if method == 'POST' and final == 'passwords':
            if self.fail_write:
                return types.SimpleNamespace(status=503), '{}'
            self.credentials[postargs['name']] = postargs['password']
            return types.SimpleNamespace(status=503 if self.uncertain_write else 201), '{}'
        name = final.split(':')[1]
        if name not in self.credentials or (self.fail_read and name.startswith('hec_token_v_')):
            return types.SimpleNamespace(status=404), '{}'
        return types.SimpleNamespace(status=200), json.dumps({'entry': [{'content': {'clear_password': self.credentials[name]}}]})

    def request(self, **fields):
        return handler.execute_request(dict(action='configure_hec', session_key='admin', **fields))

    def current(self):
        return self.path.read_bytes() if self.path.exists() else None

    def assert_secret_free(self, value):
        wire = json.dumps(value)
        for secret in (OLD, NEW, REPLACEMENT):
            self.assertNotIn(secret, wire)
        if self.path.exists():
            for secret in (OLD, NEW, REPLACEMENT):
                self.assertNotIn(secret, self.path.read_text())

    def test_legacy_fixed_entry_read_and_endpoint_only_compatibility(self):
        self.credentials['hec_token'] = OLD
        self.assertEqual(handler.HECCredentialStore('admin').read(), OLD)
        code, response = self.request(hec_url='https://localhost:8088/services/collector')
        self.assertEqual(code, 200)
        self.assertEqual(response['config']['hec_credential_ref'], '')
        self.assertEqual(handler.HECCredentialStore('admin').read(), OLD)
        self.assertFalse([call for call in self.calls if call[0] == 'POST'])
        self.assert_secret_free(response)

    def test_initial_provisioning_and_replacement_preserve_historical_entries(self):
        self.credentials['hec_token'] = OLD
        code, response = self.request(hec_url=handler.DEFAULT_CONFIG['hec_url'], hec_token=NEW)
        self.assertEqual(code, 200)
        first = response['config']['hec_credential_ref']
        self.assertRegex(first, r'^hec_token_v_[0-9a-f]{32}$')
        self.assertEqual(handler.HECCredentialStore('admin').read(), NEW)
        code, response = self.request(hec_token=REPLACEMENT)
        second = response['config']['hec_credential_ref']
        self.assertEqual(code, 200)
        self.assertNotEqual(first, second)
        self.assertEqual(self.credentials['hec_token'], OLD)
        self.assertEqual(self.credentials[first], NEW)
        self.assertEqual(handler.HECCredentialStore('admin').read(), REPLACEMENT)
        self.assertTrue(all(call[1].split('?')[0] == handler.HECCredentialStore.collection
                            for call in self.calls if call[0] == 'POST'))
        self.assert_secret_free(response)

    def test_endpoint_only_update_preserves_versioned_reference(self):
        code, response = self.request(hec_token=NEW)
        first = response['config']['hec_credential_ref']
        posts = len([call for call in self.calls if call[0] == 'POST'])
        code, response = self.request(hec_url='https://localhost:8088/services/collector', hec_token='')
        self.assertEqual(code, 200)
        self.assertEqual(response['config']['hec_credential_ref'], first)
        self.assertEqual(handler.HECCredentialStore('admin').read(), NEW)
        self.assertEqual(len([call for call in self.calls if call[0] == 'POST']), posts)

    def test_validation_failures_leave_disk_and_store_unchanged(self):
        self.request(hec_token=OLD)
        before, credentials = self.current(), dict(self.credentials)
        bad = [dict(hec_url='http://localhost:8088'), dict(hec_url='https://unlisted.invalid:8088'),
               dict(hec_url='https://user:dummy-password@localhost:8088'),
               dict(hec_token=NEW + '\r\nInjected: value'), dict(hec_token=None),
               dict(target_eps=0), dict(ssl_verify='false'), dict(idx_network_ops='bad | search'),
               dict(hec_credential_ref='hec_token_v_' + 'a' * 32), dict(hec_allowed_hosts=['unlisted.invalid'])]
        for fields in bad:
            with self.subTest(fields=fields):
                code, response = self.request(**fields)
                self.assertEqual(code, 400)
                self.assertEqual(response['status'], 'error')
                self.assertEqual(self.current(), before)
                self.assertEqual(self.credentials, credentials)
                self.assert_secret_free(response)

    def test_storage_failure_and_uncertain_staging_never_activate(self):
        self.credentials['hec_token'] = OLD
        self.request(hec_url=handler.DEFAULT_CONFIG['hec_url'])
        before = self.current()
        for field in ('fail_write', 'uncertain_write', 'fail_read'):
            with self.subTest(field=field):
                setattr(self, field, True)
                code, response = self.request(hec_token=NEW)
                setattr(self, field, False)
                self.assertEqual(code, 503)
                self.assertEqual(self.current(), before)
                self.assertEqual(handler.HECCredentialStore('admin').read(), OLD)
                self.assert_secret_free(response)

    def test_failed_publication_preserves_old_active_pair_and_leaves_orphan_inactive(self):
        self.request(hec_token=OLD)
        before = self.current()
        with patch.object(handler.os, 'replace', side_effect=OSError(NEW)):
            code, response = self.request(hec_url='https://localhost:8088/services/collector', hec_token=NEW)
        self.assertEqual(code, 500)
        self.assertEqual(self.current(), before)
        self.assertEqual(handler.HECCredentialStore('admin').read(), OLD)
        self.assertIn(NEW, self.credentials.values())
        self.assertFalse(list(self.path.parent.glob('.hec-config-*')))
        self.assert_secret_free(response)

    def test_stage_does_not_activate_before_atomic_publication(self):
        self.credentials['hec_token'] = OLD
        original_replace = handler.os.replace
        seen = []
        def publish(source, destination):
            self.assertEqual(handler.HECCredentialStore('admin').read(), OLD)
            self.assertIn(NEW, self.credentials.values())
            self.assertIsNone(self.current())
            seen.append(True)
            original_replace(source, destination)
        with patch.object(handler.os, 'replace', side_effect=publish):
            code, _ = self.request(hec_token=NEW)
        self.assertEqual(code, 200)
        self.assertEqual(seen, [True])
        self.assertEqual(handler.HECCredentialStore('admin').read(), NEW)

    def test_initial_failed_publication_never_selects_orphan_after_restart(self):
        with patch.object(handler, '_write_config', side_effect=OSError(NEW)):
            code, response = self.request(hec_token=NEW)
        self.assertEqual(code, 500)
        self.assertIsNone(self.current())
        self.assertIn(NEW, self.credentials.values())
        handler.CONFIG_FILE = handler.RUN_DIR = ''
        self.assertEqual(handler.HECCredentialStore('admin').read(), '')
        self.assert_secret_free(response)

    def test_restart_resolution_does_not_discover_or_fallback_to_inactive_entries(self):
        self.request(hec_token=NEW)
        cfg = json.loads(self.current())
        self.credentials['hec_token'] = OLD
        self.credentials['hec_token_v_' + 'a' * 32] = REPLACEMENT
        handler.RUN_DIR = handler.CONFIG_FILE = ''
        self.assertEqual(handler.HECCredentialStore('admin').read(), NEW)
        del self.credentials[cfg['hec_credential_ref']]
        before = self.current()
        with self.assertRaises(RuntimeError):
            handler.HECCredentialStore('admin').read()
        code, _ = self.request(hec_url='https://localhost:8088/services/collector')
        self.assertEqual(code, 503)
        self.assertEqual(self.current(), before)

    def test_admin_enforcement_initial_missing_token_and_forged_session(self):
        code, _ = handler.execute_request(dict(action='configure_hec', session_key='viewer', hec_token=NEW))
        self.assertEqual(code, 403)
        self.assertFalse(self.credentials)
        code, response = self.request()
        self.assertEqual((code, response['code']), (400, 'token_required'))
        self.assertIsNone(self.current())
        request = {'session': {'authtoken': 'viewer'}, 'payload': json.dumps({
            'action': 'configure_hec', 'session_key': 'admin', 'hec_token': NEW})}
        result = handler.DataBlasterRestHandler().handle(json.dumps(request))
        self.assertEqual(result['status'], 403)
        self.assertFalse(self.credentials)

    def test_execution_uses_active_snapshot_and_ignores_browser_credentials(self):
        self.request(hec_token=NEW)
        cfg = handler.get_stored_config('admin')
        self.request(hec_token=REPLACEMENT)
        with patch.object(handler, 'get_stored_config', return_value=cfg):
            clean = handler.validate_and_sanitize({'action': 'test_hec', 'session_key': 'admin'})
        self.assertEqual(clean['token'], NEW)
        reply = MagicMock(status=200)
        reply.__enter__.return_value = reply
        reply.read.return_value = b'{"code":0}'
        reply.getcode.return_value = 200
        with patch('urllib.request.urlopen', return_value=reply) as send:
            code, response = handler.execute_request(dict(action='test_hec', session_key='admin',
                hec_url='https://unlisted.invalid', hec='https://unlisted.invalid',
                token=OLD, hec_token=OLD, hec_credential_ref='hec_token'))
        self.assertEqual(code, 200)
        self.assertEqual(send.call_args.args[0].full_url, cfg['hec_url'])
        self.assertEqual(send.call_args.args[0].get_header('Authorization'), 'Splunk ' + REPLACEMENT)
        self.assert_secret_free(response)
        before = self.current()
        handler.execute_request(dict(action='save_config', session_key='admin', hec_credential_ref=''))
        self.assertEqual(json.loads(self.current())['hec_credential_ref'], json.loads(before)['hec_credential_ref'])

    def test_secret_free_responses_files_and_failure_logs(self):
        with patch.object(handler.logger, 'warning') as warning:
            code, response = self.request(hec_token=NEW)
            self.assertEqual(code, 200)
            self.assert_secret_free(response)
            code, response = handler.execute_request(dict(action='get_config', session_key='admin'))
            self.assertEqual(code, 200)
            self.assert_secret_free(response)
            self.assert_secret_free(str(warning.call_args_list))
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        for path in self.path.parent.iterdir():
            if path.is_file():
                self.assertNotIn(NEW, path.read_text())


class NativeSetupUITests(unittest.TestCase):
    def test_real_save_javascript_success_rejection_and_uncertain_failure(self):
        program = r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const deny = () => { throw Error('network forbidden'); };
require('net').Socket.prototype.connect = deny;
for (const name of ['http', 'https']) { require(name).request = deny; require(name).get = deny; }
for (const name of ['lookup', 'resolve', 'resolve4', 'resolve6']) require('dns')[name] = deny;
const source = fs.readFileSync(process.argv[1], 'utf8');
async function run(status, code, networkFail, token) {
  let ready = false, sent, cache = {}, elements = {};
  const values = {'cfg-hec-url':'https://localhost:8088/services/collector','cfg-hec-token':token,
    'cfg-ssl-verify':'true','cfg-target-eps':'100','cfg-default-scenario':'full_network_topology',
    'cfg-idx-network':'idx_network_ops','cfg-idx-security':'idx_security_fw',
    'cfg-idx-wireless':'idx_wireless_ops','cfg-idx-perf':'idx_performance_metrics','cfg-idx-mdt':'cisco_mdt_metrics'};
  const element = id => elements[id] || (elements[id] = {value:values[id] || '',type:'password',style:{},disabled:false});
  let chain; chain = new Proxy({}, {get: (obj, prop) => prop === 'length' ? 0 : () => chain});
  const jq = () => chain;
  const context = {window:{location:{pathname:'/en-US/app/netspout/configuration'}},
    document:{cookie:'',getElementById: id => ready ? element(id) : null},
    localStorage:{setItem:(key,value)=>{cache[key]=value;},getItem:()=>null,removeItem:()=>{}},
    setTimeout:()=>0,console,fetch: async (url, init) => {
      sent = JSON.parse(init.body);
      assert.strictEqual(cache.datablaster_config, undefined);
      if (networkFail) throw Error('dummy-token-do-not-display');
      return {ok:status===200,status,json: async()=>({status:status===200?'success':'error',code,
        config:status===200?{hec_url:values['cfg-hec-url'],hec_token_configured:true}:undefined})};
    },require:(deps,fn)=>fn(jq,{})};
  vm.runInNewContext(source, context); ready = true;
  await context.window.datablasterSaveConfig();
  assert.strictEqual(sent.action, 'configure_hec');
  assert.strictEqual(sent.hec_token, token || undefined);
  assert.strictEqual(element('btn-save-config').disabled, false);
  if (status===200 && !networkFail) {
    assert.strictEqual(element('cfg-hec-token').value, '');
    assert.strictEqual(element('cfg-hec-token').disabled, false);
    assert.strictEqual(element('cfg-hec-url').disabled, false);
    assert(element('cfg-status-badge').innerHTML.includes('Configuration Saved'));
    assert(cache.datablaster_config);
  } else {
    assert.strictEqual(cache.datablaster_config, undefined);
    assert(!element('cfg-status-badge').innerHTML.includes('Configuration Saved'));
  }
  assert(!JSON.stringify(cache).includes('dummy-token-do-not-display'));
  assert(!element('cfg-alert-box').innerHTML.includes('dummy-token-do-not-display'));
  if (networkFail) assert(element('cfg-status-badge').innerHTML.includes('unknown'));
}
(async()=>{
  await run(200, '', false, 'dummy-token-do-not-display');
  await run(200, '', false, '');
  for (const [status,code] of [[400,'invalid_setup'],[400,'token_required'],[403,'forbidden'],
      [503,'credential_store_failed'],[500,'publication_failed']])
    await run(status,code,false,'dummy-token-do-not-display');
  await run(0,'',true,'dummy-token-do-not-display');
  process.stdout.write('8 UI scenarios passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
        result = subprocess.run([shutil.which('node'), '-e', program,
            str(ROOT / 'netspout/appserver/static/configuration.js')],
            capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '8 UI scenarios passed')


if __name__ == '__main__':
    from run_sec2b_offline import network_guard
    sys.addaudithook(network_guard)
    unittest.main(verbosity=2, failfast=True)
