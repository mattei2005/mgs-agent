import importlib.util
import json
from pathlib import Path
from datetime import datetime
import tempfile
import unittest
from unittest.mock import patch
spec = importlib.util.spec_from_file_location('creation_counts', '/root/.hermes/profiles/ares/scripts/shein-campaign-creation-daily.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
policy = m.load(m.POLICY)


def snapshot():
    s = {'start': '2026-10-29T00:00:00-04:00', 'cutoff': '2026-10-29T18:08:00-04:00', 'accounts': []}
    for index, code in enumerate(policy['manager_codes']):
        for brand in policy['brands']:
            s['accounts'].append({'account_id': str(10000 + len(s['accounts'])), 'manager_code': code, 'manager': ['Icaro','Geizian','Isliago','Joe','Kelly','Nicolas'][index], 'brand': brand, 'complete': True, 'campaigns': []})
    return s


class CountsTests(unittest.TestCase):
    def test_dedupe_and_actual_created_time(self):
        a = {'account_id':'12345','campaigns':[],'seen_ids':[],'pages':0,'used_cursors':[]}
        c = {'id':'99999','account_id':'12345','name':'30/10 misleading date COPY C1','created_time':'2026-10-29T12:00:00-0400','status':'PAUSED'}
        body = {'data':[c,c]}
        m.add_page(a, body, datetime.fromisoformat('2026-10-29T00:00:00-04:00'),datetime.fromisoformat('2026-10-29T18:08:00-04:00'))
        self.assertEqual(len(a['campaigns']),1); self.assertTrue(a['complete']); self.assertEqual(a['scanned'],1)
    def test_exact_boundaries_and_eastern_conversion(self):
        a = {'account_id':'12345','campaigns':[],'seen_ids':[],'pages':0,'used_cursors':[]}
        stamps = ['2026-10-29T03:59:59+00:00','2026-10-29T04:00:00+00:00','2026-10-29T22:08:00+00:00','2026-10-29T22:08:01+00:00']
        data=[{'id':str(10000+i),'account_id':'12345','name':'anything','created_time':v,'status':'ARCHIVED'} for i,v in enumerate(stamps)]
        m.add_page(a, {'data':data},datetime.fromisoformat('2026-10-29T00:00:00-04:00'),datetime.fromisoformat('2026-10-29T18:08:00-04:00'))
        self.assertEqual([c['id'] for c in a['campaigns']],['10001','10002'])
    def test_pagination_repeated_cursor_fails(self):
        a = {'account_id':'12345','campaigns':[],'seen_ids':[],'pages':0,'used_cursors':['repeated']}
        with self.assertRaises(AssertionError):m.add_page(a,{'data':[],'paging':{'next':'not-followed','cursors':{'after':'repeated'}}},m.now(),m.now())
    def test_partial_is_never_zero(self):
        s=snapshot();s['accounts'][0]['complete']=False
        a=m.aggregate(s,policy)
        self.assertIsNone(a['rows'][0]['cells']['Boostingecon']);self.assertIsNone(a['rows'][0]['total']);self.assertFalse(a['complete'])
        text=m.render(s,policy);self.assertIn('Parcial',text);self.assertIn('n/d',text)
    def test_all36_reconciles(self):
        s=snapshot()
        for a in s['accounts']:a['campaigns']=[{'id':a['account_id']}]
        c=m.aggregate(s,policy)
        self.assertEqual(c['observed_total'],36);self.assertEqual(sum(r['total'] for r in c['rows']),36);self.assertEqual(sum(c['site_totals'].values()),36)
        self.assertLessEqual(len(m.render(s,policy)),1900)
    def test_dst_fixed_local_cutoff(self):
        for stamp in ['2026-10-31T19:00:00-04:00','2026-11-01T19:00:00-05:00']:
            start,end=m.period(datetime.fromisoformat(stamp),True)
            self.assertEqual((start.hour,end.hour,end.minute),(0,18,8));self.assertEqual(start.date(),end.date())
    def test_wrong_account_rejected(self):
        a={'account_id':'12345','campaigns':[],'seen_ids':[],'pages':0,'used_cursors':[]}
        with self.assertRaises(AssertionError):m.add_page(a,{'data':[{'id':'99999','account_id':'12346'}]},m.now(),m.now())
    def test_delivery_exact_get_and_replay_without_second_post(self):
        class Discord:
            def __init__(self):self.posts=0;self.content=None
            def verify(self,bindings):return {'threads':bindings}
            def call(self,method,path,payload=None):
                if method=='POST':self.posts+=1;self.content=payload['content'];return {'id':'123456789'}
                if '/messages/' in path:return {'channel_id':policy['destination_thread_id'],'author':{'id':m.BOT_ID},'content':self.content}
                return {'guild_id':policy['destination_guild_id']}
        with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as temp:
            d=Discord();p=Path(temp)
            self.assertEqual(m.deliver(d,p,policy,'test report','key'),'123456789')
            self.assertEqual(m.deliver(d,p,policy,'test report','key'),'123456789')
            self.assertEqual(d.posts,1)
    def test_ambiguous_post_never_repeated(self):
        class Discord:
            def verify(self,bindings):return {}
            def call(self,method,path,payload=None):
                if method=='POST':raise AssertionError('Unexpected repeated POST')
                return [] if 'messages?' in path else {'guild_id':policy['destination_guild_id']}
        with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as temp:
            p=Path(temp);content='test report';sha=m.hashlib.sha256(content.encode()).hexdigest()
            m.save(p/'outbox.json',{'sha256':sha,'content':content,'status':'IN_FLIGHT'})
            with self.assertRaisesRegex(AssertionError,'AMBIGUOUS_POST'):m.deliver(Discord(),p,policy,content,'key')

if __name__=='__main__':unittest.main(verbosity=2)
