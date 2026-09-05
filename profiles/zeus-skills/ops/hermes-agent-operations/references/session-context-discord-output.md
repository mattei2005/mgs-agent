# Sessions, Context Compression, and Discord Output

> Extracted from the former monolithic `SKILL.md` on 2026-07-10. Load this file only when its branch is relevant.

## Discord — “só aparece digitando”, sem histórico ao vivo

Quando Rodolfo perguntar por que não vê mais o “histórico” enquanto o agente está digitando, primeiro diferencie três coisas:

- **histórico do Discord**: mensagens já enviadas, que não foram apagadas;
- **indicador “digitando…”**: presença temporária do bot;
- **tool progress**: mensagens/edições transitórias que mostram consultas e ferramentas durante a execução.

Diagnóstico mínimo, antes de afirmar a causa:

1. Ler a configuração viva do profile em `display.tool_progress` e `display.platforms.discord.tool_progress`.
2. Conferir `display.platforms.discord.streaming`, `cleanup_progress` e `interim_assistant_messages`; não confundir streaming da resposta com progresso de ferramentas.
3. Comparar com o mirror versionado e, quando houver regressão recente, usar o histórico Git do arquivo para identificar exatamente quando `all/on` virou `false/off`.
4. Conferir o horário do último restart do gateway: uma alteração de config pode existir há horas e só se tornar visível após o restart.

Interpretação:

- `tool_progress: false/off` explica por que não aparecem mensagens/edições como `Reading skill`, `terminal` e demais ferramentas.
- Isso **não desliga o indicador nativo** `Zeus is typing…`: ele é controlado separadamente por `typing_indicator` no config da plataforma e tem default `true`.
- Portanto, nunca atribuir o desaparecimento do `is typing…` a `tool_progress: off` sem validar o valor resolvido de `PlatformConfig.typing_indicator` e o caminho real de `send_typing()`.
- Isso **não significa perda do histórico do Discord** nem perda do contexto interno; apenas oculta o acompanhamento operacional ao vivo.
- `cleanup_progress: true` pode remover o progresso transitório após a resposta final, mas não é a causa primária quando o progresso nunca aparece.

### Diagnóstico separado do indicador `is typing…`

Quando Rodolfo apontar especificamente para a linha nativa `Zeus is typing…`:

1. Confirmar qual superfície ele quer dizer; não tratar “digitando” e “progresso das ferramentas” como sinônimos.
2. Ler o valor resolvido do Discord no runtime, não apenas procurar a chave no YAML. Se `typing_indicator` estiver omitido, o default atual pode continuar sendo `true`.
3. Conferir o código vivo: o handler base inicia `_keep_typing()` quando `PlatformConfig.typing_indicator` é verdadeiro; o adapter Discord implementa `send_typing()` pelo endpoint `/channels/{channel_id}/typing`.
4. Procurar erros de typing no journal e executar os testes focados de Discord/typing quando necessário.
5. Se a credencial já estiver disponível no profile e o pedido for um diagnóstico visual na thread atual, pode-se fazer um smoke efêmero no endpoint de typing, sem imprimir o token, reportando somente o status HTTP. `204` prova que o Discord aceitou o evento; não prova sozinho que o cliente do usuário o exibiu continuamente.
6. Se o endpoint aceitar e o config resolvido estiver `true`, classificar a ausência como intermitência/continuidade do indicador até haver evidência mais forte — não “configuração desligada”. Inspecionar também a cadência: o adapter mantém uma tarefa persistente e chamadas duplicadas podem ser ignoradas; qualquer intervalo maior que a duração visual do Discord pode criar lacunas.

Teste focado útil no checkout vivo:

```bash
python -m pytest -q tests/gateway/test_discord_send.py -k typing tests/gateway/test_typing_indicator_toggle.py tests/gateway/test_keep_typing_timeout.py
```

Ao explicar uma mudança histórica, reconstruir a autorização original antes de chamá-la de regressão. Pedido para remover comandos técnicos brutos das threads humanas **não autoriza** desligar `tool_progress`; a correção deve preservar o acompanhamento ao vivo e reduzir/rotear apenas o detalhe excessivo. Se uma interpretação anterior ampliou o escopo para `off`, registrar o erro e restaurar o estado canônico `all` após a correção explícita de Rodolfo.

Resposta executiva recomendada: informar separadamente o estado de `tool_progress` e de `typing_indicator`, o horário/commit da mudança quando confirmados e o restart/hot-read que a ativou. Se a mudança entrou junto de refactor/sync sem pedido explícito, classificá-la honestamente como possível regressão de visibilidade, não como comportamento intencional presumido.

