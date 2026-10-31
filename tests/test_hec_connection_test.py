"""HEC connection test: separate statuses, real failure classes (DNS, refused, TLS, auth, index, timeout), allowlist, no credential leakage, saved-destination only."""
import json
import socket
import ssl
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT / 'src'), str(ROOT / 'backend')):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from fastapi.testclient import TestClient

from app import main
from netspout_core.hec_connection_test import run_test

TOKEN = 'tok-SECRET-12345'
ALLOWED = ['dev_test_replay']


def serve(handler_state, tls=None):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            handler_state['gets'] = handler_state.get('gets', 0) + 1
            self.send_response(handler_state.get('health', 200))
            self.end_headers()
            self.wfile.write(b'{"text":"HEC is healthy","code":17}')

        def do_POST(self):
            n = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(n)
            handler_state.setdefault('posts', []).append((self.headers.get('Authorization'), json.loads(body)))
            if handler_state.get('sleep'):
                time.sleep(handler_state['sleep'])
            status, reply = handler_state.get('reply', (200, {'text': 'Success', 'code': 0}))
            if self.headers.get('Authorization') != 'Splunk ' + TOKEN:
                status, reply = 401, {'text': 'Invalid token', 'code': 4}
            self.send_response(status)
            self.end_headers()
            self.wfile.write(json.dumps(reply).encode())
    srv = HTTPServer(('127.0.0.1', 0), H)
    if tls:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(*tls)
        srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def cfg(srv, scheme='http', **kw):
    return {'hec_url': '%s://127.0.0.1:%d/services/collector' % (scheme, srv.server_port), 'deployment_mode': 'DOCKER_LAB', 'allow_insecure_tls': False, **kw}


def statuses(r):
    return r['statuses']


def test_full_success_with_independent_search_is_the_only_fully_verified_outcome():
    st = {}
    srv = serve(st)
    seen = []
    def search(q):
        seen.append(q)
        return [{'count': '1'}], None
    r = run_test(cfg(srv), TOKEN, 'dev_test_replay', ALLOWED, search, 'pw', polls=2, interval=0.01)
    assert r['overall'] == 'FULLY_VERIFIED' and statuses(r) == {'connection': 'REACHABLE', 'authentication': 'AUTHENTICATED', 'acceptance': 'ACCEPTED', 'indexing': 'VERIFIED'}
    auth, body = st['posts'][0]
    assert auth == 'Splunk ' + TOKEN and body['index'] == 'dev_test_replay' and body['sourcetype'] == 'netspout:connection_test' and 'synthetic' in body['event']
    assert r['test_id'] in seen[0] and 'dev_test_replay' in seen[0]
    assert TOKEN not in json.dumps(r) and 'pw' not in json.dumps(r)


def test_acceptance_without_search_is_not_verified():
    srv = serve({})
    r = run_test(cfg(srv), TOKEN, 'dev_test_replay', ALLOWED, None, None)
    assert r['overall'] == 'ACCEPTED_NOT_VERIFIED' and statuses(r)['acceptance'] == 'ACCEPTED' and statuses(r)['indexing'] == 'NOT_CONFIGURED'


def test_accepted_but_not_found_by_search_is_not_verified():
    srv = serve({})
    r = run_test(cfg(srv), TOKEN, 'dev_test_replay', ALLOWED, lambda q: ([{'count': '0'}], None), 'pw', polls=2, interval=0.01)
    assert r['overall'] == 'ACCEPTED_NOT_VERIFIED' and statuses(r)['indexing'] == 'NOT_FOUND' and statuses(r)['acceptance'] == 'ACCEPTED'


def test_search_failure_is_reported_separately_from_acceptance():
    srv = serve({})
    r = run_test(cfg(srv), TOKEN, 'dev_test_replay', ALLOWED, lambda q: ([], 'HTTP Error 401: Unauthorized'), 'pw')
    assert statuses(r)['acceptance'] == 'ACCEPTED' and statuses(r)['indexing'] == 'SEARCH_FAILED' and r['overall'] == 'ACCEPTED_NOT_VERIFIED' and r['error']['category'] == 'SEARCH'


def test_wrong_token_is_an_authentication_failure():
    srv = serve({})
    r = run_test(cfg(srv), 'wrong-token', 'dev_test_replay', ALLOWED, None, None)
    assert statuses(r)['authentication'] == 'REFUSED' and statuses(r)['acceptance'] == 'REJECTED' and r['error']['category'] == 'AUTH_FAILED' and 'wrong-token' not in json.dumps(r)


def test_index_refused_by_hec_is_distinct_from_authentication():
    srv = serve({'reply': (400, {'text': 'Incorrect index', 'code': 7})})
    r = run_test(cfg(srv), TOKEN, 'dev_test_replay', ALLOWED, None, None)
    assert r['error']['category'] == 'INDEX_REFUSED' and statuses(r)['authentication'] == 'AUTHENTICATED' and statuses(r)['acceptance'] == 'REJECTED'


def test_unreachable_hec_is_a_connection_failure_with_no_event_sent():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
    r = run_test({'hec_url': 'http://127.0.0.1:%d/services/collector' % port, 'deployment_mode': 'DOCKER_LAB'}, TOKEN, 'dev_test_replay', ALLOWED, None, None, connect_timeout=1)
    assert r['error']['category'] == 'REFUSED' and statuses(r)['connection'] == 'FAILED' and statuses(r)['acceptance'] == 'NOT_RUN'


