import pathlib,json,ast,hashlib,fcntl,importlib.util,sys
from datetime import datetime
R=pathlib.Path(__file__).parent;H=pathlib.Path('/root/.hermes/profiles/ares');A=R/'amendments/1573430872906924114';P=R.parent/'1573054587685052684'
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);assert s and s.loader;m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
m=module('current',H/'scripts/shein-g004-mavroa-cpr-roi-20261120.py');d,_,ac=m.helpers();manifest=m.load(R/'manifest.json');auth=m.load(A/'authorization.json');cut=datetime.fromisoformat(auth['timestamp'].replace('Z','+00:00'))
idx=m.load(P/'artifact-index.json');e=next(e for e in idx['entries'] if e['path'].endswith('00-shein-g004-mavroa-cpr-roi-20261119.py'));p=pathlib.Path(e['path']);assert hashlib.sha256(p.read_bytes()).hexdigest()==e['sha256'];old=module('old_selection',p)
src=ast.get_source_segment(p.read_text(),next(n for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='discover'));src=src.replace("end=datetime.now(z)","end=datetime.fromisoformat(m['edit_cutoff'])");exec(compile(src,str(A/'scoped-selection.py'),'exec'),old.__dict__);(A/'scoped-selection.py').write_text(src)
b=m.load(R/'binding.json');run=A/'selection';run.mkdir(exist_ok=True);r=d.Runner({'policy_id':manifest['request_id']},run,[b],manifest['date']);temp={**manifest,'edits_frozen':False,'edit_cutoff':cut.isoformat()};members,_,missing=old.discover(r,temp,run,ac);assert not missing
m.save(A/'selected-members.json',list(members.values()));print(json.dumps({'selected':[{'number':x['number'],'created_time':x['created_time'],'reasons':x['reasons'],'status':x['status']} for x in members.values()],'events':m.load(run/'membership-evidence.json')},ensure_ascii=False))
