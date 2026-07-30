# Hermes busy input steering — diagnóstico, mídia e rollout MGS

## Quando usar

Quando uma mensagem enviada durante um turno ativo só chega depois da primeira resposta, quando o usuário quer consolidar complementos no trabalho em andamento, ou quando imagem/áudio/caption somem em `busy_input_mode=steer`.

## Modelo mental

`display.busy_input_mode` controla novas mensagens enquanto a sessão executa:

- `queue` — preserva o turno atual e agenda outro turno.
- `interrupt` — aborta/redireciona o turno e pode cancelar tools/subagentes.
- `steer` — injeta texto no próximo ponto seguro do turno ativo, anexando-o ao último resultado `role=tool` com o marcador out-of-band confiável.

O recurso existir no código não significa estar ativo no profile. Nunca responder “já está ativo” sem ler o valor vivo.

## Arquitetura end-to-end do Discord

Fluxo relevante:

```text
Discord on_message
  -> dedup/autorização/filtros
  -> DiscordAdapter._handle_message
       -> normaliza caption/menção
       -> classifica anexos
       -> baixa para cache
       -> MessageEvent(text, message_type, media_urls, media_types)
  -> BasePlatformAdapter.handle_message
       -> se sessão ativa: busy_session_handler ANTES do preprocessamento normal
  -> GatewayRunner._handle_active_session_busy_message
       -> running_agent.steer(payload)
```

`MessageEvent` não tem `image_path`/`audio_path`. Mídia fica em listas paralelas:

```python
media_urls = ["<local path ou URL fallback>", ...]
media_types = ["image/png", "audio/ogg", ...]
```

Tipos Discord/Hermes:

- imagem: `MessageType.PHOTO`;
- voice note nativo Discord: `MessageType.VOICE` (`Attachment.is_voice_message()` ou duration+waveform);
- arquivo de áudio comum: `MessageType.AUDIO`.

O `message_type` global é escolhido pelo primeiro attachment reconhecido. Para mensagens mistas, classificar cada item pelo seu próprio `media_types[i]`; nunca promover todos os arquivos com base apenas no tipo global.

Caches canônicos:

```text
<HERMES_HOME>/cache/images/img_<12hex>.<ext>
<HERMES_HOME>/cache/audio/audio_<12hex>.<ext>
```

O caminho primário usa `Attachment.read()` autenticado. Em falha, imagem/áudio podem cair para URL CDN, então `media_urls` não é garantia absoluta de path local.

## Estado do evento antes do busy handler

Antes de `_prepare_inbound_message_text`, a matriz é:

```text
Entrada                    event.text                                      message_type  media_urls
Imagem sem caption         (The user sent a message with no text content)  PHOTO         cached path/URL
Imagem + caption            caption normalizada                            PHOTO         cached path/URL
Voice sem caption          placeholder                                     VOICE         cached path/URL
Voice + caption             caption                                         VOICE         cached path/URL
Áudio comum sem caption     placeholder                                     AUDIO         cached path/URL
Áudio comum + caption       caption                                         AUDIO         cached path/URL
```

Transcrição, vision enrichment, native image content parts, document/audio context notes e tradução de paths ainda não aconteceram.

## Gap crítico do steer baseado só em `event.text`

Se o busy handler fizer:

```python
steer_text = (event.text or "").strip()
running_agent.steer(steer_text)
```

então:

- mídia com caption envia só a caption;
- mídia sem caption envia só o placeholder;
- o placeholder é não-vazio, portanto `steer()` aceita;
- steer bem-sucedido não entra na fila, logo o asset some do turno corrente e não é replayado depois.

Há dois gates busy no runner/base; ambos devem chamar o mesmo serializador para não haver comportamento diferente por timing/race.

## Preprocessamento normal quando idle/queued

`GatewayRunner._prepare_inbound_message_text()` faz o enriquecimento completo:

- imagem: visão nativa ou `vision_analyze` textual com descrição e path;
- `VOICE`: STT e transcript antes da caption;
- `AUDIO`: não faz STT no caminho fresco; injeta nota com path para processamento explícito;
- documentos: injeta conteúdo ou nota de path conforme MIME.

