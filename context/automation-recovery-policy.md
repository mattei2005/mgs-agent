# MGS — Continuidade obrigatória de crons e operações autorizadas

Status: política aprovada; execução e cobertura técnica devem ser comprovadas separadamente.
Dono executivo: Rodolfo Mattei. Responsabilidade de coordenação e fechamento: Zeus; executor de negócio preservado.
Fonte: Discord, thread `1569185140502954077`, mensagem `1569191908020981801`, autor `344196393512075265`.
Chave canônica: `operations.automation.recovery-continuity`.

## 1. Decisão do dono

1. PC1 ocupado não cancela nem encerra uma função autorizada de cron: identificar a ocupação, entrar em fila persistente e retomar quando houver disponibilidade, sem depender de Rodolfo lembrar ou pedir novamente.
2. Timeout não encerra o pedido: aguardar intervalo adequado, tentar novamente com segurança e continuar até conclusão real validada ou bloqueio explícito que exija decisão humana. Um aviso de erro não é entrega nem fechamento.

A política vale independentemente do assunto da função; a autoridade e os limites do pedido original continuam delimitando o que pode ser executado.

## 2. PC1 — espera durável, não abandono

- Consultar a lease compartilhada e distinguir ocupado, livre, estado inválido e desafio de autenticação. Não tomar a sessão de outro executor, matar processo alheio ou abrir perfil alternativo para contornar a ocupação.
- Antes de encerrar o turno que encontrou ocupação, persistir o mesmo pedido na fila/continuidade com: identidade estável e chave de dedupe; agente executor; job e origem; recurso; alvos autorizados; etapas já concluídas; próxima etapa; evidências; `queued_at`; `retry_at`; estado e motivo. Não armazenar credenciais nem conteúdo privado de outra thread.
- `waiting_resource` não é erro de execução nem consome orçamento de falhas do trabalho de negócio. Manter posição e evitar starvation; prioridade diferente precisa de regra aprovada e rastreável.
- Uma nova ocorrência do mesmo cron reconcilia o pedido pendente; não cria segundo writer nem duplica ações. Coalescer somente quando a semântica da operação permitir, preservando ocorrências com fatos/períodos distintos.
- Retomar automaticamente pelo executor durável comprovado ao liberar a lease ou no próximo instante de verificação previsto. Adquirir a lease de novo e revalidar identidade, escopo e checkpoint antes de agir.
- Checkpoint sozinho não é fila executável. Só afirmar 'está na fila e retomará automaticamente' quando o registro persistido, o consumidor ativo, seu próximo disparo e o caminho de fechamento estiverem verificados.

## 3. Timeout — repetir a etapa faltante com segurança

- Na primeira ocorrência, reconciliar processos, writes, recibos e destino real; preservar resultados concluídos. Repetir somente leituras/etapas faltantes ou comprovadamente inválidas.
- Respeitar `Retry-After`, cooldown e limites reais do fornecedor. Na ausência deles, usar backoff limitado com jitter; esperar sem busy-loop e liberar o recurso compartilhado durante esperas que não exijam sua posse.
- Persistir `retry_at`, contagem por causa, último erro, etapa pendente e evidência antes de sair do turno. Se a espera ultrapassar a execução corrente, usar mecanismo durável existente ou autorizado e provar seu agendamento/consumidor; nunca substituir execução por lembrete.
- POST/write ambíguo exige readback ou idempotência real antes de repetir. Não reenviar relatório ou criar/pagar/ativar objetos às cegas.
- Diagnosticar e corrigir causa recorrente dentro da autoridade vigente. Preservar os limites de anti-loop de `AGENT.md` e SOUL: interromper a mesma ferramenta após cinco falhas consecutivas, ou antes diante de loop. Isso interrompe a tentativa cega, não cancela nem esquece o pedido; mantê-lo aberto, com dono, diagnóstico e condição de retomada/escalonamento.
- Execução única consumida não acorda sozinha. Provar continuação durável ou declarar a lacuna técnica, sem alegar recuperação automática inexistente.

## 4. Estados e condições de fechamento

Estados não terminais: `queued`, `waiting_resource`, `retry_scheduled`, `running`, `waiting_human`, `blocked_decision`, `reconciling_ambiguous_effect`.
Estados terminais permitidos: `completed_validated` ou cancelamento explícito e rastreável pelo dono autorizado. Prazo vencido não é sucesso nem cancelamento implícito.

