"""Offline notice/outbox fixtures; never deliver to Discord."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_automation_continuity import Queue


class NoticeTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('notice_supervisor','/root/mgs-agent/scripts/mgs_automation_supervisor.py');assert spec and spec.loader
        self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.q=Queue(Path(self.tmp.name)/'q.sqlite3');self.addCleanup(self.q.close)
        row=self.q.enqueue('fixture:notice',{'kind':'fixture','alert_channel':'1498132022634483894','alert_id':'100'},'fixture')
        self.q.defer(row['key'],'blocked_decision','fixture');self.row=self.q.get(row['key'])
        self.key='notice:'+row['key']+':blocked_decision'

    def test_long_notice_preserves_exact_question_and_explicit_push(self):
        question='Autoriza a entrega histórica tardia da rodada original nas mesmas threads?'
        text='Bloqueado: evidência de fixture.\n'+('Detalhe de fixture. '*300)+'\n'+question
        sent=[]
        def transport(body,**kw):sent.append(body);kw['on_created']('200');return '200'
        self.m.notify_result(self.q,self.row,text,transport)
        self.assertIn(question,json.dumps(sent[0],ensure_ascii=False))
        self.assertEqual(sent[0]['allowed_mentions']['users'],['344196393512075265'])
        self.assertLessEqual(len(sent[0]['embeds'][0]['description']),4096)

    def test_accepted_notice_retries_get_with_frozen_original_payload(self):
        calls=[]
        def transport(body,**kw):
            calls.append((body,kw.get('prior_id')))
            if not kw.get('prior_id'):kw['on_created']('200');raise RuntimeError('fixture GET failed after accepted POST')
            return '200'
        with self.assertRaises(RuntimeError):self.m.notify_result(self.q,self.row,'Bloqueado: primeira evidência de fixture.',transport)
        self.m.notify_result(self.q,self.row,'Bloqueado: texto posterior diferente de fixture.',transport)
        self.assertEqual(calls[0][0],calls[1][0]);self.assertEqual(calls[1][1],'200')

    def test_legacy_verified_notice_is_edited_not_reposted(self):
        self.q.service(self.key,{'verified':True,'message_id':'200','nonce':'fixture'})
        edits=[]
        def update(body,**kw):edits.append((body,kw));return '200'
        def forbid_post(*a,**kw):raise AssertionError('unexpected replacement POST')
        with patch('mgs_alert_transport.update_verified',side_effect=update):self.m.notify_result(self.q,self.row,'Bloqueado: pergunta completa de fixture?',forbid_post)
        self.assertEqual(len(edits),1);self.assertEqual(edits[0][1]['message_id'],'200')
        state=json.loads(self.q.db.execute('SELECT value FROM service WHERE key=?',(self.key,)).fetchone()[0])
        self.assertEqual(state['render_version'],2);self.assertTrue(state['verified'])

if __name__=='__main__':unittest.main()
