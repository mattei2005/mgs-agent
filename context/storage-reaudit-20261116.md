# Reauditoria global da VPS — ciclo 1571983565292441731

## Autoridade e fronteira

- Dono: Rodolfo Mattei, Discord `344196393512075265`, thread `1569928464033783862`, pedido `1571983565292441731`.
- Nova direção: refazer a auditoria de toda a VPS e dos sistemas locais atuais; reiniciar a sequência de classificação passo a passo até encerramento. Não repetir exclusões já concluídas nem reutilizar aprovações antigas.
- Caches continuam pausados pela decisão `1571982102264549498`: foram medidos apenas para reconciliar a ocupação, sem proposta de descarte nem retenção automática.
- Auditoria dos sistemas **instalados nesta VPS**, não auditoria funcional de todas as plataformas externas, sites RunCloud, campanhas ou fontes financeiras. Produção/configurações/serviços permaneceram sem mutação por esta auditoria. Foram criados registros e procedimentos próprios.
- Fonte de execução: `data/storage-reaudit-1571983565292441731/`. O inventário antigo é contexto histórico, não baseline atual nem confirmação de novos alvos.

## Etapa global realizada

Varredura independente de `/`, `/boot` e `/boot/efi`, sem atravessar mounts, pseudo-filesystems ou imagens Snap somente leitura. Ledger privado completo com caminhos, tipos, device/inode, tamanhos, blocos, hardlinks, modos/donos/mtime e destinos de links. Nenhum banco foi aberto ou iniciado. Somente os marcadores textuais `PG_VERSION` foram lidos para identificação de raízes de clusters; isso não certifica descartabilidade.

A partição `category-role-ledger.json` reconcilia os blocos por inode e explicita hardlinks compartilhados. Não somar tabelas de detalhe aos pais nem converter ocupação em espaço removível. A coleta é uma observação concorrente, não snapshot atômico. Os arquivos criados pela própria análise ficam em raízes separadas e são contabilizados como custo novo, não como resíduo preexistente.

O mapa de sistemas contempla serviços instalados/carregados/em execução, processos e seletores de caminhos existentes, listeners TCP, pacotes do sistema, aplicações locais, crons de sistema/root, scripts periódicos, timers e agendamentos dos perfis. Prompts, argumentos completos, conteúdo de credenciais e valores financeiros não foram publicados. Rotinas comerciais não foram disparadas para testar funcionamento.

## Sistemas e papéis

- **Zeus, Ares e Atena:** gateways locais, histórico/sessões/checkpoints, ferramentas, mídias e diretórios de trabalho mapeados separadamente. Uma pasta de trabalho não é automaticamente memória, e um snapshot histórico não é a instalação ativa.
- **MGS Router:** serviço local ativo com binário em `/opt/mgs-router/mgs-router` e estado em `/var/lib/mgs-router`; o código em `apps/mgs-router` é uma classe distinta.
- **Fila SHEIN do Ares:** serviço local ativo; não foi invocada execução de campanha nem alterada fila.
- **Financeiro:** código, helpers, materiais de execução e bancos locais identificados. A implantação produtiva é documentada em MatteiInc01 nos runbooks, fora do host auditado. Esta etapa não conectou à produção remota nem alterou dados/regras. O helper Meta lookup local estava inativo com `Result=success`/exit0; isso sozinho não configura falha do sistema financeiro nem prova sua saúde funcional.
- **Infraestrutura de suporte:** cron/timers, auto-versionamento, SSH/Tailscale, proteção, logging, update automático e backup/restore existentes inventariados; nenhuma agenda ou política foi alterada.

## Pico temporário reconciliado

O snapshot capturou um workspace nativo `tmp/mgs-dr-backup-uipjbqf9` com ZIPs intermediários e upload criptografado. A fonte `scripts/mgs-offsite-backup.py:948-1024` usa `TemporaryDirectory`; o agendamento horário `3ff8bd8ca40d` e o recibo exato `mgs-dr-hourly-20261116T202348Z.zip.gpg` confirmam a origem. O produtor registrou PASS e stream SHA-256 remoto verificado; o workspace desapareceu pelo seu ciclo nativo. Não é nova exclusão desta auditoria, anomalia ou economia atribuível a Zeus. O recibo local não substitui um novo restore remoto, que não foi executado.

Fonte: `transient-backup-reconciliation.json`. A medição atual de disco deve ser lida no resultado final e não confundida com o pico observado durante a coleta.

## Primeiro aprofundamento de conteúdo

