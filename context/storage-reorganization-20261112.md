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

## Direção da revisão em oito pontos — 2026-11-13

Fonte humana: Rodolfo `1570799339108958250`, nesta mesma thread. Para esta iniciativa, o resultado desejado é preservar apenas o último backup validado da VPS e o último conjunto validado do Hermes, listar o que pode sair nas demais categorias sem comprometer a dashboard, dados, memórias, histórico, autenticação ou operação, e explicar a retenção real de caches e a necessidade do histórico Git local. Esta direção supersede a indefinição anterior sobre a quantidade desejada de backups VPS/Hermes; não constitui confirmação de um manifesto destrutivo, alteração automática de produtores, redução de retenção offsite nem autorização para descartar ativos únicos de outros domínios.

Checkpoint específico: `ZEUS-STORAGE-REVIEW-1570799339108958250`. Evidências: `data/storage-review-1570799339108958250/`. Backups locais de controle, código copiado, snapshots nativos, dump financeiro, backup operacional safety, backup Hostinger e DR criptografado são classes distintas; um arquivo de maior data não substitui as outras classes por nome/mtime. Dependências de código ativo e histórico operacional ficam protegidos até prova de cobertura ou decisão específica. A retenção desejada não está implantada por este registro.

## Segundo lote: estado histórico de testes gerados — executado

Rodolfo confirmou a aposentadoria deste lote em `1570486008917655623`, depois de esclarecido o efeito sobre os testes e a exclusão de memórias/perfis/produção do escopo. **Execução concluída e validada em 2026-11-12:** 60 clusters locais de teste e 21 exportações `.tar`, totalizando 81 alvos/61.283 arquivos ausentes. O aumento de espaço livre medido foi de 17.117.822.976 bytes (~15,94 GiB); a medição pós-validação registrou 75,25% de uso e 47,69 GiB disponíveis. Resultado: `data/storage-reorganization-1570447435074109502/generated-tests-1570473727043436596/cleanup-result.json`. Os seis fingerprints financeiros produtivos, quatro raízes de teste retidas, três fontes de entrada e 12 arquivos de controle dos perfis permaneceram iguais; os três agentes passaram em config/smoke e mantiveram PIDs. Nenhuma retenção futura foi alterada.

Registro histórico da preparação: o candidato delimitado foi `data/storage-reorganization-1570447435074109502/generated-tests-1570473727043436596/manifest.json`, com 60 clusters locais gerados por testes (`test-pg`, `catalog-test`, `ui-test`) e 21 exportações `.tar` desses testes, totalizando 81 alvos/61.283 arquivos e 17.122.353.152 bytes alocados (~15,95 GiB). A projeção no congelamento era 75,23% de uso; ela não substitui a medição real acima.

A origem foi conferida em `tests/api.test.mjs`, `tests/catalog.test.mjs` e `tests/workspace.test.mjs`: os testes abrem diretórios isolados com UUID novo e geram exportações de teste. Foram preservados os quatro diretórios explicitamente retidos na revisão anterior, os demais clusters não incluídos, fontes/fixtures, código, recibos e todos os bancos produtivos. A varredura não detectou processos nem referências literais em executáveis aos alvos. O verificador passou em modo read-only e bloqueou apply sem uma nova confirmação.

**Efeito irreversível confirmado e executado:** abandono do estado salvo dessas execuções antigas de teste e suas exportações, não exclusão de dados do banco produtivo. Isso é aposentadoria de histórico de teste, não deduplicação comprovada nem promessa de reproduzir exatamente o antigo estado a partir dos testes atuais. A confirmação anterior `1570460898970181713` valeu somente para os 28 dumps do primeiro lote; o segundo foi executado exclusivamente pela confirmação própria `1570486008917655623`.

**Correção da classificação inicial:** a localização em `candidate/private` não comprova recópia recursiva. A revisão encontrou ali bancos e arquivos criados pelos próprios testes. Os 13,67 GiB antes agrupados como evidência recopiada devem ser entendidos como ocupação dentro dessas árvores, não como 13,67 GiB de duplicatas comprovadas ou de falha de cópia.

## Terceiro lote: cópias locais financeiras com recuperação remota — executado

