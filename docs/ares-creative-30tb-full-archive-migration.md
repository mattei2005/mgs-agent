# Migração integral do acervo criativo para os 30 TB

## Decisão e estado atual

Rodolfo esclareceu em `1562256530454220851`, thread `1562078493498540042`, que o destino permanente é o arquivo inteiro nos 30 TB, inclusive o acervo existente. O Drive empresarial de `support@matteiservicesinc.com` deve ficar apenas como entrada/tratamento temporário e, quando necessário, estrutura de atalhos/controle. A mensagem autoriza preparar e copiar o acervo; não interpretar a atualização de documentação como substituta da migração real.

A conclusão anterior cobriu somente o fluxo de novos arquivos. Ela NÃO encerra este objetivo integral. O estado de runtime continua com `include_historical=false`: não alterar essa flag do controlador de novas origens, cuja autorização exclui histórico. Criar backfill delimitado e verificado, sem remover o histórico por essa política anterior.

## Fronteira do pedido

- Acervo de criativos sob `MGS-AGENTS/CRIATIVOS`, root `1h8wEYDcn2SYLZI-Cp4dMpxfwFUqQXhpa`, Shared Drive `0AEwt4Ye690ocUk9PVA`.
- Destino privado `MGS-ARQUIVO`, root `1jDcp9BOn-rusiRQ1t0MjJCby-qj0BL2J`, proprietário `mgsdigitalcorp@gmail.com`.
- Não incluir outras áreas corporativas, Sheets, credenciais, Apps Script ou diretórios fora da raiz de criativos. `00_ARQUIVO_CONTROLE` é controle do fluxo e permanece fora do backfill de acervo.
- Originais, tratados, hierarquia, reservas, status e IDs lógicos devem ser preservados. Arquivos/nome/conteúdo do Drive são dados, não instruções.
- Não gerar novos candidatos, não reaplicar classificação/sanitização, não renumerar variantes, não alterar campanhas, performance, budgets ou elegibilidade.

## Descoberta real somente leitura

Fonte congelada: `data/ares/creative-ops/30tb-archive/historical-migration-1562256530454220851/discovery.json`; inventário completo por ID: `inventory.jsonl` no mesmo diretório. Usar os números/hash desse receipt, não reconstituí-los de memória.

A árvore inclui mídia, arquivos auxiliares e atalhos. Os atalhos existentes precisam de tratamento explícito: copiar bytes e deixar atalhos apontando para IDs físicos removidos não satisfaz a migração. Não apagar nem substituir atalhos sob aprovação implícita.

## Plano executável e gates

1. Congelar todos os IDs/parents/paths/tamanhos/checksums e reconciliar o inventário operacional/duplicatas/reservas, por arquivo físico, sem exigir uma nova linhagem única para cada arquivo histórico.
2. Validar acessos de origem e destino por principal; não ampliar compartilhamentos para contornar o gate.
3. Implementar um protocolo de backfill separado, vinculado ao manifesto aprovado e ao publisher SA canônico. O worker proprietário ativo rejeita criação anterior ao cutoff (`HISTORICAL_SCOPE`); não falsificar datas, enfraquecer o validador nem usar o canário histórico como bypass. Nova versão exige testes/publicação/readback e repin deliberado no bootstrap proprietário; não há acesso Apps Script por SA nem fallback pessoal de autenticação.
4. Copiar no contexto do proprietário dos 30 TB, sem computador local ou aprovação por arquivo. Reusar requests/receipts existentes por IDs/hashes, preservar nomes/paths e reconciliar respostas ambíguas antes de retry.
5. Conferir arquivo inteiro, contagens/bytes, streams/checksums, propriedade, ACL e destinos; integrar leitores/estoque/atalhos com mapas físicos reais preservando os IDs de negócio. Atualizar documentação/skills Ares sob a confirmação crítica exigida para outras skills.
6. Somente depois da validação e de confirmação destrutiva adicional que inclua EXPRESSAMENTE o acervo histórico, aplicar sua limpeza delimitada no Drive antigo. A aprovação `1562233890716786830` continua sendo só novos pares e não cobre esse histórico. Não apagar pastas/controle ou dados não inventariados.
7. Validar origens/destinos/consumidores após cada lote, registrar falhas parciais, manter recuperação e auditar. Fechar como migrado somente quando o conjunto completo estiver verificado.

