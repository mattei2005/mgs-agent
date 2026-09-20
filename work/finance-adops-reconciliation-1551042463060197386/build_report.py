import json,datetime,hashlib
from decimal import Decimal as D
from pathlib import Path
W=Path(__file__).parent
load=lambda n:json.loads((W/n).read_text())
p=load('spend-reconciliation.json');r=load('revenue-vs-dashboard.json');sources=load('revenue-source-reconciliation.json')
fmt=lambda n:f'{D(str(n)):,.2f}'.replace(',','X').replace('.',',').replace('X','.')
lines=['# Agosto 2026 — AdOps x dashboard: auditoria integral de fontes','',
'Autoridade: Rodolfo `1551042463060197386`; thread `1545426987756298340`.',
'Fonte: https://docs.google.com/spreadsheets/d/1HoF7ihPzb0_oQIR5cZ0bsWd2b-_5jsHcKBalFi9HG7g/edit — oito abas completas, SA canônica, segunda leitura integral idêntica.',
'Dashboard: PostgreSQL produtivo MatteiInc01; workspace-2026-08 revision 391; master-ad-accounts revision 6. Fonte/ui-model produtivos coletados; dados de fonte imutável usados somente para resolver inputs legados. Nenhuma escrita financeira.',
'Execução: '+datetime.datetime.now(datetime.timezone.utc).isoformat(),'',
'## Decisão fornecida e limites','',
'AV consolidado governa o pagamento deste fechamento, conforme Rodolfo. SB1 é CAD, SB2 USD. Comparações USD abaixo presumem AV USD/bruto; o cabeçalho AV não declara moeda nem bruto/líquido, portanto confirmar essa base antes de aplicar descontos. Não houve envio de dinheiro, alteração de billing, parâmetros, contas, receita ou gastos.',
'Primeiro diagnóstico/lista conforme a opção final do pedido. Correções financeiras aguardam fonte íntegra e resposta sobre as ambiguidades. PEND-092 permanece aberta.',
'', '## Bloqueios e inconsistências de fonte','',
'- SB2: A796:E1909 é exatamente igual, linha a linha, à SB1: 1.114 linhas, 122.749,647894028879 CAD. A formatação muda para CA$ na linha 796. Os dados próprios iniciais A2:E795 somam USD 87.151,001420629774 para CPV, Fincgriffin e GameZoneAd. A soma cega da aba (209.900,649314658653) mistura moedas e duplicaria receita. O cálculo isolado dos primeiros 794 registros é hipótese auditada, não exclusão autorizada da fonte.',
'- AV: consolidado 106.459,31; detalhado recalculado 99.521,91. Falta finanzas.topfeed.fun (6.937,50) no detalhado; os demais sites somam diferença líquida -0,10. Footer literal $99,521,81 diverge do recálculo por 0,10.',
'- AV: quatro valores são textos malformados: G701=$1,419,47; G914=$1,309,12; G1893=$1,144,90; G2150=$1,145,41. O recálculo interpreta respectivamente 1419.47,1309.12,1144.90,1145.41, sem alterar originais. O total informado acima é condicionado a essa interpretação.',
'- Google: primeiros 12 dias de cada conta foram convertidos pelo locale pt_BR em 08/jan,08/fev,...08/dez; dias 13–31 permanecem strings US. O total mensal independe da reinterpretação; comparação diária usa explicitamente a hipótese de 01–31/08. Nenhuma data foi escrita.',
'- M2: consolidado 4.611,87 coincide por arredondamento com o novo detalhado 4.611,868541642177. Não coincide com a captura anterior do browser Profit Attribution (5.148,75), que não governa esta nova fonte automaticamente.',
'- M2: todos os registros detalhados trazem wantabrand.com, incluindo pg-19326 (7,83112536661), que coincide dia a dia com finance.wantabrand.com no consolidado (desvio máximo 0,004244140909). Origem por domínio deve ser confirmada; não reescrever silenciosamente o Domain.',
'- LyzmoFinanzas: fonte traz conta -02, USD74,51 (04/08 2,49;05/08 72,02); dashboard traz mesmos dias/valores em -01, ID1818460511984988. Sem Account ID na sheet, coincidência não prova identidade. Resolver ID/nome antes de remapear.',
'- Cliquet principal/Finanzas: apenas receitas SB a partir de 21/08, sem nenhum domínio Cliquet no AV entregue; dashboard contém receita de 01–20/08. Não substituir receita anterior por zero antes de confirmar o fechamento da antiga rede.',
'- Fincgriffin: relatório está na SB2/USD, enquanto cadastro de agosto aponta SB Rede1. Separar acerto de receita da correção de cadastro histórico/regras.',
'- Cinco sites com resíduos SB1 não possuem bloco no workspace de agosto: Boostingecon,Cephyric,DicasFinancas,Escalatepower,Mavroa. Cadastro não pode ativar rateio silenciosamente.',
'', '## Gastos — resumo e controle','',
'- Facebook: 825 registros,48 nomes distintos,zero duplicatas account/day/currency;47 matches exatos,36 com diferença mensal,2 com total igual e dias diferentes,9 com todos os dias iguais;1 nome sem match (-02 Lyzmo). Há ainda a contraparte -01 com gasto na dash e ausente da fonte.',
'- Facebook: dash USD286.088,46; sheet USD286.368,15; delta +279,69. Esse delta trata o valor Lyzmo como mesmo gasto econômico, sem resolver a identidade.',
'- Google Gamingadx-US-01: R$11.216,30 → R$11.207,23, delta -9,07; Mattei 1/GameZoneAd: R$60.019,90 → R$59.967,01, delta -52,89. Total Google delta -61,96 BRL.',
'- Controle independente: inputs FB + inputs Google/USDBRL reproduzem o gasto consolidado da dash USD300.082,189594663086 com diferença menor que 1e-20. Nenhum gasto positivo legado ficou sem classificação: os únicos slots monetários sem source_links de conta são os Google R$ dos dois sites.',
'', '### Facebook — todas as diferenças mensais, USD (dash → fonte)','']
for x in sorted(p['fb'],key=lambda x:x['name']):
 if x['id'] and x['sheet_present'] and D(x['delta']):lines.append(f"- {x['name']}: {fmt(x['dash'])} → {fmt(x['sheet'])}; delta {fmt(x['delta'])}; {x['diff_days']} dias diferentes.")
