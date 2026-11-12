# Reorganização de armazenamento da VPS MGS

## Autoridade e estado

- Dono: Rodolfo Mattei, Discord `344196393512075265`.
- Pedido: `discord:1569928464033783862/1570447435074109502`.
- Direção autorizada: identificar o que é redundante ou deixou de ter uso, preservar a operação, confirmar os alvos antes da exclusão e reorganizar produtores/retenção para evitar reacúmulo.
- Estado: **primeiro lote de 28 dumps locais redundantes excluído e validado em 2026-11-12**, por confirmação nativa de Rodolfo `1570460898970181713`, vinculada ao manifesto `c999586429f3227b665da1b17c4141dcb008e03b779f8efb18bb1b0a8c5fb489`. Nove representantes locais e nove cópias remotas foram preservados. Nenhuma nova retenção automática foi ativada; as outras categorias não foram autorizadas para exclusão por essa confirmação.
- As confirmações críticas do AGENT.md permanecem obrigatórias. Este pedido não é confirmação de um manifesto ainda não apresentado.

## Separação de armazenamento

A VPS não deve ser tratada como arquivo histórico ilimitado. Separar estado ativo e recuperação operacional necessária de evidência histórica de tarefas encerradas, mídias entregues e ambientes de teste. Para mídia e material corporativo, resolver a topologia vigente em `context/drive-flat-intake-cutover.md`; os 30 TB não são um filesystem de execução da VPS, e a existência de uma pasta remota não comprova cobertura de todos os arquivos locais.

Material único ou de uso ainda não esclarecido permanece preservado até ter uma destinação validada. Não inferir descartabilidade de idade, nome, ausência de processo, mtime ou sucesso de uma limpeza anterior. Backup de credenciais, sessões autenticadas e dados financeiros não podem ser enviados a uma pasta de criativos ou receber ACLs amplas. Não alterar a identidade Google, os consumidores de outros agentes ou suas skills sem o gate correspondente.

## Frentes e critérios de aceite

1. **Financeiro:** separar dumps, clusters locais de teste, fontes financeiras e cópias de evidência dentro de candidate/stage. Demonstrar bytes idênticos, recuperação retida, ausência de consumidores e manifesto exato antes de remover redundância. Evidência única exige preservação validada ou decisão explícita sobre a perda histórica.
2. **Perfis:** conferir entrega remota por IDs/tamanho/hashes e fechamento da tarefa. Separar RAW, variantes, fontes, evidências e entregáveis. Um item não encontrado no manifesto histórico consultado não deve ser descrito como ausente de todo o Drive. Preservar bancos de sessão, navegador autenticado, locks e runtimes operacionais.
3. **Hermes:** preservar runtime ativo, rollback imediato e dependências Git/ambiente. Resolver worktrees, alternates, scripts com caminhos fixos e customizações não commitadas antes de chamar versões antigas de sem uso.
4. **Produtores e recorrência:** a limpeza imediata e a prevenção são entregas separadas. Inventariar os produtores grandes, eliminar recópia recursiva de evidências e definir a retenção por classe com integridade e consumidor reais. Uma proteção existente em um helper não prova adoção universal. Não inventar um prazo global nem habilitar exclusão recorrente por esta direção geral.
5. **Fechamento:** medir espaço efetivamente liberado, preservação de dados/recuperação e efeito real nos produtores. Não fechar a reorganização por um lote parcial ou por documentação.

## Primeiro lote delimitado

Manifesto: `data/storage-reorganization-1570447435074109502/finance-duplicate-lot.json`.

São 28 arquivos locais de dump redundantes, com 9 representantes locais byte-idênticos preservados e 9 cópias remotas validadas por hash/tamanho e catálogo pg_restore. Este lote não inclui pastas, fontes, JSONs financeiros, banco produtivo, perfis, versões do Hermes nem retenção futura. A leitura do catálogo não é prova de restauração materializada. O executor é read-only por padrão e recusa apply sem uma nova confirmação nativa de Rodolfo vinculada ao hash do manifesto e ao executor.

O restante da investigação permanece com Zeus no checkpoint `ZEUS-STORAGE-REORGANIZATION-1570447435074109502`. Fonte de medição e gates: diretório `data/storage-reorganization-1570447435074109502/`.
