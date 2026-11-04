# Entrada simples MGS e organização definitiva nos 30 TB

## Estado vigente e autoridade

**Implantado e ativo em 2026-11-02.** Resolver `data/ares/creative-ops/30tb-archive/flat-intake-binding.json` e `queue-config.json` para estado vivo; aprovação não substitui esses consumidores. Ativação: `flat-intake-1566814476626563115/activation.json`. O preflight bloqueado abaixo foi supersedido pela confirmação e pelo cutover validado, não permanece uma decisão pendente.

- Dono: Rodolfo Mattei, Discord `344196393512075265`, thread `1562078493498540042`.
- Redesenho confirmado em `1566814476626563115`, após proposta/pergunta `1566814035171868805` / `1566814036144685211`; evidência nativa em `authority.json`.
- Preservação/reaplicação dos mesmos acessos confirmada em `1566825959645253764`, em resposta a `1566816697044959233`; escopo congelado em `access-authority.json`.
- Permitido: mesmos usuários, leitura/edição equivalentes somente nos itens movidos e contêineres confinados; mesmos IDs, bytes e links; adaptar consumidores, intake e as duas skills Ares e espelhos já especificados.
- Proibido: exclusão/trash, novos usuários, membership/acesso geral aos 30 TB, ampliação para material não relacionado, credenciais/identidades alternativas, campanhas, budget, estratégia ou início. Regras de backup corporativo são outro escopo e não foram alteradas.

## Topologia e uso

- **Drive MGS** (`0AEwt4Ye690ocUk9PVA`): apenas `UPLOAD MANUAL` (`1ARBvLammWUHuAclNmcriwkkgeedKryBd`) na raiz ativa.
- **UPLOAD MANUAL**: arquivos enviados diretamente; sem pastas permanentes de operações/gestores. `_PROCESSAMENTO` (`1h8wEYDcn2SYLZI-Cp4dMpxfwFUqQXhpa`) é a única pasta técnica, interna e temporária; não é uma instrução para usuários separarem material ali.
- **30 TB / MGS-ARQUIVO** (`1jDcp9BOn-rusiRQ1t0MjJCby-qj0BL2J`): `CRIATIVOS`, organização permanente por operação/formato/gestor e `_MGS_CONTROLE`. As árvores de entrada antigas foram retidas como legado técnico controlado, não uma segunda entrada/pool.
- **30 TB / MGS-CORPORATIVO** (`16fP9b4bp3inB1Gze95znQLYq3rdtTEhp`): relatórios, referências e backups, com ACL por objeto; não herdar indiscriminadamente o acesso amplo dos criativos.

O pedido humano informa operação, gestor e destino; Ares registra a mensagem/autor/canal nativos e os IDs exatos via `scripts/ares_flat_intake.py register` (plano; depois `--apply`). O mesmo job `528c5710269d` consome o lote estável, sem writer paralelo. Upload sozinho não autoriza campanha. Fonte operacional Ares: `creative-operations-mgs/references/flat-upload-intake.md` e `direct-traffic-shein-operations`.

Tratamento conserva gates de IMG/VID, classificação factual, naming, sanitização, SHA/dedupe, inventário e reservas. Destino `common` organiza em `01_READY` sem liberar elegibilidade/reservas; `exclusive` entrega em `<NOME> - Exclusivos` depois do ACK. Somente uso de campanha comprovado passa a `<NOME> - Usados`; reupload exato preserva linhagem, reserva, uso e destino anteriores. Material sem contexto permanece intacto, não é atribuído ao gestor por adivinhação.

## Implementação e preservação