lines+=['','### Diferenças de conta/dia que não devem ser duplicadas','',
'- Infinitynexx conta sem G001 tem 7.851,59 (6.859,76 principal +991,83 complementar), mas fonte 6.914,27. Conta -G001 fonte996,08/dash0. Site total dash7.851,59/fonte7.910,35: aumento líquido58,76, não996,08. Há deslocamento de datas no bloco complementar.',
'- CPV05-G006: 193,38→298,98; CPV16-G006:179,48→74,57. Em15/08,104,91 pertence à05 no relatório, mas está na16 na dash; os demais deltas da05 somam0,69.',
'- EggbevFinanzas-US-CC-ES-01: total542,12 igual;38,36 está no15/08 na dash e16/08 na fonte.',
'- NewsounFinanzas-US-CC-ES-01: total299,86 igual;41,25/38,94/33,56 estão em17–19/08 na dash versus18–20/08 na fonte.',
'', '## Receitas por fonte','',
'- SB1: CAD'+fmt(sum(D(v) for v in sources['sb']['sb1'].values()))+'.',
'- SB2: USD87.151,00, somente segmento inicial de794 registros, pendente de confirmação de integridade.',
'- AV consolidado:106.459,31; moeda/basis bruta assumida para a ponte.',
'- M2 consolidado: USD4.611,87; detalhado direto518,684613060005 e BOT4.093,183928582172 (inclui pg-19326).',
'- M2 Wantabrand principal: USD5.150,28→4.604,04; financeiro7,40→7,83; delta combinado-545,81. Separação de país/vertical não existe no novo detalhado e não deve ser inventada a partir de campaign sem regra aprovada.',
'', '## Ponte de receita por site — condicionada, não plano de escrita','',
'USD/CAD da dash: '+r['fx_usdcad']+'. Fórmula: SB1_CAD/H1 + SB2_USD + AV_consolidado_USD + M2_USD. Comparado ao gross USD real da dashboard, incluindo segmentos complementares. Fontes acima incompletas/ambíguas não justificam zerar dados históricos.',
'Formato: site — dash → soma de fontes; delta. Valores exibidos arredondados individualmente, cálculo interno Decimal completo.','']
for x in r['rows']:
 if any(D(x[k]) for k in ['sb1','sb2','av','m2','dash']):lines.append(f"- {x['site']}: {fmt(x['dash'])} → {fmt(x['expected_usd'])}; delta {fmt(x['delta_usd'])}; SB1 CAD={x['sb1']}, SB2 USD={x['sb2']}, AV={x['av']}, M2={x['m2']}.")
