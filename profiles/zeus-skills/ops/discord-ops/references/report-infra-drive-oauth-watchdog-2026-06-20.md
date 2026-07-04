# REPORT-INFRA — Drive OAuth watchdog em profile de agente

Quando um agente reportar criação/modificação de watchdog OAuth Google Drive com Hermes cron script-only:

## Classe do caso

- Scripts versionados no repo (`/root/mgs-agent/scripts/*.py`).
- Wrapper local do profile (`/root/.hermes/profiles/<agent>/scripts/*.sh`) usado pelo cron Hermes.
- Cron Hermes `no_agent=true`, recorrente, com `deliver` para canal/thread operacional.
- Possível mudança em `SOUL.md`/skill do profile para anti-loop ou regra operacional.
- State file runtime (`data/<agent>/...state.json`) gerado pelo watchdog: normalmente não versionar; registrar só se virar artefato runtime relevante.

## Validação mínima

1. Rodar sync seletivo antes de comparar SHA quando o report inclui SOUL/skill:
   - `/root/mgs-agent/scripts/sync-souls.sh`
2. Validar scripts sem expor segredo:
   - `python3 -m py_compile /root/mgs-agent/scripts/<watchdog>.py /root/mgs-agent/scripts/<oauth-init>.py`
   - `bash -n /root/.hermes/profiles/<agent>/scripts/<wrapper>.sh`
   - `python3 -m json.tool /root/.hermes/profiles/<agent>/cron/jobs.json >/dev/null`
3. Ler o cron sanitizado em `jobs.json` e confirmar:
   - `id`, `name`, `schedule`, `script`, `enabled`, `state`, `next_run_at`, `no_agent`, `deliver`, `repeat`.
4. Conferir runtime/versioned SHA match para SOUL e skill reportada.
5. Fazer secret-scan nos arquivos versionados e no wrapper para padrões de token/API key; nunca imprimir credenciais.

## Inventário

Atualizar `/root/mgs-agent/data/infra-inventory.json` de forma cirúrgica:

- `scripts[]` para os scripts versionados no repo, com `agent`, `purpose`, `validation`, `sha256`, `size_bytes`, `modified_at`.
- `runtime_artifacts[]` para wrapper local do profile, com `type=profile_script`, `git_tracked=false`, SHA e validação `bash -n`.
- `crons[]` para o Hermes cron, com `type=hermes_cron`, `profile`, `id`, `schedule`, `script`, `next_run_at`, `enabled`, `state`, `no_agent`, `deliver`, `repeat`.
- `data_files[]` para cópia versionada de `profiles/<agent>-soul.md` quando mudou, incluindo `runtime_path` e `runtime_versioned_sha_match`.
- `profile_skill_references[]` para skill do profile, incluindo runtime path, versioned path e SHA match.

Registrar evento compacto em `logs/events-audit.jsonl` com validações e `inventory_updated=true`.

## Commit/staging

Commitar somente:

- `data/infra-inventory.json`
- scripts versionados reportados
- cópia versionada de SOUL/skill efetivamente alterada

Não commitar:

- wrapper fora do repo
- `cron/jobs.json` do profile
- state file do watchdog, salvo pedido explícito
- audit outputs, logs, artefatos `/tmp` ou diffs de outro fluxo

## Pitfalls

- Se `sync-souls.sh` trouxer muitas mudanças de outros agentes, não stagear tudo. O commit deve continuar cirúrgico ao REPORT-INFRA atual.
- `deliver=discord:#zeus` em cron Hermes é metadata runtime; registrar no inventário, não presumir que exista arquivo versionado correspondente.
- Um watchdog que detecta `invalid_grant` deve reportar o erro sanitizado (`invalid_grant`, HTTP, impacto) sem refresh token/client secret/access token.
- Não tratar `py_compile ok` informado pelo agente como suficiente; validar localmente antes do ACK.

## ACK

Só responder depois de validação + inventário + commit/auto-commit verificado:

- `✅ Registrado. Inventário atualizado (commit XXXX).`