Queued/drain tem caminhos adicionais que podem tratar `AUDIO` junto com `VOICE` e transcrever áudio comum. Exigir consistência entre fresh, queue e steer; áudio comum não deve mudar de semântica só porque chegou enquanto busy.

## Contrato recomendado: `MessageEvent -> steer payload`

Criar/reusar um helper central, puro ou com efeitos explícitos, que retorna texto sem mutar/consumir o evento. Formato recomendado:

```text
[Discord inbound message id=123456789]
Attachments:
- image 1; MIME=image/png; path=<agent-visible-path>
  Inspect with vision_analyze if relevant.
- audio 1; kind=voice|audio; MIME=audio/ogg; path=<usable-path>
  Transcribe or process this file directly if its contents matter.

User caption:
<caption exatamente uma vez>
```

Invariantes:

1. Todos os anexos aparecem uma vez e na ordem original.
2. Cada mensagem inclui `message_id`/framing próprio; múltiplos steers podem ser concatenados sem destruir fronteiras.
3. Caption aparece uma vez.
4. Imagem inclui path que `vision_analyze` consegue resolver.
5. Voice pode incluir transcript já obtido, mas sempre mantém o path; falha de STT nunca apaga o asset.
6. Steer aceito não é também enfileirado.
7. Steer rejeitado mantém o `MessageEvent` original completo para queue/fallback.
8. Não usar `MEDIA:<path>`: é diretiva outbound, não referência inbound.
9. Passar texto puro a `AIAgent.steer()`; não pré-aplicar `format_steer_marker()`, evitando wrapper duplicado.
10. Notas geradas dos anexos devem preceder a caption, ou delimitadores do marker dentro da caption devem ser neutralizados para não quebrar o framing.

## Paths e sandbox

Use `to_agent_visible_cache_path()` para o caminho que o agente/terminal deve enxergar. Nuances:

- atualmente a tradução cobre Docker; outros backends remotos exigem validação própria;
- `vision_analyze` aceita paths visíveis do container e faz tradução inversa;
- `transcribe_audio()` historicamente valida `Path(file_path)` diretamente. Se receber path Docker traduzido sem `from_agent_visible_cache_path()`, pode falhar no host.

Contrato ideal: ferramentas que consomem cache inbound aceitam o mesmo path visível ao agente e traduzem internamente. Até isso ser garantido, diferenciar `agent_path` e `host/tool_path` no payload/adapter sem perder nenhum deles.

## Álbuns e múltiplas mensagens

- Vários attachments no mesmo post Discord já formam um único `MessageEvent`.
- Posts separados não têm media-group ID Discord dedicado.
- `merge_pending_message_event` concatena paths/MIME e mescla captions, promovendo para `PHOTO` se houver foto.
- O FIFO busy pode agregar qualquer evento com mídia ao head slot, não apenas álbuns; preservar boundaries e definir explicitamente se reply anchor/message ID final é o primeiro ou o último.
- `AIAgent.steer()` concatena chamadas com newline e injeta um único bloco out-of-band. Cada payload precisa de framing próprio.

## Role alternation

`AIAgent.steer()` deve continuar:

- sem criar nova mensagem `role=user` mid-loop;
- anexando ao último `role=tool`;
- preservando tool results multimodais;
- re-stash quando ainda não há tool result;
- entregando `pending_steer` como um próximo turno exatamente uma vez se o run terminar antes da injeção.

Nunca resolver mídia steer criando um user message sintético no meio do loop; isso quebra alternância e prompt caching.

## Deduplicação/replay

Discord usa dedup em memória por `message.id`, default TTL 300s e máximo 2000 IDs. A checagem ocorre antes do download, e thread starters são pré-semeados. Porém restart do processo ou replay após TTL pode executar novamente. Para side effects fortes, testar/considerar barreira durável `(platform, message_id)` antes de cache/steer.

## Diagnóstico e rollout MGS

