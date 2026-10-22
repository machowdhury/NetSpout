"""Offline display branding and retained Splunk compatibility contracts."""
import ast
import configparser
from pathlib import Path
import re
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
import test_splunk_setup_workflow as fixtures

ROOT = Path(__file__).resolve().parents[1]


class NativeBrandingTests(unittest.TestCase):
    def test_app_identity_and_navigation(self):
        app = configparser.ConfigParser()
        app.read(ROOT / 'netspout/default/app.conf')
        self.assertEqual(app['package']['id'], 'netspout')
        self.assertEqual(app['ui']['label'], 'NetSpout PulseForge')
        self.assertTrue(app['launcher']['description'].startswith('NetSpout PulseForge:'))
        nav = ET.parse(ROOT / 'netspout/default/data/ui/nav/default.xml')
        labels = {e.get('name'): e.get('label') for e in nav.iter('view')}
        for name in ('guided_onboarding', 'configuration', 'datablaster_console', 'help'):
            self.assertIn('PulseForge', labels[name])
        self.assertIn('datablaster_dashboard', labels)
        self.assertIn('netspout_canvas', labels)

    def test_native_visible_branding_and_technical_probe_names(self):
        views = ROOT / 'netspout/default/data/ui/views'
        for name in ('guided_onboarding', 'configuration', 'datablaster_console', 'datablaster_dashboard', 'help'):
            root = ET.parse(views / (name + '.xml')).getroot()
            self.assertIn('NetSpout PulseForge', root.findtext('label'))
            visible = ' '.join(root.itertext())
            visible = re.sub(r'datablaster:(?:preflight|probe)', '', visible)
            self.assertIsNone(re.search(r'data[ -]?blaster', visible, re.I), name)
        onboarding = ET.parse(views / 'guided_onboarding.xml')
        options = {e.get('value'): ''.join(e.itertext()) for e in onboarding.iter('option')}
        for name in ('datablaster:preflight', 'datablaster:probe'):
            self.assertIn(name, options)
            self.assertIn('PulseForge', options[name])
        console = ET.parse(views / 'datablaster_console.xml').getroot()
        self.assertEqual(console.get('script'), 'datablaster_console.js')

    def test_legacy_react_display_and_entry_points(self):
        folder = ROOT / 'netspout/appserver/static'
        html = (folder / 'index.html').read_text()
        self.assertIn('<title>NetSpout PulseForge Console</title>', html)
        self.assertIn('id="datablaster-app-root"', html)
        self.assertIn('src="datablaster_react_app.js"', html)
        js = (folder / 'datablaster_react_app.js').read_text()
        self.assertIn('"NetSpout PulseForge Studio"', js)
        self.assertNotIn('"Network Data Blaster Studio"', js)
        self.assertIn('function DataBlasterApp()', js)
        self.assertIn('"/services/datablaster/execute"', js)
        self.assertIn('"datablaster_hec_url"', js)
        console = (folder / 'datablaster_console.js').read_text()
        for value in ('window.datablasterStopAll', 'window.datablasterLaunchScenario',
                      "'/splunkd/__raw/services/datablaster/execute'", "'/app/netspout/datablaster_console'"):
            self.assertIn(value, console)

    def test_legacy_rest_registration_and_single_handler(self):
        conf = configparser.ConfigParser()
        conf.read(ROOT / 'netspout/default/restmap.conf')
        route = conf['script:datablaster_execution']
        self.assertEqual(route['match'], '/datablaster/execute')
        self.assertEqual(route['script'], 'datablaster_rest.py')
        self.assertEqual(route['handler'], 'datablaster_rest.DataBlasterRestHandler')
        self.assertEqual(route['scripttype'], 'persist')
        self.assertEqual(route['capability'], 'netspout_admin')
        self.assertEqual(route['requireAuthentication'], 'true')
        self.assertEqual(sum(v.get('match') == '/datablaster/execute' for v in conf.values()), 1)
        web = configparser.ConfigParser()
        web.read(ROOT / 'netspout/default/web.conf')
        self.assertEqual(web['expose:datablaster_execution']['pattern'], 'datablaster/execute')
        self.assertTrue((ROOT / 'netspout/bin/datablaster_executor.py').is_file())
        self.assertIsNotNone(fixtures.handler.DataBlasterRestHandler)

    def test_legacy_executor_and_runner_helpers_keep_control_flow(self):
        # Preserve existing helpers while allowing explicitly approved new
        # protocol routing in _main (covered by native destination CLI tests).
        class NormalizeStrings(ast.NodeTransformer):
            def visit_FunctionDef(self, node):
                if node.name == 'prepare_scenario_config':
                    # The approved incident-only materialization branch is
                    # covered by IncidentRebuildCompatibilityTests. Continue
                    # comparing every statement of the legacy rebuild path.
                    node.body = [statement for statement in node.body if not (
                        isinstance(statement, ast.If)
                        and ast.dump(statement.test) == ast.dump(ast.parse(
                            '"pulseforge_incident" in scenario', mode='eval').body))]
                return self.generic_visit(node)
            def visit_Constant(self, node):
                if isinstance(node.value, str):
                    node.value = '<string>'
                return node
            def visit_Name(self, node):
                if node.id == 'runtime_config': node.id = 'get_stored_config'
                return node
            def visit_Call(self, node):
                self.generic_visit(node)
                if isinstance(node.func, ast.Name) and node.func.id == 'hec_request':
                    node.keywords = [k for k in node.keywords if k.arg != 'configuration']
                return node
        # Approved per-run snapshots replace live reads; destination tests verify
        # their contents and lifetime. All other existing helper structure stays.
        for name in ('netspout/bin/run_simulation.py', 'netspout/bin/datablaster_executor.py'):
            baseline = subprocess.run(['git', 'show', 'b3b3ad9:' + name], cwd=ROOT,
                capture_output=True, text=True, check=True, timeout=10).stdout
            old = NormalizeStrings().visit(ast.parse(baseline))
            new = NormalizeStrings().visit(ast.parse((ROOT / name).read_text()))
            if name.endswith('run_simulation.py'):
                current = {node.name: node for node in new.body if isinstance(node, ast.FunctionDef)}
                for node in old.body:
                    if isinstance(node, ast.FunctionDef) and node.name != '_main':
                        self.assertEqual(ast.dump(node), ast.dump(current[node.name]), node.name)
            else:
                self.assertEqual(ast.dump(old), ast.dump(new), name)

    def test_documentation_headings(self):
        for name in ('README.md', 'docs/QUICKSTART.md', 'docs/TROUBLESHOOTING.md', 'docs/LIMITATIONS.md'):
            self.assertTrue((ROOT / name).read_text().startswith('# NetSpout PulseForge'), name)


class NativeBrandingStateTests(unittest.TestCase):
    setUp = fixtures.NativeSetupTests.setUp
    rest = fixtures.NativeSetupTests.rest

    def test_saved_state_names_and_existing_config_remain_compatible(self):
        api = fixtures.handler
        for actual, expected in ((api.CONFIG_FILE, 'datablaster_config.json'),
                                 (api.STATUS_FILE, 'datablaster_status.json'), (api.PID_FILE, 'datablaster.pid')):
            self.assertEqual(Path(actual).name, expected)
        code, _ = api.execute_request(dict(action='configure_hec', session_key='admin', hec_token='dummy-branding-token'))
        self.assertEqual(code, 200)
        code, config = api.execute_request(dict(action='get_config', session_key='admin'))
        self.assertEqual(code, 200)
        self.assertIn('hec_credential_ref', config['config'])
        self.assertNotIn('dummy-branding-token', str(config))
        self.assertEqual(api.HECCredentialStore('admin').read(), 'dummy-branding-token')


if __name__ == '__main__':
    from run_sec2b_offline import network_guard
    sys.addaudithook(network_guard)
    unittest.main(verbosity=2, failfast=True)
