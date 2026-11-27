import ast,json
from pathlib import Path
R=Path(__file__).parent
tree=ast.parse((R/'archive.py').read_text())
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='account_archive_files')
ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'archive-files-fixture','exec'),ns)
results=[]
class FakePath:
 def __init__(self,available,name=None):self.available=available;self.name=name
 def __truediv__(self,name):return FakePath(self.available,name)
 def exists(self):return self.name in self.available
for label,available,fail,expected in [
 ('mandatory_missing',set(),True,set()),
 ('conditional_missing',{'source.json'},False,{'source.json'}),
 ('conditional_present',{'source.json','optional.json'},False,{'source.json','optional.json'})]:
 rejected=False
 try:
  found=ns['account_archive_files'](FakePath(available),{'source.json'},{'optional.json'})
 except AssertionError:
  rejected=True
 assert rejected==fail
 if not fail:assert {p.name for p in found}==expected
 results.append({'fixture':label,'passed':True})
nodes=[n for n in tree.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and isinstance(n.value.func.value,ast.Name) and n.value.func.value.id=='root_names' and n.value.func.attr=='update' and 'refresh-diagnostic-' in ast.unparse(n)]
assert len(nodes)==1
for label,available in [('refresh_absent',set()),('refresh_partial',{'refresh-diagnostic-0.json'}),('refresh_complete',{'refresh-diagnostic-0.json','refresh-diagnostic-50.json'})]:
 scope={'root_names':set(),'R':FakePath(available),'all_ids':list(range(63))}
 exec(compile(ast.Module(body=nodes,type_ignores=[]),'archive-refresh-fixture','exec'),scope)
 assert scope['root_names']==available
 results.append({'fixture':label,'passed':True})
result={'status':'PASS','tests_run':len(results),'fixtures':results}
(R/'archive-test-results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
