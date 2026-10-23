"""Naming migration compatibility: module identity, CLI delegation and display."""
from pathlib import Path
import os,subprocess,sys,tempfile,unittest
from unittest.mock import patch
import test_splunk_setup_workflow

ROOT=Path(__file__).resolve().parents[1]
class PulseForgeNamingTests(unittest.TestCase):
    def test_executor_imports_share_one_implementation_and_state(self):
        import datablaster_executor as legacy
        import pulseforge_executor as preferred
        self.assertIs(legacy,preferred)
        self.assertIs(legacy.DataBlasterExecutor,preferred.PulseForgeExecutor)
        self.assertEqual(Path(preferred.__file__).name,'pulseforge_executor.py')
        with patch.object(legacy,'APP_DIR','dummy-compat-path'):
            self.assertEqual(preferred.APP_DIR,'dummy-compat-path')
        self.assertIs(legacy.logger,preferred.logger)
        self.assertEqual(len(preferred.logger.handlers),1)

    def test_both_cli_paths_delegate_without_execution(self):
        for filename in ('datablaster_executor.py','pulseforge_executor.py'):
            with tempfile.TemporaryDirectory() as home:
                code="import runpy,sys;sys.path[:0]=['netspout/bin','tests'];from run_sec2b_offline import network_guard;sys.addaudithook(network_guard);sys.argv=['executor','--help'];runpy.run_path("+repr(str(ROOT/'netspout/bin'/filename))+",run_name='__main__')"
                p=subprocess.run([sys.executable,'-B','-c',code],cwd=ROOT,env=dict(os.environ,SPLUNK_HOME=home),capture_output=True,text=True,timeout=15)
                self.assertEqual(p.returncode,0,p.stderr)
                self.assertIn('NetSpout PulseForge Backend CLI',p.stdout)

    def test_conflicting_executor_module_rejected(self):
        code="import sys,types;sys.path[:0]=['netspout/bin','tests'];from run_sec2b_offline import network_guard;sys.addaudithook(network_guard);fake=types.ModuleType('pulseforge_executor');fake.__file__='/wrong/pulseforge_executor.py';sys.modules['pulseforge_executor']=fake\ntry:import datablaster_executor\nexcept ImportError as e:assert str(e)=='Conflicting PulseForge executor module identity'\nelse:raise AssertionError('conflicting module accepted')"
        p=subprocess.run([sys.executable,'-B','-c',code],cwd=ROOT,capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr)

    def test_current_app_links_and_visible_labels(self):
        js=(ROOT/'netspout/appserver/static/datablaster_react_app.js').read_text()
        self.assertNotIn('/app/TA-network-data-blaster/studio_',js)
        self.assertIn('/app/netspout/studio_multivendor_enterprise',js)
        self.assertIn('pathname.includes("/netspout/")',js)
        self.assertIn('"Legacy external engine (unverified)"',js)
        for alias in ('/TA-network-data-blaster/','/network-data-blaster/','/TA-datablaster/'):
            self.assertIn(alias,js)
        xml=(ROOT/'netspout/default/data/ui/views/guided_onboarding.xml').read_text()
        self.assertIn('value="datablaster:preflight">PulseForge Ingestion',xml)
        self.assertNotIn('>datablaster:preflight',xml)

    def test_manifest_app_selection_keeps_legacy_aliases(self):
        code = r"""const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('netspout/appserver/static/datablaster_react_app.js','utf8');
const expression=source.match(/const appName = ([\s\S]*?);/)[1];
for(const [path,expected] of [['/en-US/app/netspout/configuration','netspout'],['/en-US/app/TA-network-data-blaster/configuration','TA-network-data-blaster'],['/en-US/app/network-data-blaster/configuration','network-data-blaster'],['/en-US/app/TA-datablaster/configuration','TA-datablaster'],['/','netspout']]) {
  assert.strictEqual(vm.runInNewContext(expression,{window:{location:{pathname:path}}},{timeout:1000}),expected);
}
"""
        result=subprocess.run(['node','-e',code],cwd=ROOT,capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
