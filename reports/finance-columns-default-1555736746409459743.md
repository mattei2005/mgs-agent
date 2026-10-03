# Layout permanente dos gestores — novembro e posteriores

Autoridade: Rodolfo `1555736746409459743`, thread `1545426987756298340`. Estado: **publicado e validado**. Supersede somente o limite setembro/outubro do release `1555702482557075539`; preserva seu desenho, fórmulas e dados. Contrato ativo: `docs/finance-manager-columns-sep-oct.md`.

## Resultado

- As duas tabelas (diário de 13 colunas e resumo realizado/estimado com referências 7%/10%) passam a ser padrão dos cinco gestores em novembro/2026 e todas as competências posteriores.
- Setembro/outubro continuam iguais. Agosto/2026 e anteriores preservam o layout histórico.
- Vigência por competência válida `YYYY-MM >= 2026-09`, sem lista fechada ou teto de ano. Novas competências herdarão o layout quando forem cadastradas. Esta execução não criou meses financeiros.
- Não altera dados, regras de receita/custo, comissão, pagamento ou ROI. Meses sem dias completos não recebem projeções inventadas.

## Implementação

Somente a condição de vigência em `public/operations.js` e o teste de fronteiras em `tests/manager-layout.test.mjs`. CSS e todos os componentes financeiros permanecem iguais.

SHA256:
- JS local/remoto: `d0db32b2d4d6cb17dc845465236b26279f8684fd9d3fa8e4c7e239ce91b140cf`.
- Teste local: `fe88bd68d90fab459285b7b45aaeef8de839b3016959a2c162ec8b0412ac34f3`.

Publicação pelo controlador canônico, release `columns-1555736746409459743`, journal committed. Recarregado somente o serviço financeiro remoto conforme protocolo; gateway Hermes, socket e PostgreSQL preservados, serviços ativos.

## Validação

- Gates completos e atuais: **245/245 Node** e **193/193 Python**, sem skips/falhas. Testes incluem fronteiras agosto/setembro, novembro/dezembro, virada de ano, 2028/2035 e rejeição de mês malformado.
- Auditoria de dependências de produção: zero vulnerabilidades reportadas.
- Stage e produção, cada fase: **160 telas autenticadas**, cobrindo os cinco gestores em todas as competências cadastradas de setembro/2026 a dezembro/2027, viewports 1440/390; **2.914 verificações de grupos** de domínio/país/TOTAL.
- Conferência dos cabeçalhos, origens, componentes, lucro, ROI, totais e referências/projeções; agosto mantido como controle negativo.
- Zero requisição financeira de escrita, zero erro JS, zero falha HTTP same-origin, sem overflow global. Sessões MFA de validação revogadas; sessões humanas preservadas. As telas dos gestores foram verificadas pela prévia administrativa legítima, sem alegar novos logins individuais.
- Fingerprints de todos os cenários/revisões/resultados/overrides/additions, ledger e história imutável exatamente iguais imediatamente antes/depois do cutover e após browser produtivo.
- Nenhum processo de gate ficou pendente: execução silenciosa concluída e resultados consumidos antes do cutover.

## Backup e evidência

Diretório privado: `apps/finance-system/private/columns-default-1555736746409459743/`, incluindo manifest, stage/browser, gates, runtime readback, audit de dependências e `backup.json`.

Dump remoto `/home/zeus/mgs-finance-backups/columns-1555736746409459743/finance-before.dump`, catálogo validado e cópia local com SHA256 idêntico. Backups exatos de código em `apps/finance-system/private/releases/columns-1555736746409459743/`. Não foi executado novo restore materializado nesta mudança de apresentação. Rollback é somente de código sob admissão, não restauração de banco sobre atividade posterior.

Contrato e skill financeira atualizados com supersessão explícita; registry mantém somente a nova vigência ativa da chave canônica. Inventário/audit/REPORT-INFRA completam a entrega operacional.