def test_dns_failure_is_named():
    r = run_test({'hec_url': 'https://no-such-host.invalid:8088/services/collector', 'deployment_mode': 'SPLUNK_ENTERPRISE'}, TOKEN, 'dev_test_replay', ALLOWED, None, None, connect_timeout=2)
    assert r['error']['category'] == 'DNS' and 'DNS lookup' in r['error']['message']


def test_a_read_timeout_after_sending_is_unknown_and_never_retried():
    st = {'sleep': 1.5}
    srv = serve(st)
    r = run_test(cfg(srv), TOKEN, 'dev_test_replay', ALLOWED, None, None, http_timeout=0.4)
    assert statuses(r)['acceptance'] == 'UNKNOWN' and r['overall'] == 'FAILED' and len(st['posts']) == 1
    assert 'not retried' in json.dumps(r['steps'])


@pytest.fixture(scope='module')
def selfsigned(tmp_path_factory):
    d = tmp_path_factory.mktemp('tls')
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(d / 'k.pem'), '-out', str(d / 'c.pem'), '-days', '1', '-subj', '/CN=localhost',
                    '-addext', 'subjectAltName=DNS:localhost,IP:127.0.0.1'], check=True, capture_output=True)
    return str(d / 'c.pem'), str(d / 'k.pem')


def test_untrusted_certificate_fails_tls_validation_and_nothing_is_sent(selfsigned):
    st = {}
    srv = serve(st, tls=selfsigned)
    r = run_test(cfg(srv, 'https'), TOKEN, 'dev_test_replay', ALLOWED, None, None)
    assert r['error']['category'] == 'TLS_CERTIFICATE' and statuses(r)['connection'] == 'FAILED' and 'posts' not in st
    assert 'not trusted' in r['error']['message']


def test_lab_exception_allows_a_self_signed_certificate_but_says_so(selfsigned):
    srv = serve({}, tls=selfsigned)
    r = run_test(cfg(srv, 'https', allow_insecure_tls=True), TOKEN, 'dev_test_replay', ALLOWED, None, None)
    tls = next(s for s in r['steps'] if s['id'] == 'tls')
    assert statuses(r)['acceptance'] == 'ACCEPTED' and tls['status'] == 'WARN' and 'NOT verified' in tls['detail']


def test_index_outside_the_allowlist_sends_nothing():
    st = {}
    srv = serve(st)
    r = run_test(cfg(srv), TOKEN, 'prod_main', ALLOWED, None, None)
    assert r['error']['category'] == 'INDEX_NOT_ALLOWED' and 'posts' not in st and st.get('gets', 0) == 0


def test_plain_http_is_refused_outside_the_lab_destination():
    r = run_test({'hec_url': 'http://hec.example.com:8088/services/collector', 'deployment_mode': 'SPLUNK_CLOUD'}, TOKEN, 'dev_test_replay', ALLOWED, None, None)
    assert r['error']['category'] == 'CONFIG'


def test_splunk_cloud_style_host_is_recognized_without_contacting_it():
    r = run_test({'hec_url': 'https://http-inputs-example.splunkcloud.com:443/services/collector', 'deployment_mode': 'SPLUNK_CLOUD'}, TOKEN, 'dev_test_replay', ALLOWED, None, None, connect_timeout=0.2)
    assert any('Splunk Cloud-style host' in s['detail'] for s in r['steps'] if s['id'] == 'config')        # the host is then not reachable here; we only classify, we never test a real stack


# ---------------------------------------------------------------- API
client = TestClient(main.app)


@pytest.mark.parametrize('body,code', [({}, 422), ({'test_index': 'dev_test_replay', 'hec_url': 'https://evil.example/services/collector'}, 422), ({'test_index': 'dev_test_replay', 'hec_token': 'x'}, 422),
                                       ({'test_index': 'bad index!'}, 422)])
def test_api_refuses_caller_supplied_transports_and_missing_index(body, code):
    assert client.post('/api/setup/test-connection', json=body).status_code == code


def test_api_requires_a_saved_destination_and_applies_the_allowlist():
    with patch.object(main.release_candidate_configuration, 'load', return_value={'configured': False}):
        assert client.post('/api/setup/test-connection', json={'test_index': 'dev_test_replay'}).status_code == 409
    srv = serve({})
    conf = {'configured': True, **cfg(srv), 'indexes': ['dev_test_replay']}
    with patch.object(main.release_candidate_configuration, 'load', return_value=conf), patch.object(main.release_candidate_configuration.secrets, 'hec_token', TOKEN, create=True), \
            patch.object(main.release_candidate_configuration.secrets, 'search_secret', None, create=True):
        r = client.post('/api/setup/test-connection', json={'test_index': 'dev_test_replay'}).json()
        assert r['overall'] == 'ACCEPTED_NOT_VERIFIED' and TOKEN not in json.dumps(r)
        bad = client.post('/api/setup/test-connection', json={'test_index': 'other_index'}).json()
        assert bad['error']['category'] == 'INDEX_NOT_ALLOWED'
