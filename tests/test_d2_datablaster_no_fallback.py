"""Offline regression tests for the Data Blaster no-fallback refusal (F1) and the Stop ESRCH boundaries (F7, D2-5)."""
import errno
import os
import signal
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

BIN = Path(__file__).resolve().parents[1] / 'netspout' / 'bin'
sys.path.insert(0, str(BIN))
import datablaster_rest as handler  # noqa: E402
import run_simulation as runner  # noqa: E402

HEC = 'https://127.0.0.1:8088/services/collector'


class StreamerRefusal(unittest.TestCase):
    def refuse(self, text):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, 'no_events.yml')
        if text is not None:
            Path(path).write_text(text)
        with mock.patch.object(runner, 'resolve_hec_urls', return_value=[HEC]), \
                mock.patch.object(runner, 'get_stored_config', return_value={}), \
                mock.patch('urllib.request.urlopen') as urlopen:
            with self.assertRaises(runner.NoStreamableEventsError) as ctx:
                runner.run_python_streamer(path, HEC, 'fake-token', 10)
        self.assertIn('no_events.yml', str(ctx.exception))
        self.assertNotIn('fake-token', str(ctx.exception))
        urlopen.assert_not_called()

    def test_native_only_config_refused(self):
        self.refuse('generatorWorkers: 1\n')

    def test_missing_file_refused(self):
        self.refuse(None)

    def test_no_builtin_events(self):
        self.assertNotIn('core-sw01.corp.internal', (BIN / 'run_simulation.py').read_text())


class Clock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, s):
        self.now += s


class StopBoundaries(unittest.TestCase):
    def stop(self, sigterm=None, probe='alive', sigkill=None):
        def killpg(pid, sig):
            if sig == signal.SIGTERM and sigterm:
                raise sigterm
            if sig == 0:
                if probe == 'gone':
                    raise ProcessLookupError(errno.ESRCH, 'gone')
                return None
            if sig == signal.SIGKILL and sigkill:
                raise sigkill
        clock = Clock()
        with mock.patch.object(handler, 'get_current_status', return_value={'running': True, 'pid': 99}), \
                mock.patch.object(handler, 'cleanup_stale_run_files'), \
                mock.patch.object(handler, 'PID_FILE', os.path.join(tempfile.mkdtemp(), 'p.pid')), \
                mock.patch.object(handler, 'time', SimpleNamespace(monotonic=clock.monotonic, sleep=clock.sleep)), \
                mock.patch.object(handler.os, 'killpg', side_effect=killpg), \
                mock.patch.object(handler.os, 'waitpid', side_effect=ChildProcessError()):
            return handler.stop_simulation()

    def test_sigkill_esrch_is_success(self):
        self.assertEqual(self.stop(sigkill=ProcessLookupError(errno.ESRCH, 'gone'))['status'], 'success')

    def test_sigterm_esrch_is_success(self):
        self.assertEqual(self.stop(sigterm=ProcessLookupError(errno.ESRCH, 'gone'), probe='gone')['status'], 'success')

    def test_sigkill_eperm_is_error(self):
        self.assertEqual(self.stop(sigkill=PermissionError(errno.EPERM, 'no'))['status'], 'error')


if __name__ == '__main__':
    unittest.main()
