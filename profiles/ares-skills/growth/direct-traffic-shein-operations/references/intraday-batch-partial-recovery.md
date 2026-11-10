# Intraday: retomada parcial de lote

- Isole a conta cujo render falhou e entregue os bindings independentes já validados. Preserve o universo original e as pendências nominais; sucesso do subconjunto não significa conclusão global.
- Teste a identidade compacta completa contra a largura efetiva do renderer: número literal + lance abreviado + origem COPY + quiz, inclusive `n/d`, podem exceder Nº mesmo quando cada componente é válido. Preserve todos os componentes; não invente quiz, trunque identidade nem amplie uma coluna fora da autorização vigente. Registre as células excedentes no audit, peça somente a decisão visual necessária e retome o mesmo modelo, sem recoleta financeira ou reenvio das contas concluídas.
- Reconcile pares conta/thread esperados, integrais GET_VERIFIED, complementos ativos, message IDs únicos e ordem posterior dos complementos. Separe pendência de apresentação de falta de grant remoto; nenhuma autoriza troca de token ou permissão.
- Quando message ID for o próprio ID da thread, GET404 no endpoint de mensagens da thread pode indicar que a mensagem inicial está no pai. Consulte o mesmo ID no pai real e confirme autor, conteúdo, canal e thread.parent_id. Não dispense autenticação nem procure outra mensagem semelhante.

## Verificações de regressão

- Identidade compacta excedente deve ser rejeitada pelo renderer normal, sem truncamento ou alteração de largura implícita.
- Autenticação deve distinguir mensagem inicial no pai de resposta na thread, preservando o ID e conferindo autor e conteúdo exatos.
- Falha de apresentação em uma conta não deve interromper bindings independentes; reconcilie os pares entregues e pendentes, além dos complementos ativos.
- Nova rodada deve usar fontes e nonces próprios; replay do mesmo request deve reconciliar intents e GETs sem duplicar mensagens.