Para restaurar, tratar como mudança de configuração: alterar profile vivo e mirror canônico, validar com `hermes -p <profile> config check` e confirmar o valor resolvido no runtime. No checkout Hermes atual, `gateway/run.py` relê a configuração de display por turno; portanto `tool_progress` entra no próximo turno sem restart. Só usar restart seguro (Zeus por último) se a versão implantada não fizer hot-read ou se o smoke real provar que o valor novo não foi carregado. Não assumir que strings antigas (`all`, `off`) e booleanos atuais são intercambiáveis.

### Estado canônico MGS autorizado

Rodolfo prefere o acompanhamento ao vivo ligado em todos os agentes. O estado canônico de Zeus, Atena, Ares e agente legado é:

```yaml
display:
  tool_progress: all
  platforms:
    discord:
      tool_progress: all
      interim_assistant_messages: true
      cleanup_progress: true
```

Há três superfícies independentes que devem ser diagnosticadas separadamente:

1. `typing_indicator` — indicador nativo “digitando…”; default resolvido `true` quando omitido.
2. `tool_progress` — breadcrumbs de ferramentas, como leitura, terminal e chamadas de API.
3. `interim_assistant_messages` — mensagens naturais de andamento emitidas pelo assistente enquanto ainda executa.

Se Rodolfo disser que só vê “digitando…” e não vê o progresso, **não encerrar o diagnóstico ao encontrar `tool_progress: all`**. Verificar `interim_assistant_messages`: ele pode estar `false` enquanto typing e ferramentas continuam habilitados. Um smoke HTTP 204 no endpoint `/typing` prova apenas a superfície 1; não valida as superfícies 2 ou 3.

Regras operacionais:

- Aplicar nos quatro profiles vivos e nos quatro mirrors versionados; não corrigir apenas Zeus.
- Para restaurar acompanhamento completo no Discord, preservar `tool_progress: all` e definir `display.platforms.discord.interim_assistant_messages: true` como booleano real pelo writer canônico.
- Uma reclamação de Rodolfo sobre comandos brutos, blocos de terminal ou poluição técnica **não autoriza desligar o acompanhamento ao vivo**. Preservar o progresso; corrigir a apresentação, reduzir previews e rotear detalhes extensos para logs/`#alerts-infra` sem remover a visibilidade.
- Em refactors/sincronizações YAML, preservar semanticamente `all` e o booleano `true`; não normalizar para `false` como efeito colateral de formatação.
- Validar `config check` 4/4, readback live+mirror 8/8 com tipo e valor, e o resolver de runtime 4/4.
- Confirmar o hot-read no resolver/runtime e fazer smoke real no próximo turno; `interim_assistant_messages` e o display do Discord são relidos por turno no runtime atual, então não reiniciar apenas para essa alteração. Reiniciar com Zeus por último somente se a versão implantada exigir ou o smoke falhar.
- `cleanup_progress: true` pode remover mensagens transitórias no fim; isso é compatível com a preferência. A ausência delas no histórico após a resposta não prova que faltaram durante o turno — validar durante uma execução real ou por telemetria apropriada.
- Não confundir progresso resumido das ferramentas ou do assistente com despejo de logs brutos; outputs extensos continuam reduzidos na origem.

## Discord — suprimir previews automáticos de links

Use quando Rodolfo pedir que mensagens dos agentes não gerem cards/previews automáticos para URLs no Discord.

Estado MGS canônico:

- Chave por profile: `discord.suppress_link_previews: true`.
- Bridge interno: `DISCORD_SUPPRESS_LINK_PREVIEWS` em `plugins/platforms/discord/adapter.py`.
- Mensagens simples e captions usam `suppress_embeds=True`; edições de streaming preservam a flag com `suppress=True`.
- Embeds explícitos do Hermes (aprovação, clarify, model picker) não usam o helper de mensagens simples e devem continuar visíveis.
- Patch persistente: `/root/mgs-agent/patches/hermes/discord-suppress-link-previews.patch`.
- Patch guard: `/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh`.

Validação mínima após alteração/update:

1. `hermes -p <profile> config check` e readback de `discord.suppress_link_previews`.
2. `git apply --reverse --check` no patch contra o checkout vivo.
3. `pytest -q tests/gateway/test_discord_send.py`.
4. Para gateways não-Zeus, fazer restart seguro quando a implantação exigir. Para Zeus, pedir autorização explícita de timing antes de incluir no finalizer; `aplica para os 4` autoriza a configuração, não um restart imediato do Zeus.

