# Continuidade financeira — agosto/2026

Este documento preserva o ponto de retomada da thread Discord 1545426987756298340. A solicitação atual é conferir integralmente os gastos e as receitas de agosto na dashboard financeira. A autorização de recuperação 1551287899746598946 exige preservar esse contexto; não autoriza novas decisões financeiras nem apagar mensagens do Discord.

## Fontes e sequência

- Fonte de fechamento recebida em 1551042463060197386: https://docs.google.com/spreadsheets/d/1HoF7ihPzb0_oQIR5cZ0bsWd2b-_5jsHcKBalFi9HG7g/edit?gid=565588781 . Oito abas: rede 1 SB, rede 2 SB, rede AV consolidado, rede AV - detalhado, M2 consolidado, M2 detalhado, Facebook e Google; resolver nomes/coordenadas pelas leituras salvas e header vivo.
- Auditoria inicial completa: /root/mgs-agent/reports/finance-adops-reconciliation-1551042463060197386.md.
- Rodolfo respondeu aos itens em 1551275920671776839. Acrescentou o detalhado TopFeed em 1551279009415958700.
- Aplicação parcial e decisões: /root/mgs-agent/reports/finance-adops-application-1551275920671776839.md. Esse relatório é mais recente que o checkpoint antigo que dizia sem escrita financeira.
- Evidências completas e scripts: /root/mgs-agent/work/finance-adops-1551275920671776839/; final-summary.json, verify-out.json, plan.json, snapshots das fontes e correções da planilha.
- Skill dona: mgs-finance-dashboard, references/adops-monthly-source-reconciliation.md. Planilha principal histórica 16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak não substitui a nova Sheet de fechamento.
- Sessão original íntegra: 20260920_125643_eea54d90 em /root/.hermes/profiles/zeus/state.db; backup consistente protegido em /root/.hermes/profiles/zeus/secure-backups/finance-security-1551287899746598946/state-before.db. Todas as sessões anteriores da thread permanecem no banco e as mensagens no Discord. O resumo ativo não é a única cópia do histórico.

## Decisões que permanecem válidas

1. Comparação de RECEITA BRUTA (gross), antes de revshare/clawback; não confundir com payout líquido. AV consolidado governa o fechamento mensal.
2. Rodolfo excluiu a cauda duplicada de SB2. Readback: 794 linhas de dados, USD 87.151,00; SB1 é CAD e SB2 é USD. Não reimportar cauda antiga.
3. A nova planilha governa os gastos FB/Google por conta e dia, pois plataformas revisam gastos após o fechamento. Nada de ajuste artificial de gasto no último dia ou nova automação por inferência.
4. Infinitynexx pertence a Joe e Ícaro/G001 opera como convidado: preservar fonte tagged G001, incluindo CAD 923,5661480497590605 MX e CAD 1,322205407245324684 US; restante pertence a Joe. Não somar novamente complemento já contabilizado.
5. CPV05/16: corrigir atribuição pela fonte. EggbevFinanzas US$38,36 é 16/08; NewsounFinanzas US$41,25/38,94/33,56 é 18–20/08. Demais diferenças seguem conta/dia.
6. LyzmoFinanzas suffix02 é correto, ID1818460511984988 preservado; não fabricar histórico de nome Meta. Fincgriffin é SB Rede2/USD para agosto.
7. Ambos os reports Google cobrem 01–31/08; datas seriais dos primeiros12 dias estavam invertidas por locale. A normalização autorizada da importação não modificou essas células Google.
8. Wantabrand principal alvo USD4.604,04; Wantabrand Finance USD7,83. Referência atual preserva pg-19326 no Finance a partir da resposta afirmativa à pergunta anterior. Diante de nova dúvida de ownership, reler texto original em vez de reinterpretar o literal por conta própria.
9. M2: utm_campaign normalizada começando b01 é Direto; todo o restante, inclusive /empty/, é BOT. Novo detalhe fecha USD4.611,87; não voltar à antiga divergência do Profit Attribution como falta de fonte.
10. AV Eggbev consolidado USD59.978,57. Openzed AV foi separado por Rodolfo em G00312.637,77 + G0015,00. Preservar principal/complementar e medium correto.
11. Cliquet e Cliquet Finanzas: consolidados279,12/182,35 foram acrescentados; detalhados ainda faltam. Não reduzir a zero dias de receita ausente. TopFeed Finanzas consolidado6.937,50 é fonte de fechamento.
12. Boostingecon, Cephyric, DicasFinancas, Escalatepower e Mavroa: receitas residuais em agosto atribuídas G002/MGS, SEM ativar rateio de despesas gerais.
13. Permanecem ownership por gestor e moedas nativas, snapshots históricos fechados, câmbios e regras financeiras canônicas. Nenhum pagamento, campanha ou budget faz parte desta conferência.