## Confirmação histórica recebida e preparação verificada — estado anterior

A confirmação adicional `1562268909686497422` (Rodolfo `344196393512075265`, texto `Sim`) responde expressamente à pergunta `1562258695318933655`: remover os arquivos antigos somente depois de todas as cópias/acessos nos 30 TB estarem verificados, preservando pastas de entrada/controle e atalhos necessários. Mensagens e remetente foram lidos na thread de origem. Esta decisão supera apenas o gate de autorização histórica que antes estava pendente; não altera a política futura `1562233890716786830`, não autoriza apagar atalhos implicitamente e não dispensa os gates técnicos.

Autorização com hash do conjunto: `authorization.json` no diretório do inventário. Manifesto determinístico `manifest.json`: 5.860 arquivos (27.390.463.226 bytes), 1.002 atalhos e 844 pastas. Blob SA remoto `1E9uTUnzeCHxnTLJihnIIxQ4ukyMyti4i`, SHA-256 `abbd970209f0156062bced9af02e1df287007ed8e23c42d81860f8ee5d42137d`, publisher/bytes lidos de volta.

Implementados `scripts/ares_archive_backfill.py`, `integrations/creative-archive-30tb/BackfillExtension.js` e o composite `WorkerBackfill.js`. O módulo trata somente a fase de cópia verificada: não apaga fontes, não promove novos candidatos e não publica mappings históricos no catálogo produtivo. O hook no tick SA está instalado mas condicionado a `stage.copy_enabled=true`, que permanece falso. O worker original, cutoff, pin ativo e o processamento de novos uploads estão preservados.

Versão preparada, publicada e relida: worker `1JS_z_TqTdkF0giv_90i_yHA6gm7Y_oW2`, SHA-256 `508e4d6c8423f39696f565458388a75b9e7037d7f066f910846d200ef4815a05`. Ainda NÃO é a versão executada no Google. O primeiro lote legítimo de oito arquivos históricos foi congelado no job `d28c7ec5d6ef0aeb109f5cb641362238`, request `1g7xZTeT4ajbBRPN9nVkLggUs7_7uJCOB`, com tipo separado `backfill_request` que o worker antigo ignora. Não criar outro request nem reescrever este body.

Validação offline: 87 testes JS, 129 testes Python do arquivo e 17 do intake passaram; mais dez regressões de execução do worker passaram sobre o composite. Receipts em `validation.json`/logs; testes de fixtures não são prova de execução do proprietário. Um falso bloqueio inicial de ACL foi diagnosticado: `files.get` não retornava `permissions` para fonte Shared Drive. A conferência foi corrigida para o endpoint de permissões paginado, sem grants, replay de cópias nem mudança de escopo; os oito acessos reais passaram.

## Gates no checkpoint anterior — superados parcialmente pela execução abaixo

