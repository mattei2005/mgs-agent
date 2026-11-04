# Entrada simples MGS — contexto explícito de pedido

## Autoridade e estado vivo

Redesenho aprovado por Rodolfo em `1566814476626563115`; preservação/reaplicação dos mesmos acessos confirmada em `1566825959645253764`, thread Zeus `1562078493498540042`. Fonte canônica: `context/drive-flat-intake-cutover.md`. Confirmar `ares_flat_intake.policy()` / `data/ares/creative-ops/30tb-archive/flat-intake-binding.json`: somente `phase=active` é fluxo implantado. Não confundir preparação ou teste técnico com uma campanha real.

## Regra de entrada

- A pessoa envia IMG/VID diretamente na mesma `UPLOAD MANUAL`, ID `1ARBvLammWUHuAclNmcriwkkgeedKryBd`. Não exigir subpasta de nicho ou gestor.
- Operação, finalidade e eventual gestor destinatário vêm do pedido humano autorizado; distinguir remetente/origem de destinatário exclusivo. O nome do arquivo, uploader, pasta antiga ou referência não substituem o contexto.
- Congelar os IDs exatos do lote informado. Não absorver imagens vizinhas, inferir o gestor dos pendentes ou reaproveitar um comando antigo para fontes novas. Se o lote/contexto for ambíguo, perguntar somente a informação que falta.
- `common` destina à organização `01_READY`, preservando os demais gates de elegibilidade/reserva; `exclusive` destina a `<NOME> - Exclusivos`. Não liberar reservas ou promover referência a criativo final pelo simples modo de armazenamento.
- No pedido geral de Kelly com país/vertical/língua e lote identificado, “aplique as regras e mova para a pasta correta”, sem gestor destinatário nem exclusividade, usar `common`; não perguntar qual gestor apenas para preencher esse fluxo e não entregar em `KELLY - Exclusivos` pelo nome da remetente. Exemplo US/SHEIN/espanhol: tratados IMG em `MGS-ARQUIVO/CRIATIVOS/SHEIN_US_ES/IMG/01_READY`; tratados VID em `MGS-ARQUIVO/CRIATIVOS/SHEIN_US_ES/VID/01_READY`. Originais permanecem preservados, fora do pool de tratados. Pedido de entrega própria de gestor ou destinatário exclusivo explícito continua no fluxo `exclusive`; não generalizar este exemplo para ambiguidades reais, fontes sem pedido ou reservas preexistentes.
- As antigas pastas de envio por operação/gestor foram preservadas nos 30 TB como histórico técnico. Não pedir que usuários continuem enviando nelas nem recriá-las no MGS.

## Registrar e executar sem writer paralelo

Ares identifica e valida o pedido original, depois usa o helper com o autor humano real, a thread/canal e a mensagem reais:

```
python3 /root/mgs-agent/scripts/ares_flat_intake.py register --operation SHEIN_US_ES --manager Nicolas --destination exclusive --source-id ID_EXATO --requester-id AUTOR_HUMANO --channel-id THREAD_ORIGEM --message-id MENSAGEM_ORIGINAL
```

Acrescentar `--source-id` para os demais membros congelados. Primeiro conferir o plano; aplicar o mesmo comando com `--apply`. O helper valida a mensagem Discord nativa, whitelist/canal, origem exata e IDs/hashes/versionamento; não cria campanhas, não trata mídia e não move arquivos. Não inventar mensagem/autor nem cadastrar o lote em nome de Rodolfo se outra pessoa pediu.

Para o exemplo geral da Kelly, usar o mesmo helper com `--operation SHEIN_US_ES --manager Kelly --destination common`, além dos source IDs e autor/canal/mensagem nativos reais. Nesse caso, `--manager Kelly` é atribuição interna da origem do lote, não solicitação de exclusividade nem alteração de reserva/elegibilidade. A entrega exclusiva só ocorre com `--destination exclusive` e destinatário efetivamente pedido. O request real `460f5b805715f8acc9727823559da3bb` comprova essa combinação common/Kelly; não reexecutá-lo como teste.