- `mgs_flat_layout.py`: manifesto congelado/CAS, permissões normalizadas por capacidade, ancestrais limitados, intents sem replay mutante ambíguo; PATCH/DELETE genérico do owner continua fechado.
- `mgs_flat_cutover.py`: 29 raízes e 247 objetos históricos relocados, incluindo 91 mídias com streams completos verificados antes/depois. Duas fontes pendentes foram normalizadas à entrada sem tratamento/classificação novos. `source-relocation-state.json` e snapshot/receipt publicados pelo controle SA preservam a prova e os mesmos IDs.
- Quatro itens permanentes da raiz (três Sheets / sete abas e um ZIP) movidos aos 30 TB com mesmos IDs/ACLs, fórmulas/valores/bytes e canário SA de escrita/leitura/restauração. Evidência `reports-state.json` e provas individuais.
- `mgs_flat_source_compat.py` valida snapshots/receipts nativos publicados por SA, associação exata de source ID e estado atual; consumidores históricos continuam lendo as fontes retidas sem reprocessar.
- `ares_archive_retirement.py` bloqueia DELETE no binding flat de preservação; `queue-config.json.delete_source=false`. Aprovações destrutivas antigas ficam como histórico, não são reaproveitadas neste modo.
- `mgs_flat_maintenance.py`: executado como subprocesso privado pelo monitor **existente**; arquiva gerações concluídas do staging por mesmo ID somente após conclusão/bytes/stock/ACK e encaminha relatórios permanentes que reapareçam na raiz. Limits técnicos: uma geração e até dois relatórios por ciclo; locks intake → queue, sem credencial owner no processo agente, sem novo cron e sem DELETE/trash.
- Prompt nativo do job e seis arquivos das duas skills/espelhos foram atualizados por rota autorizada; horário, modelo, delivery e demais settings do job preservados. Prova `ares-procedure-activation.json`.

## Validação e limite da aceitação

- Canário nativo não vazio: mesmo ID/bytes e mesmos 12 principais com capacidades equivalentes. A primeira diferença de herança em descendente foi retida como diagnóstico; propagação do Drive foi reconciliada antes de repetir a verificação, sem repetir movimento já realizado.
- Canário de entrada flat: mensagem humana nativa, plano sem writes de produção, arquivo técnico real, três polls em janela real de estabilidade, descoberta/contexto/claim local isolado e saída por mesmo ID. Zero linhagens/campanhas de produção criadas.
- Canário de manutenção: geração técnica e relatório na raiz encaminhados, bytes/ACL/ancestrais/receipts nativos validados, zero delete.
- 44/44 jobs históricos relacionados reconciliados com ACK/streams; nenhum bloqueio na aceitação. Testes focados e readbacks finais em `flat-intake-1566814476626563115/`.
- Primeiro novo pedido **real** após o cutover aceito: request `460f5b805715f8acc9727823559da3bb`, Kelly, thread `1566998348169220228`. Foram conferidas as 38 fontes exatas, 38 candidatos novos, zero duplicatas, 76 providers RAW/clean com streams completos, 38 sanitizações e reservas, 38 protocolos request/receipt/ACK e os 38 mesmos IDs originais preservados. Entrega Ares na origem relida nos IDs `1567037603189100556`, `1567037604925407323`, `1567037605856682147`, com os 38 pares original → final e links permanentes. Fonte: artifacts Zeus `ares-intake-pipeline-1567021305822314609/final-native-request-acceptance.json`. Isso fecha o gate de intake/arquivo/entrega real, não é criação nem aceitação de campanha.
- Readback da raiz fonte: `final-native-root-readback.json`. Na ativação havia 15 imagens sem contexto registrado, preservadas diretamente em UPLOAD MANUAL; não foram tratadas nem atribuídas implicitamente por esta autorização de organização. `_PROCESSAMENTO` estava vazio.

## Continuação mecânica por batch — `1567021305822314609`

Rodolfo confirmou a correção da rotina e dos procedimentos do Ares na thread `1562078493498540042`, preservando Ares como executor único, blocos de quatro, agendas, campanhas, acessos e gates. A implementação ativa é `scripts/ares_intake_archive_pipeline.py`, consumida pelo mesmo `ares_autonomous_intake.py complete`; binding em `intake-config.json.archive_pipeline_enabled` / `archive_pipeline_authority_message_id`.

Depois do tratamento e QA feitos pelo Ares, a continuação usa o produtor SA existente em até dois pares por passagem, executor owner isolado existente em até dois jobs/100s, helpers de ACK/atalhos e transporte de até quatro atalhos por tick. Os locks intake → queue, IDs e provas nativas são preservados; todas as mídias do batch precisam de provider/stock/ACK e streams completos antes de `complete`. A rotina não produz conteúdo, exclui, altera ACL ou executa campanha.

