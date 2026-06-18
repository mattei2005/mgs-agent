# Hermes update — local patch surface restore/fail-closed (2026-06-17)

## Contexto
Após update Hermes controlado, o runtime MGS ficou online, mas parte do diff local pré-update não tinha sido restaurada. O script de validação comparava principalmente nomes de arquivos críticos e invariants antigos; isso deixou passar a perda de funções locais recentes.

Sintoma observado:
- Thread title author suffix (`Título - PrimeiroNome`) parou de funcionar.
- Auditoria do `pre-local-diff.patch` mostrou outros markers/funções ausentes antes da restauração.

## Causa raiz
O fluxo salvava `pre-local-diff.patch` e `pre-local-diff-cached.patch`, mas não garantia que ambos voltassem após `hermes update`. A comparação pós-update checava que os mesmos arquivos críticos ainda apareciam em diff, mas não checava se as funções/strings adicionadas pelo diff pré-update continuavam presentes.

Erro de classe: **file-level compare não é suficiente para proteger patches locais**. Precisa de compare por conteúdo/markers.

## Correção aplicada
1. Restaurar o diff local pré-update no checkout vivo.
2. Promover o patch do sufixo para o guard canônico:
   - `discord-thread-title-author-suffix.patch`
3. Fortalecer `ensure-hermes-mgs-patches.sh` com invariants novos:
   - `AUTO_ATTACH_LOCAL_FILES_ENV`
   - `_auto_attach_local_files_enabled`
   - `codex response remained incomplete`
   - `_DISCORD_BOT_LOOP_NOISE_MARKERS`
   - `_is_discord_bot_loop_noise`
   - `_append_thread_author_suffix`
   - `_append_discord_thread_author_suffix`
   - `async def delete_message`
4. Fortalecer `run-hermes-update-controlled.sh`:
   - `restore_saved_local_diffs()` reaplica `pre-local-diff-cached.patch` e `pre-local-diff.patch` após update.
   - Falha fechado se qualquer diff salvo não restaurar.
   - `compare_python_patch_surface()` valida markers/funções adicionados, não só nomes de arquivos.
   - `check_local_diff_against_upstream()` testa se o diff local vivo aplicaria em `origin/main` antes de mutar o checkout. Se não aplicar, update real para antes de tocar no runtime.
5. Limpar `patches/hermes/`:
   - raiz contém só patches ativos referenciados pelo guard/update;
   - snapshots/experimentos/obsoletos vão para `archive/<data>/` com manifest;
   - adicionar `ACTIVE-PATCHES.md`.

## Validação usada
- `ensure-hermes-mgs-patches.sh` OK.
- `py_compile` em `gateway/platforms/base.py`, `gateway/run.py`, `plugins/platforms/discord/adapter.py`.
- Testes alvo:
  - `tests/gateway/test_discord_bot_filter.py`
  - `tests/gateway/test_discord_free_response.py`
  - `tests/gateway/test_restart_resume_pending.py`
  - `tests/gateway/test_platform_base.py`
  - `tests/gateway/test_telegram_noise_filter.py`
- Comparação de todos os markers/funções do `pre-local-diff*.patch` contra runtime vivo: `missing=0`.
- Restart seguro dos gateways via `/root/mgs-agent/scripts/mgs-gateway-restart-safe.sh`, Zeus por último.

## Regra operacional nova
Depois de qualquer update Hermes MGS, não basta dizer que serviços estão online. Para afirmar que “recuperou tudo”, validar:

1. Serviços ativos.
2. Guard canônico OK.
3. `py_compile` OK.
4. Testes alvo OK.
5. **Todos os markers/funções adicionados no diff local pré-update existem no runtime vivo.**
6. Se `pre-local-diff-upstream-check.txt` mostrar drift, update futuro deve ser bloqueado antes de mutação e exigir port manual.

## Comunicação com Rodolfo
Rodolfo não quer ouvir só “está online”. Quando ele disser “confere tudo”, responder explicitamente se os patches/funções locais foram recuperados. Use termos como:

- “comparei 35/35 markers do diff pré-update; missing=0”
- “runtime íntegro; pendência é só higiene de patch artifact”
- “update futuro agora falha fechado antes de mexer se diff local não aplicar em origin/main”

Evitar resposta genérica de status de serviço quando a preocupação é perda de configuração/patch local.