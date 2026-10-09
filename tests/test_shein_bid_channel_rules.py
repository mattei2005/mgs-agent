"""Offline regression for Rodolfo's SHEIN bid deltas/channel permission rule."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_shein_general_runtime import case, CHANNELS, MANAGERS
from ares_campaign_v3 import shein_general as general
from ares_campaign_v3 import shein_single_clone as route
from ares_campaign_v3.schema import Manifest, ManifestError
from ares_campaign_v3.prevalidation import prevalidate_payload
from ares_campaign_v3.media_registry import MediaRegistry
from ares_campaign_v3.engine import CampaignEngine
from ares_campaign_v3.transport import FakeBatchTransport


class BidDeltaTests(unittest.TestCase):
    def build(self, alias, value=None, mode='pure_clone'):
        r,s,a,_=case(4, mode=mode)
        a['shein_naming']={'enabled':True,'route_regex':r'/quiz/us/sh([123])-g[0-9]{3}/','layout_version_map':{'1':'v1','2':'v2','3':'v3'}}
        r['bid_strategy']=alias
        if value is not None:r['bid_usd']=value
        before=copy.deepcopy(s)
        p=general.build(r,s,114,a)
        self.assertEqual(s,before)
        return p,s,a

    def test_maxvol_to_cocap_and_bidcap_set_exact_cap_and_target_name(self):
        for alias,strategy in [('COCAP','COST_CAP'),('BIDCAP','LOWEST_COST_WITH_BID_CAP')]:
            with self.subTest(alias=alias):
                p,s,a=self.build(alias,'1.25')
                c=p['campaigns'][0]
                self.assertEqual(c['campaign_updates']['bid_strategy'],strategy)
                self.assertEqual(c['adset_updates'],{'bid_amount':'125','bid_constraints':{}})
                self.assertIs(c['bid_override'],True)
                self.assertIn(' - '+alias+' - ',c['name'])
                self.assertEqual(c['source_campaign_id'],s['campaign']['id'])
                Manifest.from_dict(p)

    def test_missing_invalid_fractional_or_maxvol_amount_rejected(self):
        for alias,amount in [('COCAP',None),('BIDCAP',None),('COCAP','0'),('BIDCAP','-1'),('COCAP','1.001'),('COCAP','NaN'),('MAXVOL','1'),('cocap','1')]:
            with self.subTest(alias=alias,amount=amount),self.assertRaises(ValueError):self.build(alias,amount)

    def test_cap_to_maxvol_clears_target_cap_not_source(self):
        r,s,a,_=case(4);s['campaign']['bid_strategy']='COST_CAP';s['adset']['bid_amount']='250';s['adset']['bid_constraints']={'roas_average_floor':10000}
        r['bid_strategy']='MAXVOL';p=general.build(r,s,114,a)
        self.assertEqual(p['campaigns'][0]['adset_updates'],{'bid_amount':'0','bid_constraints':{}})
        self.assertEqual(s['adset']['bid_amount'],'250')

    def test_clone_without_delta_preserves_source_no_extra_updates(self):
        r,s,a,_=case(4);s['campaign']['bid_strategy']='COST_CAP';s['adset']['bid_amount']='250'
        p=general.build(r,s,114,a)
        self.assertNotIn('adset_updates',p['campaigns'][0])
        self.assertNotIn('bid_override',p['campaigns'][0])
        self.assertEqual(p['campaigns'][0]['campaign_updates']['bid_strategy'],'COST_CAP')

    def test_delta_from_zero_and_new_media_clone(self):
        for mode in ['clone_prestaged','from_zero_prestaged']:
            p,_,_=self.build('COCAP','1.25',mode)
            c=p['campaigns'][0]
            if mode=='from_zero_prestaged':
                self.assertEqual(c['campaign_create']['bid_strategy'],'COST_CAP')
                self.assertEqual(c['adset_create']['bid_amount'],'125')
            else:self.assertEqual(c['adset_updates']['bid_amount'],'125')
            Manifest.from_dict(p)

    def test_arbitrary_adset_delta_and_other_operation_still_forbidden(self):
        p,_,_=self.build('COCAP','1.25')
        p['campaigns'][0]['adset_updates']['targeting']={'age_min':18}
        with self.assertRaises(ManifestError):Manifest.from_dict(p)
        p,_,_=self.build('COCAP','1.25');p['operation']='Other'
        with self.assertRaises(ManifestError):Manifest.from_dict(p)

    def test_offline_core_plan_execute_and_idempotent_replay(self):
        p,_,a=self.build('COCAP','1.25')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);p=prevalidate_payload(p,MediaRegistry(root/'media.json'))
            config={'enabled':True,'write_enabled':True,'accounts':{a['shein_profile']['account_id']:a},'state_root':str(root/'state'),'audit_root':str(root/'audit')}
            transports=[];operations=[]
            class Capture(FakeBatchTransport):
                def execute(self, ops, stage):
                    operations.extend(ops)
                    return super().execute(ops,stage)
            def factory(aid):
                t=Capture(aid);transports.append(t);return t
            engine=CampaignEngine(config,transport_factory=factory);m=Manifest.from_dict(p)
            plan=engine.dry_run(m)
            result=engine.execute(m)
            self.assertEqual(result['status'],'COMPLETE_PAUSED')
            self.assertEqual(result['campaign_ids'],engine.execute(m)['campaign_ids'])
            self.assertTrue(any(op.kind=='adset_update' and op.body.get('bid_amount')=='125' for op in operations))
            self.assertEqual(plan['writes'],0)
            self.assertEqual(sum(op.kind=='campaign_copy' for op in operations),1)

    def test_request_accepts_explicit_bid_fields(self):
        r,_,_,_=case(4);r.update(bid_strategy='COCAP',bid_usd='1.25')
        route.validate_request(r)


class ChannelRuleTests(unittest.TestCase):
    def test_non_owner_uses_live_permissions_and_wrong_parent_still_denied(self):
        r,s,a,_=case(4);r['authorized_by']=MANAGERS[1]
        a['shein_profile']['channel_authorization_policy']={'enabled':True,'approved_by':'344196393512075265','channel_ids':CHANNELS}
        with patch('ares_campaign_v3.shein_channel_authority.verify',return_value={'verified':True}) as verify:
            general.build(r,s,114,a);verify.assert_called()
            r['source_channel_id']=CHANNELS[1]
            with self.assertRaises(ValueError):general.build(r,s,114,a)

    def test_live_permission_failure_not_replaced_by_manager_id(self):
        r,_,a,_=case(4)
        a['shein_profile']['channel_authorization_policy']={'enabled':True,'approved_by':'344196393512075265','channel_ids':CHANNELS}
        with patch('ares_campaign_v3.shein_channel_authority.verify',side_effect=ValueError('permission denied')):
            with self.assertRaises(ValueError):general.authorize(r,a['shein_profile'])

    def test_effective_permissions_respect_member_and_role_deny(self):
        from ares_campaign_v3.shein_channel_authority import effective_permissions
        roles=[{'id':'guild','permissions':str((1<<10)|(1<<11)|(1<<38))},{'id':'team','permissions':'0'}]
        member={'user':{'id':'actor'},'roles':['team']}
        channel={'permission_overwrites':[{'id':'team','type':0,'deny':str(1<<11),'allow':'0'}]}
        self.assertEqual(effective_permissions('guild','not-owner',roles,member,channel)&(1<<11),0)
        channel['permission_overwrites'].append({'id':'actor','type':1,'deny':'0','allow':str(1<<11)})
        self.assertNotEqual(effective_permissions('guild','not-owner',roles,member,channel)&(1<<11),0)

    def test_verifier_checks_parent_and_private_thread_membership(self):
        from ares_campaign_v3 import shein_channel_authority as auth
        r,_,a,_=case(4);actor=r['authorized_by'];parent=r['source_channel_id'];thread=r['source_thread_id'];guild='1185714635991679006'
        responses={f'/channels/{parent}':{'id':parent,'guild_id':guild,'type':0,'permission_overwrites':[]},
                   f'/guilds/{guild}':{'id':guild,'owner_id':'other'},
                   f'/guilds/{guild}/roles':[{'id':guild,'permissions':str((1<<10)|(1<<11)|(1<<38))}],
                   f'/guilds/{guild}/members/{actor}':{'user':{'id':actor,'bot':False},'roles':[]},
                   f'/channels/{thread}':{'id':thread,'parent_id':parent,'guild_id':guild,'type':12},
                   f'/channels/{thread}/thread-members/{actor}':{'user_id':actor}}
        with patch.object(auth,'_get',side_effect=lambda path:responses[path]):
            self.assertTrue(auth.verify(r,a['shein_profile'],force=True)['verified'])
            responses[f'/channels/{thread}']['parent_id']='wrong'
            with self.assertRaises(ValueError):auth.verify(r,a['shein_profile'],force=True)

if __name__=='__main__':unittest.main()
