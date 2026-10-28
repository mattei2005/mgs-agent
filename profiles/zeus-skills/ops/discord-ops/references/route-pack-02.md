### Transporte literal de mensagens Discord

Construa mensagens com Markdown e valores monetários como payload JSON literal em arquivo de trabalho ou em um programa Python, e entregue o JSON ao transporte por stdin com `subprocess.run(..., shell=False)`. Nunca coloque o texto da mensagem dentro de um `python -c` envolvido por aspas duplas no shell: backticks podem virar substituição de comandos e `$45` pode ser expandido, removendo nomes, parâmetros e valores antes do POST. Antes de enviar, valide comprimento e allowlist de mentions. Se o POST já tiver publicado conteúdo corrompido, não faça uma segunda cópia nem apague o histórico: edite a própria mensagem por ID e confirme igualdade exata do conteúdo via GET antes de declarar entrega concluída.

### Mentions cross-agent em canal de outro agente

**Destinatário antes do handoff:** em thread compartilhada, uma continuação sem mention pode continuar dirigida ao agente executor da conversa. Não interpretar o simples recebimento pelo Zeus, nem “quando terminar, informa na thread”, como autorização para Zeus intervir ou encaminhar. Exigir pedido novo inequivocamente dirigido ao Zeus para coordenação/handoff; caso contrário, não publicar mensagens adicionais nem mencionar o executor.

Quando Rodolfo disser que marcou um agente dentro da thread/canal de outro agente e esperava resposta (ex.: Ares marcado em thread da agente legado), tratar como roteamento de gateway, não como falha do modelo. O agente marcado só receberá o evento se o canal pai/thread estiver em `discord.allowed_channels` efetivo dele; `thread_require_mention=true` sozinho não basta.

**Mensagens enviadas por outro bot/agente:** quando `DISCORD_ALLOW_BOTS=mentions`, uma mensagem de Zeus/agente legado/Ares/Atena sem mention direta do agente destinatário pode aparecer normalmente no Discord, mas será ignorada pelo gateway desse agente. Toda instrução cross-agent enviada por bot deve começar com `<@BOT_ID_DESTINATÁRIO>`, inclusive em thread já aberta. Depois do envio, validar em duas etapas: (1) readback confirma a mensagem e a mention no thread ID correto; (2) uma nova mensagem/atividade do agente destinatário confirma que ele acordou. Não interpretar apenas “mensagem enviada com sucesso” como handoff concluído. Se a primeira orientação saiu sem mention, reenviar de forma consolidada com mention — não depender de o agente reler histórico silenciosamente.

Para criar uma sessão nova de Atena/Ares exclusivamente para provar carregamento de política após restart/deploy, siga `references/cross-agent-session-policy-cutover.md`: thread nova, mention direta, turno sem ferramentas/produção, readback de `state.db.system_prompt` por thread ID e fechamento por evento de revalidação distinto — nunca reescrevendo um finalizer falho.

Caso inverso validado: se Rodolfo disser que qualquer mensagem sem mention acorda os dois agentes na thread de um deles, auditar o agente visitante. O canal externo pode estar em `allowed_channels` com `thread_require_mention=false` no YAML ou no `.env` efetivo. Corrigir para `thread_require_mention=true` e validar `/proc/<pid>/environ`, não apenas o arquivo. Detalhe: `references/discord-cross-agent-thread-reply-scope-2026-06-20.md`.

**Não transformar readback técnico em tarefa humana:** em um handoff cross-agent, a instrução deve conter gates objetivos e dizer explicitamente quando o agente pode continuar sem Rodolfo. Se status/report já confirmar página correta, rota correta e `authenticatedLikely=true`, não pedir que ele abra noVNC, dê F5, faça scroll ou responda “pronto” apenas para validar o que a máquina já provou. Intervenção humana fica restrita a login, MFA/2FA, CAPTCHA/challenge visível ou lacuna real de autenticação/cards. Quando Rodolfo tiver marcado “confiar neste dispositivo”, cookies e perfil viram estado crítico: manter a mesma rota de rede, impedir instâncias concorrentes, fazer shutdown limpo e criar snapshot seguro com lock liberado antes de nova operação. O orquestrador deve corrigir imediatamente o agente executor e liberar a continuidade automática quando os gates passarem.

### Canal novo de relatórios: diagnóstico e habilitação

