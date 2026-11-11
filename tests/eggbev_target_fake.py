"""Stateful in-memory Meta for target clone integration; never network."""
import copy
from ares_campaign_v3.transport import BatchResult

class TargetFakeMeta:
    last_outer_headers={}
    def __init__(self, crash_seed=False, wrong_final=False):
        self.objects={};self.calls=[];self.counter=90000;self.crash_seed=crash_seed;self.wrong_final=wrong_final
    def new(self,value):
        self.counter+=1;key=str(self.counter);self.objects[key]={'id':key,**copy.deepcopy(value)};return key
    def execute(self,operations,stage):
        rows=[]
        for op in operations:
            self.calls.append((stage,op.name,op.method,op.relative_url))
            path=op.relative_url.split('?')[0];body=copy.deepcopy(op.body)
            if op.method=='GET':
                if path.endswith('/campaigns'):result={'data':[x for x in self.objects.values() if x.get('_kind')=='campaign']}
                elif path.endswith('/adcreatives'):result={'data':[x for x in self.objects.values() if x.get('_kind')=='creative']}
                elif path.endswith('/adsets'):result={'data':[x for x in self.objects.values() if x.get('_kind')=='adset' and x.get('campaign_id')==path.split('/')[0]]}
                elif path.endswith('/ads'):
                    parent=path.split('/')[0];sets={parent} if self.objects.get(parent,{}).get('_kind')=='adset' else {x['id'] for x in self.objects.values() if x.get('_kind')=='adset' and x.get('campaign_id')==parent}
                    result={'data':[x for x in self.objects.values() if x.get('_kind')=='ad' and x.get('adset_id') in sets]}
                else:result=copy.deepcopy(self.objects[path])
            elif op.kind=='campaign_create':result={'id':self.new({**body,'_kind':'campaign','account_id':'1034081997659047'})}
            elif op.kind=='adset_create':result={'id':self.new({**body,'_kind':'adset'})}
            elif op.kind=='creative_create':result={'id':self.new({**body,'_kind':'creative'})}
            elif op.kind=='ad_create':
                creative=self.objects[body['creative']['creative_id']];result={'id':self.new({**body,'creative':creative,'_kind':'ad'})}
                if self.crash_seed:
                    self.crash_seed=False;raise KeyboardInterrupt('simulated uncertain seed response')
            elif op.kind=='ad_copy_with_creative':
                source=path.split('/')[0];seed=self.objects[source];payload=body['creative_parameters'];creative_id=self.new({**payload,'_kind':'creative'})
                if self.wrong_final:self.objects[creative_id]['object_story_spec']['page_id']='999999'
                key=self.new({'_kind':'ad','name':seed['name'],'adset_id':body['adset_id'],'source_ad_id':source,'status':body['status_option'],'creative':self.objects[creative_id]});result={'copied_ad_id':key}
            else:
                self.objects[path].update(body);result={'success':True}
            rows.append(BatchResult(op.name,200,copy.deepcopy(result)))
        return rows
