### Mentions cross-agent em canal de outro agente

Quando Rodolfo disser que marcou um agente dentro da thread/canal de outro agente e esperava resposta (ex.: Ares marcado em thread da Hera), tratar como roteamento de gateway, não como falha do modelo. O agente marcado só receberá o evento se o canal pai/thread estiver em `discord.allowed_channels` efetivo dele; `thread_require_mention=true` sozinho não basta.

Caso inverso validado: se Rodolfo disser que qualquer mensagem sem mention acorda os dois agentes na thread de um deles, auditar o agente visitante. O canal externo pode estar em `allowed_channels` com `thread_require_mention=false` no YAML ou no `.env` efetivo. Corrigir para `thread_require_mention=true` e validar `/proc/<pid>/environ`, não apenas o arquivo. Detalhe: `references/discord-cross-agent-thread-reply-scope-2026-06-20.md`.