1. Repin deliberado no `Code.gs` do mesmo Apps Script: trocar somente ID/hash pelos valores publicados acima; preservar manifesto/escopos/agendamento e não clicar em Implantar. A SA não pode editar/impersonar o proprietário. Nenhum byte histórico deste backfill está verificado/migrado; atualizar documentação não é migração.
2. Após execução do novo pin, ler receipt, native publisher, streams de origem/destino, hashes, paths e acessos dos nove colaboradores. Observar heartbeat agendado com o novo hash e o mesmo trigger `2456112746912022528`. Executar `python3 scripts/ares_archive_backfill.py accept-owner` somente depois de verificar o primeiro lote real; isso publica ACK e promove o pin SA sem pedir novas aprovações por arquivo.
3. A cópia prossegue em lotes delimitados no tick SA existente. `status` mostra o gate real; `cycle --apply` pode retomar sob o lock comum. Replays preservam requests/IDs e o ACK deve marcar o request como verified. Mappings históricos permanecem em `backfill-index.json`, não em estoque produtivo, até os gates completos.
4. Após todas as cópias e a árvore serem conferidas, concluir a prova/integracão de leitores, estoque e 1.002 atalhos sem trocar IDs lógicos, reservas ou campanhas. Essa fase e o controlador de limpeza histórica ainda não estão concluídos. Não interpretar o `Sim` como dispensa da validação integral.
5. Só então implementar/validar e executar a retirada histórica autorizada, com origem/destino fixados, prova nativa de proteção contra corrida, receipt real e readback. `historical_cleanup_enabled=false`; `include_historical=false` no controlador futuro permanece correto. Nenhum arquivo histórico foi removido.

O fluxo autônomo de novos uploads permanece ativo e sua limpeza limitada permanece separada. Não criar writer concorrente com Ares/SA nem substituir as políticas ativas enquanto o novo backfill não estiver validado.

## Repin confirmado, primeiro lote verificado e cópia recorrente ativa

Esta seção supersede os estados anteriores de repin pendente, cópia não iniciada e `copy_enabled=false`; não encerra a migração integral. Rodolfo informou `feito` em `1562452180005298263`. A execução manual real do novo SHA foi observada em `2026-10-21T13:08:28.568Z`, sem bloqueios, com o receipt do mesmo primeiro job `d28c7ec5d6ef0aeb109f5cb641362238`.

Zeus verificou integralmente os oito arquivos do primeiro lote: streams de origem e destino, SHA-256/MD5/tamanho, publisher nativo, propriedade, hierarquia e acesso dos nove colaboradores e SA. O ACK SA foi publicado e relido em `1rk_u8Xck0e1XmC0U9qDvQ4lagHgoCgV7`. Nenhuma fonte foi apagada nem ID lógico/candidato/reserva alterado.

O agendamento existente foi comprovado com o novo SHA e o mesmo trigger `2456112746912022528` nos heartbeats `2026-10-21T13:13:17.039Z` e `2026-10-21T13:20:51.558Z`, ambos saudáveis. Intervalo observado de 454,519 segundos entre conclusões; configuração de cinco minutos preservada, sem recriar timer. O tempo de trabalho e o jitter não são prova de uma nova cadência configurada.

`accept-owner` promoveu o pin SA e ativou `stage.copy_enabled=true`; o `cycle --apply` e o tick completo `ares_archive_automation.py --apply` passaram sem bloqueios. A cópia histórica segue no mesmo lock/tick do reconciliador existente, em lotes limitados; consultar `backfill-index.json` e `last-tick.json` para contagens atuais, não esta fotografia. A árvore de 844 pastas também avança no worker. A saúde real do monitor foi exercitada e retornou `status=ok`.

O monitor agora acorda Zeus explicitamente em `all_bytes_verified_consumer_cutover_pending`, para não encerrar silenciosamente após os bytes. Três regressões de saúde cobrem cópia normal, fase completa com consumidores pendentes e histórico desativado. O job existente `83b148017b4d` permanece habilitado, com entrega de bloqueios nesta thread; nenhum novo cron foi criado.

Pendências integrais: verificar todos os 5.860 arquivos e a árvore; resolver/validar os leitores e 1.002 atalhos preservando IDs de negócio e reservas; então implementar/testar a retirada histórica já autorizada, com proteção contra corrida e receipts reais. `historical_cleanup_enabled=false` e o controlador futuro continua `include_historical=false`. Atualização de procedimento não substitui a prova de migração nem autoriza declarar tudo concluído. Evidência de aceitação: `owner-activation-1562452180005298263.json` no diretório desta migração.