Os 326 arquivos da classe de archives/exportações/SQL do financeiro foram lidos integralmente por `sha256sum`, em lotes de baixa prioridade, sem cópia de payload e sem drift de metadados. Foram encontrados somente cinco grupos byte-idênticos em inodes independentes, com duplicação alocada potencial inferior a 1 MiB, ainda sem certificação de consumidores/recuperação. Isso não prova que os grandes arquivos têm conteúdo lógico único: wrappers, timestamps ou estados internos podem diferir. Tampouco prova que são úteis ou descartáveis. A deduplicação simples não libera os gigabytes apresentados como ocupação dessa classe.

Fontes: `finance-footprint-classes.json`, `finance-archive-content-review.json`; hashes/grupos completos em ledger privado. Nenhum alvo de exclusão novo foi certificado.

## Sequência nova de trabalho

1. **Financeiro local:** classificar os clusters locais e os arquivos de execuções/exportações antigas por produtor, encerramento, consumidor/evidência e recuperação. Começar pelo estado de testes remanescente; preservar fontes/checksums acoplados e um conjunto compatível quando houver consumidor de família. Ausência de processo não prova falta de uso.
2. **Trabalhos e testes dos agentes:** revisar workspace/work/codex-pilots remanescentes por tarefa, separando ferramentas, estado único, material entregue e execuções encerradas. Não remover diretórios inteiros por nome/idade.
3. **Mídias, artefatos e relatórios:** validar linhagem/consumidores e recuperação pelo backend aprovado antes de retirar cópias locais; preservar trabalho editorial ou criativo aberto.
4. **Backups e snapshots locais:** resolver conjunto validado vigente, histórico único e dependências dos compactos/bases. A diretriz latest-only não elimina automaticamente classes diferentes nem prova cobertura de estado antigo.
5. **Código/runtimes e Git:** remapear runtime ativo, rollback imediato, ferramentas, worktrees e alternates; separar profundidade histórica local de dependências reais. Não apagar `.git`, reescrever história ou retirar bases por esta auditoria.
6. **Demais arquivos de sistema e temporários não-cache:** concluir classificação de resíduos e logs sem desinstalação, truncamento ou alteração de retenção implícita.

Cada família terá ledger residual próprio: necessário comprovado; preservado pendente de prova; candidato com gate; concluído; ou mantido por decisão do dono. Ao encontrar um lote realmente validado, apresentar somente esse lote e pedir a confirmação crítica exata. Não pedir novamente autorização genérica para continuar a análise já solicitada. Sem novo manifesto/confirmacão, nenhuma exclusão está liberada.

## Passo 1 — diretórios locais de testes, continuação 1571996311308214363

Esta continuação supersede somente a afirmação anterior de que ainda não havia lote novo preparado. Os 34 diretórios foram classificados: seis com dependência identificada ou preservação explícita anterior; 25 preservados pendentes de esclarecer evidência/consumidor histórico (não declarados indispensáveis); três candidatos exatos à aposentadoria de estado de testes. Fonte ativa: `data/storage-local-tests-1571996311308214363/`.

A busca percorreu 286.507 fontes indexadas: 286.500 foram lidas; sete arquivos históricos de `cron/output` desapareceram antes da leitura e continuavam ausentes na conferência. A origem individual dessas sete remoções concorrentes não foi atribuída, e elas não foram chamadas de anomalia nem de leituras bem-sucedidas. Nenhum arquivo existente teve erro de leitura. Houve complemento de 6.381 logs textuais; binários dos clusters e conteúdo de archives foram excluídos da busca de referências. O coletor inicial excedeu o transporte de 420s; confirmou-se sua ausência, preservaram-se os parciais e a coleta integral foi refeita com matcher de prefixos e batches de 160s, cobertura final contígua por índice e validação de positivos reais/limites de diretórios. Não houve duplicação de executor ou mutação dos alvos.

As três raízes candidatas ficam exclusivamente em `apps/finance-system/private/charge-date-1571201800063680562/candidate/private/`:

- `ui-test-5a826fc1-d673-4f4c-aab8-023cd3ec4da7`;
- `test-pg-4a583d60-d608-4277-b755-a3f0d1f3628a`;
- `catalog-test-dd6d8f6e-d31a-45f4-8517-9037f3f30e11`.

Não foram encontradas referências a esses três UUIDs nas fontes/logs declarados nem uso por processo, FD, cwd, exe ou maps. A tarefa charge-date consta publicada/validada no relatório canônico; os geradores criam UUID novo, não reabrem esses três caminhos. Cada família mantém sua contraparte com vínculo explícito à evidência; essas três contrapartes estão incluídas nos 31 diretórios preservados. A raiz padrão `private/pgdata` e `networks-1546579646227943506/isolated-pglite` são dependências reais de código/helpers e estão fora do lote. Os quatro diretórios expressamente preservados no lote de testes anterior também ficam.

