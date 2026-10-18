# Runtime e recuperação do observador

## When to Use

Consultar quando precisar dos comandos de execução, vínculo da sessão real, recuperação de tentativa/intake ou reconciliação de notificações. O fluxo obrigatório e as preferências do operador ficam no SKILL.md; não restaurar comandos antigos de janela privada/coleta de frames como default da rota enxuta.

## 1. Preparação e execução do lote contínuo

### Identificar runtime, sessão e propriedade

1. Resolver o executável real antes de abrir qualquer landing:

```bash
HERMES_PY="$(dirname "$(readlink -f "$(command -v hermes)")")/python"
```

2. Usar o ID real da sessão que fará os inputs; `owner` lógico da fila não é esse ID. Se precisar recuperar a identidade de um turno foreground, consultar apenas a conversa atual no banco nativo read-only:

```sql
SELECT s.id, s.source, s.thread_id
FROM session_turn_leases AS l
JOIN sessions AS s ON s.id = l.conversation_id
WHERE l.expires_at > ?
  AND s.source = 'discord'
  AND COALESCE(NULLIF(s.thread_id, ''), s.chat_id, '') = ?;
```

Exigir uma única sessão viva compatível com a origem. Nunca gerar uma identidade para satisfazer o guard, reutilizar worker encerrado ou tomar uma lease viva.

3. Ler o job e reservar a mesma pendência pelo controlador existente. Com `Queue.claim(owner, ttl=...)`, conferir a chave retornada antes de qualquer input; se vier outro alvo, devolver a reserva sem navegar. Reconciliar janelas incertas antes de iniciar outro item.

A lease física é administrada por `scripts/mgs-pc1-computer-use-lock.py` com `status`, `acquire`, `renew` e `release`. Renovar antes de expirar. Liberar somente com fechamento seguro ou ausência de input comprovada; término do processo não basta.

### Chamar a rota enxuta contínua

O despachante congela `batch-scope.json` com owner, pedidos/digests e conjunto da rodada. Reutilizar os mapeamentos de `prepared_landing_links`; se faltarem destinos, resolver TODOS antes de obter PC1 e fornecer um único manifest `{"items":[{"job":"<key>","index":0,"url":"<landing-real>","mapping_source":"<fonte-canônica>","destination_count":1}]}` com cobertura exata dos pendentes. Destinos A/B distintos não podem ser omitidos ou declarados como únicos por conveniência.

```bash
"$HERMES_PY" /root/mgs-agent/scripts/ares-direct-traffic-batch-observe.py \
  --scope '<batch-scope.json>' --owner <owner> \
  --pc1-session-id "$HERMES_SESSION_ID" \
  --manifest '<mapa-completo.json>'
```

Omitir `--manifest` quando o mapa já estiver completo no cache vinculado ao digest do pedido. O loop faz `begin`, verifica mobile nativo, navega, aciona somente o CTA editorial autorizado quando presente, aguarda liberação real do artigo/rewarded, confirma rolagem e mede 20–30s de observação após essas etapas, captura um frame final, fecha e só então analisa/registra `result` de forma serial; não chamar `begin` fora dele. Manter o backend durante o lote e encerrá-lo uma vez ao final seguro. A pausa e o deadline são verificados entre tentativas; erro técnico devolve diagnóstico, janela incerta impede próxima abertura. Não criar outro turno de modelo por URL e não esperar HTTP de Discord entre itens.

O CLI `ares-direct-traffic-lean-observe.py --key <key> --owner <owner> --index <idx> --pc1-session-id "$HERMES_SESSION_ID" --url '<landing exata>' --mapping-source '<fonte>'` permanece apenas como compatibilidade individual, usando o MESMO `landing_lean.observe_prepared`. Não confundir nenhum deles com os comandos legados de janela privada/coleta.

O módulo `ares_campaign_v3.landing_lean` concentra abertura normal, fechamento próprio, alvo de rolagem, decisão visual estruturada e validação compacta. Usar o handler público `computer_use`; não modificar o driver compartilhado ou importar um caminho privado de input para contornar seus gates.

### Preservar o endereço de origem

`observation_url` aplica somente a extensão autorizada pelo contrato ativo. O flag `nocache` é bare: usar `?nocache` quando não há query e `&nocache` depois dos parâmetros existentes. Preservar ordem, escapes e valores; não usar `=1`, duplicar o flag ou escrever na URL Meta. Guardar a URL canônica original e a efetivamente aberta em campos distintos.

