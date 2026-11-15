import ast,copy,difflib,json,sys
from datetime import datetime,timezone
from pathlib import Path
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_9700e988';sys.path.insert(0,str(R/'scripts'))
from ares_campaign_v3 import target_start_revision as rev
from ares_campaign_v3 import target_continuation as tc
install=rev.load(M/'install-receipt.json');receipt=rev.load(install['receipt_path']);cfg=rev.load(R/'data/ares/meta-ads/engine-v3/config.json');h=Path(receipt['request_path']).parent
assert rev.file_digest(install['receipt_path'])==install['receipt_sha256']
protected=rev.load(M/'protected-before.json');assert all(rev.file_digest(p)==v for p,v in protected.items())
pins=rev.load(M/'tested-runtime-hashes.json');assert all(rev.file_digest(R/p)==v for p,v in pins.items())
results=rev.load(M/'installed-final-tests.json');assert all(r['success'] and r['skipped']==0 for r in results);assert sum(r['tests'] for r in results)==487
core=rev.load(M/'core-baseline-comparison.json');assert core['exact_same_failures'] and core['installed']==core['baseline']
baseline=rev.load(M/'before/config.json');restored=copy.deepcopy(cfg);restored['accounts'][receipt['account_id']]['target_page_replacement']['continuations'].pop(receipt['request_id']);assert restored==baseline
before=ast.parse((M/'before/target_continuation.py').read_text());after=ast.parse((R/'scripts/ares_campaign_v3/target_continuation.py').read_text())
a={n.name:ast.dump(n,include_attributes=False) for n in before.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))};b={n.name:ast.dump(n,include_attributes=False) for n in after.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))};changed=[n for n in a if a[n]!=b[n]];assert changed==['validate_local','admission'];assert set(b)-set(a)=={'_asap_revision'}
writers=[]
for p in Path('/proc').glob('[0-9]*'):
    try:argv=(p/'cmdline').read_bytes().split(b'\0')
    except OSError:continue
    if b'execute' in argv and any(x.endswith(b'/ares-eggbev-target-clone.py') for x in argv):writers.append(p.name)
assert not writers
context=tc.validate_local(receipt['request_path'],rev.load(h/'manifest.json'),cfg);assert context['temporal']['last'][1]['start_time']==install['start_time']
for name,target in [('target_continuation.py',R/'scripts/ares_campaign_v3/target_continuation.py'),('config.json',R/'data/ares/meta-ads/engine-v3/config.json')]:
    (M/(name+'.diff')).write_text(''.join(difflib.unified_diff((M/'before'/name).read_text().splitlines(True),target.read_text().splitlines(True))))
paths=[R/'scripts/ares_campaign_v3/target_continuation.py',R/'tests/test_target_asap_continuation.py',R/'data/ares/meta-ads/engine-v3/config.json',Path(install['receipt_path']),Path('/root/.hermes/profiles/zeus/skills/growth/meta-ads-api-operations/SKILL.md'),Path('/root/.hermes/profiles/zeus/skills/growth/meta-ads-api-operations/references/target-asap-partial-continuation.md')]
result={'status':'VERIFIED','verified_at':datetime.now(timezone.utc).isoformat(),'installed_hashes':{str(p):rev.file_digest(p) for p in paths},'tested_runtime_hashes':len(pins),'protected_unchanged':len(protected),'modified_existing_ast':changed,'new_helper':'_asap_revision','unchanged_runner_engine_comparers_schema_quota':True,'pertinent_passed':487,'new_asap_tests':31,'core_passed':core['installed']['passed'],'core_failed_preexisting':len(core['installed']['failed']),'core_baseline_identical':True,'config_extra_passed':8,'config_extra_failed_preexisting':1,'legacy_config_cause':'unchanged development_access vs legacy standard_access expectation','operational_writers':writers,'operational_engine_calls':0,'meta_writes':0,'drive_writes':0,'new_revisions_uploads_reservations_pbia':0,'live_admission_verified':install['fresh_live_authority_and_admission'],'cli_production_check_executed':False,'reason_cli_not_executed':'check-continuation instantiates Engine; maintenance explicitly forbids operational Engine. Both CLI paths proved offline with original arguments; production admission/schema and direct GETs independently verified.'}
rev.atomic_json(M/'verification.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))
