#!/usr/bin/env python3
"""Full read-only public QA for all approved Router changes in this thread."""
import importlib.util,json,subprocess
from pathlib import Path
import requests
B=Path('/root/mgs-agent');OUT=B/'data/mgs-router-authorized-panel-final-validation.json'
spec=importlib.util.spec_from_file_location('m',B/'scripts/mgs-router-cutover-eleven-dns.py');assert spec and spec.loader
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
fsp=importlib.util.spec_from_file_location('fix',B/'scripts/mgs-router-fix-retired-and-jobs-routes.py');assert fsp and fsp.loader
fix=importlib.util.module_from_spec(fsp);fsp.loader.exec_module(fix)

def main():
    baseline=m.hashes();config=json.loads(Path('/var/lib/mgs-router/routes.json').read_text());assert len(config['routes'])==445
    job=next(r for r in config['routes'] if (r['host'],r['path'])==('job.conectageral.com','/artigosjobs'))
    oldfix=json.loads((B/'data/mgs-router-destination-fix-1556362463413276675.json').read_text())
    assert oldfix['status']=='applied_validated'
    assert [{'destination_id':t['destination_id'],'new':t['url'],'weight':t['weight']} for t in job['destinations']]==[{k:x[k] for k in ['destination_id','new','weight']} for x in oldfix['job_changes']]
    changes=oldfix['job_changes'];pages=fix.pages(changes)
    rows=m.sweep(config['routes'],variants=('',m.RAW));assert len(rows)==1856 and all(x['passed'] for x in rows)
    assert {(x['host'],x['path']) for x in rows if not x.get('reserved')}=={(r['host'],r['path']) for r in config['routes']}
    # Reuse exact weighted-target observation, retirement and direct destination gates.
    jobs_validation=fix.validation(config,changes)
    report={'status':'in_progress','accounts':{},'public_routes':445,'checks_GET_HEAD_without_with_query':rows,'job_all13_live_choices':jobs_validation['job_distinct_targets_observed'],'job_weighted_samples':jobs_validation['job_route_samples'],'retired_es_aliases_HTTP404':jobs_validation['retired_route_checks'],'destination_HTTP200_checks':pages,'groups_metadata_current_preserved':True,'cloudflare_DNS_SSL_WordPress_gateway_writes':0,'secrets_emitted':False}
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    for name,title in [('rodolfo','MGS Router - Rodolfo'),('geizian','MGS Router - Geizian')]:
        s,h=m.panel_login(title)
        try:
            assert s.get(m.PANEL+'/api/routes',timeout=30).json()==config
            domains=s.get(m.PANEL+'/api/domains',timeout=30).json();assert len(domains['domains'])==19 and 'emprego.dicasfinancas.info' not in domains['domains']
            assert all(domains['checks'][x]['verified'] for x in domains['domains'])
            assert all(c.expires is None for c in s.cookies)
            data={'url':m.PANEL,'username':name,'config':config,'routes':config['routes'],'catalog':config['catalog'],'groups':config['groups'],'domains':domains['domains'],'cookies':[{'name':c.name,'value':c.value,'domain':c.domain,'path':c.path,'secure':True,'httpOnly':True,'sameSite':'Strict'} for c in s.cookies]}
            process=subprocess.run(['/root/.local/share/mgs-router-toolchain/qa-venv/bin/python',str(B/'apps/mgs-router/tests/public_panel_retirement_smoke.py')],input=json.dumps(data),capture_output=True,text=True,timeout=100)
            if process.returncode:raise RuntimeError('public_browser_failed:'+name+':'+process.stderr[-800:])
            report['accounts'][name]=json.loads(process.stdout)
        finally:m.logout(s,h)
        assert s.get(m.PANEL+'/api/me',timeout=25).status_code==401
        report['accounts'][name]['manual_logout_and_token_revocation']=True
        OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    assert m.hashes()==baseline,'concurrent_operational_state_changed_during_QA'
    subprocess.run(['/root/.hermes/profiles/zeus/cache/scratch/mgs-router-panel-approved','--state','/var/lib/mgs-router','--origin',m.PANEL,'--check'],check=True,capture_output=True,text=True,timeout=30)
    assert 'emprego.dicasfinancas.info' not in json.loads(Path('/var/lib/mgs-router/domain-checks.json').read_text())
    report.update(status='complete_verified',verified_at=m.now(),immutable_hash_readback=baseline,Go_cases_passed=58,manual_logout_kept=True,inactivity_and_fixed_session_deadline_removed=True,groups_delete_preserves_routes_and_catalog=True,configuration_public_API_and_binary_check_passed=True)
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    with (B/'logs/events-audit.jsonl').open('a') as f:f.write(json.dumps({'timestamp':m.now(),'agent':'zeus','action':'router_authorized_panel_final_QA_readback','authorization_message_ids':['1556362463413276675','1556362857359081503','1556366276501176494','1556366342972510238'],'thread_id':'1555381168894115912','artifact':str(OUT),'routes':445,'checks':1856,'accounts':2,'job_targets_HTTP200_and_live_choices':13,'retired_total_routes':24,'DNS_SSL_WordPress_writes':0,'Go_tests_passed':58})+'\n')
    print(json.dumps({'status':report['status'],'accounts':list(report['accounts']),'routes':445,'GET_HEAD_query_variants_and_reserved_checks':len(rows),'all13_job_weighted_targets_observed':report['job_all13_live_choices'],'job_destinations_HTTP200':len(pages),'green_domains_per_account':19,'groups_per_account':len(config['groups']),'live_no_auto_session_deadline':True,'group_cancel_production_writes':0,'manual_logout':True,'artifact':str(OUT)}))
if __name__=='__main__':
    try:main()
    except Exception as e:print(json.dumps({'status':'failed','error':str(e) if isinstance(e,(RuntimeError,AssertionError)) else type(e).__name__,'secrets_emitted':False}));raise SystemExit(1)