1. Ler `display.busy_input_mode` no config vivo.
2. Checar `busy_text_mode` e `HERMES_GATEWAY_BUSY_INPUT_MODE` quando presentes.
3. Comparar live com `/root/mgs-agent/profiles/<agent>-config.yaml`.
4. Confirmar valor resolvido com o Python do venv.
5. Aplicar, quando solicitado:

```bash
hermes -p <agent> config set display.busy_input_mode steer
```

6. Atualizar mirror, registrar audit/infra e reiniciar de forma detached se o gateway não recarregar.
7. Validar serviços e fazer smoke funcional real durante tool call ativa.

## Proteção canônica MGS do runtime

A correção não termina no checkout vivo. Os artefatos canônicos são:

```text
/root/mgs-agent/patches/hermes/mgs-busy-steer-universal-media-2026-07-10.patch
/root/mgs-agent/patches/hermes/mgs-busy-steer-startup-merge-2026-07-11.patch
/root/mgs-agent/patches/hermes/mgs-busy-steer-startup-race-hardening-2026-07-11.patch
/root/mgs-agent/patches/hermes/mgs-busy-steer-reentrant-followup-2026-07-12.patch
/root/mgs-agent/patches/hermes/mgs-busy-steer-reentrant-rebuild-2026-07-12.patch
```

Os patches devem permanecer listados, na mesma ordem, em ambos:

```text
/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh
/root/mgs-agent/scripts/run-hermes-update-controlled.sh
```

Invariantes mínimos do guard:

- `async def _prepare_busy_steer_payload` existe;
- `_prepare_inbound_message_text(..., for_mid_turn_steer=True)` existe;
- imagens viram markers com path agent-visible sem consumir o native-image buffer do turno ativo;
- VOICE segue STT e AUDIO/document/video preservam path;
- os dois gates busy usam o mesmo helper;
- PHOTO só força queue quando o modo efetivo não é `steer`;
- falha de enrichment mantém caption + paths e tenta steer antes de queue;
- follow-up recebido enquanto `_running_agents[session_key]` ainda é `_AGENT_PENDING_SENTINEL` reserva ordem de chegada antes de qualquer preprocessamento assíncrono;
- o worker aguarda todas as reservas em voo, drena em FIFO e promove o sentinel para o agente real de forma atômica sob a mesma barreira;
- follow-up recursivo na mesma geração reconhece a promoção já concluída: reutiliza o mesmo `AIAgent` quando a assinatura continua igual e transfere ownership atomicamente para um `AIAgent` reconstruído quando skill/config/session cache mudou entre os dois turnos; essa transferência só é permitida em `_interrupt_depth > 0`, enquanto geração substituída e troca de agente em turno inicial continuam fail-closed;
- quando um evento anterior já ocupa a fila do próximo turno e o turno atual termina com `result["pending_steer"]`, o leftover steer é anexado, com framing out-of-band, ao evento anterior depois do preprocessamento inbound; nunca pode ser descartado pela presença simultânea de `pending_event`, nem replayado como terceiro turno;
- chamadas diretas legadas de `_run_agent()` com `run_generation=None` e slot vazio continuam válidas sem enfraquecer o ownership de runs gerenciados;
- `_try_busy_steer_event()` relê geração e identidade do agente depois de STT/enrichment; resultado atrasado nunca é aplicado a agente encerrado/substituído;
- `_merge_startup_steer_into_message()` acontece antes da primeira chamada ao modelo, inclusive quando o primeiro resultado não usa tools;
- `_persist_user_message_override` acompanha a mensagem efetivamente mesclada nos caminhos de resume/tool-tail;
- cleanup de turno/stop fecha a janela, remove buffer/reservas/sequence e acorda qualquer waiter;
- fallback de mídia usa path agent-visible tanto em sucesso quanto em erro de enrichment;
- testes busy/media/startup, concorrência FIFO e stale-agent rodam dentro do guard.

Para cada mudança futura, validar `git apply --reverse --check` no checkout vivo, `git apply --check` em worktree limpa de `origin/main`, `ruff`, `py_compile`, pytest alvo e depois smoke Discord real. Um patch presente em disco, mas ausente do guard/precheck, é regressão futura esperando o próximo update.