## O que já foi aplicado e validado

- workspace-2026-08 revision392 e master-ad-accounts revision7; audit1513/1514. Recuperações bloqueadas recovery-adops-1551275920671776839 e correspondente -accounts.
- 48 contas Facebook + 2 Google;1550 checks conta/dia;199 correções de gastos.
- Facebook USD286.368,15; Google BRL71.174,24. Gasto consolidado USD300.349,7080935767661016147653 ao FX do período preservado.
- Receitas de21 sites com fonte completa SB (16existentes +5resíduos),814grupos +20linhas residuais,811correções gross. Não confundir esses21 com toda a carteira reconciliada.
- Cinco resíduos somam CAD1,3642065391097813660; rateio e despesas gerais preservados.
- Fincgriffin Rede2 e nome LyzmoFinanzas02 corrigidos.
- Células G701/G914/G1893/G2150 no AV detalhado corrigidas para numéricos1419,47/1309,12/1144,90/1145,41. Readback fórmula/unformatted/formatted e demais células preservadas.
- Zero erros de cálculo. O readback financeiro anterior foi SQL/result; não alegar aceitação visual autenticada que não ocorreu.

## O que ainda falta — não encerrar como conferência completa

- Ajustes gross AV/multirrede e M2 NÃO aplicados. PEND-092 continua aberta.
- Receita parcial da dash USD411.172,1132835894960372163176 NÃO é total final reconciliado.
- AV detalhado sem país; diferenças mensais do consolidado sem dia de origem; M2 sem país confirmado. O próximo passo é apresentar decisão sobre ajuste de fechamento mensal identificado separadamente versus distribuição explícita. NÃO inventar dia/país nem ratear silenciosamente.
- TopFeed recém-acrescentado:1677linhas, USD6.937,68 detalhado versus6.937,50 consolidado (excesso0,18). Datas1–12 vieram como seriais Jan08…Dec08 e posteriores texto US até08/19; normalização diária depende de validação, não da mera soma mensal.
- Eggbev detalhado corrigido59.978,59 versus59.978,57 consolidado (diferença0,02). A diferença antiga5018,88 era erro do helper que ignorava texto numérico.
- AV consolidado completo106.920,78; detalhado atual106.459,59. Detalhados dos dois Cliquet ainda pendentes.
- Ao retomar, não pedir novamente a Sheet nem repetir correções já aplicadas. Reler o estado vivo e comparar com os relatórios antes de qualquer nova escrita.

## Incidente separado e estado atual da recuperação

O backup do banco entrou indevidamente no Git público. Isso interrompeu a conferência, mas não desfez valores financeiros. A remediação autorizada em1551287899746598946 já rotacionou as seis senhas de Geizian, Ícaro, Isliago, Joe, Kelly e Nicolas nos respectivos itens existentes do1Password; revogou141sessões e8dispositivos. MFA preservado: chave não encontrada na varredura exata de todos os blobs Git alcançáveis. Rodolfo mantém sua senha; todos precisam autenticar novamente. Kelly já estava com enrollment pending, preservado.

O main remoto foi reescrito de modo controlado, sem o dump e sem mudança de tags; guard preventivo de dumps adicionado. GitHub ainda entregou o objeto antigo por SHA (HTTP206); isso exige remoção de dados sensíveis pelo suporte GitHub. Não declarar o incidente integralmente encerrado ou reexecutar trocas de senha/histórico na thread financeira. A pendência de suporte é acompanhada na thread1551285829584953484, separada da contabilidade.

A sessão financeira pode prosseguir na análise e nas decisões autorizadas de agosto. Nenhuma proteção do provedor ou2FA foi desativada. O pedido de confirmação antigo relativo à remediação já foi atendido nas camadas acima; não tratá-lo como comando novamente pendente.