Rodolfo confirmou o manifesto `534f424d1b06c1713f9bc27f7d701b49a37d963f6e3f2b427b8414ac237b645d` na mensagem `1570808050183307336`, após a pergunta `1570807718049095735`. Foram excluídos exatamente 27 arquivos locais `mgs_finance-before.dump`, sem remover suas pastas. Economia imediata observada: 4.639.363.072 bytes (~4,32 GiB). As 27 cópias remotas foram revalidadas por tamanho, SHA-256 e catálogo legível antes da ação; quatro dumps locais (mais recente e três importações parciais) ficaram preservados. Seis fingerprints das tabelas financeiras permaneceram iguais em transações read-only; 563 arquivos de fontes, recibos e controles permaneceram iguais, incluindo 12 controles dos perfis. Zeus, Atena e Ares passaram em configuração e smoke sem ferramentas; PIDs dos gateways foram preservados e não havia units falhas. Resultado canônico: `data/storage-review-1570799339108958250/finance-lot/cleanup-result.json`. Não houve alteração de retenção, exclusão remota, SQL de escrita ou autorização para apagar materiais de perfis. O próximo ponto solicitado era apresentar a revisão de cópias de materiais nos perfis, sem avançar automaticamente para outro lote destrutivo.

## Ponto 2: cópias locais dos perfis — lote executado e validado

Rodolfo autorizou continuar a revisão em `1570811193906700471`. A varredura dos materiais Ares/Atena inventariou 63.469 arquivos sem erros; 12.111 mídias da Biblioteca Meta foram comparadas por tamanho, MD5 e SHA-256 com o índice histórico. As 858 correspondências locais apontam a 493 IDs remotos, todos aceitos pelo consumidor nativo do Ares com mapeamento/ACK/ancestrais/acesso e stream integral validados. Um GET de transporte retornou status 0 e foi recuperado por leitura nativa exata, sem mudança de credencial ou fallback de identidade.

O lote delimitado continha **754 cópias físicas locais** dos pacotes POUPLIX de 17/09 e 19/09: 308 + 446 arquivos, 571.994.112 bytes alocados (~0,53 GiB), somente arquivos, sem diretórios. A tarefa de origem está encerrada; baseline, inventários, comprovantes e comparações ficam preservados. As referências encontradas eram 12 JSONs históricos, não consumidores executáveis ou processos nas fontes verificadas. Os originais permanecem imutáveis, acompanhados de índice local-path → logical/provider/stock IDs e hashes. Material e proveniência continuam recuperáveis nos 30 TB pelo caminho nativo; somente os pathnames físicos das 754 cópias locais foram retirados após a confirmação.

Os 104 outros arquivos com correspondência permanecem fora do lote por não terem fechamento do trabalho de origem suficientemente reconciliado nesta revisão. As 11.253 mídias sem prova nesse índice também permanecem: ausência no índice consultado não prova ausência global no Drive. Todo o work da Atena fica preservado, pois ainda sustenta etapas SEO/schema/sitemap abertas e não possui cobertura remota integral comprovada. Histórico de conversas, memórias, logins, browser/collector/Playwright e recuperação operacional não integram os alvos.

Manifesto: `data/storage-profile-review-1570811193906700471/lot-754/manifest.json`, hash `1290b048ad7080c958bc74a2c191c3cbd2537a850571aad06cfc1a310e434011`. Na preparação, o executor passou no preflight e nos quatro negativos (contagem, escopo, drift de metadados, ausência de aprovação). O estado anterior de espera foi supersedido pela confirmação nativa de Rodolfo `1570817191878721637`, vinculada à pergunta `1570817111289241711` e ao mesmo manifesto.

**Executado e validado:** 754/754 arquivos ausentes, zero diretórios excluídos e 571.994.112 bytes (~0,53 GiB) efetivamente liberados. Antes da ação, 393 IDs lógicos selecionados foram novamente aceitos pelo consumidor nativo, ACK, ancestralidade, acesso e hashes; as provas de streams integrais já estavam preservadas. Depois, duas leituras remotas independentes passaram, 14 arquivos de evidência (incluindo 12 JSONs históricos) e 19 arquivos protegidos permaneceram iguais, incluindo três contêineres do navegador autenticado e 12 controles dos agentes. Zeus/Ares/Atena passaram em config e smoke sem ferramentas; PIDs foram preservados e zero units falhas. Não houve writes nos 30 TB, alterações de campanha, arquivos da Atena, retenção, credenciais, scripts do coletor ou runtime. Resultado: `data/storage-profile-review-1570811193906700471/lot-754/cleanup-result.json`. Checkpoint `ZEUS-STORAGE-PROFILES-1570811193906700471`. Próximo solicitado por `1570817230491492455`: ponto 3, revisão dos backups antigos VPS/Hermes com preservação do conjunto validado mais recente de cada classe; nenhuma nova exclusão está autorizada por este lote.
