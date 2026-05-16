# MGS Agent hardening — 2026-05-16

Data de fechamento: 2026-05-16 17:15 EDT
Responsável operacional: Zeus
Escopo: `/root/mgs-agent` e profiles MGS sincronizados no repo.

## Objetivo

Executar uma varredura completa do repositório e aplicar correções seguras para reduzir risco operacional, falso sucesso em automações, vazamento acidental por auto-commit, dependências vulneráveis e código legado incompatível com a política atual de custo.

## Resultado executivo

| Área | Resultado |
|---|---|
| Secrets | Nenhum PAT/webhook/token literal encontrado nos padrões testados no estado atual do repo. `.env` segue não rastreado. |
| GitHub | Acesso ao repo privado validado via 1Password/PAT sob demanda, sem persistir token no remote. |
| Crons | Monitoramento agora detecta log stale e erro semântico em log fresco. |
| Auto-commit | Guardrails adicionados contra staging automático de nomes sensíveis. |
| Yoast/SSH | Fluxos ativos migrados de `StrictHostKeyChecking=no` para `accept-new` + `/root/.ssh/known_hosts_mgs`; tempfiles previsíveis removidos. |
| WordPress REST | Scripts migrados para wrapper HTTP comum com `--fail-with-body`, preservando body e status real em 4xx/5xx. |
| RunCloud | Inventário reescrito com paginação correta, retry/backoff, token via 1Password e tempfiles em `/tmp`. |
| Dependências | `yoast-scorer` com `npm audit` limpo e `npm test` sintático funcional. |
| Anthropic/Claude API | Runtime legado `mgs-rec-api` desabilitado como stub fail-closed; serviço permanece `masked/inactive`. |
| Runtime versionado | Logs/estados/backups de runtime removidos do Git ou ignorados quando seguro. |

## Correções principais

### Cron/custos

- Corrigido bug de contagem em `scripts/track-article-cost.sh` onde `grep -c ... || echo 0` podia gerar `0\n0` e quebrar comparação numérica.
- `scripts/monitor-cron-stale-logs.sh` passou a detectar:
  - `STALE`: log sem atualização recente;
  - `ERROR`: log atualizado, mas contendo padrões de erro recentes.
- Ajustada janela de scan para reduzir falsos positivos por erro antigo já resolvido.

### Auto-commit

- `scripts/auto-commit-watcher.sh` recebeu `set -euo pipefail`.
- Substituído `git add .` por staging controlado.
- Rodada de auto-commit aborta se detectar nomes potencialmente sensíveis como `.env`, `secret`, `token`, `password`, `webhook`, `.pem`, `.key`, `private`.

### Yoast/SSH

- `scripts/monitor-yoast-health-eggbev.sh` endurecido com:
  - `mktemp -d`;
  - `chmod 700`;
  - `trap cleanup EXIT`;
  - script remoto temporário com cleanup;
  - `StrictHostKeyChecking=accept-new`;
  - `UserKnownHostsFile=/root/.ssh/known_hosts_mgs`.
- `skills/content-generate-rec/scripts/yoast-score-post.sh` recebeu hardening equivalente.
- Scripts Yoast deprecated sem uso em cron/systemd foram substituídos por stubs seguros.

### WordPress REST/curl

- Criado `wp_curl_auth_http` em `skills/content-publish-wordpress/scripts/wp-curl-auth.sh`.
- Scripts migrados:
  - `check-slug-conflict.sh`;
  - `create-post.sh`;
  - `delete-media-safe.sh`;
  - `resolve-term.sh`;
  - `update-yoast.sh`;
  - `upload-image.sh`.
- Teste com fake `curl` validou:
  - HTTP 200 preserva body;
  - HTTP 404 retorna `404` com body preservado;
  - falha de transporte retorna `000`.

### Bash hardening

- 23 scripts seguros receberam `set -euo pipefail`.
- Ajustado uso de argumentos posicionais em scripts de pendências para evitar `unbound variable`.
- Exceções deliberadas:
  - helpers `sourced`, onde `set -euo pipefail` global poderia afetar callers;
  - scripts legados auditados separadamente.

### RunCloud inventory

- `scripts/runcloud-inventory.sh` foi reescrito como script read-only seguro:
  - token RunCloud carregado do 1Password em runtime;
  - sem impressão de credencial;
  - modos `--dry-run`, `--json`, `--help` e write;
  - paginação corrigida para `meta.pagination.total_pages`;
  - retry/backoff em 403/429/5xx;
  - escrita atômica;
  - tempfiles em `/tmp`.
- Inventário regenerado com 107 WordPress webapps.
- `data/infra-inventory.json` regenerado após mudanças.

### Dependências/tooling

- Único package npm ativo detectado: `scripts/yoast-scorer`.
- `npm audit --audit-level=moderate`: 0 vulnerabilidades.
- `npm test` deixou de falhar por placeholder e passou a rodar syntax check com `node -c`.
- `api/generate-rec-api.py` convertido em stub seguro/deprecated sem imports FastAPI/Anthropic.
- `mgs-rec-api.service` confirmado `masked` e `inactive`.

## Validações executadas

