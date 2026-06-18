# Hermes update — guard de superfície local MGS (2026-06-17)

## Contexto
Após update controlado do Hermes, Rodolfo detectou que o sufixo ` - PrimeiroNome` nos títulos de threads Discord parou de funcionar. Auditoria mostrou que o update preservou alguns patches canônicos antigos, mas perdeu parte do diff local pré-update que não estava protegido pelo guard.

## Causa raiz
O fluxo antigo fazia backup e capturava `pre-local-diff.patch` / `pre-local-diff-cached.patch`, mas a validação pós-update era fraca demais:

- comparava principalmente **nomes de arquivos Python** pré vs pós;
- rodava invariantes canônicos antigos;
- não verificava se os **markers/funções/strings introduzidos pelo diff local pré-update** continuavam presentes.

Resultado: os mesmos arquivos ainda apareciam modificados, então o update parecia seguro, mas funções locais tinham sumido.

## Sintoma observado
Funções/markers que estavam no diff local pré-update e ficaram ausentes no runtime vivo:

- `_append_thread_author_suffix`
- `_append_discord_thread_author_suffix`
- `AUTO_ATTACH_LOCAL_FILES_ENV`
- `_auto_attach_local_files_enabled`
- `_DISCORD_BOT_LOOP_NOISE_MARKERS`
- `_is_discord_bot_loop_noise`
- filtro para `codex response remained incomplete`
- `async def delete_message` no adapter Discord
- testes desses comportamentos

## Correção aplicada
1. Restaurar o patch local pré-update salvo:
   - `/root/mgs-agent/patches/hermes/mgs-local-preupdate-20260617-093617-execute.patch`
   - manter staged/cached diff separado quando existir.
2. Adicionar `discord-thread-title-author-suffix.patch` ao guard canônico.
3. Fortalecer `ensure-hermes-mgs-patches.sh` com invariantes de conteúdo:
   - auto-attach safety gate;
   - filtro anti-loop multiagente;
   - filtro de ruído Codex;
   - sufixo de autor em título inicial e rename IA;
   - `delete_message` para cleanup progress;
   - `py_compile` também em `gateway/platforms/base.py`.
4. Fortalecer `run-hermes-update-controlled.sh`:
   - depois do update, chamar `restore_saved_local_diffs()` antes de `post_validate`;
   - se `pre-local-diff.patch` ou `pre-local-diff-cached.patch` não restaurar limpo, falhar fechado antes de validação/restart;
   - `compare_python_patch_surface()` deve extrair markers de funções/classes/strings adicionadas nos diffs pré-update e confirmar presença no checkout vivo.

## Regra operacional permanente
Para update Hermes MGS, **não basta comparar arquivos**. É obrigatório comparar a superfície de conteúdo local:

- nomes de arquivos modificados;
- diffs salvos pré-update;
- markers/funções/classes/strings adicionados por patches locais;
- invariantes canônicos do runtime;
- `py_compile` dos arquivos afetados;
- testes alvo quando existirem.

Se qualquer marker local pré-update sumir e não houver evidência clara de que foi incorporado upstream com comportamento equivalente, o update deve falhar fechado e não reiniciar gateway.

## Validação recomendada

```bash
BASE=/root/mgs-agent REPO=/root/.hermes/hermes-agent \
  LOG=/root/mgs-agent/logs/ensure-hermes-mgs-patches.log \
  /root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh

cd /root/.hermes/hermes-agent
PY=venv/bin/python; [ -x "$PY" ] || PY=python3
$PY -m py_compile gateway/platforms/base.py gateway/run.py plugins/platforms/discord/adapter.py
$PY -m pytest -q \
  tests/gateway/test_discord_bot_filter.py \
  tests/gateway/test_discord_free_response.py \
  tests/gateway/test_restart_resume_pending.py \
  tests/gateway/test_platform_base.py -q
```

## Pitfall
Não usar `ALLOW_PATCH_DRIFT=1` como desculpa para aceitar perda silenciosa de comportamento. Drift pode ser aceitável apenas quando invariantes equivalentes estão presentes. Caso contrário, é port manual obrigatório.