# Discord Threads — Ciclo de Vida e Gestão de Tokens

Referência validada em conversa com Rodolfo — 2026-05-14.

## Ciclo de vida de uma thread

| Fase | O que acontece |
|---|---|
| **Criação** | Hermes auto-cria uma thread no canal-pai quando chega mensagem DM |
| **Ativa** | Enquanto houver mensagens recentes, fica visível na lista de threads |
| **Arquivada** | Após X horas de inatividade, some da lista mas permanece no histórico |
| **Deletada** | NÃO ocorre automaticamente — permanece indefinidamente a menos que deletada via API/manualmente |

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