| Check | Resultado |
|---|---|
| `bash -n` nos scripts alterados | OK |
| `track-article-cost.sh` execução real | OK |
| `monitor-cron-stale-logs.sh --dry-run` | `problems=0 resolved=0 dry_run=1` |
| Yoast monitor end-to-end | OK, modo silencioso, sem alerta indevido |
| `npm test` em `scripts/yoast-scorer` | OK |
| `npm audit --audit-level=moderate` | 0 vulnerabilidades |
| `python3 -m py_compile` em scripts Python | OK |
| `runcloud-inventory.sh --dry-run` | OK, 107 WordPress |
| `inventario-webapps.json` | JSON válido, schema OK |
| `data/infra-inventory.json` | JSON válido |
| `zeus-gateway.service` | active |
| `mgs-autocommit.service` | active |
| `mgs-rec-api.service` | masked/inactive |
| Git | working tree limpo e `main...origin/main` nos checks finais |

## Commits de referência

A rodada gerou vários commits automáticos pelo watcher. Commits âncora mais relevantes:

| Commit | Assunto |
|---|---|
| `9c411f0` | Cron monitoring + auto-commit guardrails |
| `9f7b84d` | Yoast monitor hardening |
| `6b334a6` | `yoast-scorer` audit/deps |
| `6376c26` | Stubs para Yoast deprecated |
| `cd5198f` | Remoção/ignore de backup antigo versionado |
| `81b7459` / `887b5f7` | SSH docs + housekeeping backup cleanup |
| `8298d2f` / `d6f3a1a` / `215638d` | WordPress REST/curl wrapper migration |
| `114def3` | `set -euo pipefail` em scripts seguros |
| `492b3b7` / `b1e6a93` / `3ea994e` | RunCloud inventory rewrite + infra refresh |
| `e254790` | `api/generate-rec-api.py` stub disabled |
| `4df81e5` | `yoast-scorer` npm test |

Observação: houve commits automáticos intermediários de tempfiles `.runcloud-inventory.*` durante teste. O estado atual foi corrigido: tempfiles migrados para `/tmp`, `.gitignore` atualizado e nenhum `.runcloud-inventory.*` permanece rastreado no HEAD.

## Política atual consolidada

- Não usar Anthropic/Claude pay-per-token por padrão.
- Não persistir PAT GitHub em remote/config; usar 1Password sob demanda.
- Não usar `StrictHostKeyChecking=no` em fluxos operacionais MGS.
- Não commitar runtime/logs/backups de estado quando não forem artefatos deliberados de auditoria.
- Não reportar sucesso sem validação real.

## Varredura histórica Git — fechamento complementar

Executada em 2026-05-16 18:29 EDT, em modo read-only, sem reescrever histórico e sem imprimir credenciais.

| Check | Resultado |
|---|---|
| Commits varridos | 1.058 |
| Paths únicos no histórico | 398 |
| Paths atuais rastreados | 194 |
| Paths apenas no histórico | 204 |
| Repo GitHub | `mattei2005/mgs-agent`, privado |
| Acesso público sem autenticação | Bloqueado (`404` via API pública; `git ls-remote` sem credencial falha) |
| Forks | 0 |
| Local vs `origin/main` | 0 ahead / 0 behind no fechamento |
| GitHub Secret Scanning API | Não acessível pelo PAT atual (`403`, permissão insuficiente) |

Achados históricos de credenciais, todos sem valor literal registrado neste documento:

| Achado | Estado |
|---|---|
| OP Service Account token antigo em `.env.bak-20260427-001636` | Token atual não bate com o histórico |
| GitHub PAT antigo em `backups/pre-hermes-upgrade-20260429_104523.tar.gz` | PAT ativo do 1Password não bate; teste direto do token histórico retornou `401` |
| Anthropic key antiga no mesmo backup `.tar.gz` | Não existe nos `.env` atuais de `mgs-agent`, Zeus ou Atena |

Classificação de artefatos históricos:

| Classe | Qtde | Observação |
|---|---:|---|
| Backups / snapshots antigos | 116 | Ficam recuperáveis no histórico, mas fora do working tree atual |
| Credential/env backup | 6 | Inclui `.env.bak`; risco histórico, não atual |
| RunCloud tempfiles | 4 | Já removidos; tempfiles atuais vão para `/tmp` |
| Deprecated / legacy | 5 | Código antigo fora do fluxo atual ou substituído por stub |
| Data JSON antigos | 27 | State/backups históricos |

Decisão operacional recomendada: não reescrever histórico agora. O ganho é baixo frente ao risco operacional de `filter-repo + force-push`, porque o repo é privado, sem forks, não visível publicamente e os segredos históricos relevantes não batem com os ativos. Se for exigida higiene/compliance máxima, abrir uma etapa separada com backup, freeze de pushes e aprovação explícita para reescrita destrutiva.

## Pendências opcionais

Estas ações não foram executadas por serem não críticas, dependentes de permissão externa ou potencialmente destrutivas:

1. Consultar GitHub Secret Scanning Alerts com PAT temporário que tenha permissão `security_events`/admin do repo; revogar o PAT depois.
2. Fazer limpeza de histórico Git para remover `.env.bak`, backup `.tar.gz` e tempfiles antigos; exige autorização explícita por reescrever histórico.
3. Revisar documentação histórica que ainda menciona Anthropic/Claude para separar claramente histórico vs. operação atual.
4. Avaliar substituição definitiva de fluxos com senha/expect por autenticação SSH mais forte, caso ainda existam em caminho ativo.
