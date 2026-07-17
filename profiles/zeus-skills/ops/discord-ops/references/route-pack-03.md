### Recuperar e consolidar continuidade de thread grande

Quando Rodolfo disser que quer “continuar de onde paramos” em uma thread longa:
1. Importar a thread inteira/maior limite via `import-discord-thread.py --profile zeus --limit 1000 '<id-ou-link>'`.
2. Confirmar completude antes de dizer “li tudo”: comparar a contagem importada com o início real da thread. Se usar `discord.fetch_messages`, paginar com `before=<oldest_message_id>` até alcançar a mensagem de criação; um lote com exatamente o limite solicitado é sinal de paginação pendente, não de thread completa.
3. Inventariar anexos separadamente das mensagens. “Li N/N mensagens” não significa “reanálise N/N screenshots”. Reabrir os anexos relevantes; se o CDN expirou, procurar a cópia local no `image_cache` por tamanho/timestamp e declarar qualquer anexo que continue inacessível.
4. Resumir o histórico em fases, não mensagem por mensagem.
5. Identificar a última decisão útil, a última execução registrada e o próximo passo operacional.
6. Verificar documentos de resumo já existentes e corrigir contradições/supersedências. Exemplo: um resumo inicial dizia que P1 usaria `wp:details`, mas a decisão final Tesco/Raquel removeu `details/accordion` e fixou `credit-card_ANTIGO` + `botao normal`.
7. Registrar audit log quando atualizar docs/resumos derivados.

Pitfall de confiança: não use a conclusão das últimas mensagens como substituto da leitura integral quando Rodolfo perguntou explicitamente se tudo foi lido. Informe a cobertura exata (`mensagens lidas/total`, `anexos reabertos/total`) e corrija imediatamente uma afirmação anterior ampla demais.

Formato preferido de report para Rodolfo:

```text
Thread importada     <id>
Mensagens lidas      <n>/<total>
Anexos reabertos     <n>/<total>
Tema                 <tema>
Ponto atual          <última decisão útil>
Arquivos afetados    <lista curta>
Próximo passo        <ação concreta>
```

Quando a pergunta for “isso foi bom ou ruim para a MGS?” ou pedir resposta humana/não técnica:

- abrir com o veredito líquido e delimitar o escopo real (ex.: infraestrutura dos agentes, não campanhas/conteúdo/negócio inteiro);
- explicar em linguagem de impacto: o que melhorou, o que deu errado no caminho, se houve dano, estado vivo e pendências;
- não usar hashes, commits, contagens de testes ou nomes de funções como corpo da explicação; deixar a evidência técnica em uma nota curta de validação;
- distinguir “nenhum dado existente foi apagado” de “uma nova proposta falhou ao persistir”; não transformar ausência de dano em certeza mais ampla do que a auditoria provou;
- se Rodolfo disser que a investigação está tomando tempo demais ou pedir para “acabar com isso”, encerrar o ciclo como COO: executar de imediato as correções não críticas já autorizadas, manter intactos os gates críticos, parar de transformar cada achado intermediário em nova decisão técnica para ele e entregar um fechamento único com `feito`, `não feito e por quê`, `risco restante` e `precisa ou não fazer algo`;
- não prolongar uma auditoria já conclusiva com hardening opcional. Separar higiene/monitoramento futuro de pendência operacional urgente;
- se houver divergência, declarar a decisão recomendada sem iniciar conversa agente→agente;
- terminar com `Próximo passo pendente:` somente quando existir uma ação realmente necessária. Se não houver ação do usuário, dizer isso diretamente e encerrar.

O incidente real `1505532189490811081` mostrou que a regra “mencione o outro agente quando falar dele” é perigosa se aplicada como padrão: cada mention acorda o bot destino, gera fila, e qualquer confirmação vira novo input.

