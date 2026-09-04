### Pitfall: não quebrar blocos ```text no meio ao dividir mensagens longas

Quando um helper postar relatórios longos no Discord e precisar dividir por limite de 2000 caracteres, **nunca dividir no meio de um bloco fenced** (` ```text ... ``` `). Isso faz o Discord renderizar metade da tabela como código e metade como texto solto, deixando a formatação “horrível/bagunçada”. O chunker deve preferir boundaries entre blocos completos; validar antes do envio que cada chunk tem code fences balanceados (`count('```') == 0 ou 2`) e tamanho `<2000`. Para relatórios tabulares longos, gere blocos menores com cabeçalho repetido (`bloco 1/N`, `bloco 2/N`) em vez de uma tabela única gigante. Quando o erro ocorrer inteiramente no preflight, antes de qualquer POST, fazer no máximo uma retentativa automática usando parser fence-aware e paginação segura; depois falhar fechado. Se qualquer parte já tiver produzido message ID, não reenviar às cegas: reconciliar por GET/readback primeiro para evitar duplicidade.

Em edição de várias mensagens existentes por `PATCH`, um `HTTP 429` não autoriza repetir todas as edições: ler `retry_after` do JSON ou `Retry-After` do header, aguardar esse intervalo com pequena margem e retry bounded. Persistir os message IDs; antes de retomar, fazer GET de cada alvo e editar somente a parte cujo conteúdo ainda diverge. Depois, repetir GET individual e exigir `channel_id`, `author.id` e conteúdo exatos para todas as partes.

Para cron/report posters que fazem `POST /channels/{id}/messages` direto na API Discord, implementar chunking no helper de postagem para nunca enviar `content` acima de 2000 caracteres. Preferir chunks de ~1900 chars, split por linha, labels `[parte N/T]`, e dry-run com `chunks`, `chunk_lengths` e `max_chunk_len`. Em modo thread existente, postar todas as partes na própria thread; em modo criar thread, criar a thread pela parte 1 e postar as demais dentro dela. Caso real e validação: `references/discord-cron-message-chunking.md`.

Quando a entrega normal do agente tiver limite de **8 mensagens Discord por resposta**, manuais longos devem ser divididos deliberadamente em partes independentes antes do envio. Cada parte deve caber com folga no limite, terminar em fronteira de seção e indicar a continuação esperada. Nunca confiar apenas no auto-chunker para um manual completo. Se houver truncamento, publicar somente as seções faltantes, sem repetir as já entregues; confirmar readback apenas quando existir leitura real da plataforma e, sem API/readback disponível, declarar a limitação em vez de inventar confirmação.

Padrão preferido:
- `content`: só mention/push + frase curta quando precisa notificação (`<@344196393512075265> alerta de ...`). Sem blocos longos no content.
- `embeds`: título curto, cor por severidade e `fields` separados por assunto (`Script`, `Estado`, `Ação`, `Detalhe técnico`, `API calls`, etc.).
- Resoluções: embed verde simples com título curto (`Cron recuperado`, `Service normalizado`) e descrição de 1 linha.
- Custo/volume: separar `Custo real`, `Custo hipotético`, `API calls`, `Tokens estimados`, `Referência`, `Nota` em fields; não jogar tudo em uma descrição Markdown única.
- Emojis: usar só como indicador de severidade no resumo/título; não repetir em toda linha.

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
## SEÇÃO C — Hook git post-commit com notificação Discord

### Quando usar
- Notificar canal Discord automaticamente após commits interativos do Rodolfo no mgs-agent
- Auditoria de mudanças de infra em tempo real

### ⚠️ PITFALL CRÍTICO: filtro por autor não funciona

O repo `/root/mgs-agent` tem `user.name=Rodolfo Mattei` para todos os commits (auto-commits do watcher, Atena, manuais). **Filtro `%an/%ae` não discrimina.**

### ✅ Solução validada: TTY check

- SSH interativo do Rodolfo → TTY ativo
- Auto-commit watcher (systemd) → sem TTY
- Gateways Zeus/Atena (systemd) → sem TTY
- Crons → sem TTY

```bash
# Capturar ANTES do subshell background (herda via variável)
IS_INTERACTIVE=0
if [ -t 0 ] || [ -t 1 ] || [ -t 2 ]; then
  IS_INTERACTIVE=1
fi
# No subshell, verificar $IS_INTERACTIVE
```

**CRÍTICO:** capturar `IS_INTERACTIVE` no processo pai (antes do `( ) & disown`). O subshell herda variáveis mas não acessa o TTY do pai após fork.

### Hook post-commit (versão produção)

Localização: `/root/mgs-agent/.git/hooks/post-commit`

Instalar: copiar conteúdo do arquivo de referência `references/git-hook-post-commit.sh` para o hook e `chmod +x`.

Webhook URL: 1Password → vault `MGS Conteúdo` → item `Discord Webhook - Alerts Infra Channel` → campo `label=webhook_url` (não `url`) para REPORT-INFRA/alertas; usar `Discord Webhook - Zeus Channel` apenas para hook de commit interativo quando explicitamente aplicável.

### Webhook 403 false-negative / User-Agent

Se um envio de REPORT-INFRA via `send_message` ou Python `urllib.request` retornar 403, não concluir imediatamente que o webhook está morto. Validar com `curl` e User-Agent explícito antes de trocar credenciais:

```bash
WEBHOOK_URL=$(op item get "Discord Webhook - Alerts Infra Channel" --vault "MGS Conteúdo" --fields label=webhook_url --reveal)
curl -sS -A 'MGS-Agent-InfraReporter/1.0' -o /tmp/body -w '%{http_code}' --max-time 15 "$WEBHOOK_URL"
```

Padrão validado no Ares: `urllib` sem User-Agent/rota direta do bot pode cair em `403`, enquanto o webhook real responde `200` em GET e `204` em POST via `curl -A`. Para REPORT-INFRA de Ares, preferir o helper persistente `/root/mgs-agent/scripts/ares-report-infra.sh`, que busca o webhook no 1Password e envia por `curl` com User-Agent. Ao resolver pendências, marcar arquivos locais como `.delivered` só depois de `http_status=204`.

### Pitfalls do hook

1. **`op` sem token no cron/background:** sempre `source /root/mgs-agent/.env` explicitamente no subshell
2. **URL hardcoded:** nunca. URL no 1Password, lida em runtime
3. **curl sem timeout:** usar `--max-time 5`; Discord pode estar offline
4. **Erros silenciosos:** usar `|| true` e `2>/dev/null` em tudo Discord; o push para GitHub NUNCA pode falhar por causa da notificação
5. **Identidade git compartilhada:** não filtrar por `%an/%ae` — usar TTY check
6. **`mapfile` em commits vazios:** `diff-tree` retorna vazio para `--allow-empty`; embed aparece sem lista de arquivos (inofensivo)
7. **Não testar via `terminal()` do Zeus:** subshell não tem TTY; testar via SSH direto do Rodolfo

---
## SEÇÃO D — Diagnóstico, Cron Scheduler e Reinicialização de Agente (Gateway Hermes)

### Quando usar
- Agente está online (processo rodando) mas não responde no Discord
- Mensagens não aparecem como `inbound message` no log
- Agente travou em loop de rate limit
- Usuário relata silêncio após período de alta atividade
- Auditar ou migrar cron jobs Hermes/Linux entre profiles MGS