Quando o pedido for o starter de uma auto-thread, o snowflake da thread pode ser igual ao da mensagem humana, mas o recurso da mensagem pertence ao canal pai. Se o GET da mensagem na thread retornar 404, consultar o mesmo message ID no pai real e validar `author.id`, `channel_id` e conteúdo antes do registro. Passar em `--channel-id` o canal nativo da mensagem que o helper realmente valida; preservar separadamente a thread de execução/resposta no checkpoint. Um 404 nessa combinação não prova falta de acesso nem ausência do pedido. Validar a correção com plano sem writes, registro e readback dos mesmos IDs; não usar outra identidade ou inventar uma mensagem substituta.

O registro alimenta o **mesmo** job `528c5710269d`. Não lançar outro executor manual em paralelo. O monitor entrega um batch determinístico com `scope_type=flat_request`, operação, gestor, destino e fonte humana. O claim atual revalida o pedido e o conjunto, congela o inventário protegido e preserva os mesmos IDs no replay. O lote técnico continua limitado pelo `intake-config.json`; uma divisão técnica não descarta o saldo do pedido.

Se uma execução manual já era dona das fontes, continuar pelo manifesto original e sua conclusão canônica, sem cadastrar outro request para os mesmos IDs. Não roubar claim, resetar o batch ou usar outro processo apenas para acelerar.

### Pedidos sobrepostos, locks e consulta de progresso

1. Antes de registrar outro envio, ler `flat-intake-requests.json`, os claims de `intake-state.json` e o checkpoint/manifesto anterior. Comparar IDs e hashes, não títulos de threads ou contagens. Excluir da descoberta tanto fontes já vinculadas a requests quanto pendências de manifestos anteriores: um arquivo ausente do registry flat não é necessariamente novo. Usar horário e nome apenas como evidência auxiliar para delimitar um conjunto inequívoco, seguido do gate de estabilidade.
2. Reduzir a leitura ao necessário: projetar `id`, `name`, MIME, tamanho, checksums, versão, horário e somente as capabilities usadas. Persistir o conjunto e exibir resumo/contagem; não despejar todas as capabilities ou todo o registry a cada poll, pois isso encobre os IDs relevantes sem melhorar a validação.
3. Registrar um conjunto realmente novo pelo mesmo helper, sem alterar o request anterior. Para consultar progresso enquanto outra execução trabalha, ler os requests, claims e evidências existentes. Não tratar `monitor` como GET inofensivo: ele também chama manutenção e pode produzir o próximo manifesto. Reservá-lo à transição canônica de descoberta/continuação e não iniciá-lo em paralelo apenas para obter status. Se devolver outro `flat_request_id`, não consumir esse batch nesta conversa nem construir manualmente um batch substituto para furar a ordem.
4. Diante de timeout em `register` ou `complete`, verificar primeiro o processo exato, o request calculado, o claim e os efeitos persistidos. O lock de intake pode permanecer ocupado durante a continuação de arquivo; timeout da observação não comprova falha do pedido. Só repetir o mesmo comando idempotente após reconciliar seu resultado e confirmar que não há a mesma chamada ainda ativa; nunca trocar IDs, owner ou identidade para contornar a espera.
5. Se houver espera real por outro request, a preparação local não autoriza um writer remoto paralelo. Preservar evidência compacta durável por source ID com caminhos locais, SHA RAW/clean, dimensões, classificação e QA; registrar separadamente que naming, upload, movimento e ACK ainda faltam. Ao obter o batch próprio pelo monitor, revalidar os hashes e reutilizar a preparação válida antes de executar as camadas faltantes. Manter checkpoint resumível; não chamar registro ou scheduler habilitado de conclusão nem prometer continuação automática somente porque o job existe.

## Tratamento e entrega

### Continuação mecânica determinística — autorização `1567021305822314609`

