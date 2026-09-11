# Financeiro MGS — cutoff, sites e atualização histórica

## Autoridade

- Thread: `1545426987756298340`
- Definição: `1547727478011727963`
- Correção do ponto 6: `1547731247793709056`
- Autorização: `1547732274936553532`
- Encerramento/correções: `1547775936697737288`

## Resultado publicado

1. Pagamentos usa faixa compacta no topo com USD→BRL, USD/CAD e GBP→USD. Inválidos continuam no motor, mas não aparecem em Pagamentos.
2. Owner pode atualizar janeiro–julho pela própria aba mensal selecionada; cada captura cria versão imutável e preserva o baseline `finance_history`.
3. Julho mantém a correção canônica SB Tech Bot 629,28 CAD, autoridade `1547697182948458611`, mesmo quando a fórmula live da aba usa I1/GBP.
4. Sites compartilhados mostram gestores com receita realizada. Yolokfx setembro: MGS, Ícaro, Isliago, Joe, Kelly e Nicolas.
5. Lista única de sites com coluna Ativo/Inativo e legenda. Receita/gastos de inativos entram no resultado; inativos não participam do rateio das Despesas Gerais.
6. Cephyric, Escalatepower e Mavroa são MGS/G002 inativos desde setembro/2026.
7. Cutoff explícito: agosto 31/08; setembro 09/09; futuras competências aguardam data completa. Realizado e tabela diária excluem dias posteriores. Estimativa projeta somente o operacional até o cutoff e inclui despesas mensais uma vez.
8. Pagamentos de mês aberto usa `realized.half_brl`.

## Readback público final

- Competências com câmbios: 24/24.
- Setembro cutoff: 09/09/2026, 9 dias completos.
- Readback público final de setembro, ainda provisório: resultado realizado USD 28.373,467375355496; estimativa 50% USD 47.289,11229225916.
- Ranking: Helixenit/Openzed etc. foi recalculado com fatos realizados e apropriação 9/30 das despesas do site; o arquivo de evidência contém a ordem exata.
- Cephyric/Escalatepower/Mavroa: Inativo + MGS; sem “A conferir” ou `SEM_COMISSAO` exposto.
- Nicolas: sem indicadores gerais e sem botão histórico.
- Desktop 1440 e celular 390; zero erros JavaScript.
- Botão real julho: “A fonte mensal já estava atualizada; nenhum valor mudou.”, seis documentos, `changed=false`, correção CAD preservada.
- Julho: devido BRL 71.984,76526680421; saldo BRL −1.090,0485236818408.

Os valores de setembro podem variar com cotações/fontes provisórias. O corte e a fórmula foram validados, não um número congelado.

## Integridade financeira

- 17 workspaces migradas com recovery por competência e revisão bloqueada.
- 17 cutoffs persistidos; 48 registros dos três sites inativos em setembro/2026–dezembro/2027.
- Receita original CAD dos três sites permaneceu idêntica. O recálculo inicial gerou apenas uma ponte sub-centavo em USD ao reaplicar o câmbio CAD; demais sites, gastos, Despesas Gerais, funcionários e unidades ativas foram preservados.
- 40 linhas `finance_history` originais preservadas; julho mudou por versões sucessoras e ponteiro atômico.
- Ledger, usuários, baseline, contas e histórico imutável mantiveram os manifestos.
- Nenhuma escrita no Google Sheets; leitura via Service Account canônica.

## Falhas encontradas e corrigidas

- A proteção histórica bloqueava a rota nova com HTTP 409: exceção restrita ao owner e à rota `/api/history-refreshes`.
- A fila usava `account_id=history-YYYYMM`, mas o transporte exige somente dígitos: alterado para `YYYYMM`; registro pendente anterior reparado sem exclusão.
- O transporte descartava `period/actor` e os campos de conclusão histórica: contrato ampliado com validação fail-closed de 5/6 documentos e correção CAD em julho.
- O import dinâmico não encontrava `history_policy.py`: diretório da aplicação inserido explicitamente no path.
- Cache parcial de julho anterior ao overlay CAD podia ser reutilizado: agora é inválido e força recaptura.
- Cinco falhas consecutivas fizeram o worker parar como projetado. Após reparo, serviço reiniciado, build lido no state e fila voltou a `pending=0`.
- O teste de logo dependia de cache transitório do Hermes: fixture validada foi congelada em `tests/fixtures/mgs-logo-original.png`, hash igual ao logo publicado.

## Testes

- Node: 112/112 PASS.
- Python: 74/74 PASS.
- History queue transport isolado: PASS.
- Restore PostgreSQL isolado, migração e replay idempotente: PASS.
- Public browser owner + Nicolas: PASS.
- Botão histórico real: PASS.

## Backups e rollback

- Backup: `/home/zeus/mgs-finance-backups/1547732274936553532/`
- Dump PostgreSQL SHA-256: `4e6fc1c18977ad989e0a468c59aa7575c0e8b96d0d9186f3dfd528930a683cd6`
- Código anterior, guard histórico e transporte de fila têm cópias separadas no mesmo diretório.
- Recoveries por workspace: `recovery-current-policy-1547732274936553532-*`.
- Ponteiro histórico anterior preservado em `recovery-history-pointer-1547732274936553532-*`.

## Evidência

- Operação: `/root/mgs-agent/work/finance-current-policy-1547732274936553532/`
- Browser: `/root/mgs-agent/apps/finance-system/private/current-policy-1547732274936553532/`
- Código: `/root/mgs-agent/apps/finance-system/`

## Follow-up — cards 100% (`1547790708344234056`)

- Os dois cards superiores da Dashboard foram alterados para `Líquido realizado · 100%` e `Estimativa do mês · 100%`.
- Readback público de setembro: realizado 100% USD 28.364,784923237337; estimativa 100% USD 94.549,28307745779.
- A composição societária e Pagamentos continuam em 50%; nenhuma linha financeira, pagamento ou permissão foi alterada.
- Cache bust de `app.js` atualizado em `public/index.html`.
- Validação: 113/113 Node, browser owner/Nicolas, 24 competências, desktop/mobile, zero JS.
- Backup remoto: `/home/zeus/mgs-finance-backups/1547790708344234056/`.
- Julho não foi alterado: BRL −1.090,05 preserva SB Tech Bot em CAD. BRL −1.144,60 corresponde à fórmula live que usa I1/GBP e conflita com a decisão canônica CAD `1547697182948458611`.