Ler instruções de URL no limite seguro entre tentativas. Se uma regra mudar durante a execução, aplicar ao próximo item sem alterar uma navegação em andamento; informar de onde passou a valer, em vez de afirmar que foi retroativa.

Quando o operador pedir um diagnóstico removendo um parâmetro de uma URL pendente, manter a autorização, original e variante em rodada separada com uma visita por alvo, validar primeiro o mapeamento original e depois a transformação literal exata. Não relaxar globalmente `tracking_query_matches`, modificar payload/digest ou converter o resultado da variante em aprovação da URL completa da campanha. Persistir o diagnóstico e preservar os estados/contadores originais; não confundir esse experimento com retry da mesma URL. Um frame inicial com anúncio não pode ser negado por um frame final após rolagem que só mostra outro trecho; registrar ambos e separar identificação de anúncio, observação cumprida e PASS do executor.

### Validar o desktop sem galeria

- Confirmar a navegação por readback após Enter; uma URL digitada na barra ainda não prova carregamento.
- Se a leitura mostrar New Tab, tela de loading ou página não confirmada, reler limitadamente na mesma aba. Não registrar `NO_AD` nem abrir outra página para resolver uma leitura inconclusiva.
- Após `capture(app="screen")`, refazer `capture(mode="ax", pid=<pid>, window_id=<window_id>)`; localizar o `Document` da página com bounds de viewport e usar seu índice fresco para scroll. Sem esse alvo, a rolagem pode ser recusada mesmo com a janela aberta.
- Examinar `code`, `effect` e `verdict`, inclusive aninhados. Uma recusa ou no-op comprovado permite escalar; input `unverifiable` exige readback antes de repetir. Não prever foreground apenas porque é Chrome.
- Fechar pelo controle nativo da janela própria, conferindo a linha de Minimize/Restore/Maximize e o Close à direita; Chrome também chama o botão da aba de Close. Uma janela técnica de uma aba deve permanecer exclusiva da tarefa.
- Verificar ausência do alvo e preservação das identidades anteriores. Se o fechamento já foi confirmado, não clicar novamente nem repetir cleanup por mudanças posteriores feitas pelo usuário.

O recibo lean vincula URL efetiva, abertura normal nova, decisão visual de anúncio/página ativa, tempo medido e enumerações nativas antes/depois do fechamento. Ausência de série de imagens não dispensa esses fatos nem transforma script/slot vazio/CTA editorial em anúncio.

## 2. Fila, resultado e recuperação

Comandos do controlador, usados somente no estado e na finalidade correspondentes:

```text
python3 scripts/ares-direct-traffic-followup.py status
python3 scripts/ares-direct-traffic-followup.py show --key <key>
python3 scripts/ares-direct-traffic-followup.py defer --key <key> --owner <owner>
python3 scripts/ares-direct-traffic-followup.py retry-now --key <key> --owner <owner> --index <idx> --pc1-session-id "$HERMES_SESSION_ID"
python3 scripts/ares-direct-traffic-followup.py result --key <key> --owner <owner> --index <idx> --pc1-session-id "$HERMES_SESSION_ID" --result PASS|NO_AD|ERROR --evidence <arquivo>
python3 scripts/ares-direct-traffic-followup.py reconcile --key <key> --index <idx> --pc1-session-id "$HERMES_SESSION_ID" --evidence <arquivo> --resume
```

Não registrar resultado de novo se o runner já o gravou. Antes de `--recovered`, verificar o formato e o suporte do validador para a prova atual; não mesclar um recibo lean com flags legadas de samples para fazê-lo passar.

### Autorizar uma tentativa pontual após revisão

Para novo pedido explícito sobre um único `REVIEW_REQUIRED`, usar `landing_retry_policy.authorize_single_retry(q, key, idx, authority_message_id=..., authority_thread_id=..., not_before=...)`. Resolver ID e timestamp da mensagem humana pelo banco nativo read-only; não inventar IDs. A função exige fechamento da tentativa exata, preserva contador/evidência anteriores, grava autorização imutável e concede somente uma ausência adicional. O deadline é persistido em `links.due`; espera solicitada não ocupa o PC1. O consumidor existente pode executar quando vencer; se for foreground, fazer claim normal e conferir a chave antes de chamar o CLI lean. Repetir a mesma autorização é idempotente, não concede outra visita. Não usar `retry-now`, zerar contador ou editar estados diretamente para contornar a revisão. Depois conferir resultado, consolidado, avisos e checkpoint. Teste: `test_direct_traffic_landing_manual_retry.py` cobre deadline, histórico, idempotência, ausência única, PASS e rejeição de alvo/fechamento/autoridade inválidos.