- Ocupação, timeout, esgotamento de um lote de tentativas e envio de alerta não podem converter o pedido em concluído.
- Um bloqueio humano conserva o pedido, a etapa e o executor; escalar com pergunta exata e impacto. Após a resolução, revalidar e retomar, sem pedir de novo o escopo já aprovado.
- Para operações sensíveis a horário, não executar uma ação expirada com nova estratégia/horário por inferência. Preservar e escalar o gate específico; a regra de continuidade não autoriza alterar campanha, orçamento ou início.
- Somente concluir após readback do efeito real e da entrega exigida na origem. Registrar estado final e limpar a pendência pelo fluxo autorizado, sem apagar evidências.

## 5. Limites preservados

Não autoriza alterar credenciais, permissões, billing, pagamentos, budget, estratégia, firewall, exclusões ou outras ações do Critical Subset. Não altera o próprio `AGENT.md`, skills de outros agentes, cadências ou retenção por inferência. Login/2FA exigido segue o fluxo protegido; jamais contornar o desafio por insistência.

Esta política complementa a recuperação resiliente do `AGENT.md`. Supersede apenas a interpretação operacional de que 'ocupado', 'timeout' ou 'escalado' encerram a responsabilidade e permitem abandonar o pedido; não supersede limites de segurança/anti-loop.

## 6. Situação técnica na adoção desta decisão

O helper `scripts/mgs-pc1-computer-use-lock.py` fornece lease e retorna `lock_held`; isso não comprova uma fila persistente com consumidor universal. Não declarar esse mecanismo universal implantado por editar documentação ou SOUL.

A implementação deve demonstrar: busy→fila; dedupe e executor único; liberação→retomada; timeout→espera→retry; reinício→pedido preservado; efeitos ambíguos→readback; bloqueio humano→pendência visível; conclusão→efeito e entrega validados. Cada consumidor precisa de prova própria de adoção. Até então, distinguir **regra persistida** de **automação universal implantada**.

## 7. Camada comum implantada — 2026-11-08

Autorização de implementação: Rodolfo `1569193434189668453`, mesma thread. Esta seção atualiza a situação de implementação, sem alterar os limites da política nem afirmar certificação funcional universal.

- Fila durável: `/root/.hermes/shared/automation-continuity/queue.sqlite3`; implementação `scripts/mgs_automation_continuity.py`.
- Consumidor: `scripts/mgs_automation_supervisor.py`, chamado pelo entrypoint do resolvedor `scripts/alerts-infra-failed-alert-resolver.py`, reutilizando seu cron/flock existente de cinco minutos. Nenhuma nova agenda de negócio foi criada.
- Ingresso/FIFO PC1: `scripts/mgs-pc1-computer-use-lock.py`; busy só retorna fila confirmada quando a persistência realmente funcionou. Contrato nativo alterado, pausa e gates humanos/criticos não viram autorização de retry.
- Watchdog independente do worker: `scripts/mgs_continuity_health.py`, integrado ao stale monitor existente. Observa heartbeat, fila e diagnóstico; cinco falhas não descartam o pedido.
- DTR: `scripts/mgs_dtr_continuity.py` adiciona progresso válido por usuário e outbox congelada com IDs aceitos/GET. A retomada produtiva confirmou 73/73 usuários e entregou as três partes do relatório sem repetir a coleta completa.
- Evidência produtiva: ticks naturais do resolvedor em processos distintos, incluindo entrega DTR às 23:32 ET e posterior estado `completed_validated`. A fila e o consumidor são execução real, não somente esta documentação.
- Inventário observado: 106 alvos (root cron, cron de sistema, Hermes Zeus/Atena/Ares e timers); o manifesto/recibos ficam no banco e no relatório de implementação. Inventariar um alvo ou provar sua saúde técnica não certifica todos os seus efeitos de negócio. Recibos por workflow/período continuam obrigatórios.

Procedimento reutilizável: skill `log-monitor-discord-alert`, referência **Common automation continuity**. Evidência detalhada: `reports/automation-recovery-implementation-1569193434189668453.json`. Pendências de recurso, autenticação e histórico fora do inventário ativo permanecem explicitamente abertas; não entram no total de recuperação concluída por inferência.