Não remover a permissão Discord `Embed Links`: isso pode quebrar UI interativa. Não envolver URLs em `<...>` como workaround, porque altera o texto visível.

## Discord — continuação automática de respostas longas

Quando o Discord exibir `Response truncated — this reply exceeded the delivery limit (8 messages)`, o conteúdo foi gerado por completo, mas o adapter aplicou o teto anti-flood e substituiu a cauda por um aviso. O usuário não deve precisar detectar a falha, pedir “continua” nem recuperar o texto nos logs.

Estado MGS para o profile Zeus:

```yaml
discord:
  auto_continue_long_responses: true
  long_response_batch_delay_seconds: 1.0
```

Contrato operacional:

- Preservar `MAX_SPLIT_MESSAGES = 8` como tamanho do lote, não como teto destrutivo, quando `auto_continue_long_responses` estiver habilitado.
- Entregar todos os chunks da mesma resposta automaticamente, em lotes de até oito, com pausa configurada entre lotes.
- Não pedir nova inferência ao modelo e não criar um novo turno: a continuação é a cauda exata já gerada, evitando divergência, repetição de pesquisa ou side effects duplicados.
- Manter o comportamento upstream fail-safe (`auto_continue_long_responses: false`) nos profiles que não habilitarem explicitamente a opção.
- Aplicar o mesmo contrato a envio normal, fórum e overflow de edição/streaming.
- Se um envio real falhar no meio, registrar entrega parcial e retomar somente a cauda comprovadamente ausente; nunca reenviar cegamente os chunks já publicados.
- Não substituir a continuação por anexo sem pedido explícito do usuário.

Validação mínima:

1. `hermes -p zeus config check`.
2. Readback tipado: `auto_continue_long_responses` como `bool true` e delay como número.
3. Resolver `PlatformConfig.extra` no runtime e confirmar as duas chaves.
4. Executar `tests/gateway/test_discord_split_cap.py`, preservando tanto o cap default quanto a entrega completa opt-in.
5. Após restart seguro, observar uma resposta controlada com mais de oito chunks e confirmar no Discord que todas as partes chegaram sem o aviso de truncamento.

## 6. Session reset / manter contexto em threads

Use quando Rodolfo perguntar sobre mensagens do Hermes como:

```text
◐ Session automatically reset (daily schedule at 4:00). Conversation history cleared.
Use /resume to browse and restore a previous session.
Adjust reset timing in config.yaml under session_reset.
```

Interpretação correta: isso é política de `session_reset` do gateway, não erro do modelo nem apagamento de mensagens do Discord. O efeito é limpar o contexto interno daquela conversa/thread para o agente; o histórico visual do Discord continua existindo, mas a sessão precisa de `/resume` ou reconstrução via logs/mensagens se o agente responder depois do reset.

Se Rodolfo disser que não quer perder contexto nas threads, o ajuste canônico do profile é:

```yaml
session_reset:
  mode: none
```

`mode: none` é o modo Hermes oficial para desabilitar reset automático: sem reset diário e sem reset por idle. Isso não remove o limite físico de contexto do modelo; conversas muito grandes ainda dependem de compression/summary. Para MGS, preferir `session_reset.mode: none` + compression ativa em vez de reset bruto por agenda.

Workflow seguro:

1. Confirmar qual profile/gateway será afetado, normalmente `/root/.hermes/profiles/zeus/config.yaml` para Zeus.
2. Verificar o schema no código vivo quando houver dúvida: `gateway/config.py` → `SessionResetPolicy` (`daily`, `idle`, `both`, `none`) e overlay de `config.yaml` via chave top-level `session_reset`.
3. Aplicar no `config.yaml` do profile:

```bash
hermes config set session_reset.mode none
```

ou patch YAML equivalente se o CLI não suportar bem nested keys.

4. Validar que o arquivo contém `session_reset: {mode: none}` ou bloco equivalente.
5. Reiniciar/recarregar o gateway com o padrão MGS de restart seguro; não reiniciar Zeus no meio de tool calls foreground ou sem finalizer externo.
6. Explicar o limite operacional: “não haverá reset automático; contexto extremo ainda pode compactar por limite de tokens”.

Pitfalls:

