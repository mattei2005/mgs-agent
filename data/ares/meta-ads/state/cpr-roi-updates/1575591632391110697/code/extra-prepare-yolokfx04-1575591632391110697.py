import pathlib,json,hashlib,ast
B=pathlib.Path('/root/mgs-agent');H=pathlib.Path('/root/.hermes/profiles/ares');OLD=B/'data/ares/meta-ads/state/cpr-roi-updates/1575576678325813283';RID='1575591632391110697';R=B/'data/ares/meta-ads/state/cpr-roi-updates'/RID
R.mkdir(parents=True,exist_ok=True,mode=0o700)
idx=json.loads((OLD/'artifact-index.json').read_text());entries=[e for e in idx['entries'] if e['role']=='reusable_code']
for e in entries:assert hashlib.sha256(pathlib.Path(e['path']).read_bytes()).hexdigest()==e['sha256']
def code(source):
 e=next(e for e in entries if e['source']==str(source));return pathlib.Path(e['path']).read_text()
runner=H/'scripts/shein-g004-cpr-roi-20261126.py';wrapper=runner.with_suffix('.sh')
t=code(H/'scripts/shein-g004-mavroa07-cpr-roi-20261126.py').replace('1575576678325813283',RID).replace('1770569568407466','781612907182683').replace('1575250717093011567','1558147211026501643').replace('Mavroa Conta 07','Yolokfx Conta 04').replace('13:19 EST','14:18 EST')
def repl(text,name,new):
 n=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name==name);ls=text.splitlines(True);return ''.join(ls[:n.lineno-1])+new+'\n'+''.join(ls[n.end_lineno:])
t=repl(t,'scope',"""def scope(m):
 assert (m['request_id'],m['account_id'],m['thread_id'],m['requester_discord_id'])==(REQUEST,AID,TID,USER)
 assert m['mode']=='finite_read_only_periodic_cpr_roi' and not m['dynamic_discovery']['enabled']
 assert m['date']=='2026-11-26' and m['meta_writes'] is False and not m['discover_future_edits']
 assert m['cohort_frozen'] is True
 for cmd in [[sys.executable,str(BASE/'scripts/mgs-ares-asset-scope.py'),'check-account',AID,'--json'],[sys.executable,str(BASE/'scripts/mgs-domain-scope.py'),'check','--agent','ares',m['domain']]]:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=30);assert p.returncode==0,'Scope gate'
  if '--json' in cmd:assert json.loads(p.stdout)['allowed'] is True
 assert USER in load(BASE/'data/authorized-users.json')['agents']['ares']['authorized_user_discord_ids']
 b=next(b for b in load(BASE/'data/ares/discord/shein-intraday-report-bindings.json')['bindings'] if b['thread_id']==TID)
 assert (b['account_id'],b['channel_id'])==(AID,m['parent_id'])
 return {**b,'account_name':m['account_name']}
""")
runner.write_text(t);runner.chmod(0o700)
wt=code(H/'scripts/shein-g004-mavroa07-cpr-roi-20261126.sh').replace('shein-g004-mavroa07-cpr-roi-20261126.py',runner.name);wrapper.write_text(wt);wrapper.chmod(0o700)
for name in ['test_fixed.py','freeze-cohort.py','schedule-audit.py','finalize.py']:
 t=code(OLD/name).replace('1575576678325813283',RID).replace('shein-g004-mavroa07-cpr-roi-20261126','shein-g004-cpr-roi-20261126')
 if name=='test_fixed.py':
  t=t.replace("self.assertIn('Conta 07',text);self.assertNotIn('Conta 04',text)","self.assertIn('Conta 04',text);self.assertNotIn('Conta 07',text)").replace('fixed_cohort_07','fixed_cohort_yolokfx04')
 if name=='freeze-cohort.py':
  t=t.replace("sc=m.load(m.BASE/('data/ares/discord/thread-scopes/'+m.TID+'.json'));assert (sc['account_id'],sc['parent_channel_id'])==(m.AID,x['parent_id'])","sc=next(b for b in m.load(m.BASE/'data/ares/discord/shein-intraday-report-bindings.json')['bindings'] if b['thread_id']==m.TID);assert (sc['account_id'],sc['channel_id'])==(m.AID,x['parent_id'])")
 if name=='finalize.py':t=t.replace('Mavroa07','Yolokfx04').replace('13h19EST','14h18EST')
 (R/name).write_text(t)
m={'request_id':RID,'source_message_id':RID,'requester_discord_id':'1214246869484576890','request_time':'2026-11-26T19:18:38.239000+00:00','request_text':'me mande um relatório, a cada meia hora, até o final do dia, do custo por resultado e o RÓI das campanhas que subi hoje.','mode':'finite_read_only_periodic_cpr_roi','account_id':'781612907182683','account_name':'Yolokfx-US-SHEIN-EN-04-G004','domain':'yolokfx.com','thread_id':'1558147211026501643','parent_id':'1558147066826334309','date':'2026-11-26','timezone_name':'America/New_York','currency':'USD','dynamic_discovery':{'enabled':False,'future_creations':False,'future_changes':False,'criterion':'created_time_today_at_or_before_authenticated_request'},'discover_future_edits':False,'cohort_frozen':False,'edits_frozen':True,'campaigns':[],'slots':[],'cadence_minutes':30,'expires_at':'2026-11-27T00:00:00-05:00','meta_writes':False,'dashboard_writes':False,'runner':str(runner),'wrapper':str(wrapper),'publisher':{'publisherId':'digital-trust_yolokfx','name':'yolokfx.com'},'metric_cpr':'Meta spend/offsite_conversion.fb_pixel_add_to_wishlist','metric_roi':'100*(SB_NET_REVENUE/SB_INVESTIMENT_ADJUSTED-1)','antecedent_request_id':'1575576678325813283','state':'PREPARING_FIXED_COHORT','wrapper_timeout_seconds':165}
for name in ['manifest.json','fixture-manifest.json']:(R/name).write_text(json.dumps(m,ensure_ascii=False,indent=2))
(R/'provenance.json').write_text(json.dumps({'antecedent_request_id':'1575576678325813283','verified_reusable_entries':entries,'adaptation':'New exact account/thread/request; fixed creation cohort before authenticated request; zero inherited campaign IDs, sources, receipts or job'},ensure_ascii=False,indent=2))
print(json.dumps({'prepared':True,'root':str(R),'runner':str(runner),'integrity_verified':True}))
