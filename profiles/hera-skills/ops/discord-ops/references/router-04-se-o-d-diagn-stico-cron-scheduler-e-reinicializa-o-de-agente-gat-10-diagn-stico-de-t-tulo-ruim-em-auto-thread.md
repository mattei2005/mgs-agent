### Diagnóstico de título ruim em auto-thread

Quando Rodolfo perguntar por que uma thread não foi renomeada, ou por que o título ficou genérico/truncado, não assumir erro de Discord/permissão. Ver `references/discord-auto-thread-title-diagnostics.md`.

Resumo operacional:
- O título inicial da thread Discord é escolhido pelo gateway no momento de criação (`_auto_create_thread` / `_auto_thread_name_from_message`), antes da resposta do agente.
- Logs de `Auxiliary title_generation` depois da resposta são o título GPT-style interno de sessão Hermes. Se esse título não estiver conectado a um callback de rename Discord, a UI do Discord continuará mostrando fallback/truncamento.
- Validar via Discord API o `name` atual da thread e comparar com a primeira mensagem/inbound log.
- Se só alguns assuntos parecem inteligentes, provavelmente `_auto_thread_name_from_message(...)` está cobrindo apenas regras hardcoded e o fallback está usando os primeiros termos limpos da mensagem.
- Padrão MGS esperado por Rodolfo: igual ChatGPT — toda thread deve receber título semântico pelo assunto real do primeiro prompt, não só famílias pré-programadas.
- Correção preferida: arquitetura híbrida. Manter regras class-level rápidas no `_auto_thread_name_from_message(...)`, mas conectar o `agent/title_generator.py` pós-primeira resposta a um callback Discord que renomeia a thread com o título GPT-style, sem sobrescrever título manual específico.
- Playbook detalhado: `references/discord-gpt-style-thread-title-rename.md`.