### Encerrar por determinação do operador, sem nova visita

1. Resolver o alvo a partir da mensagem respondida: request, conta, campanha, job, índice e URL/UTMs. Aplicar o gate de domínio antes da consulta operacional. Recuperar o `platform_message_id` da autorização na conversa atual pelo banco nativo `mode=ro` e `PRAGMA query_only=ON`; conferir a seção acionável e a thread, pois a mesma mensagem pode conter histórico citado que não concede autoridade nova.
2. Ler somente o job exato com `ares-direct-traffic-followup.py show --key <key>` e conferir `WAITING_HUMAN`/`REVIEW_REQUIRED`. Validar o fechamento da tentativa corrente por `landing_retry_policy.closed_latest(q, key, link)`; resolução administrativa não libera janela incerta nem lease física. Não adquirir PC1, executar `tick`/intake, fazer HTTP da landing ou percorrer inventário global para encerrar uma pendência já identificada.
3. Preferir o mutador dedicado quando disponível. Para uma atualização pontual autorizada pelo controlador `Queue`, usar `q.tx()` e reler os registros sob lock antes de mudar o alvo. Preservar `attempt` e `evidence` integralmente; alterar somente o link para `RESOLVED_BY_OPERATOR`, zerar seu prazo e acrescentar evento com mensagem/autor/thread, declaração literal, estado anterior e ausência de nova visita. Não substituir o recibo automatizado pela declaração humana. Tornar a operação idempotente pela mensagem+job+índice: resolução já aplicada exige apenas readback, não outro evento ou fechamento.
4. Contar os alvos do pedido em código, separando `PASSED` de `RESOLVED_BY_OPERATOR`. Encerrar o job como `COMPLETE` somente se todos os seus links forem terminais; conferir todos os filhos antes de declarar conclusão do pedido humano agregado. Não passar pela promoção de sucesso automatizado para forçar uma resolução humana: validadores e mensagens de PASS podem exigir anúncio realmente observado.
5. Verificar em conexão independente read-only o estado final, a igualdade de contador/evidência anteriores e a quantidade de pendências do recorte. Salvar verificação/inventário, atualizar o checkpoint pelo `mgs-knowledge-control.py checkpoint-upsert` e cumprir o REPORT-INFRA aplicável à alteração de dados. Separar o encerramento administrativo de eventual entrega externa; envio só é confirmado após GET da mensagem exata.
6. Responder em uma frase ou duas: identificação da campanha, pendência encerrada por determinação do operador e nenhuma nova abertura. Não chamar de anúncio confirmado se o operador apenas informou que abriu o link.

### Escolher a prova certa

1. Construir o caminho pela rodada, job, índice, owner e número da tentativa corrente.
2. Se o recibo corrente não existir, tratar como prova ausente. **Nunca cair no último arquivo disponível por glob/mtime:** ele pode ser o fechamento de uma visita anterior.
3. Conferir que abertura, observação e fechamento pertencem à mesma tentativa e ocorreram na ordem correta. Prova completa permite registro sem outra visita; prova parcial permite apenas o cleanup que sustenta.
4. Em ausência de navegação, provar ausência de inputs/nova janela por leitura da sessão e do desktop. Não inventar uma aba fechada para liberar um guard.
5. Se registros têm o mesmo início, identidade e fechamento, investigar duplicidade antes de somar tentativas. Preservar a classificação antiga por supersessão explícita, sem contá-la como outro erro/visita.

### Estados e decisões

