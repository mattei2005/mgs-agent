# Regras genéricas de decisão de campanha

Esta referência não contém thresholds, budgets ou horários globais. Cada operação declara seus parâmetros no arquivo vivo de `data/ares/meta-ads/operations/` e na skill específica da estratégia.

## Ordem de decisão

1. Validar conta, timezone, moeda, estratégia e período.
2. Ler status e métricas reais da Meta.
3. Ler receita/ROI externo somente quando a operação tiver fonte e join key aprovados.
4. Aplicar learning, carência, hold, bid strategy e proveniência do contrato.
5. Produzir `nenhuma ação`, recomendação dry-run ou write autorizado.
6. Confirmar qualquer write por GET e registrar before/after.

## Regras invariantes

- Não misturar métricas ou thresholds entre países, sites ou estratégias.
- Não usar regra de tráfego direto em BOT/Messenger sem revisão explícita de compatibilidade.
- Não converter evidência histórica em regra ativa.
- Replacement/clone começa pela linhagem da source real e pela conciliação Meta × Drive.
- Budget e ativação seguem gates próprios.
- IDs técnicos ficam no audit; relatório usa alias e nome operacional.

## Calibração

Nova operação começa em `read_only/dry_run`. Comparar recomendações da API com a conferência manual do gestor durante a janela definida no contrato. Só depois promover thresholds e eventual autonomia por decisão explícita.
