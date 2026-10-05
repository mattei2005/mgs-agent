# Reinício pontual de D1 — conta CPV13

Use quando Rodolfo autorizar reativação de campanhas existentes com retorno ao D1 operacional. Isso não é reset técnico do aprendizado Meta.

- Resolver IDs imutáveis pela operação e confirmar por API conta, moeda, fuso, estado da campanha e filhos ACTIVE. Não criar/duplicar campanha para simular o reinício.
- Em conjuntos cujo início já passou, não tentar reescrever start_time. Manter o pai PAUSED e agendar uma única ativação campaign-level pelo horário explícito do pedido.
- Budget explícito usa POST absoluto único e GET. Congelar nome, budget, updated_time e hierarquia no request para impedir ativação sobre drift posterior.
- A data do nome e cycle_start_date apontam ao novo D1; preservar wrapper UTM, IDs, criativos e copy. Antes do início, a data futura representa PREP.
- Superseder o ciclo anterior preservando snapshot/audit. Ao construir cycle_history, excluir cycle_history do snapshot interno: copiar o registro depois de anexar a própria lista pode produzir referência circular e falhar na serialização JSON.
- Arquivar o registro de performance-guardrails anterior e iniciar histórico matinal vazio e contador pós-escala zero para o novo ciclo. Não carregar checkpoints D1/D2 antigos na decisão D3 nova: o gate legado agrega por cycle_day e pode misturar ciclos se os mapas antigos permanecerem ativos.
- Não rearmar first-delivery para uma campanha existente já liberada. Não retomar outros crons pausados como efeito lateral.
- O one-shot determinístico utiliza lock exclusivo da lane da conta, estado in_flight com fsync, GET antes de recovery, readback final e checkpoint institucional. Agendamento exige inventário global, readback e REPORT-INFRA.
- Testar antes de agendar: idempotência da supersessão, ausência de JSON circular, preservação do histórico, reset dos guardrails e bloqueio de ativação antecipada. Dry-run live não altera Meta.
