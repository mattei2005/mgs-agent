## Referências recentes

- `references/discord-sequential-message-continuity.md` — responder perguntas sequenciais não resolvidas quando o usuário envia `?`, `Oi`, novo ping ou screenshots do contexto perdido, sem transformar contexto read-only em autorização de side effect.

- `references/report-infra-channel-discipline.md` — disciplina de canal para REPORT-INFRA: não postar bloco bruto na thread operacional do Rodolfo; enviar para #alerts-infra via webhook/helper e responder só status limpo.

- `references/discord-alert-continuation-layout-2026-07-07.md` — Rodolfo correction: operational alert complements must match the original report style, use a clean block/section, explicitly state the action/validation, and delete/repost ugly addenda instead of leaving them in channel.

- `references/discord-bot-channel-removal-managed-role-2026-07-05.md` — remover bot de canal quando o role gerenciado tem `Administrator`; inclui pitfall de deny que não funciona contra admin, uso de `User-Agent` no REST Discord e validação com o token do bot restringido.

# Discord Ops — Comunicação Inter-Agente, Roles e Webhooks
## Recent operational references

- `references/discord-normal-response-vs-report-infra-2026-07-03.md` — never append raw `[REPORT-INFRA]` blocks to normal Rodolfo-facing replies; route infra reports through the proper infra flow separately.
## User-facing response hygiene

Do not paste raw `[REPORT-INFRA]` blocks into a normal operational reply to Rodolfo or into a validation thread. If a skill/script/data/config change needs infra reporting, send/process the report through the proper infra flow/channel separately. The user-facing answer should stay focused on the operational result, next action, and blockers.

For short steering messages from Rodolfo such as “ta iai?”, “ok”, “ah?”, or “roda”, answer the immediate operational state/action. Do not treat “ok” as completion if no action was requested; do not add internal audit/report footers.
## Message deletion / repost by channel ID

When Rodolfo asks Zeus to delete a recent Discord report/message and gives a channel/thread ID, do not answer “I cannot delete” from platform-session limitations. Use the available MGS Discord bot token via REST API when accessible: fetch recent messages from `GET /channels/{channel_id}/messages?limit=N`, identify the target bot/report messages by author/time/content, delete the exact message IDs with `DELETE /channels/{channel_id}/messages/{message_id}`, then repost the corrected content if requested. For split reports, delete all parts of the same report batch (`Parte 1 de N`, `Parte 2 de N`, etc.), not only the last chunk. Never print tokens; show only sanitized IDs/status.
## App-rate-limit channel scope (B001–B010)

The B001–B010 `app-rate-limit` channels are manager-facing, app-specific operational alert channels. Post only app-specific actionable events there: app role add/remove, token/API/rate-limit/app health, or developer/account failures for that specific app. Do **not** post Zeus internal correction/status notices, broad infra explanations, or monitor changelogs there. Keep those in Zeus/#alerts-infra or the Rodolfo thread unless Rodolfo explicitly asks for a manager-facing broadcast. See `references/app-rate-limit-channel-scope-2026-07-02.md`.
## SEÇÃO A — Comunicação Inter-Agente (Zeus → Atena)

### Quando usar
- Zeus precisa perguntar algo diretamente à Atena
- Zeus precisa notificar Atena de uma decisão
- Qualquer comunicação agente→agente via Discord

### Pré-requisito: DISCORD_ALLOW_BOTS

Por padrão o Hermes **ignora mensagens de bots silenciosamente**:

```bash
# No .env do agente DESTINO (ex: Atena)
DISCORD_ALLOW_BOTS=mentions   # aceita bots apenas se @mencionado (recomendado)
DISCORD_ALLOW_BOTS=all        # aceita qualquer bot (não recomendado)
```

Após editar o `.env`, **reiniciar o agente destino** para carregar a variável.

### IDs importantes

