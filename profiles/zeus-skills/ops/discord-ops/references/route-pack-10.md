### Regra MGS: renomear thread nova uma vez; nunca renomear thread já aberta

Política correta tem dois estágios:

1. **Thread nova auto-criada pelo bot:** pode nascer com título provisório/determinístico e receber **um único rename semântico pós-primeira resposta** estilo ChatGPT, quando o título LLM ficar disponível.
2. **Thread já aberta/renomeada:** deve manter o nome até ser finalizada. Não renomear por follow-up, pausa longa, session reset, reply curto, pergunta nova dentro da mesma thread ou novo auto-title interno da sessão Hermes.

#### Sufixo do autor sem alterar o padrão aprovado

Quando Rodolfo pedir para acrescentar o nome de quem abriu a thread, preservar 100% da lógica de título existente e aplicar apenas um pós-processamento final: `Título Base - PrimeiroNome`. Não mexer em heurística, prompt, idioma, tamanho-alvo, guardrails, nem regra de thread antiga. O sufixo deve usar só o primeiro nome humano (`display_name`/`source.user_name`), sem ID/mention/sobrenome, truncando somente a base se necessário para respeitar o limite de 100 caracteres do Discord. Detalhe e checklist: `references/discord-thread-title-author-suffix-2026-06-17.md`.

Pitfall pós-update validado: documentar o sufixo em skill/referência não protege runtime. O patch `discord-thread-title-author-suffix.patch` precisa estar no guard canônico de Hermes (`ensure-hermes-mgs-patches.sh` e update controlado) e a validação pós-update deve procurar `_append_thread_author_suffix` no adapter e `_append_discord_thread_author_suffix` no gateway. Se o título voltar sem ` - PrimeiroNome`, auditar primeiro perda de patch local pós-update antes de mexer na heurística de título.

#### Pitfall validado: duplicata de função sobrescrevendo trava segura

Ao corrigir rename de thread em `/root/.hermes/hermes-agent/gateway/run.py`, não validar só a presença de `_discord_thread_safe_to_autorename(...)`. Python usa a **última definição** de um método dentro da classe; se houver uma segunda `_rename_discord_thread_for_session_title(...)` abaixo da versão segura, ela sobrescreve a primeira e pode ignorar a trava.

Checklist obrigatório antes de restart:
- `grep -n "def _is_discord_thread_lane\|def _sanitize_discord_thread_title\|async def _rename_discord_thread_for_session_title\|def _schedule_discord_thread_title_rename" /root/.hermes/hermes-agent/gateway/run.py`
- Confirmar contagens esperadas depois do patch: exatamente 1 para `_discord_thread_safe_to_autorename`, `_rename_discord_thread_for_session_title`, `_schedule_discord_thread_title_rename`, `_is_discord_thread_lane` e `_sanitize_discord_thread_title`.
- Confirmar reasons: `"MGS AI-generated session title"` = 1 e `"Hermes auto-generated session title"` = 0 quando a versão insegura antiga foi removida.
- Se qualquer grep divergir, **parar e reverter do backup antes de restart**. Não atualizar patch reaplicável nem reiniciar gateways até o gate passar.

Incidente validado: o patch tinha colado um bloco contíguo duplicado com `_is_discord_thread_lane`, `_sanitize_discord_thread_title`, uma `_rename_discord_thread_for_session_title` insegura (sem `await self._discord_thread_safe_to_autorename`, reason `Hermes auto-generated session title`) e um `_schedule_discord_thread_title_rename` duplicado. A correção segura foi remover o bloco duplicado contíguo inteiro, preservando as versões boas anteriores.

Guardrails esperados para o rename semântico de thread nova:
- Só aplicar em thread Discord auto-criada pelo bot atual.
- Só aplicar enquanto a thread ainda é recente (janela curta pós-criação; ex. até ~30 min).
- Só sobrescrever se o nome atual ainda bate com o título inicial determinístico derivado da primeira mensagem.
- Nunca sobrescrever título manual/específico, thread criada por humano ou thread antiga reativada por reset/follow-up.

Em thread existente, usar o contexto da thread/reply como assunto principal e responder sem tocar no título. Se a conversa mudar completamente de objetivo, abrir/usar outra thread em vez de renomear a atual.

#### Pitfall crítico: função segura pode estar sobrescrita por duplicata posterior

Incidente validado em 2026-06-14: `_discord_thread_safe_to_autorename(...)` existia e estava correta, mas uma segunda definição posterior de `_rename_discord_thread_for_session_title(...)` em `gateway/run.py` sobrescrevia a versão segura. Sintoma: log de rename indevido após pausa/session reset e reason efetivo `Hermes auto-generated session title` em vez de `MGS AI-generated session title`.

Ao diagnosticar rename indevido, não basta ler a primeira ocorrência da função. Sempre contar definições e reasons antes de patch/restart:

```bash
RUN=/root/.hermes/hermes-agent/gateway/run.py
python3 -m py_compile "$RUN"
grep -c 'async def _rename_discord_thread_for_session_title' "$RUN"
grep -c 'def _schedule_discord_thread_title_rename' "$RUN"
grep -c 'async def _discord_thread_safe_to_autorename' "$RUN"
grep -c 'def _is_discord_thread_lane' "$RUN"
grep -c 'def _sanitize_discord_thread_title' "$RUN"
grep -c 'MGS AI-generated session title' "$RUN"
grep -c 'Hermes auto-generated session title' "$RUN" || true
```

Estado correto: todos os helpers/rename/schedule/guard = `1`, reason MGS = `1`, reason Hermes legado = `0`. Se houver duplicatas, fazer backup, cortar apenas o bloco duplicado contíguo e revalidar antes de reiniciar. Detalhe completo: `references/discord-thread-title-dedupe-and-restart-loop-2026-06-14.md`.

Pitfall validado 1: Rodolfo respondeu `Ok` em reply a um status de execução da Fase 4, mas Zeus tratou como mensagem solta e renomeou a thread para um assunto errado/em espanhol. Correção: em reply, resolver primeiro o contexto citado; se a thread já existe e o objetivo continua, não mexer no título. Referência: `references/discord-open-thread-rename-pitfall-2026-06-07.md`.

Pitfall validado 2: remover totalmente o callback Discord de auto-title evita renomear thread antiga, mas também quebra o comportamento desejado para thread nova. Correção: restaurar callback apenas com guardrails de thread nova. Ver `references/discord-gpt-style-thread-title-rename.md`, `references/discord-new-thread-title-guardrails-2026-06-07.md` e `references/discord-new-thread-ai-title-once-guard.md`.