1. Resolver o ID fornecido com `discord_admin.channel_info` e ler as mensagens recentes com `discord.fetch_messages`. Separar canal de entrega, thread de origem e pai da thread; o contexto atual não substitui o alvo explícito.
2. Ler o canal e seu histórico com a identidade de cada bot envolvido antes de propor overwrites. GET bem-sucedido prova acesso de leitura, não envio nem admissão de eventos pelo gateway. Se as permissões já bastam, corrigir apenas o roteamento.
3. Comparar `allowed_channels`, `free_response_channels`, `require_mention`, `thread_require_mention`, `no_thread_channels` e overrides equivalentes no profile, espelho e env. Um agente já coberto por `allowed_channels: '*'` e destinado a responder por menção não precisa de alteração nem restart.
4. Para o executor responder a mensagens comuns no canal dedicado, acrescentar somente o alvo a `allowed_channels` e `free_response_channels`. Não inferir entrega inline a partir de resposta sem menção: preservar o padrão auto-thread dos canais operacionais, salvo pedido explícito em contrário. Somente se a entrega inline tiver sido solicitada, acrescentar o alvo a `no_thread_channels` explicitamente: patches locais podem manter auto-thread mesmo em canais de resposta livre. Preservar as entradas existentes e manter o agente visitante por menção.
5. Registrar a finalidade em rota canônica e, quando necessário, no prompt do canal. Definir destino de relatórios não autoriza criar relatórios agora, alterar campanhas, budgets, crons ou usuários. Validar YAML e espelho e ativar somente o agente alterado pelo fluxo em `references/gateway-restart-coordination.md`.
6. Fazer um canário de comunicação com mention direta ao executor, solicitando uma frase no canal exato, sem ferramentas ou produção. Ler de volta o envio e a resposta do bot. Para comprovar resposta livre, aproveitar uma mensagem humana nova sem menção e sua resposta; não se passar pelo usuário nem tratar canário de bot marcado como prova desse segundo gate. Se não houver mensagem humana, declarar essa cobertura como não observada, sem pedir teste humano como condição para fechar os gates técnicos já verificáveis.
7. Fechar com destino, quem responde sem menção, quem responde por menção e evidência observada. Registrar inventário/audit e REPORT-INFRA com readback, sem outra cópia textual do report.

### Challenges por IP de datacenter em fluxos Ares/agente legado

Quando Rodolfo suspeitar que Hetzner/VPS/datacenter IP está causando bloqueio em YouTube/agente legado ou Meta/Ares, não responder de memória nem propor migração de VPS como primeira ação. Importar a thread afetada em modo read-only, separar `browser consumer anti-bot` de `Marketing API endpoint trust`, e usar o teste de isolamento: mesma conta/token/payload/script, mudando apenas a origem de rede via proxy residencial/AdsPower. Para o playbook completo, ver `references/datacenter-ip-browser-api-challenge-diagnostics-2026-06-18.md`.

Padrão seguro para habilitar cross-agent por mention:
- Adicionar o canal do outro agente em `allowed_channels` do agente chamado.
- Manter `free_response_channels` restrito ao canal próprio do agente para evitar resposta livre fora da área dele.
- Manter `require_mention=true` e `thread_require_mention=true`, de modo que ele só acorde no canal externo com mention direta.
- Inspecionar e reconciliar os três lugares quando existirem: config ativa (`/root/.hermes/profiles/<agent>/config.yaml`), config versionada (`/root/mgs-agent/profiles/<agent>-config.yaml`) e `.env` ativo se ele define gates Discord. Confirmar a precedência no resolver/adapter instalado; não presumir que uma regra universal de env versus YAML cobre todos os gates e versões. Preservar fontes já coerentes, sem criar overrides redundantes.
- Ao patchar `.env`, preservar linhas operacionais não relacionadas (`DISCORD_HOME_CHANNEL`, `DISCORD_ALLOW_BOTS`, `BROWSER_DISABLE_SCREENSHOTS`, etc.) e evitar deixar chaves duplicadas; validar exibindo só chaves não secretas/valores sanitizados.
- Registrar audit log, deixar auto-commit/versionamento capturar o config versionado e reiniciar somente o gateway do agente afetado via restart seguro/detached.

Exemplo validado: para Ares responder a mentions em threads agente legado, `allowed_channels` do Ares deve incluir `1508853425952133180,1513005743954198538`, mas `free_response_channels` deve continuar apenas `1508853425952133180`.

Regra prática:
1. Identificar o escopo ativo da thread antes de mencionar arquivos fora dele.
2. Se um arquivo modificado for de outro agente/área, só reportar se ele bloquear a ação atual.
3. Caso o usuário corrija o escopo, incorporar imediatamente e manter os reports seguintes restritos ao escopo correto.

