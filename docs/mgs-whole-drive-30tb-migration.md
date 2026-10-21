# Migração integral MGS-AGENTS → conta de 30 TB

## Autoridade e supersessão

Rodolfo `344196393512075265`, thread `1562078493498540042`, definiu o novo escopo em `1562459142814306425`, recebeu a explicação do desenho e autorizou iniciar em `1562459803186626571`. Objetivo: migrar TODO o conteúdo do Shared Drive `0AEwt4Ye690ocUk9PVA`, não apenas CRIATIVOS, para a conta `mgsdigitalcorp@gmail.com`; deixar no Drive empresarial somente a entrada `CRIATIVOS/UPLOAD MANUAL`, suas pastas-pai e a estrutura temporária estritamente necessária; tratar via Ares, arquivar original+tratado, validar e liberar staging após pelo menos 24h da verificação/liberação do processamento. Sem mensagens de progresso; informar apenas 100% validado, necessidade real de editor Apps Script ou bloqueio de segurança/Critical Subset.

Esta fonte supersede o limite anterior de migração apenas criativa para o objetivo integral; a migração criativa já autorizada permanece válida e continua pelo mesmo writer/locks. Não ampliar implicitamente o manifesto histórico criativo nem sua política de exclusão futura. O pedido autoriza implementação e migração; não dispensa confirmação crítica de exclusão/credenciais/permissões novas ou alteração de skills de outros agentes.

## Descoberta integral real

Evidência: `data/ares/creative-ops/30tb-archive/whole-drive-migration-1562459803186626571/{inventory.json,discovery.json,source-access.json}`.

O inventário inicial completo/paginado contém 7.884 objetos ativos e 228.215.846.168 bytes reportados, sem parents não resolvidos. A árvore CRIATIVOS tem 7.771 objetos; `_DISASTER_RECOVERY`, 102 objetos e 200.820.560.275 bytes, com 97 arquivos criptografados. Existem oito planilhas nativas, distribuídas pela raiz, Meta Utility Templates e referências da Atena. O conjunto pode avançar por produtores autorizados; revalidar antes de mutações, nunca congelar o universo futuro pelo número de hoje.

## Invariantes

- Usar exclusivamente SA canônica para agentes; owner Apps Script isolado já aprovado para operações que exigem propriedade/cota Gmail. Sem token pessoal, OAuth alternativo, consentimento de navegador ou mudança de autenticação.
- Preferir recursos/IDs preservados para Sheets, links, atalhos e backups; provar por canário antes de mover produção entre Shared Drive e My Drive. Cópia de uma Sheet não preserva o ID e não equivale a migrar suas dependências.
- Preservar o acesso efetivo por item, sem ampliar os colaboradores de arquivos restritos. O root Shared Drive tem quatro principais (owner Gmail, Rodolfo, support e SA); o arquivo criativo tem onze principais. NÃO copiar backups criptografados para um pai com nove colaboradores criativos e tratar herança como paridade. Nunca descriptografar backups apenas para migrar armazenamento.
- Preservar criptografia, hashes, catálogo, retenção e restore funcional dos backups. Mudar só destino sem ajustar produtor, retenção, verificadores e recuperação não satisfaz automação integral.
- Preservar fórmulas, IMPORTRANGE, IDs de abas, formatação, permissões e consumidores/Apps Script das oito Sheets. Inventariar dependências antes do cutover; registrar erro preexistente separadamente.
- Preservar IDs lógicos, reservas, catálogo, campanhas e elegibilidade do Ares. Migração de armazenamento não autoriza campanha, budget ou novo tratamento do histórico.
- Nenhum arquivo histórico, pasta, atalho, backup ou Sheet será apagado para forçar fechamento. Exclusão exige o gate aplicável, cópias e consumidores completos, prova contra corrida e receipt real.
- Criativos históricos seguem no protocolo atual até o novo protocolo ser provado e deliberadamente promovido; sem writer paralelo, duplicação ou mudança de escopo dos requests existentes.

## Próxima fronteira do proprietário

O worker Google ativo e seu bootstrap estão limitados a CRIATIVOS. Não conseguem inspecionar/migrar o escopo corporativo por comando SA. Uma extensão hash-pinned precisa ser publicada e deliberadamente repinada no mesmo Code.gs; preservar manifesto, consentimentos e o timer. Primeiro provar capacidades reais do proprietário e o modelo de acesso dos alvos corporativos, sem mover/copiar/deletar produção nesse probe. O fato de a SA mostrar `canMoveItemOutOfDrive=true` não comprova o comportamento ou propriedade resultante quando executado pelo owner Gmail.

## Fases de aceitação

