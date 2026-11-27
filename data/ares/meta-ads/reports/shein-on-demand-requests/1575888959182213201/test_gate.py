import importlib.util,json,copy
from pathlib import Path
R=Path(__file__).parent
s=importlib.util.spec_from_file_location('task',R/'intraday.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
original=a.d.load;approved=original(R/'approved-review.json');results=[]
def run(name,mutate=None):
 v=copy.deepcopy(approved)
 if mutate:mutate(v)
 def load(p):return v if Path(p)==R/'approved-review.json' else original(p)
 a.d.load=load
 try:
  a.validate_review();passed=mutate is None
 except AssertionError:passed=mutate is not None
 finally:a.d.load=original
 assert passed,name
 results.append({'fixture':name,'passed':passed})
run('valid_current_review')
run('wrong_request_rejected',lambda v:v.update(request_id='other'))
run('missing_binding_rejected',lambda v:v['bindings'].pop())
run('changed_artifact_hash_rejected',lambda v:v['sha256'].update({next(iter(v['sha256'])):'0'*64}))
run('missing_artifact_rejected',lambda v:v['sha256'].pop(next(iter(v['sha256']))))
a.d.save(R/'gate-test-results.json',{'status':'PASS','tests_run':len(results),'fixtures':results})
print(json.dumps({'status':'PASS','gate_tests':len(results)}))
