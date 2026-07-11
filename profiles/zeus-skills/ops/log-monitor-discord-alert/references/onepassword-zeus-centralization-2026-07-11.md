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
- jobs redundantes pausados: Ares `d1a064017e27` e Hera `d2a7853ae86f`.

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

## Limites

Não migrar para bot Zeus credenciais operacionais necessárias a Meta, DTR, Smart Bidding, WordPress, GitHub ou SSH. Redução de acesso ao 1Password não significa persistir essas credenciais em texto local.
