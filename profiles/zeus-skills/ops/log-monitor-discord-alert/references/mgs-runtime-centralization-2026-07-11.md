# Centralização Zeus e redução 1Password — 2026-07-11

## Honcho

Runtime:
- `/root/mgs-agent/scripts/monitor-honcho-health.sh`
- `/root/mgs-agent/scripts/mgs-memory-copilot`

Regra atual:
1. o monitor faz uma única leitura de `Honcho API - MGS` por ciclo;
2. exporta `HONCHO_API_KEY` somente no processo;
3. os quatro copilots reutilizam a variável e não consultam o 1Password;
4. se a leitura inicial falhar, o ciclo aborta sem quatro retries multiplicativos;
5. alertas usam `/root/mgs-agent/scripts/discord-bot-post.py`.

Projeção conservadora: 48 para 12 requests/dia.

## Google Drive

Runtime: `/root/mgs-agent/scripts/monitor-drive-auth-unified.py`
Cron root: `19,49 * * * *`
State: `/root/mgs-agent/data/drive-auth-unified-state.json`

Regra atual:
- OAuth usuário local é testado em cada ciclo;
- Service Account do 1Password é testado no máximo uma vez a cada 24 horas enquanto OAuth está saudável;
- falha do OAuth força teste imediato do fallback;
- o estado nunca persiste token ou chave;
- alertas e recovery usam o bot Zeus;
- jobs redundantes pausados: Ares `d1a064017e27` e agente legado `d2a7853ae86f`.

Validação real de 2026-07-11: OAuth `token_ok`; fallback identificado como `my_drive_sa_upload_blocked`; ciclos subsequentes passaram com `sa_checked=0` mesmo sem `op` disponível no PATH.

Projeção do componente Service Account: 144 para aproximadamente 3 requests/dia.

## Transporte Discord sem 1Password

Helper canônico: `/root/mgs-agent/scripts/discord-bot-post.py`.

Scripts migrados:
- `monitor-auto-push.sh`
- `monitor-tool-loops.sh`
- `monitor-webshare-status.sh`
- `hermes-mgs-patch-watchdog.sh`
- `ares-report-infra.sh`
- `send-report-infra-embed.sh`
- Git hook `.git/hooks/post-commit`
- alertas Honcho

O helper:
- lê `DISCORD_BOT_TOKEN` do `.env` local do perfil Zeus;
- aceita um payload JSON via stdin;
- publica pela API Discord;
- exige HTTP 200/201;
- valida `channel_id` por readback em chamadas reais;
- nunca imprime o token.

Teste obrigatório após mudança: mock HTTP deve confirmar header `Authorization: Bot`, payload esperado, ausência de segredo no stdout/stderr e exit code zero.

## Autenticação SSH dedicada do Yoast

Runtime: `/root/mgs-agent/scripts/monitor-yoast-health-eggbev.sh`.

Estado aplicado em 2026-07-11:
- chave dedicada: `/root/.ssh/mgs_yoast_monitor_ed25519`, modo `600`;
- chave pública instalada para `zeus` no S03 `46.4.95.117` e no S01 `162.55.28.178`;
- S01 continua acessado por ProxyCommand através do S03;
- `BatchMode=yes`, `IdentitiesOnly=yes` e `StrictHostKeyChecking=yes` são obrigatórios;
- o monitor não carrega `/root/mgs-agent/.env`, não chama `op`, não usa senha e não usa `expect`;
- as credenciais antigas permanecem no 1Password somente como rollback administrativo, sem consumo do cron.

Validação obrigatória:
1. acesso S03 em BatchMode com a chave;
2. acesso S01 via S03 em BatchMode com a mesma chave;
3. `bash -n` e busca estática com zero `op item get`/`expect`;
4. execução real `--dry-run` com `op` fora do PATH;
5. confirmação de SCP, query remota, parsing dos scores e nenhuma postagem Discord no dry-run.

Validação de 2026-07-11: 280 posts, SEO G206/A39/R0/N35 e readability G205/A36/R39/N0. Projeção: aproximadamente 6 para 0 requests/dia.

## GitHub com deploy key SSH dedicada

Estado aplicado em 2026-07-11:
- repositório: `mattei2005/mgs-agent`;
- chave dedicada: `/root/.ssh/mgs_github_deploy_ed25519`, modo `600`;
- deploy key GitHub com escrita, ID `156991446`, `read_only=false` e `verified=true`;
- remote: `git@github.com:mattei2005/mgs-agent.git`;
- `core.sshCommand` e o hook `.git/hooks/post-commit` fixam a chave, `IdentitiesOnly=yes`, `BatchMode=yes`, `StrictHostKeyChecking=yes` e `/root/.ssh/known_hosts_github_mgs`;
- host keys vêm do endpoint oficial `https://api.github.com/meta` e ficam no arquivo dedicado;
- o hook não carrega `/root/mgs-agent/.env`, não chama `op` e não lê mais `GitHub PAT - mgs-agent`.

Validação obrigatória:
1. `git ls-remote` via SSH com a chave dedicada;
2. `git fetch --prune origin`;
3. `git push origin HEAD:main`;
4. busca estática com zero `op item get`/`GitHub PAT - mgs-agent` no hook;
5. commit real e readback de igualdade entre `HEAD` e `origin/main`.

Rollback: restaurar o hook e a URL HTTPS do backup mais recente em `/root/mgs-agent/backups/github-ssh-cutover-*`; somente depois de confirmar o PAT funcional, remover a deploy key pelo ID registrado.

## Limites

Não migrar para bot Zeus credenciais operacionais necessárias a Meta, DTR, Smart Bidding ou WordPress. Para GitHub/SSH, usar chave dedicada somente após confirmação crítica, instalação, teste BatchMode e rollback documentado.
