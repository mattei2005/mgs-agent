# Discord Threads — Ciclo de Vida e Gestão de Tokens

Referência validada em conversa com Rodolfo — 2026-05-14.

## Ciclo de vida de uma thread

| Fase | O que acontece |
|---|---|
| **Criação** | Hermes auto-cria uma thread no canal-pai quando chega mensagem DM |
| **Ativa** | Enquanto houver mensagens recentes, fica visível na lista de threads |
| **Arquivada** | Após X horas de inatividade, some da lista mas permanece no histórico |
| **Deletada** | NÃO ocorre automaticamente — permanece indefinidamente a menos que deletada via API/manualmente |

## Encerramento explícito com histórico preservado

Use quando um participante autorizado pedir para finalizar a thread atual; não rode o arquivador em lote de threads antigas para atender a um único alvo.

1. Leia `GET /channels/{thread_id}` e `GET /channels/{thread_id}/messages/{request_message_id}`. Confira autor real, `parent_id`, guild e escopo vigente; o nome de exibição não substitui identidade.
2. Use o transporte canônico do perfil responsável. Se a ferramenta disponível não expuser arquivamento, reutilize o carregador de credencial e os headers do helper `/root/mgs-agent/scripts/discord-bot-post.py` para chamadas REST em memória; não imprima token nem amplie permissões.
3. Envie `POST /channels/{thread_id}/messages` com confirmação breve, `allowed_mentions: {"parse": []}` e referência à mensagem do pedido. Leia `GET /channels/{thread_id}/messages/{sent_message_id}` e confira o conteúdo exato. Evite afirmar que já está arquivada antes do PATCH.
4. Faça `PATCH /channels/{thread_id}` com apenas `{"archived": true}`. Preserve título, `locked`, membros e duração de autoarchive.
5. Faça `GET /channels/{thread_id}` e exija `thread_metadata.archived == true`. Se houver erro ou timeout, releia o alvo antes de repetir a escrita; não reenvie automaticamente a confirmação já entregue.
6. Termine sem outra mensagem pública: uma resposta automática posterior pode reabrir a thread. Se o transporte exigir uma resposta final, resolva essa entrega antes do arquivamento; não declare o estado final com base em um GET anterior a uma nova publicação.

Arquivar preserva o histórico. Não use DELETE nem bloqueio de thread como substitutos de encerramento.

## Auto-archive time configurável

- 1 hora, 24 horas (padrão MGS), 3 dias, 1 semana
- Canal `#zeus-admin-agent`: **24 horas** (configuração atual)

## Impacto em tokens

- **Thread arquivada parada** → **zero tokens**. O Hermes não lê nem processa nada dela.
- **Tokens só são consumidos quando uma mensagem nova chega na thread** — aí o histórico da thread é carregado no contexto.
- Threads antigas no histórico: custo zero, disponíveis para consulta.

## Memória cross-session (importante)

Por padrão, threads novas começam **sem acesso ao histórico de threads antigas**.

Dois mecanismos preservam contexto entre sessões:

| Mecanismo | Como funciona | Quando ativa |
|---|---|---|
| **Memory** | Fatos salvos explicitamente pelo agente | Injetado automático em TODA sessão nova |
| **Session Search** | Busca em transcrições passadas | Requer acionamento explícito |

Fatos importantes → salvos na memory → aparecem automaticamente.
Detalhes técnicos, rascunhos, conversas exploratórias → ficam no histórico, acessíveis via busca.

## Recomendação operacional MGS

- Archive em 24h: ideal para conversas de admin (curtas e conclusivas)
- Não deletar threads: histórico é valioso para auditoria, custo é zero
- Summarization automática do Hermes: controla crescimento de tokens em threads longas
- Cada nova sessão = nova thread = sem arrastar contexto de conversas antigas

## Configuração atual do canal Zeus

- Canal: `#zeus-admin-agent` (1496267442899521627)
- Auto-archive: 24 horas
- Deleção automática: desabilitada (histórico preservado)
