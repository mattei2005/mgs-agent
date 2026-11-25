import importlib.util
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import argparse
import json

PATH = '/root/.hermes/profiles/ares/scripts/shein-campaign-creation-weekly.py'
s = importlib.util.spec_from_file_location('weekly', PATH)
w = importlib.util.module_from_spec(s); s.loader.exec_module(w)
p = w.d.load(w.POLICY)


class WeeklyTests(unittest.TestCase):
    def test_closed_previous_week(self):
        a,b=w.period(datetime.fromisoformat('2026-11-30T07:02:25-05:00'))
        self.assertEqual(a.isoformat(),'2026-11-23T00:00:00-05:00')
        self.assertEqual(b.isoformat(),'2026-11-29T23:59:59.999999-05:00')
    def test_midweek_validation_same_previous_week(self):
        a,b=w.period(datetime.fromisoformat('2026-11-25T07:02:25-05:00'))
        self.assertEqual(a.date().isoformat(),'2026-11-16')
        self.assertEqual(b.date().isoformat(),'2026-11-22')
    def test_dst(self):
        a,b=w.period(datetime.fromisoformat('2026-11-02T07:02:25-05:00'))
        seconds=(b.timestamp()+0.000001)-a.timestamp()
        self.assertEqual(seconds,169*3600)
    def test_year_boundary(self):
        a,b=w.period(datetime.fromisoformat('2027-01-04T07:02:25-05:00'))
        self.assertEqual(a.date().isoformat(),'2026-12-28')
        self.assertEqual(b.date().isoformat(),'2027-01-03')
    def test_filter_boundaries_and_dedupe(self):
        a,b=w.period(datetime.fromisoformat('2026-11-30T07:02:25-05:00'))
        rec={'account_id':'123','seen_ids':[],'campaigns':[],'pages':0,'used_cursors':[]}
        rows=[{'id':str(i+1),'account_id':'123','created_time':t,'status':'PAUSED'} for i,t in enumerate(['2026-11-22T23:59:59-05:00','2026-11-23T00:00:00-05:00','2026-11-29T23:59:59-05:00','2026-11-30T00:00:00-05:00'])]
        w.d.add_page(rec,{'data':rows+rows},a,b)
        self.assertEqual({c['id'] for c in rec['campaigns']},{'2','3'})
    def test_wrong_account_rejected(self):
        a,b=w.period(w.d.now());rec={'account_id':'123','seen_ids':[],'campaigns':[]}
        with self.assertRaises(AssertionError):w.d.add_page(rec,{'data':[{'account_id':'456','id':'1','created_time':a.isoformat()}]},a,b)
    def snapshot(self):
        approved=w.d.load(w.d.BASE/p['approved_selection'])['accounts']
        a,b=w.period(w.d.now())
        return {'start':a.isoformat(),'cutoff':b.isoformat(),'accounts':[{'account_id':x['account_id'],'manager_code':x['manager_code'],'manager':x['manager_name'],'brand':x['name'].split('-')[0],'campaigns':[],'complete':True} for x in approved]}
    def test_render_and_missing_not_zero(self):
        snap=self.snapshot();text=w.render(snap,p)
        self.assertIn('semanal',text);self.assertIn('Semana fechada',text)
        self.assertNotIn('Corte parcial',text)
        self.assertLessEqual(len(text.encode('utf-16-le'))//2,2000)
        snap['accounts'][0]['complete']=False
        self.assertIn('n/d',w.render(snap,p))
    def test_unique_and_totals(self):
        snap=self.snapshot();snap['accounts'][0]['campaigns']=[{'id':'1'}]
        n=w.d.aggregate(snap,p)
        self.assertEqual(sum(r['total'] for r in n['rows']),1)
        self.assertEqual(sum(n['site_totals'].values()),1)
        snap['accounts'][1]['campaigns']=[{'id':'1'}]
        with self.assertRaises(AssertionError):w.d.aggregate(snap,p)
    def test_early_guard_without_discovery(self):
        with patch.object(w.d,'now',return_value=datetime.fromisoformat('2026-11-30T07:01:59-05:00')),patch.object(w.d,'resolve',side_effect=AssertionError('no API')):
            self.assertEqual(w.main(argparse.Namespace(scheduled=True,validate_live=False)),0)
    def test_replay_no_collection(self):
        with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as td:
            root=Path(td)/'2026-11-23';root.mkdir();(root/'outbox.json').write_text(json.dumps({'content':'persisted','key':'weekly-2026-11-23'}))
            class Transport:
                class Discord:pass
            with patch.object(w,'STATE',Path(td)),patch.object(w.d,'now',return_value=datetime.fromisoformat('2026-11-30T07:02:25-05:00')),patch.object(w.d,'resolve',side_effect=AssertionError('no discovery')),patch.object(w.d,'Collector',side_effect=AssertionError('no collection')),patch.object(w.d,'module',return_value=Transport),patch.object(w.d,'deliver',return_value='verified') as send:
                self.assertEqual(w.main(argparse.Namespace(scheduled=True,validate_live=False)),0)
                send.assert_called_once()


if __name__=='__main__':unittest.main()
