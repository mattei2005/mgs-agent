import asyncio
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

spec=importlib.util.spec_from_file_location('health_finalize',Path(__file__).resolve().parents[1]/'scripts/dtr-sb-page-health-sync.py')
if spec is None or spec.loader is None:
    raise RuntimeError('Cannot load canonical health sync')
sync=importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

class FinalizeTests(unittest.IsolatedAsyncioTestCase):
    def source(self):
        return {'today':sync.today(),'started_at':sync.today()+'T15:30:02-05:00','mode':'apply','ok':False,'writes':0,'new_restrictions_alerted':0,'errors':[{'sheet_update_failed':'Error: read ECONNRESET GET https://api.jbfdigital.com.br/campaigns/Messenger?companies[]=fixture'}],'sheet_active_users':1,'matched_1p_users':1,'stats':{'users_scanned':1}}

    def test_scope_gates(self):
        source=self.source(); source['log']='original'; state={'runs':[{'log':'original'}]}
        sync.validate_finalize_source(source,['a'],state,['a'])
        for field,value in [('writes',1),('new_restrictions_alerted',1),('today','2000-01-01'),('matched_1p_users',0),('discord_deliveries',[{}]),('sheet_update',{'readback_ok':True})]:
            changed=copy.deepcopy(source);changed[field]=value
            with self.assertRaises(RuntimeError):sync.validate_finalize_source(changed,['a'],state,['a'])
        with self.assertRaises(RuntimeError):sync.validate_finalize_source(source,['b'],state,['a'])
        with self.assertRaises(RuntimeError):sync.validate_finalize_source(source,['a'],state,['a','a'])

    async def test_get_retry_sanitizes_headers_and_honors_cooldown(self):
        get=AsyncMock(side_effect=[RuntimeError('secret-cookie'),SimpleNamespace(status=200)])
        with patch.object(sync.asyncio,'sleep',new_callable=AsyncMock) as sleep:
            await sync.sb_read(SimpleNamespace(request=SimpleNamespace(get=get)),'fixture',{})
            sleep.assert_awaited_once_with(1)
        get=AsyncMock(side_effect=RuntimeError('secret-cookie'))
        with patch.object(sync.asyncio,'sleep',new_callable=AsyncMock):
            with self.assertRaisesRegex(RuntimeError,'after 3 attempts') as caught:
                await sync.sb_read(SimpleNamespace(request=SimpleNamespace(get=get)),'fixture',{})
        self.assertNotIn('secret',str(caught.exception))
        get=AsyncMock(return_value=SimpleNamespace(status=429,headers={'retry-after':'120'}))
        with self.assertRaisesRegex(RuntimeError,'cooldown 120'):
            await sync.sb_read(SimpleNamespace(request=SimpleNamespace(get=get)),'fixture',{})
        self.assertEqual(get.await_count,1)

    async def test_resume_does_not_rescan_or_repeat_post_after_failed_get(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=self.source(); path=root/'dtr-sb-page-health-sync-source.json';source['log']=str(path);path.write_text(json.dumps(source))
            (root/'dtr-sb-page-health-sync.log').write_text(f"[{sync.today()}T15:30:01-05:00] dtr-sb-page-health-sync.sh START args=--apply --quiet-noop\nPROGRESS user_done a accounts=1 reports=1 errors=0\n")
            posts=[]
            def failed_get(payload,**kwargs):
                if not kwargs['prior_id']:
                    posts.append('123');kwargs['on_created']('123')
                raise RuntimeError('GET unavailable')
            with patch.object(sync,'LOG_DIR',root),patch.object(sync,'sheet_rows',return_value=[]),patch.object(sync,'active_users_from_sheet',return_value=['a']),patch.object(sync,'load_state',return_value={'runs':[{'log':str(path)}]}),patch.object(sync,'get_sb_context',new_callable=AsyncMock,return_value=(SimpleNamespace(stop=AsyncMock()),SimpleNamespace(close=AsyncMock()),None,{})),patch.object(sync,'fetch_sb_rows',new_callable=AsyncMock,return_value=([],[])),patch.object(sync,'restricted_sheet_rows',return_value=([],{})),patch.object(sync,'write_google_sheet',return_value={'readback_ok':True}) as writer,patch.object(sync,'exited_restrictions_from_sheet',return_value=[]),patch.object(sync,'build_no_new_restrictions_alert',return_value='fixture'),patch.object(sync,'build_operational_summary_alerts',return_value=[]),patch.object(sync,'build_exited_restrictions_alerts',return_value=[]),patch.object(sync,'scan_dtr_user',new_callable=AsyncMock) as scan,patch('mgs_alert_transport.post_verified',side_effect=failed_get):
                with self.assertRaisesRegex(RuntimeError,'GET unavailable'):await sync.resume_finalize(path)
                def verified(payload,**kwargs):
                    self.assertEqual(kwargs['prior_id'],'123');return '123'
                with patch('mgs_alert_transport.post_verified',side_effect=verified):await sync.resume_finalize(path)
                writer.assert_called_once();scan.assert_not_awaited();self.assertEqual(posts,['123'])
            receipt=json.loads(path.with_suffix('.finalize.json').read_text());self.assertEqual(receipt['stage'],'GET_VERIFIED')

if __name__=='__main__':unittest.main()