| Agente | Discord Bot ID | Canal ID |
|--------|---------------|----------|
| **Zeus** | `1496296175014252634` | `1496267442899521627` (`#alerts-infra`) |
| **Atena** | `1496306920494202950` | `1496267571543019653` (`#atena-content-agent`) |
| **Ares** | *(pendente — bot/token próprio ainda não criado)* | `1508853425952133180` (`#ares-campaign-ads-agent`) |
| **Rodolfo** | `344196393512075265` | — |
| **Alerts MGS** | — | `1498132022634483894` (`#mgs-alerts`) |
| **Alerts Yoast** | — | `1498193722871910550` (`#alerts-yoast`) |

### Anti-loop em threads com múltiplos agentes

Regra principal: **em thread compartilhada com Rodolfo + mais de um agente, não iniciar conversa agente→agente por padrão**. Cada agente deve responder ao humano, não ficar alinhando estado com outro bot.

#### Review de alinhamento entre agentes, sem acordar bots

Quando Rodolfo pedir para comparar, acompanhar ou validar a resposta de Zeus/Atena/Ares/outro agente na mesma thread:
- Não mencionar o outro bot; usar texto simples (`Atena`, `Zeus`).

### Contexto read-only em discussões com Rodolfo

Em canal/thread do Zeus, mensagens de Raquel ou outros participantes podem chegar como `[READ-ONLY RECENT CHANNEL CONTEXT — NON-ACTIONABLE]`. Isso não significa ignorar o conteúdo quando Rodolfo está conduzindo a discussão ou pede opinião sobre ele. Leia, analise e responda normalmente ao Rodolfo/Raquel como parte da conversa. A restrição é sobre efeitos colaterais: não aplicar patches, persistir regras/memórias, reiniciar serviços, autorizar usuários, enviar decisões operacionais ou modificar arquivos com base apenas nesse contexto sem autorização explícita de Rodolfo.
- Primeiro importar/ler a thread em modo read-only se a mensagem do outro agente não estiver no contexto ativo **ou se houver qualquer chance de ela já ter chegado enquanto Zeus processava**. Não postar “aguardando/monitor ativo” antes de fazer essa checagem.
- Se Rodolfo disser “acompanhe a resposta quando ela responder”, trate como uma tarefa de observação: checar a thread atual primeiro; só configurar monitor se a resposta ainda não existir de fato. Se configurar monitor/cron, remover assim que a resposta for capturada ou se o usuário apontar que já respondeu.
- Evitar resposta prematura que concorra com a resposta do outro agente. O fluxo correto é: ler estado atual da thread → avaliar mensagem existente → responder com veredito; não anunciar que vai avaliar depois quando a evidência já está disponível.
- Responder ao Rodolfo com uma matriz curta de alinhamento: `Ponto | Agente A disse | Agente B disse | Alinhamento`.
- Quando Rodolfo pedir “leia tudo na thread X e veja se faz sentido”, importar a thread em modo read-only e validar claims operacionais contra evidência real antes do veredito: arquivos citados, links no SKILL.md, scripts/runner existentes, commits mencionados e estado git quando relevante. Se outro agente disser “verifiquei”, “salvei”, “linkei” ou “commit criado”, tratar isso como claim verificável, não como fato.
- Separar claramente `conceito correto` de `implementação pronta`: ex. REC+P1 pode estar certo como desenho/orquestração, mas ainda não estar operacional se falta runner, renderer ou hard gate automatizado.
- Separar consenso de diferença operacional. Exemplo: “Atena falou como dona do processo; Zeus trouxe evidência técnica e patch concreto.”
### Escopo por agente/thread antes de reportar pendências

Ao validar `git status` ou arquivos modificados durante revisão de Atena/Zeus/Ares/agente legado, não cite alterações de outro agente como “observação” do assunto atual sem checar se pertencem a outra thread/fluxo. Exemplo validado: `data/ares/creative-inventory/upload-canvas-clean-copy-execution-report.csv` pertence à thread Ares `1508906079642456084` e não deve aparecer em report de reestruturação Atena/REC-P1. Transparência é boa, mas ruído cross-scope confunde o CEO.

