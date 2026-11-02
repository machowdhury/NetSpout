"""Mixed HEC verification requires independently indexed logs AND metrics."""
import json
import types
import unittest
import uuid
from unittest.mock import patch
import test_native_run_monitoring as fixtures

api, monitor = fixtures.handler, fixtures.monitor


class MixedVerificationTests(unittest.TestCase):
    setUp = fixtures.MonitoringTests.setUp
    rest = fixtures.MonitoringTests.rest
    record = fixtures.MonitoringTests.record
    complete = fixtures.MonitoringTests.complete

    def check(self, signals, status=None, datatype='metric', error=False, result_messages=None):
        r=self.complete(self.record())
        monitor.update(r['run_id'],lambda x:x.update(classification='MIXED',indexes=['logs','metrics']))
        calls=[]
        def request(url, **kw):
            calls.append((url,kw))
            if '/data/indexes/' in url:
                if error:raise PermissionError('dummy-private')
                data={'entry':[{'content':{'datatype':'event' if '/logs?' in url else datatype}}]}
            elif kw.get('method')=='POST':data={'sid':'mixed-job'}
            elif '/results?' in url:
                data={'messages':result_messages,'results':[dict(netspout_run_id=r['run_id'] if key!='UNRELATED' else str(uuid.uuid4()),netspout_signal=key,count=count) for key,count in signals]}
            else:data={'entry':[{'content':status or {'isDone':True,'dispatchState':'DONE'}}]}
            return types.SimpleNamespace(status=200),json.dumps(data)
        with patch.object(api.rest,'simpleRequest',side_effect=request):
            _,response=monitor.verification(r['run_id'],'admin')
        return response['run']['verification'],calls,r

    def test_both_signals_required_and_query_uses_typed_recorded_scopes(self):
        value,calls,r=self.check([('LOG','30'),('METRIC','30')])
        self.assertEqual(value['state'],'VERIFIED')
        self.assertEqual(value['matching_events'],30)
        self.assertEqual(value['matching_metric_points'],30)
        query=next(kw['postargs']['search'] for _,kw in calls if kw.get('method')=='POST')
        log,metric=query.split('| append')
        self.assertIn('index="logs"',log);self.assertNotIn('index="metrics"',log)
        self.assertIn('mstats count(_value)',metric);self.assertIn('index="metrics"',metric)
        self.assertNotIn('index="logs"',metric)
        self.assertIn('netspout_run_id="'+r['run_id']+'"',log)
        self.assertNotIn('netspout_run_id::',log)
        self.assertEqual(query.count(r['run_id']),2)
        self.assertEqual(query.count('earliest='+str(int(r['started_at']))),2)
        self.assertNotIn('index=*',query)

    def test_one_signal_never_verifies_and_clears_cached_job(self):
        for rows in ([('LOG','30')],[('METRIC','30')],[('LOG','30'),('METRIC','0')]):
            with self.subTest(rows=rows):
                value,_,_=self.check(rows)
                self.assertEqual(value['state'],'INCONCLUSIVE')

    def test_no_matches_complete_window(self):
        value,_,_=self.check([])
        self.assertEqual(value['state'],'NOT_FOUND')

    def test_unrelated_malformed_or_missing_signal_never_verifies(self):
        for rows in ([('UNRELATED','30')],[('LOG','bad')],[('unexpected','30')]):
            value,_,_=self.check(rows);self.assertEqual(value['state'],'INCONCLUSIVE')

    def test_index_metadata_and_search_fail_closed(self):
        value,calls,_=self.check([],datatype='unknown')
        self.assertEqual(value['state'],'INCONCLUSIVE')
        self.assertFalse(any(kw.get('method')=='POST' for _,kw in calls))
        value,_,_=self.check([],error=True);self.assertEqual(value['state'],'ERROR')
        for status in ({'isDone':False,'dispatchState':'RUNNING'},
                       {'isDone':True,'dispatchState':'DONE','messages':['warning']},
                       {'isDone':True,'dispatchState':'DONE','isFinalized':True}):
            value,_,_=self.check([('LOG','30'),('METRIC','30')],status=status)
            self.assertEqual(value['state'],'INCONCLUSIVE')

    def test_only_exact_benign_info_messages_are_allowed(self):
        messages=[{'type':'INFO','text':'Your timerange was substituted based on your search string'},
                  {'type':'INFO','text':"[subsearch]: Your timerange was substituted based on your 'where' clause"}]
        value,_,_=self.check([('LOG','30'),('METRIC','30')],
            status={'isDone':True,'dispatchState':'DONE','messages':messages},result_messages=messages)
        self.assertEqual(value['state'],'VERIFIED')
        for message in ({'type':'WARN','text':messages[0]['text']},
                        {'type':'INFO','text':'unknown diagnostic'}, {'type':'ERROR','text':'denied'}):
            value,_,_=self.check([('LOG','30'),('METRIC','30')],result_messages=[message])
            self.assertEqual(value['state'],'INCONCLUSIVE')

    def test_old_mixed_search_job_is_not_reused(self):
        original=monitor.update
        def update(run_id,edit):
            saved=original(run_id,edit)
            if saved and saved.get('classification')=='MIXED' and 'search_job' not in saved:
                original(run_id,lambda x:x.update(search_job={'sid':'old-job','latest':saved['ended_at']}))
            return saved
        with patch.object(monitor,'update',side_effect=update):
            value,calls,_=self.check([('LOG','30'),('METRIC','30')])
        self.assertEqual(value['state'],'VERIFIED')
        self.assertTrue(any(kw.get('method')=='POST' for _,kw in calls))