Lote congelado `588641e9824ab904d00bb1c9f356e7956b2488a9e69dceceeb83c71f9a94a620`; gate `2ff2819b90ca0be30a2348a77d3a570a39ef9ea7c86b18168333051b7dcf23ab`. Três raízes/3.064 arquivos regulares/81 diretórios incluindo raízes/zero links; 646.762.496 bytes alocados potencialmente liberáveis (~616,80 MiB), com todos os payloads regulares single-link. Duas passagens de metadados coerentes, alvos não versionados, preflight real PASS, 16 testes de bloqueio/ordem PASS (aplicação simulada com todas as chamadas destrutivas mockadas; nenhuma exclusão real). Os 31 diretórios retidos tiveram 31.565 payloads hasheados e revalidados; 21.757 fontes de código/config/agendamentos estão presas por census/hash, com definições de cron separadas dos contadores de execução. A checagem focada desse census também não encontrou os três UUIDs.

**Efeito irreversível:** aposentadoria do estado persistido dessas três execuções antigas de QA, não deduplicação lossless nem promessa de reconstrução byte a byte dos três bancos. Ficam fontes, geradores, relatórios, uma contraparte de cada família (incluídas nos 31 diretórios retidos), recuperação, programas e produção remota. Nenhum banco foi aberto/iniciado, lógica/valores financeiros foram avaliados ou alterados, nem houve deploy, restart, novo backup de payload, cache cleanup, cron ou retenção nova.

**Custo da análise:** os novos índices/ledgers/provas desta etapa, inclusive intermediários do passe interrompido, ocupavam 160,79 MiB na medição de proposta. A estimativa líquida direta é ~456,01 MiB, sem custos compartilhados futuros do Git. Nada foi liberado ainda. Esses intermediários são criação desta auditoria, não novo lixo preexistente encontrado na VPS; sua consolidação lossless e eventual retirada dos raw devem continuar no ledger próprio após o fechamento, com gate exato, sem limpeza implícita.

**Revalidação anterior à pergunta de exclusão:** o lote original `588641e9824ab904d00bb1c9f356e7956b2488a9e69dceceeb83c71f9a94a620` fica como preparação supersedida, nunca confirmada/executada. Alterações concorrentes em helpers do Ares mudaram somente o census de código externo; as três árvores e os 31 retidos ficaram idênticos. As alterações foram reconciliadas por handles de REPORT-INFRA e commit, sem referência aos três UUIDs ou leitores PostgreSQL nos arquivos alterados. Após três observações de código iguais, o **mesmo gate, byte a byte**, foi exercitado novamente com baseline atualizada. A preparação intermediária `revalidated-code-baseline-1/manifest.json`, SHA-256 `0d201fea271739ee0e534f17306a63b660c49beb866156905980038d30aaba3a`, passou então, mas foi novamente bloqueada antes da entrega por mudanças em helpers Meta alheios aos três bancos. Fica histórica e não executada, junto da original, sem alterar nenhum dos dois verificadores congelados.

**Proposta ativa:** `data/storage-local-tests-1571996311308214363/active-lot.json` aponta agora a `target-consumer-census-v2/manifest.json`, SHA-256 `e8c3b11124414ec881a3b4e23592a86d6d1dd99e1f1cefe56bfb3f7175e5394d`, gate novo `5b7b9f9203226a13a5be4a4a76366c042980bc0b638f12b414203c59736b3e00`. A correção foi feita ainda sem nenhuma confirmação/exclusão: o census anterior acoplava qualquer edição de qualquer agente à limpeza local. O novo lê todas as superfícies atuais para negar seletores exatos dos três alvos; congela todas as fontes financeiras e possíveis leitores locais de banco, mais cada definição individual de job pertinente, ignorando apenas código/jobs não relacionados e contadores de execução. São 14.689 entradas pertinentes presas por hash; nenhuma proteção de alvo, 31 retidos/31.565 payloads, inputs/geradores, runtime, mount, symlink, hardlink ou aprovação foi retirada. Preflight real PASS e 16 testes-base+9 regressões de escopo PASS; as regressões provam mudança externa não bloqueante versus novo leitor/UUID, fonte financeira, política e job pertinente bloqueantes. Não houve rollback de outro operador ou ampliação dos três alvos. O custo/ganho corrente é o de `active-review-final.json`, não a primeira medição histórica de proposta.