lines+=['',f"Total condicional: dash USD{fmt(r['total_dash_usd'])} → fontes USD{fmt(r['total_expected_usd'])}; delta USD{fmt(r['total_delta_usd'])}.",
'Não é lucro/pagamento final: falta confirmar fontes, atribuição e bases antes de recalcular inválidos/revshare/imposto/comissões.',
'', '## Evidência e validação','',
'- Planilha: metadata.json, oito snapshots com sheetId, formatted-anomalies.json; segundo GET integral idêntico.',
'- Dashboard: dashboard-db.json,source.json,ui-model.json; revisão produtiva391/cadastro6.',
'- Análise: spend-reconciliation.json (todas as diferenças diárias),revenue-source-reconciliation.json,revenue-vs-dashboard.json.',
'- Parser inicialmente recusou AV strings monetárias inválidas (Decimal ConversionSyntax), foi corrigido para interpretação explícita/registrada e reexecutado; nenhum fallback silencioso e nenhuma mutação na fonte.',
'- Modelo real do turno: logs mostram openai-codex/gpt-6-astra-900k e política financeira aplicada à thread.',
'- Continuidade: checkpoint ZEUS-FINANCE-ADOPS-1551042463060197386; procedimento adops-monthly-source-reconciliation.md; autoridade AV consolidado registrada.',
'', '## Respostas necessárias para aplicação','',
'1. Confirmar o descarte lógico do trecho duplicado SB2 A796:E1909 e se os primeiros794 registros são o relatório completo da rede2.',
'2. Confirmar AV USD/bruto antes de aplicar novamente inválidos/revshare; consolidado já escolhido como autoridade.',
'3. Obter a receita anterior de Cliquet/principal e Finanzas (01–20/08) ou confirmar a ausência efetiva de pagamento.',
'4. Identificar numeric Account ID de LyzmoFinanzas-02; não presumir que é a -01 cadastrada.',
'5. Confirmar pg-19326 como Finance Wantabrand e os critérios de país/vertical para M2 caso o fechamento exija essa distribuição.',
'6. Definir cadastro dos pequenos resíduos de agosto sem rateio e ajuste da rede histórica de Fincgriffin.',
'As diferenças determinísticas de gastos foram quantificadas integralmente para o lote de correção, sem mudar o sistema antes desta lista solicitada.']
report=Path('/root/mgs-agent/reports/finance-adops-reconciliation-1551042463060197386.md');report.write_text('\n'.join(lines)+'\n')
manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in W.glob('*.json')};manifest['report']=hashlib.sha256(report.read_bytes()).hexdigest();(W/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({'report':str(report),'sha256':manifest['report'],'source_tabs':len(load('metadata.json')['sheets']),'fb_monthly_differences':sum(x['id'] is not None and x['sheet_present'] and bool(D(x['delta'])) for x in p['fb']),'financial_writes':0}))
