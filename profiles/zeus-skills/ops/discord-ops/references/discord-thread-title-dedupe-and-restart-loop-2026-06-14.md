# Discord thread title dedupe + restart lifecycle anti-loop — 2026-06-14

## Contexto
Rodolfo reportou que threads Discord já abertas eram renomeadas de novo após pausa/retorno. O incidente real mostrou uma thread renomeada no início, depois idle/session reset (`history=0`), e um novo auto-title mudando o nome da thread antiga.

## Diagnóstico validado
O bug não era só janela de idade ou cache: havia duplicação de funções em `gateway/run.py`.

Estado encontrado:
- `_discord_thread_safe_to_autorename(...)` existia e era correta.
- A primeira `_rename_discord_thread_for_session_title(...)` chamava a trava e usava reason `MGS AI-generated session title`.
- Depois havia um bloco legado duplicado que sobrescrevia a função segura em Python:
  - segunda `_is_discord_thread_lane(...)` idêntica;
  - segunda `_sanitize_discord_thread_title(...)` idêntica;
  - segunda `_rename_discord_thread_for_session_title(...)` insegura, sem chamada à trava, com reason `Hermes auto-generated session title`;
  - segunda `_schedule_discord_thread_title_rename(...)`.

Sinal nos logs do incidente:
- `Discord thread renamed from auto-generated title ... previous='Verificação de atualizações Hermes'`
- reason efetivo no código era `Hermes auto-generated session title`, provando que a função insegura sobrescrevia a segura.

## Correção segura
Fazer corte contíguo do bloco duplicado começando na segunda `_is_discord_thread_lane` até o fim do segundo `_schedule_discord_thread_title_rename`, preservando as versões anteriores boas.

Gate obrigatório antes de restart:
```bash
python3 -m py_compile /root/.hermes/hermes-agent/gateway/run.py
RUN=/root/.hermes/hermes-agent/gateway/run.py
printf 'rename_defs='; grep -c 'async def _rename_discord_thread_for_session_title' "$RUN"
printf 'schedule_defs='; grep -c 'def _schedule_discord_thread_title_rename' "$RUN"
printf 'safe_guard_defs='; grep -c 'async def _discord_thread_safe_to_autorename' "$RUN"
printf 'lane_defs='; grep -c 'def _is_discord_thread_lane' "$RUN"
printf 'sanitize_defs='; grep -c 'def _sanitize_discord_thread_title' "$RUN"
printf 'mgs_reason='; grep -c 'MGS AI-generated session title' "$RUN"
printf 'hermes_reason='; grep -c 'Hermes auto-generated session title' "$RUN" || true
```

Esperado:
```text
rename_defs=1
schedule_defs=1
safe_guard_defs=1
lane_defs=1
sanitize_defs=1
mgs_reason=1
hermes_reason=0
```

Se qualquer contador divergir, reverter do backup antes de restart.

## Patch reaplicável
Preservar em `/root/mgs-agent/patches/hermes/` e no guard:
- `discord-thread-title-deduplicate-safe-autorename.patch`
- `discord-bot-gateway-lifecycle-loop-guard.patch`
- `/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh`

Para patch aplicado corretamente no runtime atual:
```bash
cd /root/.hermes/hermes-agent
git apply --reverse --check /root/mgs-agent/patches/hermes/discord-thread-title-deduplicate-safe-autorename.patch
git apply --reverse --check /root/mgs-agent/patches/hermes/discord-bot-gateway-lifecycle-loop-guard.patch
```

## Testes reais esperados
1. Thread nova auto-criada: renomeia uma única vez via reason seguro.
2. Follow-up imediato na mesma thread: não renomeia de novo.
3. Caso do incidente: thread já renomeada + pausa/session reset (`history=0`) + nova mensagem: não renomeia; log deve mostrar `reason=not_new` ou `reason=non_initial_title`.

Exemplo validado do teste C:
```text
conversation turn: session=<nova> platform=discord history=0
Discord auto-title rename skipped: thread=<id> session=<nova> reason=not_new age_seconds=132485.7
```

## Anti-loop de restart/status entre bots
Durante restart, mensagens como `⏳ Gateway is restarting and is not accepting new work right now.` podem acordar outro bot em thread compartilhada e gerar ping-pong.

Correção aplicada em duas camadas:
1. `gateway/run.py`: suprimir notificações de shutdown/restart em sessões Discord originadas por bots MGS.
2. `plugins/platforms/discord/adapter.py`: se mensagem de bot começa com `⚠️ Gateway restarting`, `⚠️ Gateway shutting down` ou `⏳ Gateway is restarting`, ignorar antes de `DISCORD_ALLOW_BOTS`.

Log esperado:
```text
Ignoring gateway lifecycle notice from bot author=<bot_id> channel=<thread_id>
Shutdown notification suppressed for bot-originated Discord session: chat=<id> thread=<id> user=<bot_id>
```

## Restart de agentes
Como `run.py` e `adapter.py` são runtime compartilhado, reiniciar todos os gateways Discord ativos após patch:
- Zeus
- Atena
- Ares
- agente legado

Não basta reiniciar só o agente onde o bug apareceu; processos não reiniciados continuam com código antigo em memória.

## Higiene final
- Não versionar o fork Hermes diretamente; manter patches reaplicáveis no repo MGS.
- Remover `.bak.*` do checkout Hermes após validar.
- Não misturar state/runtime de outros fluxos (`data/*.json`, arquivos Ares) com commit de patches Hermes.
- Testes úteis no checkout Hermes podem ser preservados em manutenção separada; não misturar com fechamento operacional urgente se patches + ensure já cobrem os invariantes.