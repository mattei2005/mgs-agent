from audit import *
from collections import Counter
from pathlib import Path
root=ROOT
manifest=load('manifest');final=json.loads((root/'final/manifest.json').read_text())
scope=load('final-scope-diff');assert not any(ch for rec in scope for ch in rec['changes'].values())
assert not load('support-final-diff');assert load('last-readback')['charts_unchanged']
coverage={book+':'+t['title']:{k:t[k] for k in ['cells','formulas','extent','grid']} for book,b in manifest.items() for t in b['tabs']}
assert len(coverage)==9 and len(manifest)==6
assert not any(t['errors'] for b in final.values() for t in b['tabs'])
recomp=load('formula-recomputation-summary');auto=sum(v['counts'].get('pass',0) for v in recomp.values());unsupported=[dict(sheet=k,**r) for k,v in recomp.items() for r in v['issues']];assert len(unsupported)==16 and all(r['status']=='unsupported' for r in unsupported)
checkfiles=[('semantic-checks','pass'),('spend-calendar-checks','passed'),('integrated-checks','passed'),('dashboard-independent-checks','passed'),('provider-continuity-checks','passed'),('calendar-scenarios','passed')]
counts={}
for name,key in checkfiles:
 items=load(name)
 if items and key not in items[0]:key='pass'
 assert all(x[key] for x in items),(name,[x for x in items if not x[key]][:4])
 counts[name]=len(items)
