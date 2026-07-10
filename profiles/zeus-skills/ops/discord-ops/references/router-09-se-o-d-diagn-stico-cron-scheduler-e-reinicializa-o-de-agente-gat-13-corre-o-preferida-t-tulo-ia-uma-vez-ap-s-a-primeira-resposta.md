### Correção preferida: título IA uma vez após a primeira resposta

Quando Rodolfo pedir para corrigir thread title “burro”/regex/hardcoded no Discord, não mexer em `_auto_thread_name_from_message(...)` como solução primária. Ela deve continuar gerando o nome provisório porque Discord cria a thread antes da resposta. A correção correta é no `gateway/run.py`: conectar o `title_callback` do Discord ao `maybe_auto_title(...)` pós-primeira resposta, mas proteger o rename com `_discord_thread_safe_to_autorename(...)`.

Guardrails mínimos:
- `maybe_auto_title(...)` já só tenta título nas primeiras trocas; manter esse filtro.
- A thread Discord deve ser nova (`channel.created_at` dentro de janela curta, ex. 30 min), bloqueando follow-up depois de idle/reset.
- O nome atual da thread deve ainda ser o provisório calculado por `adapter._auto_thread_name_from_message(primeira_mensagem_acionável)`, sanitizado via `_sanitize_discord_thread_title(...)`; se divergir, assumir rename manual/IA anterior e não editar.
- A validação deve rodar imediatamente antes de `channel.edit(...)`, porque o auto-title roda em background thread e agenda coroutine async.

Resumo operacional:
- O título inicial da thread Discord é escolhido pelo gateway no momento de criação (`_auto_create_thread` / `_auto_thread_name_from_message`), antes da resposta do agente.
- Logs de `Auxiliary title_generation` depois da resposta são o título GPT-style interno de sessão Hermes. Se esse título não estiver conectado a um callback de rename Discord, a UI do Discord continuará mostrando fallback/truncamento.
- Validar via Discord API o `name` atual da thread e comparar com a primeira mensagem/inbound log.
- Se só alguns assuntos parecem inteligentes, provavelmente `_auto_thread_name_from_message(...)` está cobrindo apenas regras hardcoded e o fallback está usando os primeiros termos limpos da mensagem.
- Padrão MGS esperado por Rodolfo: igual ChatGPT — toda thread deve receber título semântico pelo assunto real do primeiro prompt, não só famílias pré-programadas.
- Correção preferida: arquitetura híbrida. Manter regras class-level rápidas no `_auto_thread_name_from_message(...)`, mas conectar o `agent/title_generator.py` pós-primeira resposta a um callback Discord que renomeia a thread com o título GPT-style, sem sobrescrever título manual específico.
- Playbook detalhado: `references/discord-gpt-style-thread-title-rename.md`.

