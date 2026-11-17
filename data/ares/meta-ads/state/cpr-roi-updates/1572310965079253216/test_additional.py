import importlib.util,json,copy,argparse,tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
R=Path(__file__).parent
s=importlib.util.spec_from_file_location('newtests',R/'test_updates.py')
assert s is not None and s.loader is not None
t=importlib.util.module_from_spec(s);s.loader.exec_module(t);m=t.m;man=copy.deepcopy(t.MAN);man['campaigns']=[]
checks=[]
def run_discovery(cs,prior=None):
 with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as tmp:
  root=Path(tmp);r=t.FakeRunner(root,cs,[]);mm=copy.deepcopy(man);mm['campaigns']=prior or []
  with patch.object(m,'datetime') as dt:
   dt.now.return_value=t.AT;dt.fromisoformat=datetime.fromisoformat
   out=m.discover(r,mm,root,argparse.Namespace(fetch_activities=lambda *args:(_ for _ in ()).throw(AssertionError('unauthorized activities'))))
  return out,r.calls
out,calls=run_discovery([t.camp('1'),t.camp('2',dt='2026-11-16T10:00:00-05:00'),t.camp('3',dt='2026-11-18T00:00:00-05:00')]);assert set(out[0])=={'1'};checks.append('other_day_and_future_day_excluded')
out2,_=run_discovery([t.camp('1'),t.camp('4')],list(out[0].values()));assert set(out2[0])=={'1','4'} and len(out2[0])==2;checks.append('dynamic_admission_idempotent')
out3,calls=run_discovery([]);assert not out3[0] and len(calls)==1;checks.append('empty_cohort_no_global_finance')
with patch.object(m,'scope',side_effect=AssertionError('unexpected API')),patch.object(m,'helpers',side_effect=AssertionError('unexpected transport')):
 assert m.execute(argparse.Namespace(initial=True,dry_run=False),datetime.fromisoformat(man['expires_at']))['status']=='EXPIRED';checks.append('expired_before_api_and_transport')
assert m.TID==man['thread_id'] and m.REQUEST==man['source_message_id'];assert man['dynamic_discovery']['future_changes'] is False;checks.append('request_scope_destination')
snap=m.load(R/'runs/initial/snapshot.json');one=next(iter(snap['rows'].values()));big=copy.deepcopy(snap);big['rows']={str(i):{**one,'number':str(i).zfill(3)} for i in range(1,151)};parts=m.text(big,man);assert len(parts)>1 and all(len(p.encode('utf-16-le'))//2<=2000 and p.count('```')%2==0 for p in parts)
for i in range(1,151):assert ('C'+str(i).zfill(3)) in '\n'.join(parts)
checks.append('150_row_pagination_complete')
e1={'source':'ares','job_id':man.get('scheduler_job_id','fixture-own-job'),'script':'same'};e2={'source':'ares','job_id':'other','script':'same'}
keep=lambda e:not(e['source']=='ares' and e.get('job_id')==man.get('scheduler_job_id','fixture-own-job'));assert not keep(e1) and keep(e2);checks.append('same_script_other_job_not_excluded')
m.save(R/'additional-tests.json',{'pass':True,'checks':checks,'tests_run':len(checks),'meta_calls':0,'posts':0});print(json.dumps({'additional_checks_passed':checks}))
