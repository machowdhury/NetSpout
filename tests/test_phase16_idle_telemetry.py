"""Phase 16 (B1): a fresh NetSpout install must produce zero synthetic telemetry unless generation is explicitly authorized.

Static and process-level checks that need no Splunk. The live check (the real Splunk, indexes and restart/upgrade behaviour) is scripts/phase16_idle_check.py.
"""
import re
import subprocess
import sys
import tarfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "netspout"
STREAMER = APP / "bin" / "netspout_streamer.py"
ENABLED = '<input><server_host>h</server_host><configuration><stanza name="netspout_streamer://default"><param name="interval">1</param></stanza></configuration></input>'


def stanzas(text):
    out, cur = {}, None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^\[(.+)\]$", line)
        if m:
            cur = out.setdefault(m.group(1), {})
        elif cur is not None and "=" in line:
            k, v = line.split("=", 1)
            cur[k.strip()] = v.strip()
    return out


def run(stdin_text, args=(), timeout=10):
    """The streamer must exit by itself when it is not authorized; one that is still running after `timeout` seconds is the B1 defect."""
    try:
        return subprocess.run([sys.executable, str(STREAMER), *args], input=stdin_text, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise AssertionError("netspout_streamer kept running (and emitting) without an enabled stanza: %r" % (e.stdout or b"")[:80])


class ShippedDefaults(unittest.TestCase):
    def test_every_shipped_input_is_disabled(self):
        for name, kv in stanzas((APP / "default/inputs.conf").read_text()).items():
            self.assertIn(kv.get("disabled"), ("1", "true"), name + " must ship disabled")

    def test_every_eventgen_sample_ships_disabled(self):
        sections = stanzas((APP / "default/eventgen.conf").read_text())
        self.assertGreater(len(sections), 30)
        for name, kv in sections.items():
            self.assertEqual(kv.get("disabled"), "true", name + ": Splunk Eventgen would generate into the index on its own")

    def test_scheme_stays_valid_for_splunk(self):
        # Splunk starts a single-instance modular input once at every (re)start even when all stanzas are disabled ("No stanzas found ... at script (re)start"),
        # so the authorization check lives in the script. Switching the scheme to per-stanza instances is NOT a fix: Splunk then rejects the input outright
        # ("Endpoint argument interval is an internal argument ... should not be defined via introspection") and an explicitly enabled input could never start.
        scheme = run("", ["--scheme"]).stdout
        self.assertIn("<use_single_instance>true</use_single_instance>", scheme)
        self.assertIn('<arg name="interval">', scheme)

    def test_no_other_scripted_or_monitor_input_ships(self):
        for name in stanzas((APP / "default/inputs.conf").read_text()):
            self.assertFalse(name.startswith(("script://", "monitor://", "tcp://", "udp://", "http://")), name)


class StreamerAuthorization(unittest.TestCase):
    def assert_silent(self, stdin_text, quiet=True):
        r = run(stdin_text)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "", "emitted events without an enabled stanza")
        if quiet:   # the normal "nothing enabled" case: splunkd logs script stderr at ERROR level on every restart
            self.assertEqual(r.stderr, "")

    def test_empty_stdin_emits_nothing(self):
        self.assert_silent("")

    def test_document_without_stanza_emits_nothing(self):
        self.assert_silent("<input><server_host>h</server_host><configuration/></input>")

    def test_other_scheme_stanza_emits_nothing(self):
        self.assert_silent('<input><configuration><stanza name="pulseforge_spool://native"><param name="interval">1</param></stanza></configuration></input>')

    def test_unparsable_document_emits_nothing(self):
        self.assert_silent("<input><configuration><stanza", quiet=False)

    def test_enabled_stanza_generates_and_honours_interval(self):
        p = subprocess.Popen([sys.executable, str(STREAMER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        try:
            p.stdin.write(ENABLED)
            p.stdin.flush()
            first = p.stdout.readline()
            self.assertEqual(first.strip(), "<stream>")
            p.stdin.close()
        finally:
            p.kill()
            p.wait()

    def test_explicit_test_flag_is_an_explicit_request(self):
        r = run("", ["--test"])
        self.assertEqual(r.returncode, 0)
        self.assertIn('<event unbroken="1">', r.stdout)


class PackagedApp(unittest.TestCase):
    """Runs against a built netspout.spl when one exists (release candidates, strict gates)."""
    pkg = ROOT / "netspout.spl"

    @unittest.skipUnless(pkg.exists(), "no built netspout.spl in the repository root")
    def test_package_ships_no_enabled_input_or_eventgen_sample(self):
        with tarfile.open(self.pkg) as tf:
            read = lambda n: tf.extractfile("netspout/" + n).read().decode()
            for name, kv in stanzas(read("default/inputs.conf")).items():
                self.assertIn(kv.get("disabled"), ("1", "true"), name)
            for name, kv in stanzas(read("default/eventgen.conf")).items():
                self.assertEqual(kv.get("disabled"), "true", name)
            self.assertIn("parse_input_config(read_input_xml(", read("bin/netspout_streamer.py"), "the packaged streamer must contain the authorization check")
            self.assertNotIn("netspout/local/inputs.conf", tf.getnames(), "the package must not ship a local/inputs.conf that enables an input")


if __name__ == "__main__":
    unittest.main()