- `READY` / `WAIT_RETRY`: executar quando devido e o recurso permitir. Com atraso zero de ausência, reutilizar a sessão/lease quando suportado, mas persistir uma nova tentativa e abrir outra aba normal.
- `RUNNING`: existe reserva; pode ainda não haver input. `OPEN_INTENT` prova intenção durável, não carregamento.
- `NEEDS_RECONCILIATION` / `RECONCILING`: somente leitura/cleanup até resolver a janela incerta. Não navegar nem liberar a proteção física antes disso.
- `TECHNICAL_REPAIR` / `REPAIRING`: diagnosticar a camada local; executar `ares-direct-traffic-repair.py --key <key> --owner <owner> --index <idx> --pc1-session-id "$HERMES_SESSION_ID" --repair-note '<causa e correção reais>'`. No modo ativo, o teste abre somente janela vazia NORMAL e confere fechamento/preservação nativos, sem URL, Incognito, série de imagens, galeria ou timer de anúncio. O recibo de teste não aprova uma landing. Não consumir a política de ausência com falhas técnicas.
- `DEFERRED_NO_AD`: três ausências reais e fechamento seguro; continuar os outros links. Após a fase inicial, uma tentativa de retorno final.
- `COOLDOWN_NO_AD`: retorno final ainda sem anúncio. Quando TODOS os itens/retornos do lote congelado terminarem, `finite.maintain` grava um prazo único `due=agora+60s`. Devolver o PC1 e encerrar o backend durante a espera; o timer já existente agenda UMA recuperação automática por pendente ao vencer. Reinício/intake não reseta o minuto nem cria ciclo infinito. O histórico total permanece3+1+1.
- `REVIEW_REQUIRED`: também não houve anúncio na recuperação automática após o minuto. Reportar ao operador e parar após essas5ausências, sem reabrir aprovados. Novo pedido explícito para um pendente autoriza uma tentativa adicional identificável, sem conceder todas as fases de novo. Antes do input, conferir o suporte do runner à autorização; não reutilizar um comando histórico que ignore o estado. Após o resultado, reconciliar ledger, total consolidado, lista de revisão e checkpoint; preservar o retrato anterior por supersessão.
- `OBSERVED`: URLs do job técnico passaram; verificar os outros grupos do pedido humano antes da confirmação coletiva. Não reabrir URLs por pendência de notificação.
- `RESOLVED_BY_OPERATOR`: link encerrado por determinação humana identificável; não equivale a `PASSED` nem comprova anúncio renderizado. Preservar a evidência automatizada anterior e excluir o alvo das pendências sem outra visita.
- `COMPLETE`: encerramento do job; conferir se decorre de validação automatizada com entrega final verificada ou de resolução humana auditada. O rótulo isolado não prova anúncio nem nova entrega externa. Imagens legadas já purgadas não justificam outra navegação.
- `WAITING_HUMAN_UNCLOSED`: preservar o bloqueio e explicar somente a ação humana indispensável, sem retry de input incerto.

Um erro seguro de item não deve monopolizar a fila: prosseguir nos devidos quando não houver aba incerta. Congelar o conjunto da rodada para o retorno final; jobs pares `OBSERVED` contam como navegação concluída, pois aguardar a confirmação coletiva que depende do próprio pendente causaria deadlock.

## 3. Intake independente e pedidos agrupados

### Recuperar uma entrada sem alterar campanhas

1. Ler `native_intake`, o job do mesmo request e a evidência terminal salva. Não interpretar `IGNORED` como prova de que a criação não aconteceu.
2. Resolver a origem exata do pedido. Mensagem recebida durante uma execução pode não preencher `platform_message_id`; usar somente o envelope midturn do runtime, conferindo plataforma, thread/chat, pai e igualdade dos IDs. Envelope citado, malformado ou de outra partição falha fechado.
3. Fazer GET da resposta nativa exata e conferir ID, conteúdo, autor, thread e pai contra a obrigação entregue. Horário semelhante não substitui identidade.
4. Reutilizar `build_from_source` e `Intake.arm`, com prova real e gate de domínio. Registrar a recuperação pai/filho e o estado anterior em evento; reexecução deve reconciliar o mesmo job.
5. Conferir em nova leitura a cobertura de todos os links, recibos e IDs. Distinguir entrada armada, worker reservado, navegação e resultado validado.

Não escrever no banco nativo Hermes, no estado de campanha, no cursor global ou no marco de ativação. Não ampliar recuperação pontual para outras entradas ignoradas nem fazer backfill histórico.

### Enumerar uma conclusão agregada

