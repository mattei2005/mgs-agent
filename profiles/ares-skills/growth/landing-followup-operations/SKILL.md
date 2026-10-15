---
name: landing-followup-operations
description: "Use when observing landing ads after campaign completion."
version: 0.2.0
author: Rodolfo Mattei / Ares
license: internal
platforms: [linux]
metadata:
  hermes:
    tags: [mgs, growth, landing, pc1, recovery, queue]
    related_skills: [computer-use, direct-traffic-cbo-operations]
---

# Acompanhamento de landing — operação autônoma

Procedimento exclusivo do processo independente que observa anúncios depois de uma criação/duplicação já concluída e respondida. Não é campaign writer, não cria campanhas e não acrescenta etapa ao pedido do gestor.

## When to Use

- Observar landing com UTMs novas depois da resposta de conclusão.
- Recuperar visita, fechamento, captura, timeout, fila ou transporte do acompanhamento.
- Consultar pendências e validar os avisos de sucesso.
- Não carregar na rota de criação/clone: ela permanece totalmente independente.

## Autoridade e fontes

- Contrato executivo único: `/root/mgs-agent/data/ares/meta-ads/policies/direct-traffic-landing-followup.json`.
- Estado real: SQLite próprio em `data/ares/meta-ads/landing-followup/queue.sqlite3`; eventos, provas e outbox ficam nessa operação.
- Ares é dono de CADA tarefa até validação completa e aviso do gestor conferido. Silêncio, `READY`, timer ativo, correção instalada ou teste offline não são conclusão.
- Rodolfo determinou recuperação autônoma: **bloqueio recuperável também é trabalho do Ares**, não motivo para abandonar a fila nem aguardar outra mensagem/autorização já existente.
- Avisar na thread de problemas quando houver ação humana concreta indispensável **ou no relatório final dos links ainda sem anúncio após a regra 3+1, expressamente solicitado por Rodolfo para revisão**. Essa exceção não autoriza alertas por timeout, falha de ferramenta, screenshot ou reconciliação, nem avisos prematuros durante as tentativas.
- Prioridades explícitas de uma rodada vivem em `current_priority` do contrato, com o conjunto de pedidos congelado no momento da instrução. Uma URL com fechamento comprovado pode ficar para o fim sem abandonar a task; só readback/cleanup indispensável de aba incerta precede os demais. Não interromper um fechamento ativo. Após os pares estarem observados, não esperar a confirmação coletiva que depende da própria URL adiada: isso criaria deadlock. Novos pedidos posteriores não adiam indefinidamente o retorno.
- Uma instrução posterior expressa pode substituir a prioridade temporária: persistir a supersessão e usar `C121_FIRST_THEN_FIFO` para nova rodada imediata autorizada, uma vez por mensagem, depois do cleanup indispensável e sem interromper observador vivo. Selecionar a C121 antes de outros READY; após seu resultado, retomar FIFO e atualizar também os informes para não repetir a ordem antiga. Testar seleção, histórico, retomada FIFO e texto de progresso.
- Credenciais, billing, restart e Critical Subset preservam seus gates. Não modificar Router, financeiro, WordPress, GAM, campanha, budget, estratégia ou início neste fluxo. Nunca clicar em anúncio.

## Dependências mínimas

Carregar `computer-use` para interação visual. Usar o transporte PC1 já configurado, sob a lease cross-agent. Para convenções adicionais de acesso, consultar somente a referência PC1 de `adspower-segurador-token-collector`; esta tarefa usa Chrome comum, nunca perfil AdsPower/Facebook. Comandos e branches ficam em `references/runtime-and-recovery.md`.

## Fluxo normal — uma URL por execução