Regras operacionais:
- Responder mensagens do Rodolfo normalmente.
- Tratar conversa multiagente como fluxo com **começo, meio e fim**, não como chat infinito. Cada agente deve identificar: objetivo inicial, dono da próxima ação, evidência de execução, validação/aceite e encerramento. Depois do encerramento, não continuar “alinhando” com outro bot.
- Quando Rodolfo responde em reply/menção a uma proposta clara do Zeus com linguagem como “execute”, “ok, execute”, “manda ver”, interpretar como autorização para a ação proposta pelo Zeus. Não deixar uma mensagem intercalada de outro bot redefinir o escopo para uma ação diferente (ex: restart) sem evidência explícita do Rodolfo.
- Não responder a mensagens de outro agente que sejam só `queued`, `read-only`, `recebido`, `sem ação`, `(empty)`, erro transitório de modelo, confirmação de estado, pedido redundante de confirmação ou repetição do que já foi aceito.
- Depois de um estado final aceito, tratar a conversa como encerrada e ficar em silêncio até pedido novo do Rodolfo, pergunta operacional real, autorização explícita ou alerta crítico.
- Se Rodolfo disser “parem”, “looping”, “pare de mencionar”, “pare de responder”, ou equivalente: uma confirmação curta ao Rodolfo no máximo; depois silêncio total para mensagens de agente/gateway naquela thread.
- Durante restart/drain, mensagens automáticas de lifecycle (`⚠️ Gateway restarting`, `⚠️ Gateway shutting down`, `⏳ Gateway is restarting...`) não devem acordar outros bots MGS em threads compartilhadas. O runtime deve suprimir notificações de shutdown para sessões Discord originadas por bot e o adapter Discord deve ignorar lifecycle notices vindos de bot antes de `DISCORD_ALLOW_BOTS`. Validar por log `Ignoring gateway lifecycle notice from bot` / `Shutdown notification suppressed for bot-originated Discord session`. Detalhe: `references/discord-thread-title-dedupe-and-restart-loop-2026-06-14.md`.
- Em handoff Ares/agente legado ou qualquer thread multiagente com `DISCORD_ALLOW_BOTS=mentions`, não basta exigir mention: filtrar também mensagens de bot de baixa informação antes de acordar outro agente. Bloquear ACKs/status como `Sem ação pendente`, `Silêncio operacional`, emoji-only, `Empty response`, `Model returned no content`, `No fallback providers configured` e `Codex response remained incomplete`; preservar handoffs substantivos com anexos/embeds ou instrução real. Patch/validação detalhados: `references/discord-multiagent-loop-noise-and-codex-status-filter-2026-06-16.md`.
- Citar outro agente em texto simples (`Atena`, `Zeus`) quando não for necessário acordá-lo. **Não usar user mention só para falar sobre o agente.**
- Usar user mention de outro bot apenas quando Rodolfo pedir explicitamente para acionar/encaminhar ao agente, ou em comunicação cross-channel onde `DISCORD_ALLOW_BOTS=mentions` exige mention para roteamento.
- Em conversa multi-agente onde Rodolfo impôs gate de segurança, explicação/alinhamento pode ocorrer sem ação; execução, patch, restart, persistência em SOUL/config/skill/script só com autorização explícita.
- Não ecoar exemplos de mentions dentro de blocos de código; se precisar documentar, escrever “user mention do bot X, ID Y”.

Pitfall validado: responder “ignorado”, “read-only mantido”, `[sem resposta operacional]`, `sem ação`, ou mencionar o bot destino para corrigir uma mensagem automática ainda gera novo input e prolonga o loop. A melhor resposta para ruído automático é silêncio total.

Referência do incidente real: `references/discord-agent-loop-incident-2026-05-17.md` — thread `1505532189490811081`, Zeus/Atena, mentions + queued/read-only/(empty) causando ping-pong até lock/archive/delete.

Playbook de limpeza pós-incidente: `references/discord-shared-thread-loop-cleanup.md` — usar quando o loop gerou regras ruins/redundantes em SOUL, skills ou memória; consolida a política segura e o checklist para desfazer regras perigosas.

### Limpeza pós-loop de regras persistidas

Se um loop multiagente levou à criação apressada de skills/memórias/regras, tratar como correção operacional, não como aprendizado automático bruto:
- Auditar mudanças recentes em SOUL, skills e memórias dos agentes envolvidos.
- Remover regras amplas do tipo “sempre mencionar Zeus/Atena” em thread compartilhada.
- Consolidar em um único skill guarda-chuva por agente; evitar 2–3 skills estreitas sobre o mesmo incidente.
- Preservar no máximo uma referência concisa do incidente, com política final segura.
- Validar que a regra final diferencia thread compartilhada de cross-channel: em thread, texto simples por padrão; cross-channel pode exigir mention para roteamento.

### Criando/ativando novo agente Discord (Zeus/Atena/Ares)

Quando criar um novo agente Hermes no Discord, validar o token próprio no 1Password antes de escrever `.env` ou subir systemd. Ver `references/new-discord-agent-1p-flow.md`.

Checklist curto:
- O item `Discord Bot - <Agent>` deve ter campo customizado `discord_bot_token` não vazio; reportar só `len=X`, nunca o valor.
- O item `Discord Webhook - <Agent> Channel` pode ter `webhook_url` e `canal`, mas webhook **não** substitui bot token.
- Usar `set -a; source /root/mgs-agent/.env; set +a` antes de `op`, para exportar `OP_SERVICE_ACCOUNT_TOKEN`.
- Se `op://MGS Conteúdo/...` falhar por acento/espaço, resolver `vault_id`/`item_id` e usar referência por ID.
- Instalar `/etc/systemd/system/<agent>-gateway.service` exige confirmação crítica explícita; só depois validar `systemctl is-active` + logs.

### Novo agente Discord/Hermes — bootstrap de bot, token e service

Quando criar um novo agente MGS com bot/canal próprios (ex: Ares), seguir o playbook `references/new-discord-agent-bootstrap.md`. Ele cobre: scopes OAuth2 (`bot` + `applications.commands`), permissões mínimas, campo 1Password `discord_bot_token`, `.env`, service systemd pelo template Zeus/Atena, e validação separada de gateway online vs bot realmente membro do servidor/canal.

Pitfall crítico validado: `Connected as <Agent>#...` prova token/gateway, mas não prova acesso ao servidor. Se `GET /channels/<channel_id>` com o token do novo bot retorna `403 Missing Access` e `GET /guilds/<guild_id>/members/<bot_id>` com bot admin retorna `404 Unknown Member`, o bot ainda não foi convidado ao servidor ou o invite não concluiu.