- Usar a prova agregada canônica para enumerar **todos** os filhos declarados; não escolher o primeiro filho ou adivinhar por glob.
- Validar IDs literais de requests, origem, conta, campanhas únicas, quantidade de cada grupo e total. Grupo faltante/incompleto ou partição divergente impede armar o conjunto como completo.
- Vincular os filhos ao mesmo `native_obligation_id` e recibo real. Só marcar o pai `READY` após enumeração completa; o sucesso coletivo deve sair uma vez por pedido humano.
- Em reconsideração automática, usar a geração da correção e lotes limitados; priorizar pais `PENDING`. Não deixar filhos ocuparem a seleção indefinidamente nem zerar cursores, tentativas ou `PASSED`.

Testar casos positivos e negativos de envelope, partição, origem histórica, grupo faltante, conta divergente, IDs duplicados, total inconsistente, idempotência e starvation. Fixtures offline não substituem GET e readback operacional.

## 4. Informes, background e avisos atrasados

### Publicar progresso sem bloquear a visita

No modo ativo `PER_ITEM`, `prepare_item` grava o card e sua autorização na transação de `result`, sem HTTP. O intake/consumidor independente entrega `landing-item:*` pelo outbox com GET; o loop PC1 não espera a rede para seguir. Escopo e totais seguem o lote congelado nos retornos, não toda a fila histórica. O modo antigo por intervalo permanece somente como compatibilidade/configuração histórica. Em POST ambíguo, reconciliar ID/nonce antes de repetir; em rate limit, preservar o outbox para o próximo ciclo, sem fabricar entrega nem fazer outra visita.

Modelo de informe por evento, com números apurados em código:

```text
✅ Campanha <identificador> — item concluído
Anúncio identificado · mobile · artigo/rolagem · observação <tempo real entre 20–30>s · aba normal fechada.
Concluídos com anúncio: <X>/<N> · aguardando: <Y> · revisão: <Z>.
```

Para ausência esgotada, trocar a primeira linha por pendência explícita e não aumentar o contador de aprovados. Não apresentar partes do mesmo pedido como trabalhos extras. `round_complete` pode significar fim das tentativas, não aprovação de todos os links.

Na operação normal, reutilizar `flush(q, Discord())` quando aplicável e exigir todos os pares do recibo original antes do sucesso coletivo. Em replay com override autorizado, não executar um flush indiscriminado que envie o sucesso ao gestor; limitar os informes ao destino registrado para aquela rodada.

### Evitar output técnico automático

- Preparar logs locais e entrega sanitizada antes de iniciar o background. Redirecionar stdout/stderr técnicos; não usar a notificação genérica de saída para despejar traces no Discord.
- Se a notificação automática for desativada para evitar output bruto, conservar um consumidor explícito do resultado, outbox operacional e checkpoint. Silenciar o processo não pode abandonar sua conclusão.
- Para mudança de regra ou parada, preferir pausa cooperativa depois do fechamento corrente. Identificar o processo real, não apenas seu shell pai; nunca matar um input incerto nem reiniciar navegador/gateway para trocar uma URL.

### Consumir uma conclusão histórica sem reabrir trabalho

1. Tratar a notificação interna como evento, não como uma nova mensagem do operador.
2. Correlacionar o ID exato com a execução e seu checkpoint. Se já foi consumida e o encerramento está conferido, não publicar outro aviso nem repetir o sumário final.
3. Quando necessário, usar uma única checagem local: processo encerrado, resultados da rodada coerentes e pendências de revisão mantidas. Não adquirir PC1 nem abrir URL para isso.
4. Para um processo encerrado, o mecanismo suportado `process_manage(action="log", session_id=<id-exato>, limit=1)` lê o final e marca consumo no registro de processos. `wait` também consome a conclusão quando retorna o resultado encerrado; `poll` é observação de status e não deve ser tratado como confirmação equivalente de supressão no gateway.
5. Consumir no registro não retira um evento já encaminhado à conversa. Não editar JSONs globais de processos, drenar notificações de outras sessões ou prometer que um aviso já em trânsito desaparecerá. Depois de verificar/consumir o alvo necessário, encerrar — sem ciclos de autorrecapitulação, novas conferências idênticas ou retomada de links aprovados.

## 5. Auditoria de pedidos e status sem visitas

### Delimitar período e enumerar a origem