- Não responder “não dá” só porque a mensagem menciona `/resume`; `session_reset.mode: none` existe.
- Não confundir `compression.threshold` com `session_reset`: compression resume contexto grande; session reset zera por política de tempo/idle.
- Se a ordem for só explicativa (“tem como?”), responder o caminho e pedir “aplica?” antes de mutar config/restart. Se Rodolfo mandar “aplica”, executar.

## Diagnóstico de compactação frequente em thread visualmente curta

Não concluir pelo número de mensagens do Discord. Antes de alterar `compression.threshold`, medir o transcript interno da sessão em `state.db` e separar três gatilhos:

1. **limite real/estimado de tokens** — logs `Pre-API compression` e `context compression started`;
2. **válvula por contagem de mensagens** — `compression.hygiene_hard_message_limit` no gateway;
3. **inflação do turno** — quantidade de API calls, tool calls, reloads de skill e volume de tool results/replay.

Readback mínimo da sessão:

- `sessions.api_call_count`, `message_count`, `tool_call_count`;
- `messages` agrupadas por `role`, `active`, `compacted`;
- ferramentas mais chamadas e soma de `length(content)`;
- tamanho de `tool_calls` e dos campos de replay/reasoning;
- logs de compressão antes/depois, incluindo tokens aproximados e chamada real seguinte.

Interpretação:

- Uma thread com poucos posts pode legitimamente compactar se um único turno tiver dezenas ou centenas de chamadas de modelo/ferramentas.
- Recarregar a mesma skill grande, fazer muitos patches pequenos e repetir `skill_manage`/readbacks infla o contexto evitavelmente; a correção primária é reduzir o tool loop, agregar lookups e manter skills como routers enxutos.
- `hygiene_hard_message_limit` não é o threshold normal de contexto. A documentação Hermes atual define **5000** como default/safety valve para sessões que não conseguem obter usage real. Um valor MGS legado baixo, como **250**, pode forçar compactação apenas por contagem mesmo com tokens bem abaixo do limite; corrigir para o default oficial quando confirmado nos quatro profiles/mirrors.
- O número do aviso pré-API é estimativa conservadora; compare com `in=` da última chamada real e com o primeiro `in=` pós-compactação antes de chamar o gatilho de falso.
- Antes de propor mudança de threshold, consultar o histórico: se `0.90` foi uma decisão explícita de Rodolfo para preservar mais contexto, não desfazer nem elevar além disso como tentativa de mascarar tool-loop excessivo.
- Verificar a versão instalada contra o upstream: fixes de compaction por usage real, anti-thrashing e runtime context budget podem tornar um update controlado mais importante que tuning local.

A correção recomendada deve ser em camadas: eliminar o gatilho legado por contagem, conter o crescimento evitável do agente/skill e só depois avaliar update/threshold. Não desligar compression.

### Aplicação segura do limite de higiene nos profiles MGS

Quando o diagnóstico confirmar o legado `hygiene_hard_message_limit: 250`, aplicar o default oficial `5000` assim:

1. Verificar se há update/restart Hermes concorrente e ler os valores atuais em todos os profiles e mirrors.
2. Criar backup dos oito arquivos: quatro `~/.hermes/profiles/<profile>/config.yaml` e quatro mirrors `/root/mgs-agent/profiles/<profile>-config.yaml`, com hashes.
3. Para os profiles vivos, usar o writer nativo com escalar numérico: `hermes -p <profile> config set compression.hygiene_hard_message_limit 5000`.
4. Alterar somente a mesma chave nos mirrors; não reserializar o YAML inteiro.
5. Validar `config check` em todos, readback YAML de **tipo e valor** (`int`, `5000`) nos oito arquivos, diff exato contra o backup e PIDs inalterados.
6. Não reiniciar: a documentação Hermes define hot reload de `compression.*` na próxima mensagem. Não criar thread de smoke apenas para forçar o reload.
7. Atualizar inventário/audit e enviar REPORT-INFRA canônico.

Pitfalls de validação:

- `diff` retorna código `1` quando encontra a diferença esperada. Sob `set -e`/`pipefail`, trate esse status explicitamente ou valide semanticamente em Python; não classifique a mudança correta como falha.
- `config check` pode imprimir `config version X → Y (update available)` e ainda retornar código `0`; isso é aviso de migração disponível, não falha da chave alterada.
- A mudança evita compactação disparada apenas por contagem baixa de mensagens internas. Ela não elimina compactação legítima por tokens nem corrige tool loops excessivos retroativamente.
- Preserve `threshold`, `target_ratio` e `protect_last_n` quando não fazem parte do escopo autorizado.