1. Ler o job e o contrato. Exigir conclusão e resposta original entregues/readback; reutilizar a prova final salva. Nunca consultar/criar campanha para descobrir destino.
2. Confirmar fila única global e lease física livre. Uma tarefa por vez, todos os gestores. Prioridade das criações nos demais canais preservada; a conversa dedicada de controle/status não bloqueia o próprio acompanhante.
3. Resolver a landing real por configuração ativa ou prova canônica. Não abrir quiz nem inventar slug. Validar domínio antes de guardar/abrir. Preservar a query efetiva byte a byte, inclusive todos os parâmetros e UTMs novos. Quando MGS Direct Quiz for a fonte, conferir o item ativo exato de país/slug e seus destinos A/B, por WP-CLI read-only com plugins/temas pulados; destinos distintos precisam de cobertura própria.
4. Persistir `begin` ANTES da navegação. Abrir aba NOVA em janela técnica própria, com guarda vazia se necessário. Não tocar em abas alheias. Depois de entrada ambígua, recapturar antes de qualquer retry. Seguir a escalação background → foreground somente após sinal real do driver.
5. Confirmar anúncio da rede realmente renderizado e a aba ativa no desktop compositado. Iframe vazio, script carregado, HTTP200 e CTA editorial não são anúncio. Não alterar proxy, cookies, bloqueador, fingerprint ou proteção contra automação.
6. Confirmar primeiro anúncio e foco reais. Preferir `ares-direct-traffic-ui.py` para agrupar abertura/readbacks nativos em uma chamada, depois usar o coletor em uma chamada. Com prova `desktop-open.json` da mesma abertura e exclusividade revisada, habilitar `--close-owned-window --exclusive-window-reviewed`: após série completa o próprio coletor fecha e confere a janela técnica, sem novos turnos de LLM entre captura e fechamento. Esse fechamento não aprova anúncio nem dispensa revisar todos os frames antes de PASS. Sem prova compatível ou em recovery, não habilitar o fechamento automático. Os comandos e gates ficam na referência. Revisar imagens/descrições e foco; só amostras reais cobrindo pelo menos 10 segundos contínuos, com cadência válida, podem sustentar PASS. Se a cadência falhar, corrigir/recapturar na mesma aba, não reabrir a página.
7. Obtida uma série com cadência completa (`CAPTURED_NOT_PASS`), fechar prontamente apenas a aba da tentativa e conferir desaparecimento/preservação antes de demorar em revisão offline ou redação. Revisar todos os frames salvos em chamadas independentes paralelas antes de aceitar PASS; o fechamento não prova anúncio/foco. Se a cadência falhar, corrigir/recapturar na mesma aba antes de fechar. Evitar capturas redundantes sem dúvida real e agrupar leituras; os 10 segundos são mínimo visível, não espera por ferramenta. Medir separadamente preparação, abertura, série, fechamento e persistência; não prometer ciclo total de 10s nem alegar ganho sem medição real. Fechar guarda/janela somente com propriedade exclusiva comprovada. Persistir `result`, então liberar a lease em finally. Reservar chamadas finais para isso; não terminar apenas com texto dizendo que faltou registrar.
8. Regra vigente de Rodolfo: **até 3 tentativas iniciais com ausência real de anúncio** por combinação landing + UTMs. Registrar `NO_AD`, fechar/verificar e aguardar 60 segundos completos entre tentativas; falha técnica não conta como ausência. Na terceira ausência, marcar `DEFERRED_NO_AD`, pular para os próximos links e continuar a fila, sem reconferir indefinidamente abas já fechadas. Depois de processar todos os links da fase inicial, fazer **1 tentativa final por pendente**, uma execução por vez. Se passar, aplicar o validador completo; se continuar sem anúncio, marcar `REVIEW_REQUIRED` e, ao encerrar a rodada final, reportar nesta thread os links com problema para Rodolfo revisar, via outbox e GET. Sem nova repetição automática após o relatório. Preservar tentativas já feitas: itens com duas ausências recebem somente a terceira inicial, não três novas. Nunca reabrir `PASSED`. Essa regra supersede expressamente o limite antigo de duas ausências e a recuperação repetitiva; histórico preservado no contrato/audit.
9. Somente TODAS as combinações do pedido HUMANO liberam o sucesso exato do contrato na thread original. Uma resposta nativa pode conter vários jobs técnicos: agrupar pelo recibo original, exigir enumeração do intake concluída e todos os pares validados, e enviar uma única confirmação. Conferir entrega por GET. Não afirmar registro GAM sem prova própria. Não enviar prints sem pedido explícito.

## Recuperação — não abandonar estados excepcionais