1. Fixar alcance e corte no fuso do operador. Para pedidos feitos hoje, usar o timestamp da mensagem humana original; separar solicitações anteriores concluídas hoje, o replay de uma rodada antiga e campanhas programadas para outra data. Não usar `jobs.created`, data do nome ou início da campanha como substitutos da data do pedido. Separar o marco de ativação do observador sem transformá-lo em backfill.
2. Abrir bancos com SQLite `mode=ro` e `PRAGMA query_only=ON`. Enumerar as mensagens humanas dos canais/threads autorizados em `messages` + `sessions`, preservando `platform_message_id`, sessão, origem e timestamp; conferir a instrução efetiva, não o contexto citado ou o display name. Incluir aprovações/correções posteriores do mesmo pedido. Não limitar a enumeração a `delivery_obligations.state=delivered`, respostas contendo COMPLETE ou jobs já existentes: isso omite justamente solicitações não concluídas.
3. Cruzar as respostas disponíveis com a origem pelos helpers read-only `origin_for_delivery`, `terminal_references`, `source_paths` e pelos recibos salvos. Uma busca por palavras pode selecionar candidatos, mas não comprova cobertura, execução ou ausência. Não executar `intake`, `tick`, `arm` ou `build_from_source` para produzir um status: esses caminhos podem gravar fila/provas ou iniciar trabalho. Recuperar referências existentes sem criar novos jobs, navegar ou disputar a lease PC1.

### Conferir as camadas do pedido

4. Para cada solicitação, ler o estado canônico do runner mesmo quando não houver job de landing. Em SHEIN, carregar a skill da operação e consultar `state/shein-campaigns/single-clone/<request_id>/state.json`; em várias fontes, conferir os filhos `<request_id>-c<source_number>` e a verificação agregada. Extrair apenas fase, IDs persistidos, QA e resultado de ativação. `ACTIVATION_DEFERRED`, `POSTPROCESS_PENDING` e `RECOVERY_PENDING` não são conclusão integral; `engine_result.status=COMPLETE_PAUSED` não comprova que o pedido ACTIVE foi cumprido. Pedido sem conclusão elegível pode estar corretamente fora do captador, não necessariamente ter sido perdido por ele.
5. Se for preciso informar o estado atual, fazer GET read-only dos IDs exatos na conta confirmada, usando a identidade corporativa da operação. Começar pelos campos necessários à decisão, como `id,account_id,status,effective_status`; acrescentar budget, lance ou início somente conforme o que será afirmado. Não consultar mídia/prévias ou toda a hierarquia de um lote só para responder se falta ativação. Reutilizar leituras concluídas; em falha de uma consulta, declarar sua limitação e não transformar recibo histórico em status live. Confirmar o agendamento futuro separado da entrega: ACTIVE com data futura não significa veiculação agora.
6. Cruzar então com `jobs`, `links`, `native_receipts` e `messages` do observador. Agregar por pedido humano/resposta original, job técnico e combinação landing + UTMs. Uma mensagem com várias fontes pode gerar vários jobs, mas continua sendo um pedido humano. Contar IDs únicos e validar cobertura em código; não anunciar sucesso global por um dos grupos.
7. Conferir outbox `PREPARED`/`INTENT`, agrupar `OBSERVED` pelo recibo original e fazer GET das mensagens exatas necessárias para confirmar entrega. Reserva, `OPEN_INTENT`, navegação comprovada, PASS, revisão e entrega são estados diferentes; aviso coletivo pendente não exige outra visita. Timer ativo e serviço oneshot inativo com `Result=success` não provam que todos os pedidos de campanha terminaram.

### Responder sem misturar pendências

8. Apresentar por gestor/conta o que foi confirmado em criação, ativação/agendamento, PC1 e aviso. Se uma camada estiver pendente, começar por essa ressalva em vez de dizer que todos deram certo. Informar causa e próxima decisão exatas: um gate de ativação tardia não é ausência de anúncio e não recebe a retentativa automática do PC1. Uma pergunta de status não autoriza ativação, continuação de writer, alteração de budget ou recriação.
9. Separar conciliação de cadastro de links não processados. Registros pai/filho `PENDING` podem apontar para pedidos cujos jobs já estão COMPLETE; não somá-los como novas visitas faltando. Conferir a origem e o recibo antes de classificá-los ou corrigi-los; coincidência de request ID não permite remover um guard de partição. Se a consulta cobriu somente o observador, dizer explicitamente que não há pendência no PC1, sem extrapolar para toda Campaign Ops.
10. Se resultados e recibos já concordarem, encerrar a consulta sem regravar checkpoints ou reabrir links. Havendo divergência real, corrigir somente a camada autorizada e validar por readback; manter o restante como histórico.