1. Autoridade/escopo e inventário integral, ACL por item e dependências de Sheets/produtores.
2. Extensão owner publicada/testada/relida; repin deliberado e receipt nativo com capacidades/restrições do owner. Não promover pin ativo antes da execução real.
3. Canário de transferência mantendo ID e acesso ou, se inviável, cópia com cutover completo de IDs/dependências e ACL restrita explicitamente resolvida.
4. Migração delimitada das áreas corporativas, mantendo ordem de dependências e recuperação; todos os bytes/objetos conferidos.
5. Ajuste e prova de todos os produtores/leitores/backup/restore/retention para destino de 30 TB; nenhum crescimento permanente no root antigo fora do staging autorizado.
6. Concluir acervo criativo, leitores e atalhos; adequar pipeline para armazenamento antigo apenas temporário abaixo da entrada preservada.
7. Executar somente a retirada autorizada após os gates aplicáveis; verificar árvore residual real e funcionamento integral, então reportar 100% com evidências. Até isso, iniciativa permanece aberta.

## Preparação executada e gate Apps Script

Oito Sheets reais foram lidas pela SA com Drive + Sheets API e baseline persistido: 163 abas, três fórmulas e nenhuma dependência IMPORTRANGE literal encontrada. Isso não comprova ausência de consumidores externos/Apps Script; esses continuam no gate de cutover. Nenhuma Sheet de produção foi copiada, movida ou alterada.

Criada uma única Sheet técnica vazia `1x6GzlsvFzFKoZ9lHI5n8G-uxfctD37LjqWkwOkH69G4`, marcada validationOnly, fora do catálogo Ares. A listagem de propriedades atrasou após o POST inicial; o ID existente foi reconciliado e reutilizado, sem segundo POST. A implementação agora valida o ID retornado diretamente antes de confiar no índice de busca.

Manifesto SA de probe: ID `10UR_TxYDpTZhwfQ8sWj0OuJt7Dlrqcw2`, SHA-256 `9153478b8dbf4703c25806685cbd893b72c3c0f8bb73ed3908ff01d34136a238`. Quinze alvos exatos; somente leitura em produção. O único movimento permitido pela extensão é ida/volta da Sheet técnica fixada, com restauração imediata, intenção durável e reconciliação de resposta ambígua. Nenhuma chamada DELETE ou escrita de ACL é implementada. O teste observa separadamente acessos antes e depois e não transforma uma perda de herança em grant automático.

Versão anterior, supersedida pela correção abaixo: ID `1eYTggn8T3SWpKewqowuvcVvzSPV4bOH0`, SHA-256 `c95545733270833409466a01f9c04d4ee64149d9665e4e1b40182d3fb85e3ac3`, fonte `integrations/creative-archive-30tb/WorkerWholeDriveProbe.js`. Esta versão não é o pin vigente. O pin SA ativo e o backfill histórico não foram alterados na preparação. Passaram 11 testes JS do probe/composite, oito testes Python de aceitação/rollback e oito regressões Python do histórico. A primeira rodada da fixture Python usou hash staged antigo e foi corrigida para testar o candidato sem mudar o hash real de produção; a rodada final passou integralmente.

Ação externa necessária: no MESMO Code.gs, trocar somente o ID de `DriveApp.getFileById(...)` e o SHA de `if(hash !== ...)` pelos valores vigentes da seção de correção abaixo; salvar e executar apenas `mgsArquivoTeste`. Não alterar manifesto, timer, consentimentos ou Implantar. Este repin habilita a inspeção/canário do novo escopo, não declara a migração corporativa pronta.

Retomada Zeus: `python3 scripts/mgs_whole_drive_migration.py status`; verificar receipt owner, quinze alvos, prova real de restauração da Sheet técnica e capacidades/permissões observadas. Esperar heartbeat AGENDADO do novo SHA e trigger existente `2456112746912022528`, então `accept-owner` promove atomicamente os pins SA/histórico, mantendo flags, manifesto de criativos e cópias existentes. Rodar o tick comum e conferir recorrência; só então definir/executar a migração corporativa preservando IDs/ACL e produtores. Não pedir novo consentimento nem recriar timer para substituir essa verificação. Os comandos `prepare`/`publish-probe` são preparação, não aceitação live.

## Correção do validador e diagnóstico — versão anterior

A imagem de Rodolfo em `1562471409740021896` confirma execução do código após o loader e erro `WHOLE_DRIVE_PROBE_SOURCE_CHANGED`, iniciado 10:22:42 AM e encerrado 10:23:25 AM. O erro anterior não incluía ID/campo, portanto o campo exato observado pelo proprietário ainda não foi provado. A SA releu os quinze alvos sem divergência; a evidência nativa demonstra `files.get(root).name=Drive` e `drives.get(root).name=MGS-AGENTS`. Comparar esse rótulo da raiz virtual como identidade entre principais era um defeito do validador, mas não se deve afirmar que esse foi o campo específico da execução owner sem receipt.

A raiz agora é vinculada por `drives.get` e ID nativo. Os outros nomes, todos os IDs, MIME, parents e driveId continuam estritos. Uma divergência registra ID, campos esperados/observados em receipt owner e bloqueio no heartbeat, em vez de abortar silenciosamente antes das evidências. Limite de cinco tentativas/cooldown e preservação do receipt de restauração do canário evitam replay/loops.

Código anterior, supersedido pela correção de visibilidade abaixo: ID `1npryxflWsy8Lvx3LS7cnbivYp4ejyns-`, SHA-256 `4641e3f0a2f038347b2c5785d578eac1e73abe80d793cc7a58ed6956df6805dd`. Passaram dezoito testes JS, oito de aceitação Python e oito do backfill. Evidência `source-guard-diagnosis-1562471409740021896.json`.

