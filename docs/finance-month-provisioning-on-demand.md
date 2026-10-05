# Competências financeiras sob demanda

Dono: Rodolfo Mattei. Pedido1556656418319368243, confirmação adicional1556806857664897025, thread1556648387221397595.

## Decisão aprovada, ainda não implantada
Excluir operacionalmente novembro2026 até dezembro2027, preservando outubro2026 e anteriores, cadastros/contas compartilhados, auditoria, histórico e backups. Antes da exclusão, adaptar, ensaiar e publicar a rotina existente do último dia para criar somente o mês imediatamente seguinte ausente. Conservar23:04:25 America/New_York. Copiar somente configuração validada de sites, vínculos, contas, despesas e taxas apropriadas; jamais copiar receitas, gastos, pagamentos, saldos realizados ou ajustes históricos. Não reproduzir cotações liquidadas como nova cotação. Fonte Google de câmbio é assunto separado e permanece inalterada.

Esta decisão supersede o pré-cadastro de todos os meses futuros descrito na publicação histórica1546184035921829938. Mantém o restante do contrato de continuidade1555577386995552397/1555579357651537931 em docs/finance-account-ownership.md: configuração vigente no último dia, conflitos explícitos preservados, validação antes do primeiro import e exclusão dos ajustes históricos SMS. A decisão não equivale a implantação concluída.

## Ordem e limites
1. Conferir dados e dependências atuais; qualquer movimento/pagamento/fechamento futuro novo exige esclarecimento, nunca exclusão silenciosa.
2. Testar outubro→novembro com destino ausente, idempotência, concorrência, retry e rollback em ambiente isolado/restaurado; executar gates completos.
3. Publicar pelo controle canônico, com admissão/locks, backup/hash/journal e readback.
4. Só depois excluir as14competências numa operação transacional recuperável e validar ausência no banco, API owner/manager e seletor UI, além dos fingerprints preservados.
5. Não executar virada financeira em produção agora, mudar cron, criar outros meses por inferência, alterar credenciais/permissões, DROP/TRUNCATE tabelas compartilhadas ou excluir arquivos/backups.

## Estado verificado desta tentativa
Bloqueado antes de preparar/publicar código ou excluir dados:210eventos de auditoria mantêm chave estrangeira direta para os14workspaces. A exclusão física mantendo esses eventos intactos é impedida pelo banco; renomear os workspaces também é impedido pelo trigger de identidade imutável. Não foi escolhido arquivamento lógico nem removida/enfraquecida integridade referencial por inferência. Uma migração de referências/arquivo que conserve a auditoria exige desenho e alinhamento adicionais antes de retomar o mesmo objetivo.

Evidência e ponto de retomada: reports/finance-month-prune-1556806857664897025.md; checkpoint ZEUS-FINANCE-MONTH-PRUNE-1556806857664897025. A rotina produtiva original permanece ativa e ainda exige destino existente. Não tratar esta fonte como prova de mês sob demanda já disponível.