## Testes obrigatórios

1. Matriz adapter: imagem/voice/audio, com e sem caption.
2. Busy steer: payload contém caption + todos os paths; nunca placeholder-only.
3. Steer rejeitado: evento completo preservado na fila.
4. Múltiplos/mistos: classificação por MIME individual.
5. Consolidação: vários IDs preservados em ordem, uma resposta final, sem replay.
6. Álbum: todos os paths/MIME/captions preservados.
7. STT: `VOICE` transcrito, `AUDIO` comum não, igual em fresh/queue/steer; falha mantém path.
8. Docker/remote: path abre no terminal, vision e transcription.
9. Role alternation: só último tool result muda; multimodal preservado.
10. Replay: mesmo ID não baixa/steera duas vezes; cobrir restart/TTL conforme política durável.
11. Handoff com fila já ocupada: pedido A pendente + complemento B aceito como steer no fim do turno anterior devem chegar juntos ao próximo turno, em ordem, exatamente uma vez.

## Limites que devem ser explicados

- Steer depende de turno ativo e de próximo ponto seguro.
- Se o complemento chegar depois da resposta final, vira novo turno.
- Uma sessão pode já aparecer como ocupada/“digitando” enquanto `_running_agents[session_key]` ainda é `_AGENT_PENDING_SENTINEL`. No runtime MGS corrigido, esse intervalo não usa mais `queue`: a chegada reserva uma sequência antes de STT/enrichment; a promoção aguarda reservas em voo, drena FIFO e anexa tudo ao primeiro user turn antes da chamada ao modelo.
- Se config e resolver estiverem em `steer`, mas aparecer `Queued for the next turn` durante essa janela, tratar como regressão do patch/guard e verificar `_reserve_startup_steer`, `_promote_agent_and_consume_startup_steers`, `_merge_startup_steer_into_message` e os testes de barrier/stale-agent.
- Ver `Queued for the next turn` não prova que o profile voltou para `queue`. Antes de afirmar regressão de configuração, separar: (1) config vivo; (2) valor resolvido; (3) agente disponível versus sentinel; (4) retorno real de `running_agent.steer()`; (5) presença dos invariantes do startup merge.
- Para investigar um caso real, buscar a mensagem original diretamente no Discord, comparar timestamps do pedido principal e do complemento e correlacionar com a sessão/runtime. A sessão Hermes é contexto secundário; o Discord é a fonte direta para conteúdo e horário atuais.
- Esses limites de timing não justificam perder mídia recebida enquanto o turno já estiver ativo.

## Personalização da confirmação visual de steer

A confirmação de steer tem duas camadas distintas:

- `display.busy_steer_ack_enabled` controla apenas mostrar/ocultar o aviso;
- o texto do aviso pode continuar fixo em `gateway/run.py` quando a versão instalada não expõe uma chave de mensagem customizável.

Para localizar/personalizar o texto compartilhado pelos gateways MGS:

1. Confirmar no runtime vivo onde `is_steer_mode` monta a mensagem e verificar se existe configuração textual upstream antes de criar patch local.
2. Alterar somente a confirmação visível; não mexer no payload entregue a `AIAgent.steer()` nem no framing out-of-band.
3. Adicionar teste de regressão no teste stock já existente para o ack. A orientação de primeiro uso do Hermes pode ser anexada ao aviso em sessões novas; por isso, validar `content.startswith(texto_exato)` e também ausência do texto legado, em vez de exigir igualdade total nesse caminho.
4. Manter testes de startup/race focados em comportamento (`content` não vazio e ausência de `Queued for the next turn`), sem acoplá-los à redação. Isso evita que um patch de localização dependa de testes introduzidos por outro patch MGS e ausentes no upstream limpo.
5. Criar patch canônico independente em `patches/hermes/`, registrá-lo no guard e no updater controlado, e adicionar invariantes da nova frase.
6. Validar: `bash -n`, `py_compile`, pytest direcionado, `git apply --reverse --check` no checkout vivo e `git apply --check` contra `origin/main` em worktree temporária.
7. Se o runtime for compartilhado, um único patch atende Zeus/Atena/Ares/agente legado, mas todos os gateways precisam de restart seguro; Zeus sempre por último. Não editar targets depois de gerar o snapshot do finalizer.

