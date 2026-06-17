# Discord thread titles — sufixo do autor sem alterar padrão existente (2026-06-17)

## Contexto
Rodolfo aprovou o padrão atual de renomeação semântica de threads e pediu uma mudança extremamente restrita: preservar 100% da lógica atual e apenas acrescentar ` - PrimeiroNome` no final do título, para identificar quem abriu a thread.

Exemplos esperados:
- `Padrão Renomeação Threads` → `Padrão Renomeação Threads - Rodolfo`
- `Erro Bot Discord` → `Erro Bot Discord - Raquel`
- `Campanha Facebook Ads` → `Campanha Facebook Ads - Geizian`

## Regra operacional
Ao alterar o padrão de títulos Discord MGS:
1. Não reescrever heurística, prompt, idioma, tamanho, guardrails ou regra de thread antiga.
2. Tratar o nome da pessoa como pós-processamento final: título_base_existente + ` - PrimeiroNome`.
3. Aplicar no ponto comum do runtime Discord/Hermes para Zeus, Atena, Ares, Hera e futuros agentes que compartilhem o mesmo runtime.
4. Primeiro nome deve vir de `display_name`/`source.user_name`, sem mention/ID e sem sobrenome.
5. Respeitar limite Discord de 100 caracteres truncando só a base quando necessário, nunca removendo o sufixo.

## Pontos de patch usados
- Provisório criado antes da resposta: `/root/.hermes/hermes-agent/plugins/platforms/discord/adapter.py`
  - `_auto_thread_name_from_message(...)` permanece intacta.
  - `_auto_create_thread(...)` calcula `base_thread_name` pela função antiga e só depois aplica `_append_thread_author_suffix(...)`.
- Rename IA pós-primeira resposta: `/root/.hermes/hermes-agent/gateway/run.py`
  - `_sanitize_discord_thread_title(...)` permanece como base.
  - `_rename_discord_thread_for_session_title(...)` usa `_append_discord_thread_author_suffix(title, source)` antes de `channel.edit(...)`.

## Validação obrigatória
Antes de restart:
- `python3 -m py_compile plugins/platforms/discord/adapter.py gateway/run.py`
- Contagens esperadas em `gateway/run.py`:
  - `async def _rename_discord_thread_for_session_title` = 1
  - `def _schedule_discord_thread_title_rename` = 1
  - `async def _discord_thread_safe_to_autorename` = 1
  - `def _is_discord_thread_lane` = 1
  - `def _sanitize_discord_thread_title` = 1
  - `MGS AI-generated session title` = 1
  - `Hermes auto-generated session title` = 0
- Smoke test do sufixo:
  - `Rodolfo Mattei` → `Rodolfo`
  - `Raquel Oliveira` → `Raquel`
  - output final `<= 100` chars

## Pitfall
Não interpretar esse tipo de pedido como autorização para “melhorar” ou recalibrar título. Neste caso, a dificuldade anterior foi deixar a renomeação boa; a mudança correta é cirúrgica e aditiva. Qualquer alteração no classificador/heurística pode regredir o padrão aprovado.

## Restart
Restart de Zeus/Atena/Ares/Hera deve seguir o contrato seguro MGS: finalizer externo via `/root/mgs-agent/scripts/mgs-gateway-restart-safe.sh`, Zeus por último, sem polling foreground na thread ativa.