Após tratamento/QA e inventário do batch de até quatro fontes, executar o `ares_autonomous_intake.py complete` existente, com os mesmos `batch-id` e `owner_job_id`. Com `archive_pipeline_enabled=true` e a autoridade exata no config, ele chama `ares_intake_archive_pipeline.py`: publica no máximo dois pares por passagem pelo produtor SA existente, aciona somente o executor owner isolado existente (máximo dois jobs/100s por tick), verifica receipt/ACK, cria os atalhos pelos helpers atuais, transfere no máximo quatro atalhos por tick e valida cada provider por bytes completos antes do fechamento. Locks intake → queue, IDs, hashes, limites e credenciais permanecem os mesmos; não há tratamento, DELETE, campanha ou permissão nesta continuação.

Não criar um `follow_archive.py` ou outro bombeador paralelo. `complete` agora termina essas camadas no mesmo comando, sem solicitar outra decisão do modelo para cada passagem. Se houver limite sem progresso, ele preserva `treated_waiting_archive`, diário por batch e os mesmos IDs; o monitor o devolve como `resume` com `mechanical_only=true`, nunca como um caso silencioso indefinidamente suprimido. Nesse retorno, rodar apenas o mesmo `complete`, sem novo download, tratamento, naming ou enqueue manual. Bloqueio real permanece bloqueio; investigar a razão exata, sem aumentar lotes nem pular guards.

Um replay de `complete` preserva o primeiro `treated_at`, `completed_at`, provas e recibo de entrega. Não regravar horários para parecer uma execução nova. O critério do pedido inteiro é o conjunto exato de IDs do request, não o sucesso isolado de um cron ou de um batch.

Depois de cada batch completo, chamar `ares_autonomous_intake.py monitor` e ler o manifest retornado. Continuar imediatamente pelo mesmo executor somente quando o `flat_request_id` for o mesmo do pedido corrente, mantendo claim e blocos de quatro. Não esperar deliberadamente a próxima janela de 15 minutos nem disparar repetidamente o cron enquanto o próprio executor consegue continuar. Não absorver outro request, uploads vizinhos ou novos IDs. Ao concluir todos os IDs, validar o request `status=complete` e entregar na origem o mapa completo e links permanentes. Se o turno atingir seu limite, preservar checkpoint e retomada canônica silenciosa; não declarar o saldo concluído.

Preservar classificação visual, naming, sanitização, dedupe, hashes, QA e inventário do contrato principal. No batch flat, usar **o autor e o contexto reais do batch**, não os campos históricos fixos de “automação pelo CEO”. O staging `_PROCESSAMENTO` continua técnico e temporário; caminhos OP/IMG|VID/READY|LEGACY ali não são a organização permanente oferecida ao usuário.

`complete` valida RAW/clean, archive request/receipt/ACK, provider e stock. No destino exclusivo, o finalizador flat chama a entrega dedicada por mesmo ID e registra o destino permanente exato; falha dessa etapa volta como `archive_ready`, nunca novo tratamento. Duplicatas mantêm a linhagem, reservas, uso e destino anteriores: não mover uma peça usada de volta para Exclusivos.

O mecanismo de manutenção existente, executado pelo componente privado isolado, arquiva por **mesmos IDs** as gerações concluídas do staging e encaminha relatórios permanentes que apareçam na raiz para o corporativo. Só admite fontes com conclusão/bytes/ACK, snapshots e escopo nativo correspondentes. Não usa DELETE/trash; no modo flat o controlador criativo mantém preservação por movimento, sem alterar a retenção de backups corporativos. Não importar credencial owner no agente nem abrir um transporte genérico para contornar as validações.

## Campanhas e resposta

Upload/registro/tratamento não autorizam campanha. Só continuar a criação/clone pelo pedido de Campaign Ops válido e pelos gates vigentes, preservando conta, orçamento, estratégia e início. Apenas mídia realmente atribuída nos anúncios passa de Exclusivos para Usados; falha e saldo não utilizado permanecem exclusivos.

Responder com o link permanente real e o mapa original → final. Separar recebidos, novos, duplicatas e pendentes; não dizer que todo material da entrada foi tratado porque um batch terminou. Os arquivos sem contexto continuam preservados para o pedido correto, sem classificação por adivinhação.