Correção ainda NÃO executada/validada no Google. O proprietário precisa repinar somente ID/hash no mesmo Code.gs e rodar mgsArquivoTeste. O pin SA permanece anterior, nenhuma migração corporativa/exclusão/ACL foi aplicada, e a Sheet técnica foi relida na origem. O último código owner falhou antes do heartbeat, interrompendo o ciclo; não descrever o fluxo como saudável até nova execução real e recuperação validada. Não alterar timer/manifesto/credenciais nem reescrever requests para contornar o erro.

## Visibilidade do pai My Drive — pin staged vigente

A imagem `1562474366359310489` e o receipt owner nativo lido pela SA identificaram o alvo/campo real: `1jDcp9BOn-rusiRQ1t0MjJCby-qj0BL2J`, `parents`. O manifesto SA tem `[]` porque o pai não é projetado para a SA; o proprietário vê `[0AET_Qs3G4VFwUk9PVA]`. A resposta anterior comprovou execução da versão nova e progresso criativo parcial, mas NÃO sucesso do probe: `blocked` não estava vazio, `wholeDriveProbe.status=blocked` e `productionMutation=false`. O canário sequer foi movido. Receipt, publisher, expected/observed e releitura SA estão em `archive-parent-diagnosis-1562474366359310489.json`.

A correção trata somente o ID exato do archive root: não confunde parent omitido com parent vazio. Exige que o pai visto pelo owner seja o root My Drive obtido de `files.get('root')`, com propriedade da conta autenticada e MIME de pasta. Pais arbitrários, owner errado e todos os pais de fontes permanecem bloqueados. O resultado registra essa prova nativa. A identidade do root visto pelo proprietário ainda precisa ser confirmada pela execução desta nova versão, não foi presumida pelo prefixo do ID.

O top-level agora retorna `blocked` quando o probe estiver bloqueado, mesmo que uma cópia criativa tenha avançado. Passaram 23 testes JS, oito testes Python de aceitação e oito do histórico, incluindo visibilidade de parent e rejeições. Fontes criativas, requests, manifesto fixado, retenção e ACL não foram reescritos.

Único pin staged vigente: ID `1MFz88EdhGmAk86PIf7wkm6gP0b23OxIf`, SHA-256 `e4f32e02e99f29021030a58cc2a0b20a9eef35dc23e4d4e8af8e10c271a30728`. O estado anterior de repin não executado é supersedido pela comprovação abaixo; a aceitação integral continua pendente. Após receipt de conclusão/canary restaurado e heartbeat scheduled saudável com o novo digest, `accept-owner` promove os dois pins sob lock e valida rollback. A migração corporativa e seu fechamento integral continuam pendentes.

## Repin confirmado; pausa pelo limite interno de execução

Rodolfo enviou a imagem `1562558490449412126`, cuja execução manual consta concluída. A SA verificou o heartbeat owner nativo `1bfYo56Nx3tShQCQsHez9IsQphawbesT_`: novo SHA às `2026-10-21T20:09:23.484Z` manual e às `2026-10-21T20:13:02.198Z` com o mesmo trigger `2456112746912022528`. Ambos informam `runtime_budget_paused`, sem exclusão pelo owner. Isso comprova código repinado/agendamento preservado, NÃO execução do probe corrigido: o guard de runtime está antes dele. O receipt ainda é o bloqueio da versão anterior, não uma nova falha do validador corrigido.

O código pausa se o ledger móvel de 24 horas atingir 3.600.000 ms ou 350 entradas. A SA não enxerga esse ledger privado; não está comprovado qual dos dois ramos disparou nem o horário exato de liberação. Não é comprovada uma quota Google excedida. Não zerar propriedades, elevar o limite, recriar timer ou pedir novos Runs/edições: aguardar a janela pelo agendamento existente.

Corrigido no reconciliador SA o erro secundário `RETIREMENT_ACTIVATION_NOT_PINNED`: o bloqueio por saúde/reconcile-only agora é um argumento de execução, sem falsificar `queue_enabled=false` dentro do contrato destrutivo validado. Nenhuma flag produtiva, pin ativo, aprovação, request, mídia ou ACL foi alterada por essa correção. O monitor expõe status/digest/agendado estáveis do owner; a transição da pausa para execução real acordará o mesmo job `83b148017b4d`, sem novo cron/writer. Testes: 28 de automação Python, oito de aceitação Python, 23 cenários JS; dry-run real e monitor real agora mostram a pausa exata, sem erro secundário. Evidência `runtime-budget-diagnosis-1562558490449412126.json`.

Próxima ação autorizada após a liberação: ler receipt novo, validar todos os alvos e restauração live; verificar heartbeat saudável agendado do novo SHA; só então `python3 scripts/mgs_whole_drive_migration.py accept-owner` e tick comum. Monitor mantém a retomada; a iniciativa não está concluída. Não há ação necessária de Rodolfo no editor neste estado.

