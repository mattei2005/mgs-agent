# Competências financeiras sob demanda

Dono: Rodolfo Mattei. Thread1556648387221397595. Pedido1556656418319368243; confirmação inicial1556806857664897025; confirmação adicional vigente1556898264878419969 (“pode fazer”).

## Decisão ativa e supersessão

A confirmação1556898264878419969 supersede exclusivamente a retenção da auditoria e dos resíduos exclusivos dos meses vazios de novembro2026 a dezembro2027 imposta na decisão1556806857664897025. Não há arquivamento operacional desses meses. Outubro2026 e anteriores, cadastros/contas compartilhados, fontes imutáveis compartilhadas, histórico/ledger, usuários/auth/sessões, logs institucionais, reports históricos e backups globais permanecem protegidos. Backup técnico obrigatório de implantação é rollback, não um arquivo operacional de meses.

Esta regra também supersede o pré-cadastro de todos os meses futuros da publicação histórica1546184035921829938. Mantém a continuidade de configuração vigente no último dia e os limites financeiros de1555577386995552397/1555579357651537931; não autoriza transportar fatos, pagamentos, saldos, ajustes históricos SMS ou cotações liquidadas. Fonte Google de câmbio permanece separada e inalterada.

## Implantação verificada

- Release principal `month-demand-1556898264878419969`, seguida por `month-demand-ui-1556898264878419969`, ambas publicadas pelo controlador canônico. Os dois arquivos existentes do runner em scripts/ foram publicados por bootstrap estreito separado, revisado, com admissão exclusiva, backup, hash, journal e readback, pois o controlador regular exclui scripts/.
- PostgreSQL produtivo: removidos transacionalmente14workspaces (`workspace-2026-11` a `workspace-2027-12`),140snapshots recovery exclusivos e210audit_events exclusivos. Zero entity_versions/acceptance_runs dependentes. Não foi usado rename, DROP/TRUNCATE, desativação de FK/trigger nem alteração de grants.
- Só permanecem os workspaces agosto/setembro/outubro2026; histórico janeiro–julho segue disponível. API e seletor exibem10competências existentes de janeiro a outubro2026. API direta das14competências removidas retorna404; não é ocultação seletiva.
- Cron integral permanece byte-idêntico: último dia às23:04:25 America/New_York, via `scripts/finance-month-rollover.py --scheduled` e guard calendário. Nenhuma virada/criação futura foi executada em produção nesta tarefa.

## Contrato da rotina

`workspace.mjs:provisionNextPeriod` cria somente o próximo mês ausente, com advisory lock para destino inexistente, locks de linha da fonte/cadastro, cálculo validado e commit único do workspace, vínculos mensais, recibo e auditoria. Replay não altera revisão; destino existente permanece intacto. Conflito explícito de vínculos ou fonte inválida falha sem escolher mapeamento por inferência. O comportamento histórico anterior a novembro2026 e a opção recalc permanecem separados.

A configuração usa allowlists: sites/identidades/vínculos, definições de despesas/pessoal e taxas pertinentes. Charges datadas, status/datas de conferência e recarga antiga SMS não viram novos lançamentos: mantêm-se definições, mas não os valores realizados datados. A compra pré-paga de SMS não retorna como despesa. Receitas, account_spend, pagamentos, saldo/carry, custos diretos históricos SMS e cutoff realizado não são copiados. FX automático usa cotação provisória disponível; cotação confirmada/liquidada não é herdada como nova liquidação. Todas as taxas novas ficam provisórias. `registerPeriods` sem lista é no-op e rejeita reseed futuro de novembro2026 em diante.

Seletores resolvem preferência/URL de mês removido para competência realmente existente. O marcador opaco de atualização incorpora a lista de workspaces para detectar também exclusão sem criar evento financeiro artificial. Nenhum mês histórico existente é desviado.

## Evidência e continuidade

- Relatório: `reports/finance-month-prune-1556898264878419969.md`.
- Evidências: `apps/finance-system/private/month-prune-1556898264878419969/`.
- Checkpoint estável: `ZEUS-FINANCE-MONTH-PRUNE-1556806857664897025`.
- Registro sucessor: `FINANCE-MONTH-PROVISIONING-1556898264878419969`.
- Relatório anterior1556806857664897025 permanece histórico, sem apagamento; seu bloqueio por retenção de auditoria foi resolvido pela nova autoridade, não por enfraquecimento do banco.

## Aprendizado específico desta execução

FK não determina retenção de um filho que Rodolfo já confirmou excluir. Inventariar propriedade/dependências reais, usar a identidade administrativa existente e apagar filhos exclusivos antes dos pais numa única transação. Proteções continuam ligadas. Snapshot que aponta para import compartilhado não autoriza apagar esse import. Backups e fontes mistos não se tornam exclusivos por conterem um mês futuro.

Na homologação, separar produção de stage: mgsfinance tem HBA restrito ao banco produtivo; stage PostgreSQL usa o peer administrativo existente e SET ROLE da aplicação, com binário/dependências copiados por allowlist, sem mudar HBA, ACLs ou grants produtivos. O limite de transporte foreground420s exige execução exaustiva particionada de unittest, com prova de todos os IDs descobertos/executados exatamente uma vez e zero skips; nunca declarar gate completo após timeout.

Durante a execução one-shot, a edição de skills estava bloqueada; o aprendizado foi primeiro preservado nesta fonte e no report/checkpoint. No encerramento pelo Zeus da thread de origem, o roteamento e a regra de dependências exclusivas foram incorporados à skill `mgs-finance-dashboard`; auditoria integral de estrutura/links da skill passou (41 arquivos Markdown, zero issues). Isso não altera código ou dados financeiros.
