"""Resume the only missing read-only remote phase after environment preflight failure."""
import ast,json,gzip,pathlib,subprocess,time,os
from typing import Any
O=pathlib.Path(__file__).parent;collector=O/'collect.py';expected='6ad388a2697437cdc1d568dcf0e5b8d37784f84e1d71275e0f1ee4b4b9e1c05c'
assert subprocess.check_output(['sha256sum',str(collector)],text=True).split()[0]==expected
code=collector.read_text();start_anchor='start=time.monotonic();old=';end_anchor='# The canonical transport reads only exact remote files.'
assert code.count(start_anchor)==code.count(end_anchor)==1
prefix=code[:code.index(start_anchor)];suffix=code[code.index(end_anchor):]
ns:dict[str,Any]={'__file__':str(collector)};exec(compile(prefix,str(collector),'exec'),ns)
R,A,P=ns['R'],ns['A'],ns['P'];before_rows=json.loads(gzip.open(P/'reviewed326.json.gz','rt').read());before={x['path']:x['metadata']for x in before_rows}
assert len(before)==326 and all(ns['meta'](p)==m for p,m in before.items())
lineage=json.loads((O/'dump-lineage.json').read_text());census=json.loads((O/'code-consumer-census.json').read_text());assert not census['exact_target_or_run_hits'];targets=[x['path']for x in lineage if not x['retained_newest']];assert len(targets)==4
base=A/'private/gam-email-runs';all_local=sorted(base.glob('*/mgs_finance-before.dump'));latest=pathlib.Path(next(x['path']for x in lineage if x['retained_newest']));assert len(all_local)==8 and latest==all_local[-1]
# Restore the canonical producer's environment bootstrap, without accessing Google APIs.
auth=R/'scripts/mgs_google_workspace_auth.py';tree=ast.parse(auth.read_text());load=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='load_env');ens={'BASE':R,'Path':pathlib.Path,'os':os};exec(compile(ast.fix_missing_locations(ast.Module(body=[load],type_ignores=[])),str(auth),'exec'),ens);ens['load_env']();assert bool(os.environ.get('OP_SERVICE_ACCOUNT_TOKEN'))
# Extract only the already-inspected health/process read predicates.
gate=R/'data/storage-local-tests-1571996311308214363/target-consumer-census-v2/gate.py';tree=ast.parse(gate.read_text());gn:list[ast.stmt]=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))or isinstance(n,ast.FunctionDef)and n.name in {'need','health','runtime_refs'}or isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='SERVICES'for t in n.targets)];gns:dict[str,Any]={};exec(compile(ast.fix_missing_locations(ast.Module(body=gn,type_ignores=[])),str(gate),'exec'),gns)
assert not gns['runtime_refs'](targets);health=gns['health']();assert health==census['health']
ns.update(start=time.monotonic(),before=before,lineage=lineage,targets=targets,latest=latest,all_local=all_local,hits=[],inventory={str(i):None for i in range(census['source_count'])},rows=before_rows,roles=json.loads((O/'role-summary.json').read_text())['roles'],ns=gns,health=health)
# The unchanged suffix still performs every exact remote hash/size/catalogue check.
exec(compile(suffix,str(collector)+'::remote_resume','exec'),ns)
receipt={'status':'recovered_and_remote_phase_validated','initial_failure':'1Password item read failed before SSH; canonical OP_SERVICE_ACCOUNT_TOKEN environment was not loaded by the extracted helper adapter.','failure_stage':'remote credential resolution, before any remote command','credential_or_permission_changes':False,'canonical_environment_bootstrap_restored':True,'collector_sha256':expected,'original_partial_artifacts_preserved':True,'full326_hash_pass_not_repeated_or_fabricated':True,'all326_metadata_revalidated':True,'remote_phase_completed':True,'source_files_deleted':0}
assert not(O/'transport-recovery.json').exists();(O/'transport-recovery.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