## 6. Context compression / Codex gpt-5.5 notices

Use quando Rodolfo perguntar sobre mensagens do Hermes como:

```text
ℹ Codex gpt-5.5 caps context at 272K, so auto-compaction was raised to 85% (from X%)...
```

Interpretação correta: isso é um aviso de inicialização/primeiro turno, não erro e não alerta de que a thread já chegou a 85%. O Hermes detecta `openai-codex/gpt-5.5` e auto-eleva o threshold de compactação para 85% porque a rota Codex limita a janela em ~272K tokens; a mensagem apenas explica que mudou de `compression.threshold` antigo para `0.85`.

Workflow recomendado MGS:

1. Explicar de forma executiva: auto-compaction resume a conversa só quando o contexto fica grande; 85% usa mais janela antes de resumir.
2. Se Rodolfo quiser manter o comportamento mas remover o aviso repetitivo, **não desativar a compactação** e **não desligar o auto-raise como primeira opção**. Definir o threshold global do profile para o mesmo valor do auto-raise:

```bash
hermes config set compression.threshold 0.85
```

3. Validar no arquivo do profile, porque versões atuais do CLI têm `hermes config show`, mas não necessariamente `hermes config get`:

```bash
grep -n -A8 '^compression:' /root/.hermes/profiles/zeus/config.yaml
hermes config check
```

4. Se Rodolfo pedir explicitamente 90%/95%, aí desligar o auto-raise e setar manualmente:

```bash
hermes config set compression.codex_gpt55_autoraise false
hermes config set compression.threshold 0.90   # ou 0.95
```

Pitfalls:

- Não confundir “auto-compaction was raised” com “a compactação acabou de rodar”. É startup notice.
- Para MGS, 85% é a recomendação segura: em 272K, compacta em ~231K e deixa ~40.8K de folga. 90% deixa ~27.2K; 95% só ~13.6K e é arriscado com tool outputs/system prompt.
- Se uma sessão já aberta ainda mostrar o aviso, validar em nova sessão/novo init antes de concluir que a configuração falhou.

## 6. Discord link previews / suppressão de embeds automáticos

Use quando Rodolfo pedir que links enviados por Zeus, Atena, Ares, agente legado ou futuros agentes não gerem cards/previews automáticos no Discord.

### Diagnóstico canônico

1. Consulte a documentação Hermes e o código vivo do adapter Discord; não presuma que exista uma chave de config.
2. Diferencie:
   - **preview automático de URL**: card gerado pelo Discord para um link comum;
   - **embed explícito do bot**: UI usada por aprovações, clarify, model picker e outros fluxos interativos.
3. No Hermes v0.18.2, o envio textual normal passa por `plugins/platforms/discord/adapter.py::DiscordAdapter.send()` e chama `channel.send(content=..., reference=...)`; não há configuração pública documentada para suprimir previews globalmente.

### Solução recomendada

Implementar uma opção comportamental em `config.yaml` e propagá-la pelo adapter para aplicar `suppress_embeds=True` nos envios de texto normal. Cobrir todos os caminhos equivalentes, não apenas `DiscordAdapter.send()`:

- mensagens normais e retries sem `reference`;
- continuações após overflow;
- posts/follow-ups de fórum quando aplicável;
- mensagem inicial e edições do streaming, preservando a flag;
- mensagens de ferramentas/cross-platform delivery que reutilizem o adapter.

Não aplicar a supressão indiscriminadamente aos fluxos que constroem `discord.Embed` explicitamente. Aprovações, clarify, prompts e model picker devem continuar renderizando suas interfaces.

### Alternativa não recomendada

Remover a permissão Discord **Embed Links** do role do bot também impede previews automáticos, mas pode quebrar embeds explícitos e fluxos interativos. Use apenas se Rodolfo aceitar essa perda funcional.

### Contrato de implementação

