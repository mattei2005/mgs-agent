# Setembro2026 — ponto3/Facebook concluído e monitor recuperado

## Autoridade e escopo

- Rodolfo1562609136909295721 autorizou corrigir todo o ponto3 após a explicação1562608013368365209: gastosFacebook de setembro naDash, conforme relatório de fechamento. Preservar receitasRede1/2,Google,demais redes, regras, pagamentos e outros meses.
- Fonte somente leitura: spreadsheet1ARyzDDEpVhlED6ndmHs1RC3pUlsJNQ20yTyZ6wSJVtA, abaGastos FB,gid374431172.
- Mensagem1562611302655066142 trouxe imagem do alertaFinanceiro/probe_TimeoutError; tratada pelo dever permanente de investigar/recuperar o monitor, sem inferir autorização para alterar finanças por causa do alerta.

## Resultado financeiro

- Dash antes:USD500.713,57.
- Relatório/Meta/Dash depois: **USD500.749,61**.
- Aumento de gasto: **USD36,04**. Diferença final: **USD0,00**, igualdade decimal exata neste conjunto.
-38 registros conta/data corrigidos em27contas/14sites, exclusivamente29/09(+1,70) e30/09(+34,34). São2datas, não38dias.
-29inputs legados e9registros nativosaccount_spend atualizados, preservando IDs/site/gestor/moeda e todos os demais campos.
-37/37totais mensais do relatório coincidem com uma consulta oficialMeta nova e com a soma dos dias.1110/1110controles conta/data aprovados e37/37controles mensais exatos;10contas já corretas preservadas.
- O valor textualUSD5045,00 daOpenzedFinanzas já estava naDash; não foi duplicado. Vizioid reconciliada pelo mesmoID536294549227786, sem criar outra conta nem duplicarUSD2153,08. Cadastro global e bindings permanecem na revisão19; o nome antigo do cadastro não foi regravado neste ajuste financeiro de setembro.

## Transação e validação

- Usado`planSpend` implantado para validar mapping/valores anteriores e conflitos manuais, com manifesto explícito dos38alvos. A autoridade antiga exigida pelo schema do parser é somente a versão do contrato de coleta; a escrita está auditada sob1562609136909295721.
- Workspace1651→1652; media-spend-2026-09 revisão34→35; audit4954/SEPTEMBER_FACEBOOK_SPEND_RECONCILED.
- Na mesma transação, corrigidos os valores doworkspace e os38registros correspondentes do controle de importação, sem alterar os outros2632registros desse documento. Total2670preservado; Google e registroszerados não foram substituídos.
- Prova/proveniência do fechamento adicionada separadamente emsummary.closing_reconciliations, preservando o recibo da descoberta/coleta anterior. Não foi anunciada uma nova descoberta exaustiva de contas a partir de uma consulta limitada às37contas positivas do relatório.
- Recoveries imutáveis:`recovery-fbclose-1562609136909295721` e`recovery-fbclose-1562609136909295721-spend`. Locks/advisory,CAS e readbacktransacional.
- Cinco visões de gestor aprovadas; lucros e remunerações recalculados pelas regras existentes. Nenhum pagamento, desconto extra noextrato ou alteração de campanha/budget/cobrançaMeta.
- Receitas gross/net/invalid/tax por fato e totais dasRedes1/2 preservados exatamente no mesmoFX; Google e DespesasGerais preservados. Ledgerde pagamentos e outros cenários preservados.
- Readback público autenticadoMFA, desktop1440/mobile390,1110valores de mídia,37totais, telaConferência, reload, cinco gestores e notaZytiva preservada:12checksPASS, zeroerroJS e zeroPOSTfinanceiro de teste. Sessão de validação revogada.

## Backup e ensaio

- Backup privado remoto:`/home/zeus/mgs-finance-backups/fbclose-close-1562609136909295721/finance-before.dump`.
- Local ignorado noGit antes da captura:`apps/finance-system/private/september-closing-1562564679400951829/fbclose-before.dump`.
-145600075bytes; SHA256db057474c20471ce9d720b7f291dc590b96d31fe77bf862810cf045a4a2b2274. Catálogo e cópias conferidos.
- Restore materializado`mgs_finance_fbclose_1562609136909295721`,237cenários com fingerprintsiguais. Stage`/home/mgsfinance/stage-fbclose-1562609136909295721`,65arquivos reais eNode verificados. Artefatos retidos, sem exclusão.
- Ensaio, aplicação isolada, verificação/idempotência e depois aplicação/readback de produção aprovados. Fonte relida antes/depois sem alteração.

## Alerta mostrado na imagem — causa e recuperação

- Alerta em#vps-status: mensagem1562610122742833226, estadofalho23:34:44.963805UTC,codeprobe_TimeoutError.
- Causa: o monitor aguardava no máximo8s pela admissão compartilhada; o backup autorizado deste ajuste mantinha admissão exclusiva. A cópia local do dump foi concluída23:34:44.877439UTC e o backup/restauração só liberou a seção crítica ao concluir23:35:34.053501UTC. O caminho de collect confirmaTimeoutError da lease; timeoutSSH usaria outra classe. Não houve evidência de divergência financeira ou indisponibilidade daDash.
- Repetição real após a liberação:15/15combinaçõesworkspace×gestorPASS. Estado persistido ok,failure_streak0,alert_signaturelimpa. Recuperação publicada e relida:1562611766758744097, canal1522444367292268565.
- Redução de recorrência aplicada somente a`scripts/finance-readonly-health.py`: o erro exatofinance_release_admission_busy_no_changes passa a serdeferred, sem avançarlast_success, declarar cobertura ou limpar incidente aberto. Se uma nova observação ainda está bloqueada≥5min apósdeferred_since, escala contenção prolongada. Isso é limiar entre observações, não um novo scheduler5min. Timeouts diferentes e falhas reais continuam no caminho de primeira falha.
-12testesPASS: lock real emdiretórioisolado, classe/exceção exata, timeoutdesconhecido, preservação de último sucesso/incidente, escalada, recuperação, dedupe e mockHTTP. Script implantado repetido:15/15PASS,notice_sentfalse, sem novo alerta duplicado.
- Cronhorário e timeout240s preservados; nenhum serviço, credencial, permissão, schema ou regra de negócio alterado. Não foi necessário alterar código do aplicativo financeiro.
- Backups do monitor e testes anteriores retidos em`.../monitor-recovery/`. Procedimento de contenção salvo emlog-monitor-discord-alert/references/route-pack-06.md.

## Continuidade

Evidências financeiras:`apps/finance-system/private/september-closing-1562564679400951829/point3-*`, incl.sourcefresh,manifesto,backup,stage,production,final-independent-checks e snapshotfinal1652. Aceitepúblico:`apps/finance-system/private/facebook-closing-1562609136909295721/`.

Procedimento de fechamento de gasto atômico salvo em`mgs-finance-dashboard/references/adops-monthly-source-reconciliation.md`. CheckpointprincipalZEUS-FINANCE-SEPT-CLOSE-1562562282838429729.

Ponto3 encerrado. Próximo:ponto4/Google — diferença conhecida de apresentação por precisão (R$111547,89 na soma dos dias arredondados versusR$111547,927996 naDash). Não houve correçãoGoogle nem avanço paraM2 neste turno.