Pitfall de patches dependentes: se um teste foi criado por um patch MGS anterior e não existe em `origin/main`, não o inclua no patch independente de localização que precisa passar `apply --check` no upstream limpo. Torne o teste anterior neutro em relação à redação e concentre a asserção textual no teste stock que já existe upstream.

## Continuação após restart do gateway

O auto-resume de sessão interrompida não deve gerar uma resposta de “gateway recuperado”, pedir que o usuário repita o pedido nem abandonar tool outputs pendentes. O contrato MGS é:

1. O evento sintético de startup é transporte interno e nunca deve ser persistido como texto atribuído ao usuário.
2. Antes de agir, reconciliar o que já concluiu para não duplicar side effects.
3. Continuar todo trabalho pendente e responder pedidos em ordem cronológica, como se o chat não tivesse sido interrompido.
4. Não mencionar restart, recovery, checkpoint ou diretiva interna, salvo pergunta explícita do usuário.
5. Follow-up que chegar durante o auto-resume entra depois do trabalho anterior, preservando FIFO.
6. Proteger o comportamento em patch canônico, guard/updater e teste que garanta que o texto de transporte não aparece no turno do usuário.

Artefato canônico atual:

```text
/root/mgs-agent/patches/hermes/restart-recovery-natural-continuation-2026-07-11.patch
```

## Pitfalls

- **Reentrant queued follow-up após promoção:** `_run_agent_inner()` drena uma mensagem pendente chamando `_run_agent()` recursivamente com a mesma geração. Se a assinatura do cache não mudou, `current_agent is agent` significa promoção já concluída. Se skill/config/session cache mudou entre as duas etapas, o follow-up pode reconstruir legitimamente o `AIAgent`; nesse caso, e somente quando `_interrupt_depth > 0` + geração ainda atual, transfira ownership atomicamente para o agente reconstruído. Exigir identidade exata em ambos os casos aborta com `startup agent promotion lost ownership` e o Discord mostra `Sorry, I encountered an unexpected error`. Turno inicial com agente diferente ou qualquer geração substituída permanece fail-closed. Testes canônicos: `test_reentrant_followup_promotion_reuses_current_agent`, `test_reentrant_followup_does_not_mask_replaced_agent`, `test_reentrant_followup_transfers_same_generation_rebuilt_agent` e `test_recursive_run_enables_same_generation_replacement`.
- **Pending event + leftover steer no mesmo fechamento:** a fila do adapter pode já conter o pedido seguinte enquanto `turn_finalizer` devolve um complemento tardio em `result["pending_steer"]`. O antigo gate `if result and not pending and not pending_event` descartava silenciosamente o complemento. Preserve a ordem anexando o leftover, via `format_steer_marker`, à mensagem preparada do evento anterior antes da recursão. Teste canônico: `test_run_agent_merges_leftover_steer_into_earlier_queued_turn`.
- Validar apenas texto e declarar multimedia steer pronto.
- Chamar `queue` de consolidação.
- Usar `interrupt` para complementos e destruir tool/subagent work.
- Rodar o preprocessador completo com efeitos colaterais nos dois gates busy sem idempotência.
- Consumir native-image buffers ou ecoar STT antes de saber se steer foi aceito.
- Transcrever áudio comum apenas no caminho queued, mudando semântica por timing.
- Atualizar só live ou só mirror.
- Declarar concluído por YAML/test unitário sem smoke mid-turn real.
- Agendar restart enquanto revisão independente ainda está pendente.
- Editar runtime/config depois de preparar ou agendar o finalizer. Se surgir achado tardio, cancelar/pausar a execução destacada, corrigir, revalidar e gerar novo snapshot/finalizer.
- Confiar apenas em `py_compile`: ele não detecta chamada a método de instância inexistente. O preflight deve comparar calls/defs dos helpers críticos e o finalizer deve abortar se o hash validado mudar antes do restart.