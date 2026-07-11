# Yoast, GPT-5.6 OAuth e housekeeping — correções 2026-07-11

## Yoast eggbev

Runtime: `/root/mgs-agent/scripts/monitor-yoast-health-eggbev.sh`
Cron: `23 10 * * *`
Canal: `1498193722871910550`

Falha observada: o último relatório real havia chegado em 2026-06-15. O último snapshot concluído foi 2026-06-18. De 2026-06-19 em diante o script parava na etapa SCP com exit 127 porque o binário `expect` não estava instalado.

Correção canônica:

- instalar e inventariar pacote `expect`;
- manter somente as duas credenciais SSH no 1Password;
- remover lookup do webhook;
- publicar pela API Discord usando `DISCORD_BOT_TOKEN` local do Zeus;
- validar o canal retornado pelo Discord;
- usar `MGS_YOAST_FORCE_POST=1` somente para recuperação/smoke real autorizado;
- usar `MGS_YOAST_SNAPSHOT_FILE` e API/token overrides para E2E isolado.

Validação de recuperação: consulta SQL real retornou 280 posts; SEO 206 verdes/39 amarelos/0 vermelhos/35 não analisados; readability 205/36/39/0. Mensagem real do bot Zeus confirmada no canal em `1525353581320994867`.

## GPT-5.6 OAuth volume

Runtime: `/root/mgs-agent/scripts/monitor-gpt55-oauth-cost.sh` (nome legado preservado para não quebrar cron)
Cron: `44 22 * * *` ET
Canal: `1498132022634483894`

Não usar estimativa fixa de tokens por chamada nem preço hipotético sem telemetria. Os logs dos gateways expõem `response ready ... api_calls=N`, mas não input/output tokens. O relatório canônico soma chamadas LLM e respostas concluídas na janela móvel de 24h, calcula média por resposta e valida `gpt-5.6-sol` / `openai-codex` nos quatro profiles. Custo incremental real: US$ 0 via OAuth.

Validação: py_compile, dry-run com parse_errors=0 e API Discord mock com autenticação/payload sanitizados.

## Housekeeping de backups

Runtime: `/root/mgs-agent/scripts/housekeeping-bak-cleanup.sh`
Cron: `44 20 * * 2,5` ET (terça e sexta às 20:44)
Canal: `1498132022634483894`, bot Zeus direto, sem 1Password.

Proteções:

- somente nomes com marcadores explícitos `.bak`, `.backup`, `.old`, `.orig` ou `~`;
- canônicos sem marcador nunca entram na lista;
- por diretório + família normalizada, preserva sempre o arquivo mais recente, mesmo acima da retenção;
- família com um único backup nunca é deletada;
- tarballs Hermes preservam os dois mais recentes globalmente;
- `--dry-run` nunca remove nem notifica.

Teste destrutivo deve usar apenas fixture temporária via `MGS_HOUSEKEEPING_SCAN_ROOTS`, `MGS_HOUSEKEEPING_BACKUPS_ROOT`, `MGS_HOUSEKEEPING_HERMES_UPDATE_ROOT` e `MGS_HOUSEKEEPING_LOG`. Validar canônico preservado, último backup pequeno preservado, antigos removidos, dois tarballs mais recentes preservados e mais antigo removido.

Evidência histórica de produção: o script removeu backups elegíveis em 01/07, 02/07, 03/07, 05/07 e 08/07; em 05/07 removeu sete arquivos/3162,41 MB preservando os backups recentes. A validação de 11/07 também executou remoção real em fixture isolada e confirmou todas as proteções.