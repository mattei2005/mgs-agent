import unittest,datetime,json
from unittest.mock import patch
from types import SimpleNamespace
from zoneinfo import ZoneInfo
import finance_media_spend_sync as sync
from finance_spend_sources import dates
class SpendSyncTests(unittest.TestCase):
 def test_month_rollover(self):self.assertEqual(sync.window(datetime.datetime(2026,10,1,7,16,tzinfo=ZoneInfo('America/New_York'))),('2026-09-01','2026-09-30'))
 def test_same_month(self):self.assertEqual(sync.window(datetime.datetime(2026,9,9,7,16,tzinfo=ZoneInfo('America/New_York'))),('2026-09-01','2026-09-08'))
 def test_dst(self):self.assertEqual(sync.window(datetime.datetime(2026,11,2,7,16,tzinfo=ZoneInfo('America/New_York'))),('2026-11-01','2026-11-01'))
 def test_invalid_windows(self):
  for a,b in [('2026-08-01','2026-08-31'),('2026-09-01','2026-10-01'),('2026-09-08','2026-09-01')]:
   with self.assertRaises(AssertionError):dates(a,b)
 def test_notice_transport_payload(self):
  report={'pass':True,'since':'2026-09-01','until':'2026-09-07','period':'2026-09','recorded_accounts':82,'rows':574,'totals':{'USD':'111206.16'},'missing_accounts':[{'account_id':'123'}],'exceptions':[]}
  with patch.object(sync,'verify_notice',return_value={'message_id':'123456789','readback':True}),patch.object(sync.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='discord_bot_post=ok http=200 message_id=123456789')) as run:
   result=sync.notice(report);self.assertEqual(result['message_id'],'123456789');args=run.call_args;payload=json.loads(args.kwargs['input']);self.assertEqual(payload['allowed_mentions']['parse'],[]);self.assertEqual(payload['allowed_mentions']['users'],['344196393512075265']);self.assertIn(sync.THREAD,args.args[0]);self.assertNotIn('token',payload['embeds'][0]['description'].lower())
 def test_notice_failure_not_success(self):
  with patch.object(sync.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout='')):
   with self.assertRaises(RuntimeError):sync.notice({'pass':False,'error':'FixtureError','step':'source_collection'})
if __name__=='__main__':unittest.main()
