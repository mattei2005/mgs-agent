"""Read-only structural/known-regression audit; not a financial reconciliation."""
import argparse,json,re,hashlib
from pathlib import Path

def audit(skill,app,repo):
    files=sorted(skill.rglob('*.md'));issues=[];checks=[]
    def check(name,ok,detail=''):
        checks.append({'name':name,'pass':bool(ok),'detail':detail})
        if not ok:issues.append(name)
    root=(skill/'SKILL.md').read_text();texts={str(p.relative_to(skill)):p.read_text() for p in files}
    fm=root.split('---',2)[1] if root.startswith('---\n') else ''
    check('frontmatter',all(re.search(r'^'+k+r':\s*\S',fm,re.M) for k in ['name','description','version','author','license','platforms']))
    check('no_pruned_content',all('[SKILL_PRUNED]' not in s for s in texts.values()))
    refs=[];evidence=[]
    for rel,s in texts.items():
        for target in re.findall(r'(?<![\w/.-])references/[\w.-]+\.md',s):refs.append({'from':rel,'target':target,'exists':(skill/target).is_file()})
        for token in re.findall(r'`([^`\n]+)`',s):
            if re.fullmatch(r'(?:/root/mgs-agent/)?(?:docs|reports)/[\w./-]+\.md',token):
                p=Path(token) if token.startswith('/') else repo/token;evidence.append({'from':rel,'target':token,'exists':p.is_file()})
    check('internal_reference_targets',all(x['exists'] for x in refs),str(len(refs)))
    check('canonical_document_targets',all(x['exists'] for x in evidence),str(len(evidence)))
    check('application_first_branch','## Application-first execution' in root and '### Historical Sheet audit branch' in root)
    check('historical_state_label','## Historical Sheet baseline' in root and '## Current business state' not in root)
    security=texts['references/current-security-performance-and-dr.md'];review=texts['references/preventive-release-gate-and-review.md'];flow=texts['references/revenue-manager-attribution-and-sequential-daily-flow.md']
    check('documented_persistent_sessions','Rodolfo1555570216912560151' in security and 'persistent sessions replace the idle3h/absolute8h' in security and 'Never revive expired/revoked sessions'.lower() in security.lower())
    check('review_unauthenticated_vs_forbidden','unauthenticated HTML navigation303' in review and 'authenticated non-Rodolfo403' in review)
    check('review_old_blockers_labeled','publication is still blocked' not in review and 'Current blocked evidence:' not in review)
    check('review_six_item_current_boundary','Current main screen: six items only' in review)
    check('release_bundle_cutover_protocol','code local/remoto' in flow or 'código local/remoto' in flow)
    check('no_universal_recurrence_guarantee','No zero-recurrence guarantee' in root)
    guards={
      'references/navigation-profiles-media-spend.md':'Current-state supersession',
      'references/native-closed-month-views.md':'Current-state supersession',
      'references/payments-approvals-nicolas-pilot.md':'Current-state supersession',
      'references/ui-redesign-and-quote-lifecycle.md':'Current-state supersession',
      'references/august-2026-audit-ledger.md':'Historical snapshot',
      'references/manual-quotes-monthly-source.md':'Current-state supersession',
    }
    check('older_branches_have_supersession',all(marker in texts[path][:1800] for path,marker in guards.items()))
    auth=(app/'auth.mjs').read_text();daily=(app/'public/financial-summary.js').read_text();rules=json.loads((repo/'data/finance-gam-revenue-rules.json').read_text());routes=(app/'monthly-review-routes.mjs').read_text()
    check('local_runtime_persistent_sessions',"VALUES($1,$2,$3,'infinity')" in auth and 'expire?0:34560000' in auth and "expires_at='infinity' OR (expires_at>now() AND last_seen>now()-interval '3 hours')" in auth and "interval '8 hours'" not in auth)
    navigation=(app/'public/navigation.js').read_text();server=(app/'server.mjs').read_text()
    check('safe_automatic_updates',all(x in navigation for x in ['dialog[open]','dirtyForms','requests>0','sessionStorage.setItem','saved.user===a.user','AbortSignal.timeout']) and "app.get('/api/auth/update-state'" in server)
    check('local_runtime_redirect',"res.redirect(303,'/login')" in auth)
    check('local_runtime_exact_rodolfo',"rodolfo" in routes and "owner" in routes)
    check('local_runtime_partial_costs','included||staged?general/days:0,included||staged?staff/days:0' in daily)
    check('local_runtime_realized_boundary','general*elapsed/days,staff*elapsed/days' in daily)
    check('dicasfinancas_mapping',rules['brand_domains'].get('dicasfinancas')=='dicasfinancas.info' and rules['vertical_by_domain_country'].get('dicasfinancas.info|br')=='br-cc-br' and rules['site_owner_manager'].get('dicasfinancas.info')=='g002')
    related=re.search(r'related_skills:\s*\[([^\]]+)\]',fm)
    names=[n.strip() for n in related.group(1).split(',')] if related else []
    profile=skill.parents[1]
    check('related_skills_resolve',all(any(p.parent.name==name for p in profile.rglob('SKILL.md')) for name in names))
    inventory=[{'path':str(p.relative_to(skill)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
    return {'pass':not issues,'scope':'all Markdown files: structure/targets/routing and named regressions; not exhaustive accounting or production runtime audit','markdown_files':len(files),'checks':checks,'issues':issues,'missing_references':[x for x in refs if not x['exists']],'missing_evidence':[x for x in evidence if not x['exists']],'inventory':inventory}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--skill',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--app',type=Path,default=Path('/root/mgs-agent/apps/finance-system'));p.add_argument('--repo',type=Path,default=Path('/root/mgs-agent'));p.add_argument('--output',type=Path);args=p.parse_args();result=audit(args.skill,args.app,args.repo)
    if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ['inventory','checks']},ensure_ascii=False));raise SystemExit(0 if result['pass'] else 1)
