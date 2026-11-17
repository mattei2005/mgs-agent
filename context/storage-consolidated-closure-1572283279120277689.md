# Encerramento consolidado — auditoria de armazenamento

Decisão de Rodolfo: mensagem `1572283279120277689`, thread `1569928464033783862`. Dono da execução: Zeus.

## Situação confirmada

- Lote `f4fa14fa1105`: 29 cópias locais removidas, zero diretórios; originais remotos e 294 payloads retidos conferidos. Recuperação remota dos 29 arquivos repetida com sucesso depois da exclusão, sem SQL ou banco iniciado.
- As frentes abaixo vêm da sequência canônica de `context/storage-reaudit-20261116.md`; não são novos lotes liberados para apagar.
- Esta decisão substitui, nesta iniciativa, o modelo de trazer um pequeno lote e pedir `continue` para cada família. A auditoria não está concluída e nenhuma nova exclusão está aprovada.

## Todos os blocos pendentes

1. **Financeiro local remanescente:** esclarecer os 61 dumps preservados e os 232 outros arquivos da coorte original (181 SQL e 51 archives/distribuições/testes). Fechar as lacunas dos estados de teste já preservados sem reexecutar exclusões anteriores nem tratar esquemas, dados únicos ou dependências como lixo. Separar provas suficientes de preservação pendente; nenhum banco antigo precisa ser iniciado para inventariar.
2. **Trabalhos e testes dos agentes:** revisar workspace/work/codex-pilots por tarefa e consumidor; preservar ferramentas, sessões e trabalho aberto; identificar somente sobras de execuções encerradas com recuperação comprovada.
3. **Mídias, artefatos e relatórios:** separar material entregue, evidência necessária e cópias recuperáveis; provar a cópia remota pelo backend aprovado antes de propor retirada local. Não tocar produção editorial/criativa em andamento.
4. **Backups e snapshots locais:** fixar o conjunto atual de recuperação por classe, preservar histórico único e bases/checksums acoplados; não presumir que o backup mais novo substitui qualquer estado antigo.
5. **Código, runtimes e Git:** manter runtime ativo, rollback imediato, fontes, worktrees e alternates necessários; avaliar apenas resíduos e história local opcional, sem apagar `.git` ou alterar histórico remoto implicitamente.
6. **Arquivos de sistema e temporários não-cache:** concluir resíduos/temporários/logs sem desinstalar programas, truncar logs ou alterar retenção por implicação. Caches continuam fora.
7. **Índices e intermediários desta própria auditoria:** consolidar as evidências sem perda, contabilizar custo criado por Zeus e identificar cópias substituídas. Qualquer retirada requer alvo exato; não misturar esse custo com lixo preexistente.
8. **Decisão final e encerramento:** reunir os alvos que realmente passarem em um único pacote exato, com subtotais, volume líquido, recuperação e exceções; manter o que não passou com motivo objetivo. Pedir a confirmação destrutiva conjunta somente após validar esse pacote. Depois executar uma vez, conferir preservação/recuperação, espaço real, inventário e fechar a revisão geral. Reportar à parte os geradores que podem voltar a acumular; mudar retenção ou cron continua sendo decisão separada.

## Atualização vigente — qualificação final

O rascunho 643/`9f8ed9ae3408` descrito abaixo foi retirado antes de confirmação: bytes remotos não demonstram encerramento local das 304 mídias, que ficam integralmente preservadas. **O único pacote ativo tem 339 cópias JSON de 24 tarefas encerradas, cobertas por 15 primários, zero diretórios, 2,917 GiB líquidos diretos estimados e 32 testes aprovados.** Manifesto `2bd02d697289938382699ffe82ca24aee1e692cf0cf0bd799d967e1861c29537`, gate `6017bcf6a34c40cf56a77578513eb05ffce558c2b44267ce489595aab0c23f91`; fonte `context/storage-consolidated-pass-20261117.md` e `data/storage-consolidated-review-1572313312987979957/finance-final/`. Nada apagado. A próxima decisão é somente essa confirmação exata conjunta, sem nova sequência de continue por família; preservar tudo que não passou continua obrigatório.

## Atualização anterior — rascunho 643 retirado

As sete frentes foram reunidas na passagem `1572313312987979957`, com cobertura/limites e destinos registrados em `context/storage-consolidated-pass-20261117.md` e `data/storage-consolidated-review-1572313312987979957/consolidated-result.json`. O resultado para decisão é **um único pacote de 643 cópias locais**: 339 JSON com 15 primários preservados e 304 mídias com 248 IDs nativos de arquivo verificados. Potencial líquido direto estimado 4,808 GiB; zero excluídos nesta passagem. Manifesto ativo `9f8ed9ae3408e31d4796587a85b92cddc0fc9d3501a3e1c50ec93c15b2a977f9`; gate `e1021fc7af0cf21a73bd28c20b0750d3c8467b7c1824274b70b1eb0d5c196f78`. Preflight real e 34 testes passaram.

O ledger explicita dependências reais, exclusões por escopo e preservação sem prova suficiente — não certifica necessidade de todo o restante. Nenhum diretório, banco, perfil, cache, credencial ou objeto remoto está no pacote. O próximo gate é uma confirmação crítica nova para esse manifesto conjunto, não outro `continue` nem uso do `sim` do lote anterior. Antes dessa confirmação, nenhuma nova exclusão está aprovada. A conclusão da limpeza ainda depende da execução e validação desse gate; não declarar a VPS inteira semanticamente validada.

## Forma de condução

A leitura/classificação já autorizada não exige novo `continue` por item. Não abrir novo ciclo de aprovação a cada pequeno achado. Interromper apenas por bloqueio decisório real ou Critical Subset independente; não transformar este plano em autorização para exclusões desconhecidas. A existência destes blocos pendentes não significa que todos tenham espaço descartável certificado. Não há nova quantia global liberável demonstrada neste plano.
