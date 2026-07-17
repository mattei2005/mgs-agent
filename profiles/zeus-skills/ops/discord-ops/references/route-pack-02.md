### Mentions cross-agent em canal de outro agente

Quando Rodolfo disser que marcou um agente dentro da thread/canal de outro agente e esperava resposta (ex.: Ares marcado em thread da agente legado), tratar como roteamento de gateway, não como falha do modelo. O agente marcado só receberá o evento se o canal pai/thread estiver em `discord.allowed_channels` efetivo dele; `thread_require_mention=true` sozinho não basta.

**Mensagens enviadas por outro bot/agente:** quando `DISCORD_ALLOW_BOTS=mentions`, uma mensagem de Zeus/agente legado/Ares/Atena sem mention direta do agente destinatário pode aparecer normalmente no Discord, mas será ignorada pelo gateway desse agente. Toda instrução cross-agent enviada por bot deve começar com `<@BOT_ID_DESTINATÁRIO>`, inclusive em thread já aberta. Depois do envio, validar em duas etapas: (1) readback confirma a mensagem e a mention no thread ID correto; (2) uma nova mensagem/atividade do agente destinatário confirma que ele acordou. Não interpretar apenas “mensagem enviada com sucesso” como handoff concluído. Se a primeira orientação saiu sem mention, reenviar de forma consolidada com mention — não depender de o agente reler histórico silenciosamente.

Para criar uma sessão nova de Atena/Ares exclusivamente para provar carregamento de política após restart/deploy, siga `references/cross-agent-session-policy-cutover.md`: thread nova, mention direta, turno sem ferramentas/produção, readback de `state.db.system_prompt` por thread ID e fechamento por evento de revalidação distinto — nunca reescrevendo um finalizer falho.

Caso inverso validado: se Rodolfo disser que qualquer mensagem sem mention acorda os dois agentes na thread de um deles, auditar o agente visitante. O canal externo pode estar em `allowed_channels` com `thread_require_mention=false` no YAML ou no `.env` efetivo. Corrigir para `thread_require_mention=true` e validar `/proc/<pid>/environ`, não apenas o arquivo. Detalhe: `references/discord-cross-agent-thread-reply-scope-2026-06-20.md`.

**Não transformar readback técnico em tarefa humana:** em um handoff cross-agent, a instrução deve conter gates objetivos e dizer explicitamente quando o agente pode continuar sem Rodolfo. Se status/report já confirmar página correta, rota correta e `authenticatedLikely=true`, não pedir que ele abra noVNC, dê F5, faça scroll ou responda “pronto” apenas para validar o que a máquina já provou. Intervenção humana fica restrita a login, MFA/2FA, CAPTCHA/challenge visível ou lacuna real de autenticação/cards. Quando Rodolfo tiver marcado “confiar neste dispositivo”, cookies e perfil viram estado crítico: manter a mesma rota de rede, impedir instâncias concorrentes, fazer shutdown limpo e criar snapshot seguro com lock liberado antes de nova operação. O orquestrador deve corrigir imediatamente o agente executor e liberar a continuidade automática quando os gates passarem.

### Challenges por IP de datacenter em fluxos Ares/agente legado

Quando Rodolfo suspeitar que Hetzner/VPS/datacenter IP está causando bloqueio em YouTube/agente legado ou Meta/Ares, não responder de memória nem propor migração de VPS como primeira ação. Importar a thread afetada em modo read-only, separar `browser consumer anti-bot` de `Marketing API endpoint trust`, e usar o teste de isolamento: mesma conta/token/payload/script, mudando apenas a origem de rede via proxy residencial/AdsPower. Para o playbook completo, ver `references/datacenter-ip-browser-api-challenge-diagnostics-2026-06-18.md`.

Padrão seguro para habilitar cross-agent por mention:
- Adicionar o canal do outro agente em `allowed_channels` do agente chamado.
- Manter `free_response_channels` restrito ao canal próprio do agente para evitar resposta livre fora da área dele.
- Manter `require_mention=true` e `thread_require_mention=true`, de modo que ele só acorde no canal externo com mention direta.
- Atualizar os três lugares quando existirem: config ativa (`/root/.hermes/profiles/<agent>/config.yaml`), config versionada (`/root/mgs-agent/profiles/<agent>-config.yaml`) e `.env` ativo se ele define `DISCORD_ALLOWED_CHANNELS`/`DISCORD_REQUIRE_MENTION` (env vence config em runtime).
- Ao patchar `.env`, preservar linhas operacionais não relacionadas (`DISCORD_HOME_CHANNEL`, `DISCORD_ALLOW_BOTS`, `BROWSER_DISABLE_SCREENSHOTS`, etc.) e evitar deixar chaves duplicadas; validar exibindo só chaves não secretas/valores sanitizados.
- Registrar audit log, deixar auto-commit/versionamento capturar o config versionado e reiniciar somente o gateway do agente afetado via restart seguro/detached.

Exemplo validado: para Ares responder a mentions em threads agente legado, `allowed_channels` do Ares deve incluir `1508853425952133180,1513005743954198538`, mas `free_response_channels` deve continuar apenas `1508853425952133180`.

Regra prática:
1. Identificar o escopo ativo da thread antes de mencionar arquivos fora dele.
2. Se um arquivo modificado for de outro agente/área, só reportar se ele bloquear a ação atual.
3. Caso o usuário corrija o escopo, incorporar imediatamente e manter os reports seguintes restritos ao escopo correto.