Critérios de conferência da resposta:
- Fila PC1 e outbox vazios, mas campanha criada PAUSED com ativação diferida: **pedido de campanha ainda pendente**.
- Vários grupos do mesmo pedido com todos os links PASSED e aviso coletivo verificado: **acompanhamento concluído**, sem multiplicar a quantidade de pedidos humanos.
- Criação/agendamento confirmados para data futura: **programada**, não entrega atual comprovada.
- Estado atual da API não consultado ou leitura indisponível: **resultado histórico com fonte/horário**, não afirmação de status live.
- Entrada de cadastro divergente e jobs correspondentes concluídos: **conciliação técnica separada**, sem nova navegação e sem suprimir a divergência por inferência.

### Conferir o fluxo e localizar overhead

1. Ler o contrato ativo e seguir suas chamadas no despachante, no executor normal, na recuperação e no reporter. Verificar particularmente se `RUNNING`, `RECONCILING` e `REPAIRING` obedecem ao mesmo modo normal/sem galeria; uma regra no SKILL.md não corrige automaticamente um comando legado.
2. Comparar o caminho automático com o lote efetivamente exercitado: verificar se há mapa compartilhado preparado e um executor contínuo, ou se o despachante inicia um novo CLI/turno de modelo por link. Registrar a diferença como lacuna de integração, não como migração concluída.
3. Inspecionar o modo de informes e seu escopo. Distinguir entrega por item de configuração histórica por intervalo; verificar os estados dos jobs antes de atribuir bloqueio a uma prioridade antiga. Propor publicação fora do trecho crítico do PC1 preservando outbox/GET, sem afirmar que já está desacoplada se o loop aguarda a entrega antes do próximo item.
4. Apurar tempos pelos recibos da mesma tentativa: preparação/navegação até abertura, leitura e observação, fechamento, término do backend e entrega. Deduplicar tentativas antes dos cálculos. Separar amostras de PASS, NO_AD e ERROR; publicar mediana/faixa com o denominador e as exclusões. Não tratar a mediana de um PASS como duração de cada link ou previsão do lote inteiro.
5. Conferir timers e o último resultado do serviço sem acioná-los. Um serviço oneshot inativo entre ciclos, com resultado bem-sucedido e timer ativo, não é por si uma falha.
6. Entregar uma revisão operacional curta: fluxo válido, regras de exceção, medição observada e lacunas ainda não implementadas. Testes offline, replay real e integração automática são evidências diferentes. Não reabrir páginas nem alterar produção somente para responder à revisão; guardar achados temporários em relatório/checkpoint, não como novas regras globais.
7. Não diagnosticar cache pela sequência de resultados: comparar as opções realmente usadas nas ausências e no PASS. Sem isolamento da variável, registrar apenas o resultado observado e a limitação causal.

## 6. Testes e retenção

```bash
python3 -m unittest discover -s /root/mgs-agent/tests -p 'test_direct_traffic_landing*.py'
```

A suíte lean deve cobrir nova aba normal, rejeição de Incognito/reuso, query exata e extensão autorizada, loading diferente de ausência, retarget de Document para scroll, escalada após sinal, tempo inválido/NaN, propriedade/fechamento e seleção da rota do worker. Cobrir também o modo ativo nas ramificações de reconciliação e reparo, a autorização de uma única tentativa extra sem resetar o lote, a atualização coerente do consolidado após esse resultado e o modo de informe por item. Um teste do caminho feliz não demonstra que o reparador deixou de exigir Incognito/galeria. Testes legados de galeria devem selecionar explicitamente seu modo, sem obrigar o caminho atual a voltar ao comportamento antigo.

Separar testes offline de prova operacional: execução real do helper, anúncio, tempo, fechamento, estado da fila e mensagem entregue são verificações distintas. Não usar totais históricos de testes como evidência da versão corrente.

Para imagens legadas, usar apenas o mecanismo autorizado de limpeza após estado final válido e GET de entrega. Preservar metadados/recibos, proteger referências de tarefas incompletas e não seguir symlinks para outras raízes. A ausência de uma imagem já purgada não invalida um PASS registrado nem autoriza outra impressão.
