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
Cron: `54 11 * * *` ET
Canal: `1498132022634483894`

O relatório canônico usa os bancos profile-local `state.db`, tabelas `sessions` + `session_model_usage`, nos profiles ativos Zeus/Atena/Ares. Essa fonte inclui Discord, CLI/oneshot, cron, tool e subagent e expõe chamadas, tokens reais, cache, billing mode e custo real; não usar apenas `gateway.run: response ready`, porque isso omite execuções Hermes avulsas e pode produzir falso zero.

Regras:

- janela de 24h por `session_model_usage.last_seen`;
- somar chamadas e tokens reais por profile e origem;
- validar `gpt-5.6-sol`, `openai-codex` e `subscription_included`;
- mostrar gasto real OAuth separado da simulação pay-per-token;
- calcular a simulação com os tokens reais de entrada/saída e premissas US$ 7/US$ 21 por 1M;
- detectar sessões com `first_seen` anterior ao cutoff e rotular a cobertura como agregada, nunca silenciosamente exata;
- falhar fechado se qualquer `state.db` ativo estiver ausente ou ilegível;
- manter `--as-of` para recuperação/auditoria reproduzível de uma janela histórica.

Oneshots Hermes oferecem `--usage-file`, mas o monitor central não depende de instrumentar cada chamador enquanto `session_model_usage` estiver disponível e validado.

Validação: `py_compile`, fixture SQLite com CLI + Discord, sessão cruzando o cutoff, dry-run histórico/live e API Discord mock com autenticação fora do payload, `content` vazio e token ausente do corpo.

## Resolvedor automático de alertas

Quando `hermes -z` produzir stdout final não vazio e depois abortar no teardown (caso observado: `rc=-6`), o stdout continua sendo a resposta final pelo contrato do oneshot e deve ser entregue como reply. Retorno não zero sem stdout final continua sendo erro. Validar com fixture `CompletedProcess`, embed reply sem mentions e readback Discord; nunca tratar stderr/trace bruto como resposta pública.

## Housekeeping de backups

Runtime: `/root/mgs-agent/scripts/housekeeping-bak-cleanup.sh`
Cron: `44 20 * * 2,5` ET (terça e sexta às 20:44)
Canal: `1498132022634483894`, bot Zeus direto, sem 1Password.

Proteções:

- somente nomes terminados por marcadores explícitos `.bak*`, `.backup*`, `.old*`, `.orig*` ou `~`; a regex é ancorada no fim para não tratar nomes como `bakery.txt` como backup;
- canônicos sem marcador nunca entram na lista;
- por diretório + família normalizada, preserva sempre o arquivo mais recente, mesmo acima da retenção;
- família com um único backup nunca é deletada;
- tarballs Hermes preservam os dois mais recentes globalmente;
- diretórios raiz de backup usam `-mindepth 1` e nunca podem ser removidos pelo cleanup de diretórios vazios;
- cada `rm` é validado por existência; qualquer arquivo remanescente gera falha explícita;
- `--dry-run` nunca remove nem notifica.

Teste destrutivo deve usar apenas fixture temporária via `MGS_HOUSEKEEPING_SCAN_ROOTS`, `MGS_HOUSEKEEPING_BACKUPS_ROOT`, `MGS_HOUSEKEEPING_HERMES_UPDATE_ROOT` e `MGS_HOUSEKEEPING_LOG`. Validar canônico preservado, último backup pequeno preservado, antigos removidos, dois tarballs mais recentes preservados e mais antigo removido.

Evidência histórica de produção: o script removeu backups elegíveis em 01/07, 02/07, 03/07, 05/07 e 08/07; em 05/07 removeu sete arquivos/3162,41 MB preservando os backups recentes. A validação de 11/07 também executou remoção real em fixture isolada e confirmou todas as proteções.