A estratégia reutilizável agora vive em `chatpion-bot-campaign-operations`; esta operação passou a ser um consumidor com contrato próprio.

**Valores vigentes desta operação**
- Threshold Fases 1/2: `0,36`; abaixo corta, exatamente `0,36` mantém.
- Fase 3: mínimo `0,38`, sem alteração.
- Horários e crons: sem alteração nesta migração.
- Budgets, Pages, JSON, holds, authority e demais exceções continuam exclusivos deste contrato.

**Regra de manutenção**
- Mudança da família atualiza todos os consumidores ativos.
- Mudança específica desta operação atualiza somente sua rota funcional e Regras.
- A mensagem de projeção do Ares é editada e validada por GET nas próximas mudanças; histórico humano e eventos do Discord permanecem preservados.

O valor antigo `0,40` nos blocos históricos está supersedido pela decisão de `0,36` originada na thread `1544770844381679666`.