A espera flat por arquivo passa a `resume` com `mechanical_only=true`, evitando supressão silenciosa de uma etapa mecânica pendente. Replays preservam a primeira conclusão, provas, horários e recibos. O mesmo job pode continuar imediatamente os próximos blocos do mesmo request; não há novo cron, writer ou mudança de agenda. Não absorver outro request nem arquivos vizinhos. Procedimento Ares: `creative-operations-mgs/references/flat-upload-intake.md`.

Aceitação por pedido real e registros de implantação: checkpoint `ZEUS-KELLY-SUPERVISION-1567008464587456586` e artifacts Zeus `ares-intake-pipeline-1567021305822314609/`. Testes locais, ativação técnica e conclusão integral do pedido são gates separados; o estado corrente deve ser relido, não deduzido desta autorização.

## Consolidação das fontes preservadas — `1567557554018590782`

Rodolfo rejeitou a repetição de pastas de operação por lote e autorizou a correção na mesma thread. Esta decisão supersede somente a topologia permanente por geração de processamento; os snapshots/receipts anteriores continuam imutáveis e válidos como prova histórica. Preservar não significa manter múltiplas árvores de operação.

- Consumidor vigente: `scripts/mgs_flat_consolidation.py`, binding `data/ares/creative-ops/30tb-archive/folder-consolidation-1567557554018590782/binding.json`. Chamado pelo mesmo `mgs_flat_maintenance.py`, com leases intake → queue, sem novo cron ou writer paralelo.
- Os arquivos-fonte retidos são consolidados nos buckets **já existentes** de operação/formato/status dentro de `_MGS_CONTROLE/ENTRADA_ANTERIOR/PROCESSAMENTO_ANTERIOR`. Esse histórico técnico não é estoque nem entrada para gestores; a árvore de trabalho continua em `CRIATIVOS`.
- Cada geração recebe prova adicional imutável publicada pela SA, vinculada aos snapshots, jobs, assets e bytes originais. `mgs_flat_source_compat.py` aceita somente essas relocações exatas; não ignora nomes, pais ou integridade globalmente.
- Fontes, mídias permanentes e atalhos mantêm seus IDs. Não alterar estoque, reservas, elegibilidade, campanhas ou ACL. Canários técnicos e reuploads exatos sem novo job permanecem classes próprias, não novos criativos fictícios.
- As estruturas esvaziadas ficam separadas em `_ESTRUTURAS_VAZIAS`, com IDs preservados e rótulos técnicos, para reversão. Nenhum DELETE/trash foi autorizado; não confundir esses registros vazios com uma segunda pasta operacional.
- A manutenção consolida a geração depois da preservação; também recupera uma geração já preservada que ainda esteja sem aceite da consolidação, no máximo uma por tick. Dry-run não entra no caminho de mutação owner.
- Aceite inicial e estado corrente: checkpoint `ZEUS-FOLDER-CONSOLIDATION-1567557554018590782`; recibo `artifacts/folder-consolidation-1567557554018590782/closure.json` no profile Zeus. Não declarar conclusão apenas pelo monitor rotativo: conferir todos os membros congelados, consumidores, streams e paridade de inventário/mapeamentos.

## Histórico supersedido do preflight

Antes da confirmação específica, foram auditados 268 objetos e identificados 263 descendentes cujo acesso de `geizianp@gmail.com` era herdado de UPLOAD MANUAL e inexistente no destino. Roles organizer/fileOrganizer do Shared Drive não têm os mesmos nomes no My Drive; a equivalência autorizada é de pessoas e capacidades de leitura/edição, não administração/propriedade idênticas. Os quatro relatórios também exigiam ACL por objeto. Nenhum move/write de permissão ocorreu naquele preflight; o bloqueio foi resolvido exclusivamente pela confirmação `1566825959645253764`, seguida dos canários e manifestos confinados acima. Fontes imutáveis: `whole-source-native-acl-snapshot.json`, `access-preservation-proposal.json` e diagnósticos em `flat-intake-1566814476626563115/`.
