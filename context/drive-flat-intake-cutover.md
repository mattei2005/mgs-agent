# Cutover para entrada simples MGS — 1566814476626563115

## Autoridade vigente

- Rodolfo Mattei (`344196393512075265`), mensagem de confirmação `1566814476626563115`, thread `1562078493498540042`.
- Proposta real: mensagens `1566814035171868805` e `1566814036144685211`; a última contém a pergunta crítica explícita. Ambas e o autor da confirmação foram relidos por Discord nativo. Evidência `data/ares/creative-ops/30tb-archive/flat-intake-1566814476626563115/authority.json`.
- Autorizado: aplicar o redesenho descrito em `context/drive-two-location-layout-review.md`, preservando arquivos, links e acessos; adaptar código/fluxo de tratamento e arquivo e os procedimentos Ares `creative-operations-mgs` e `direct-traffic-shein-operations`, inclusive espelhos. Esta confirmação supersede a pendência de aprovação geral do redesenho na auditoria anterior.
- Excluídos expressamente: exclusões e alterações de acessos. Não há aprovação de mudança de credencial, campanha, budget, fonte de autenticação ou acesso amplo aos 30 TB. A SA permanece canônica; o owner isolado permanece limitado às operações aprovadas.

## Preflight e bloqueio decisório confirmado

Estado: **redesenho aprovado; implantação ainda não iniciada, aguardando confirmação específica da preservação técnica de permissões na mudança de tipo de Drive**.

- Metadados/capabilities e `permissions.list` paginado foram lidos para os 268 objetos ativos do Shared Drive, pelas identidades autorizadas nas superfícies correspondentes, sem escrita remota. Fonte imutável `whole-source-native-acl-snapshot.json`.
- Nos 263 descendentes da entrada, há acesso de `geizianp@gmail.com` herdado de UPLOAD MANUAL, com role `writer`. Esse principal não está no ACL atual do arquivo de 30 TB. A pasta de entrada permanece protegida e não está autorizada a ser movida por esse cutover.
- O Shared Drive também usa roles `organizer`/`fileOrganizer`; My Drive usa `owner`/`writer` e não oferece esses mesmos nomes de role. Portanto, igualdade literal de roles não pode ser prometida entre os modelos. A preservação pretendida deve ser conferida como mesmos usuários e capacidades de leitura/edição, respeitando a distinção de propriedade e administração de Drive.
- Sem um gate específico para preservar/reaplicar os acessos existentes, não é seguro assumir que a nova herança mantenha todos os usuários. Não testar essa suposição movendo material produtivo, não conceder acesso ao Drive inteiro e não ampliar genericamente o owner transport.
- As quatro peças permanentes da raiz têm ACL próprio, incluindo convidados em três Sheets. Não herdar indiscriminadamente o compartilhamento amplo de criativos para relatórios corporativos; preservar por objeto. Não inferir criador a partir de lastModifyingUser.
- Proposta técnica delimitada: `access-preservation-proposal.json`. Ela registra diagnóstico e alvos prospectivos; não é autorização executável. Antes de canário ou produção, congelar manifesto exato da fase, destino e snapshot de permissões; validar a mesma fonte e seus IDs/versões novamente.

## Decisão nova necessária

Permitir, somente nos objetos efetivamente movidos e seus contêineres confinados, a retenção/reaplicação dos acessos que esses mesmos usuários já têm hoje, com capacidades equivalentes de leitura/edição no modelo de My Drive. Não adicionar pessoas, não conceder membership no Drive de 30 TB e não abrir outras pastas do arquivo. Não converter permissões mais restritas de relatórios em acesso geral. Novo usuário, alteração de papel além da equivalência necessária ou diferença inesperada continua bloqueada.

A pergunta deve explicar em linguagem comum que o compartilhamento atual é herdado da entrada e pode não acompanhar a mudança; a confirmação geral do redesenho já existe e não deve ser solicitada novamente. Depois da decisão, usar canário isolado e readback de acessos/IDs/bytes antes da produção. Preservar todos os gates do fluxo original, não iniciar campanhas e não excluir arquivos.

## Estado da execução

- Nenhuma pasta/arquivo do Drive foi movido, renomeado, excluído ou teve permissões gravadas neste preflight.
- Nenhum script produtivo, configuração de intake, cron ou skill do Ares foi alterado para o novo desenho. O fluxo existente permanece ativo, sem writer paralelo, até cutover seguro.
- Evidências preparatórias e este checkpoint foram salvos. Não apresentar o redesenho como implantado nem dizer que só falta documentação.