**Lote executado e validado:** Rodolfo confirmou a pergunta `1572024090628325479` pela mensagem `1572075298164580365` nesta thread. O gate congelado `e8c3b1112441` passou novamente e retirou somente as três raízes: 3.064 arquivos e 81 diretórios, 3.145 nós exatos, sem entradas extras ou duplicadas no journal. A validação independente confirmou ausência de todos os nós e preservação dos 31 diretórios/31.565 payloads por SHA-256, fontes/geradores, definições pertinentes, launcher e PIDs dos três gateways. Três config checks passaram; nenhum banco foi iniciado, SQL/modelo executado, cache limpo ou serviço reiniciado. Delta observado imediatamente antes/depois: 646.230.016 bytes disponíveis a mais (616,29 MiB); não confundir com a projeção líquida histórica que descontava os índices da auditoria. Fonte de execução: `data/storage-local-tests-1571996311308214363/target-consumer-census-v2/independent-post-validation.json`; fechamento: `retirement-final.json` na mesma pasta. Não repetir fases já executadas nem iniciar outro lote por implicação. Os 25 preservados por falta de prova e as famílias 2–6 continuam abertos. Checkpoint: `ZEUS-STORAGE-LOCAL-TESTS-1571996311308214363`.

## Passo 2 — revisão dos 25 pendentes, pedido 1572091759247368262

Fonte ativa desta continuação: `data/storage-pending25-1572091759247368262/`; escopo somente leitura/preparação, os seis anteriormente protegidos fora de descarte e os três já retirados não repetidos. Os 25 diretórios permanecem iguais ao freeze anterior e sem referência de processo. Census pertinente de código/config/agendamentos inalterado; revisão adicional de 5.129 arquivos locais dos produtores, seletores relativos ao módulo e relatórios canônicos. Menções em inventários de disco foram separadas de consumidores/evidências reais. Uma consulta histórica limitada recuperou listagens de inventário, não o produtor original dos UUIDs/API antigos; não foi alegada exaustividade histórica.

Classificação completa: seis no novo lote exato; nove preservados como dependências/evidências de verificação; dez preservados pendentes de proveniência/recriação certificada. Os seis previamente fora do recorte continuam intactos. Publicação do antigo pedido `1551358728870035530` é confirmada pelo relatório final; o checkpoint histórico ainda diz pendente. Essa divergência foi registrada como documental, sem reabrir publicação ou alterar a fonte financeira.

**Novo lote preparado, não executado:** somente `stage-db`, `stage-db-v2`, `stage-db-v3`, `stage-db-v4`, `stage-db-v5` e `stage-db-v6`, dentro de `apps/finance-system/private/network-month-1552101423754514465/`. O helper final seleciona `stage-db-v7`, preservado junto de `stage-result.json` PASS, publicação committed, inputs/fontes e backups. Os seis antigos aparecem em inventários históricos, não como leitores atuais. Aposentadoria de estado histórico intermediário QA, não duplicação byte-idêntica ou promessa de restauração byte a byte.

Manifesto `04efa1a46f2dd64bb8ceaebc4d9ab7d4246c301b734dc14919e586699bb5dbc5`; gate `9f38d1b9428925d877c23acee23b11ca58c24862f25f5c1c4487f2b225ab4a37`. Seis raízes, 6.130 arquivos/162 diretórios incluindo raízes, 1.250.856.960 bytes alocados potencialmente liberáveis (~1,165 GiB). Custos desta nova análise ~2 MiB, sem descontar novamente os índices anteriores; projeção líquida direta ~1,163 GiB, sem crescimento compartilhado futuro do Git. Nada liberado nesta etapa.

Gate exercitado: preflight real PASS, 16 testes-base + 18 regressões de seletores/escopo PASS. Todos os unlink/rmdir da simulação foram mockados; apply nativo sem nova aprovação foi negado. Os outros 25 diretórios atuais (19 deste recorte + seis anteriores), com 25.435 payloads, tiveram preservação/hash conferidos. Nenhum banco iniciado, SQL/modelo executado, pacote instalado, cron/retenção/serviço/produção alterado ou exclusão feita. Nenhuma autorização anterior vale para este lote; aguardar confirmação crítica específica. Resultado/continuidade: `classification-final.json`, `manifest.json`, `review-final.json` e checkpoint `ZEUS-STORAGE-PENDING25-1572091759247368262`.

## Estado de encerramento da fase global — histórico

Levantamento global de armazenamento e sistemas locais concluído; primeiro passe de conteúdo financeiro concluído. A revisão semântica de descarte **permanece aberta**: a varredura não prova que todo o restante é necessário nem que qualquer categoria inteira é inútil. Nenhum arquivo original foi removido por Zeus, nenhum programa atualizado, serviço reiniciado, credencial alterada ou cron/retenção criado. Etapas antigas encerradas continuam históricas.

Fontes ativas: `audit-final.json` e `category-role-ledger.json` no diretório desta reauditoria. Checkpoint de fase `ZEUS-STORAGE-FULL-REAUDIT-1571983565292441731`; checkpoint global `ZEUS-STORAGE-REORGANIZATION-1570447435074109502`. O próximo recorte continua sendo a classificação de uso/recuperação dos dados locais de testes do financeiro, não mais caches.