- Preferir uma chave pública como `discord.suppress_link_previews: true`, traduzida pelo hook YAML do plugin; não criar variável `.env` como superfície de configuração.
- O default upstream deve preservar compatibilidade; o default MGS pode ser habilitado em Zeus/Atena/Ares/agente legado.
- Adicionar testes para URL comum sem preview e para embed explícito ainda presente.
- Validar no Discord real com mensagem contendo URL e readback da flag/ausência do card.
- Proteger o patch MGS contra updates.
- Separar **configuração aplicada** de **ativação por restart**. Aprovar a mudança para quatro profiles não implica reiniciar Zeus imediatamente.
- Antes de agendar restart multiagente, declarar o escopo exato. Para Zeus, exigir autorização explícita de timing (`reinicia Zeus agora` ou janela equivalente); sem isso, reiniciar apenas os demais agentes e deixar Zeus como pendência.
- Se Rodolfo interromper um restart agendado, cancelar primeiro o timer/unit antigo, validar que Zeus manteve o mesmo PID/start timestamp e só então reagendar o subconjunto autorizado. Nunca editar apenas o finalizer enquanto o timer continua armado.
- Se a pergunta for apenas “tem como?”, explicar a estratégia e pedir autorização antes de mutar config/código. Autorização de implementação e autorização de restart são decisões separadas.

### Pitfall

Não confundir “suprimir preview de link” com “proibir qualquer embed”. A primeira é uma preferência visual de mensagens textuais; a segunda pode remover controles operacionais importantes.

## 6. Reporting templates

### Resposta executiva para tooling web

```text
Pergunta                                      Resposta
──────────────────────────────────────────── ─────────────────────────────
1. Tem web_search nativo?                    Sim/Não + tool name
2. Tem web_fetch nativo?                     Sim/Não + web_extract mapping
3. MCP de busca configurado?                 Sim/Não + profile results
4. Versão trouxe capability nova?            Versão + delta conciso
5. Toolsets ativos Zeus/Atena                tabela abaixo
```

Depois: tabela de toolsets, tabela de backends, recomendação direta e `Próximo passo pendente:`.

### Resposta executiva para update

Use **blocos simples sem language tag** ou bullets curtos para qualquer matriz de status/validação/novidades. Não usar tabela Markdown crua (`|---|---|`) em Discord: Rodolfo considera visualmente regressivo e já corrigiu esse padrão. Não usar fences com linguagem como ` ```text`, ` ```bash` ou ` ```json` em respostas Discord: em algumas renderizações isso vaza uma linha solta `text` e quebra a leitura. Cabeçalhos devem nascer do contexto real do update; não copiar exemplos. Se houver drift de estilo ou dúvida sobre renderização de tabelas, ver `references/discord-table-format-and-standards-drift.md`.

Regra de anexos para Rodolfo: **nunca enviar arquivo/anexo por iniciativa própria**. Se ele pedir “mostra por aqui”, “no chat” ou apenas pedir explicação/review, responder inline. Só enviar `MEDIA:/...`/anexo quando ele pedir explicitamente arquivo/anexo. Para documentos longos, oferecer resumo inline e perguntar se quer anexo. O guard local `/root/mgs-agent/scripts/discord-response-lint.py --check` deve acusar language-tagged fences, linha solta `text`, tabela Markdown crua e diretivas `MEDIA:/...` em drafts.

Correção operacional 2026-07-07: em respostas normais de update para Rodolfo, **não colar blocos `[REPORT-INFRA]` inline na própria thread de update**. REPORT-INFRA é feed/canal operacional separado; se Zeus não tiver entrega explícita para esse destino no momento, registrar a mudança em Git/audit/inventário e resumir no report final como “infra alterada: paths + commits”, sem transformar a resposta executiva em alerta de infra.

Quando a resposta longa foi redigida em arquivo/stdin antes de enviar, validar quando prático com:

```bash
python3 /root/mgs-agent/scripts/discord-response-lint.py --check < draft.md
```

**Se Rodolfo apontar regressão visual/legibilidade após update** (ex.: “por que não está em tabela?” ou “voltou aos padrões?”), não trate como mera preferência de resposta. Faça auditoria de padrões: config viva dos profiles, backups/snapshots, SOUL/style rules, gateways e patch guard. Se o problema for regra permissiva no SOUL, fortaleça a regra para “não usar tabela Markdown crua no Discord; usar bloco `text` alinhado” nos agentes afetados. Detalhe em `references/discord-table-format-and-standards-drift-2026-06-09.md`.

```text
Resumo: atualizar agora / deferir / janela controlada.
Evidências: commits atrás, highlights, risco local, backup/checks.
Impacto: gateways offline ~1-2 min; Zeus pode interromper sessão ativa.
Próximo passo: comando exato ou validação pendente.
```

Exemplo de matriz final:

```text
Item                    | Estado
------------------------|-------------------------------
Hermes                  | v0.16.0 / behind 0
Gateways                | Zeus/Atena/Ares/agente legado active
Patches MGS             | guard OK / py_compile OK
Backup                  | removido ou path preservado
Pendência               | nenhuma ou ação concreta
```