- `NEEDS_RECONCILIATION` e aba incerta exigem `RECONCILING` para cleanup seguro antes de outra navegação. Ausência já registrada com fechamento válido não é cleanup infinito: o scheduler aplica a política finita 3+1. `DEFERRED_NO_AD` aguarda a fase final; `REVIEW_REQUIRED` aguarda somente o relatório/revisão humana, sem novos claims automáticos. Erro técnico continua sob recuperação de Ares e nunca vira `NO_AD` por conveniência.
- No recovery, não abrir URL nem repetir input incerto. Ler a tentativa mais recente do mesmo job e conferir estado real antes de fechar/repetir algo. Fechamento de tentativa antiga não prova o da última. A preservação das abas é comprovada pelos readbacks antes/depois daquela operação; mudanças posteriores feitas pelo usuário não invalidam o fechamento já provado nem autorizam restaurar/fechar janelas dele. No readback atual, conferir a ausência do alvo técnico exato e não tocar em outras janelas.
- Com fechamento/preservação reais comprovados, `reconcile --resume` devolve a mesma URL à fila com espera, nunca a PASSED. Sem qualquer navegação, exigir leitura da sessão provando zero inputs, mais diagnóstico. Não inventar aba/fechamento para satisfazer validador.
- Recuperação de `ATTENTION` com fechamento real de todas as abas afetadas não pode monopolizar a fila enquanto houver observações `READY` devidas: selecionar os próximos links e manter o diagnóstico pendente, sem promover ausência a PASS nem reabrir a mesma URL. Validar cada fechamento antes de aplicar essa prioridade; `OPEN_INTENT`, prova ausente/inválida e `NEEDS_RECONCILIATION` preservam prioridade de cleanup. Testar regressões de starvation, prova antiga, aba incerta e retorno posterior ao diagnóstico.
- Processo expirado vira recuperação com backoff; processo vivo/lease de outro trabalho nunca é contornado. Reserva órfã só pode ser liberada após provar identidade do observador Ares, vínculo ao mesmo job e ausência de processo vivo. Dúvida falha fechado e continua sob diagnóstico do Ares.
- Se uma prova COMPLETA da última tentativa já existe, revisá-la e usar `result --result PASS|NO_AD --recovered` sob a lease de recuperação. PASS exige o mesmo validador de anúncio/foco/10s; NO_AD exige screenshot real de ausência e revisão explícita. Ambos rejeitam imagens anteriores à última abertura e exigem fechamento posterior. Isso não abre outra página. Uma prova parcial/incerta não pode virar PASS; nesse caso, reconciliar o fechamento e só então retomar. Não gerar impressões adicionais para substituir um resultado já confirmado.
- Se o bloqueio for defeito do próprio observador/coletor, corrigir a camada local da operação com backup, teste e readback, fora de qualquer transação de criação. Registrar inventário/REPORT e retomar o mesmo request. Não tratar código quebrado, estado inconsistente ou skill confusa como responsabilidade de Rodolfo; não ampliar a correção para framework, gateways, billing, credenciais ou sistemas críticos sem o gate próprio.
- Se PC1 estiver indisponível/ocupado, registrar defer/backoff e manter retomada automática, sem alerta genérico. Não reiniciar gateway, PC ou navegador por conta própria.
- `need-action` é exclusivo para intervenção humana comprovadamente indispensável; o outbox exige flag explícita e ação concreta. Aba incerta mantém bloqueio físico/global até reconciliação.

## Verificação e comunicação

- Conferir invariantes de fonte, origem, request/conta, query exata, identidade da aba, anúncio, foco, tempo, fechamento e outbox; não concluir pelo processo retornar zero.
- Em status solicitado, separar execução real, recuperação aguardando, fila, links individualmente validados e pedido integralmente concluído. Usar dados atuais e contar/agrupar em código.
- Detalhes técnicos e erros recuperáveis ficam em audit local. Não narrar cada retry a Rodolfo; só contato necessário à ação dele. Quando Rodolfo solicitar atualizações de progresso, isso autoriza os status expressamente configurados em `progress_reporting`: usar outbox durável e GET, respeitar intervalo/marcos e encerrar os informes quando a rodada terminar. Essa exceção de progresso não libera alertas genéricos de erro. Confirmação de sucesso ao gestor continua obrigatória.
- Em informes recorrentes, omitir lembretes de prioridade já concluída quando o operador encerrar esse destaque; manter contagens, executor, pendências, histórico e ordem real da fila. Não apagar mensagens anteriores nem alterar a operação só para remover uma frase do relatório.
- Mudanças de procedimento/contrato são persistidas com histórico e readback. Scripts/data operacional exigem inventário e REPORT-INFRA. Nenhum output bruto, path, PID ou credencial vai à conversa operacional.
