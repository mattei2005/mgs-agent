## Referências operacionais

- `references/legacy-agent-natural-gpt-grok-backend-routing-2026-06-16.md` — padrão de Creative Ops para agente legado aceitar pedidos naturais de backend (“com GPT”, “com Grok”, “os dois”, “avatar/vídeo”), mantendo agente legado como dona de criativos e tratando GPT/OpenAI-Codex e Grok/xAI como ferramentas, não como agentes separados.
- `references/legacy-agent-ares-creative-taxonomy-sync-2026-06-07.md` — sincronização agente legado/Ares quando a taxonomia, Drive e Canva forem definidos em thread do Ares: agente legado deve herdar a taxonomia CC_US_ES, `MGS-AGENTS/CRIATIVOS`, `UPLOAD CANVAS`, `P_ORIENT` PV/NV/PS/NS, inventário e gate de plano aprovado antes de renomear/mover criativos.
- `references/creative-metadata-sanitizer-legacy-agent-ares-2026-06-08.md` — implementação do gate server-side de limpeza de metadados para criativos agente legado/Ares: usar ExifTool/mat2 via wrapper MGS, validar com PNG malicioso `PNG:Comment`, atualizar context/SOUL/docs, auditar e reportar infra.
- `references/legacy-agent-creative-agent-bootstrap-ptbr.md` — padrão capturado na criação da agente legado: sequência segura de bootstrap de agente MGS, padronização PT-BR para SOUL/docs/skills/templates e regra de anexar arquivos longos como `MEDIA:/path`.
- `references/company-os-phase3-inventory-phase4-company-2026-06-07.md` — padrão capturado na execução da Fase 3/Fase 4: inventário como mapa de risco, como explicar a revisão para Rodolfo, cobertura mínima do inventário v0.2 e padrão de primeiro bloco `context/company.md`.
- `references/company-os-phase4-context-continuity-crons-2026-06-07.md` — padrão capturado na Fase 4 sequencial: continuidade de contexto em thread longa, “ok continue” como avanço de bloco, revisão de `docs/CRONS.md` sem alterar runtime/crontab, e correções de metadados via `cron-control-plane.py`.
- `references/company-os-thread-continuity-2026-06-07.md` — pitfall de continuidade em threads longas de reestruturação: replies curtos herdam o bloco anterior, thread aberta não deve ser renomeada enquanto mantiver o objetivo, e o report deve continuar no formato executivo por fase/bloco.
- `references/company-os-thread-context-pitfall-2026-06-07.md` — correção de contexto em threads longas: thread de reestruturação mantém objetivo/nome até finalização, replies curtos herdam o bloco/fase citado, e `Ok`/`vamos continuar` não são novo assunto.
- `references/company-os-thread-title-language-pitfall-2026-06-07.md` — correção específica de título/idioma em thread longa: não renomear thread ativa por reply curto e nunca traduzir título PT-BR para espanhol/inglês por heurística genérica.

## Verification Checklist

Before reporting completion of a company-OS step:

- The deliverable exists at the declared path.
- It is clearly marked proposal/canonical as appropriate.
- No runtime file was changed unless explicitly approved.
- Sensitive sources of truth were not modified accidentally.
- Cross-file semantic consistency was checked against already-reviewed Company OS docs after any material Rodolfo correction.
- Next step is concrete and low-risk.

