### Processamento Zeus de REPORT-INFRA com cron Hermes de outro profile

Quando um agente reportar criação/modificação de cron Hermes `no_agent` + script wrapper em outro profile (ex: Ares):
1. Validar evidência mínima sem expor segredo: `py_compile` do script real, `bash -n` do wrapper, `sha256sum` dos paths reportados e leitura sanitizada do `~/.hermes/profiles/<agent>/cron/jobs.json` para confirmar `id`, `enabled`, `state`, `next_run_at`, `script`, `no_agent` e `deliver`.
2. Atualizar `/root/mgs-agent/data/infra-inventory.json` com:
   - script versionado em `/root/mgs-agent/scripts/...`;
   - wrapper/profile script fora do repo, se for parte runtime do cron;
   - registro do cron Hermes com `profile`, `id`, `schedule`, `script`, `next_run_at`, `state`, `enabled`, `no_agent` e `deliver`.
3. Registrar `report_infra_processed` em `events-audit.jsonl` com validações executadas.
4. Commitar somente os artefatos versionáveis relevantes (`data/infra-inventory.json` e script em `/root/mgs-agent/scripts/...`). Não tentar `git add` path fora do repo; registre-o no inventário.
5. Responder só depois do processamento completo, no formato curto acima.

### Convenção de canal Discord por tipo de alerta

| Tipo | Canal | Webhook 1Password |
|---|---|---|
| Infra crítica (auto-push, deploy) | `#mgs-alerts` (1498132022634483894) | `Discord Webhook - Alerts Infra Channel` |
| Updates do Hermes Agent | `#alerts-hermes-news` (1505609056771899644) | Zeus Bot API (`DISCORD_BOT_TOKEN` do profile zeus) |
| Saúde Yoast/Readability | `#alerts-yoast` (1498193722871910550) | `Discord Webhook - Alerts Yoast Channel` |
| REPORT-INFRA / alertas infra | `#alerts-infra` (1498132022634483894) | `Discord Webhook - Alerts Infra Channel` |

**NÃO usar** o webhook `#alerts-infra` para alertas automáticos de cron/monitor. Reservado para conversa operacional Rodolfo↔Zeus e commits interativos; `[REPORT-INFRA]` de agentes deve ir para `#alerts-infra` (1498132022634483894). Se um Hermes cron script-only já estiver preso a uma thread por `deliver=origin`, mudar o cron para `deliver=local` e fazer o script enviar embed próprio para `#alerts-infra`; não tentar “embelezar” stdout bruto na thread. Ver skill `log-monitor-discord-alert` → `references/hermes-cron-script-only-alert-routing.md`.

### Layout de alertas automáticos via webhook

Quando ajustar ou criar alertas nos canais `#mgs-alerts` / `#alerts-yoast`, evitar mensagens longas em texto corrido. Rodolfo considera esse formato poluído e difícil de entender.

Padrão preferido:
- `content`: só mention/push + frase curta quando precisa notificação (`<@344196393512075265> alerta de ...`). Sem blocos longos no content.
- `embeds`: título curto, cor por severidade e `fields` separados por assunto (`Script`, `Estado`, `Ação`, `Detalhe técnico`, `API calls`, etc.).
- Resoluções: embed verde simples com título curto (`Cron recuperado`, `Service normalizado`) e descrição de 1 linha.
- Custo/volume: separar `Custo real`, `Custo hipotético`, `API calls`, `Tokens estimados`, `Referência`, `Nota` em fields; não jogar tudo em uma descrição Markdown única.
- Emojis: usar só como indicador de severidade no resumo/título; não repetir em toda linha.

#### Listas longas no Discord mobile: agrupar por chave, não forçar tabela

Quando um alerta precisa mostrar lista de pessoas/contas com campos longos — especialmente `email`, `nome`, `perfil ID`, `role` — não insistir em tabela de 4 colunas. Mesmo em bloco monoespaçado, o Discord mobile corta/trunca emails e deixa a leitura ruim.

Padrão validado com Rodolfo para Meta App Roles:

```text
Usuários do app - B002
Ordenado por BOT EMAIL

disparosconecta@gmail.com
• Adalberto Vilela Oliveira — adalbertovilelaoliveira — Admin
• Afonso Araujo — fernandadossanto678 — Admin

disparosfinanceadx@gmail.com
• Fernando Narciso Acosta — 100009006839947 — Admin
```

Regra prática:
- embed curto para status/resumo;
- mensagem normal separada para a lista;
- chave agrupadora longa em linha própria (`BOT EMAIL`, domínio, site, conta);
- itens em bullets: `Nome — ID — Role/estado`;
- linha em branco entre grupos;
- ordenar pela chave agrupadora;
- validar visualmente em 1 canal canário antes de disparar em massa.

Não usar aliases artificiais (`D1`, `D2`) nem responder que é questão de “modo desktop”: o render depende do client Discord, então o layout deve ser mobile-first. Detalhe: `references/discord-mobile-grouped-list-alert-layout-2026-06-30.md`.

Exemplo jq compacto para webhook:

```bash
PAYLOAD=$(jq -n \
  --arg c "<@344196393512075265> alerta de cron stale" \
  --arg script "$SCRIPT" \
  --arg detail "$DETAIL" \
  '{content:$c, embeds:[{title:"Cron sem log recente", color:15158332, fields:[
    {name:"Script", value:("`"+$script+"`"), inline:true},
    {name:"Estado", value:"STALE", inline:true},
    {name:"Ação", value:"Verificar cron, script e log.", inline:false},
    {name:"Detalhe técnico", value:("```text\n"+$detail+"\n```"), inline:false}
  ]}]}')
```

Validação mínima antes de reportar sucesso: `bash -n` no script alterado e dry-run quando existir (`--dry-run`, sem envio Discord). Se o script for monitor cron, evitar disparar alerta real de teste para não sujar o canal; validar payload estrutural/localmente quando possível.

Em execuções multi-etapa de infra para Rodolfo, cada relatório parcial, final ou bloqueado deve terminar com `Próximo passo pendente:` e nomear a próxima ação operacional concreta até o checklist estar concluído. Mesmo quando a execução fica bloqueada por safety gate/falta de permissão, declarar o próximo comando/manual action esperado e a evidência que deve ser validada depois.

---
## SEÇÃO B — Roles Managed (não deletáveis via API)

### O Problema

Roles com `managed: true` são criados quando um bot é adicionado ao server. A API **não permite deletar**:
```
DELETE /guilds/{guild_id}/roles/{role_id} → HTTP 400: "Cannot delete a managed role"
```

### Como Identificar

```bash
curl -s -H "Authorization: Bot $DISCORD_BOT_TOKEN" \
  "https://discord.com/api/v10/guilds/{GUILD_ID}/roles" \
  | jq '.[] | select(.id == "{ROLE_ID}") | {name, managed}'
# managed: true → não deletável; managed: false → pode deletar
```

### Características

- Criados automaticamente quando bot é adicionado
- Nome = nome do bot (ex: "Zeus", "Atena")
- `mentionable: false` por padrão
- Removidos apenas quando o bot é removido do server

### Alternativa Operacional

Parar de mencionar o role — usar **user mention direto** (`<@BOT_ID>` + `<@344196393512075265>`). O role continua existindo mas inofensivo. **Por que não usar role mention:** a role `mentionable: false` e não dispara push notification para Rodolfo. User mention direto é o que realmente notifica.

---