imports=load('strict-import-parity');assert len(imports)==83;assert all(not x['mismatches'] for x in imports)
A=cmap('principal');C=cmap('principal','CAIXA SINTETICO');D=cmap('principal','DASH EXECUTIVO')
fixed={'D38':'=SUM(E36)','V38':'=SUM(W36)','AN38':'=SUM(AO36)','FY38':'=SUM(FY36)','GQ38':'=SUM(GQ36)','AKD38':'=SUM(AKD36)','AKU38':'=SUM(AKU36)','ALL38':'=SUM(ALL36)'}
assert all(formula(A[t])==f for t,f in fixed.items())
oldqueue=json.loads(Path('/root/mgs-agent/work/finance-reaudit-20260905/findings-queue.json').read_text());assert len(oldqueue)==19
old_disposition=[{'id':x['id'],'state':x['state'],'review':'rechecked via integral formula + semantic audit; F17 remains owner-confirmed, not externally substantiated'} for x in oldqueue]
issues=[{'id':'R01','type':'confirmed_documentation_error','state':'open_no_write_authorization','scope':'BASE_DASH!V123:V153','cells':31,'description':'Source text still points to former AOW:APE global block. Financial formulas correctly reference current APE:APM; no financial impact.','evidence':'dashboard-findings.json'}, {'id':'R02','type':'metric_definition_difference','state':'clarification_not_arithmetic_error','scope':['CAIXA SINTETICO!J79','DASH EXECUTIVO!A8','BASE_DASH!U154','Agosto 2026!APM36'],'description':'Cash/dashboard ROI = net profit / media spend; August global ROI = postshare net / all costs - 1. Same ROI líquido label but different bases. Preserve calculations; recommend specific labels rather than automatic formula harmonization.','values':{'cash_dashboard':val(C['J79']),'august_global':val(A['APM36'])}}]
summary={'task_message_id':'1545877165982355557','thread_id':'1545426987756298340','status':'integrated_financial_checks_PASS_documentation_followup_open','completed_at':datetime.now(timezone.utc).isoformat(),'scope':'Agosto 2026 principal and five managers; full CAIXA SINTETICO, BASE_DASH and DASH EXECUTIVO. Other monthly tabs read only at 406 direct supporting reference cells, not independently audited in full.','coverage':coverage,'totals':{'workbooks':len(manifest),'tabs':len(coverage),'cells':sum(t['cells'] for t in coverage.values()),'formulas':sum(t['formulas'] for t in coverage.values()),'automatic_formula_recomputations_pass':auto,'special_dashboard_formulas_independently_checked':6,'observed_volatile_provider_formulas':10,'import_formulas':len(imports),'exact_import_cells':sum(x['cells'] for x in imports),'exact_import_mismatches':sum(len(x['mismatches']) for x in imports),'support_cells':406,'displayed_errors_final':0,'readback_changed_cells':0,'charts':4,'site_segments':43,'country_source_segments':78},'check_counts':counts,'old_findings_disposition':old_disposition,'findings':issues,'key_values':{'cash_half_brl':val(C['J81']),'august_half_brl':val(A['J137']),'profit_usd':val(C['J77']),'gross_usd':val(C['J58']),'media_spend_usd':abs(val(C['J75']))},'limits':['Financial internal consistency and current recorded values, not audit against every bank/partner receipt.','August remains PROVISORIO; 10 live GOOGLEFINANCE-derived formula outputs observed and sanity checked, not independently priced against external market feed.','O121:P121 preserved per Rodolfo confirmation; manual USD/BRL difference is not declared a new accounting error.','Chart data ranges, source series and current query outputs verified by API; no claim of visual rendering inspection.','All live current filter outputs validated; alternate filter cases tested locally only to preserve read-only authorization.','Initial George import loading state was transient; retry and final capture both zero errors.'],'artifacts':str(root),'google_writes':0}
assert summary['totals']['formulas']==auto+6+10
save('FINAL-SUMMARY.json',summary);save('findings-queue.json',issues)
lines=['# Reauditoria integrada final — Agosto 2026','',f"Estado: {summary['status']}",f"Pedido: {summary['task_message_id']} | thread {summary['thread_id']}",'','## Cobertura integral']
for key,v in coverage.items():lines.append(f"- {key}: {v['cells']} células; {v['formulas']} fórmulas; última linha/coluna com conteúdo {v['extent']}. A leitura cobriu a aba inteira, não apenas a extensão histórica.")
lines+=['','## Validação',json.dumps(summary['totals'],ensure_ascii=False,indent=2),json.dumps(counts,ensure_ascii=False,indent=2),'','As fórmulas automáticas foram recalculadas usando precedentes capturados; os testes semânticos reconstruíram componentes independentemente, inclusive totais zero/inativos, moedas, países, lower blocks e distribuição de custos. IMPORTRANGE teve comparação estrita célula a célula, inclusive blanks. Recaptura final: nenhuma mudança de fórmulas, valores efetivos, formatação numérica exibida ou notas; metadados dos gráficos e 406 dependências de apoio também permaneceram iguais.','', '## Achados / observações']
for issue in issues:lines.append(json.dumps(issue,ensure_ascii=False,indent=2))
lines+=['','## Valores reconciliados',json.dumps(summary['key_values'],ensure_ascii=False,indent=2),'','## Limites e ressalvas']+[f'- {x}' for x in summary['limits']]
lines+=['','## Escopo de escrita','Nenhuma escrita Google realizada. Apenas capturas, validadores locais, registro de auditoria, checkpoint, inventário e documentação procedural.','', '## Histórico','Os 19 achados anteriores foram rechecados no estado atual; F17 permanece encerrado pela decisão do responsável. O resultado atual supersede final_integrated_audit_pending como auditoria executada, mas não equivale a fechamento financeiro cambial nem encerra a pendência documental R01.']
(root/'REPORT.md').write_text('\n'.join(lines)+'\n')
paths=[p for p in root.rglob('*') if p.is_file() and p.suffix in ['.py','.json','.jsonl','.md'] and '__pycache__' not in p.parts and p.name!='SHA256SUMS.json']
hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)};save('SHA256SUMS.json',hashes)
print('TOTALS',json.dumps(summary['totals']));print('TESTS',json.dumps(counts));print('VALUES',json.dumps(summary['key_values']));print('REPORT_SHA256',hashes['REPORT.md']);print('SUMMARY_SHA256',hashes['FINAL-SUMMARY.json']);print('FILES_HASHED',len(hashes))
