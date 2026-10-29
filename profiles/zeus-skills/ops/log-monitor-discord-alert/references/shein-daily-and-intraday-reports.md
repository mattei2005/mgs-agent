# SHEIN D-1 e intraday — agendamento determinístico

## Fontes e autoridade

- D-1: `data/ares/meta-ads/policies/shein-daily-report.json`.
- Intraday: `data/ares/meta-ads/policies/shein-intraday-report.json`, autorizado por Rodolfo na thread `1565155357074923732`, confirmação `1565157065234710681`.
- Resolver as mesmas24 contas/threads do D-1; quatro por G001–G006; Boostingecon e Growpowerhub continuam excluídos. Não herdar o catálogo36 como cobertura automática.
- `SHEIN-US-DIRECT.json#/reporting` aponta as duas políticas. O dispatcher único é root crontab; não criar um segundo job Hermes.

## Semântica e isolamento

- Preservar o diário07:47→publicação>=08h, referente ao dia fechado anterior.
- Intraday inicia09:32,14:11,16:02,20:02,23:31 America/New_York, com stagger físico25s. São horários de início, não promessa de entrega instantânea.
- Coletar o dia corrente, marcando somente a última das sete datas como parcial. Exibir os horários efetivos de cada fonte/conta; não rotular a coleta distribuída como corte simultâneo.
- Não apontar uma nova entrada cron diretamente para o runner D-1: ele fixa D-1, cacheia por data e encerra após completion. Usar runner intraday com estado `YYYY-MM-DD/HHMM` e nonce incluindo data+slot+conta+parte+hash.
- Compartilhar `shein-daily-report/run.lock` com D-1 para impedir coletores/publishers paralelos. O scheduler intraday possui `ares-shein-intraday-scheduler.lock` próprio, timeout2400s e até3 tentativas internas limitadas, retomando fontes/partes sem POST cego.
- Usar contexto Chromium efêmero, sessão Ares intraday protegida e preset UI Today; default UI Yesterday do diário permanece intacto. RPS é DOM visível, nunca fórmula/API substituta.
- Resolver o interpretador pelo shebang atual de `/root/.local/bin/hermes` em cada fire pelo wrapper stdlib, sem LLM e sem fixar um diretório descartável de versão.

## Validação e colisões

- Aplicar `context/cron-scheduling-policy.md`: oito datas civis, todos os profiles, root/system cron, timers e contratos de aplicação; considerar DST e o timezone real observado do daemon.
- Classificar por finalidade, não apenas por densidade: intake de criativos, reconciliação de arquivo/negócio e checker de reparo SB continuam operacionais. Baselines densas de infraestrutura podem coincidir, mas exigem registro de recursos/locks e não justificam afirmar ausência absoluta de concorrência.
- Após alterar a classificação, verificar que foi uma correção comprovada da finalidade, não reclassificação para fazer o gate passar.
- Separação de minuto não prova ausência de sobreposição pela duração. Avaliar API/throttle compartilhado, CPU/RAM, browser/session e writers; manter locks/idempotência mesmo em minutos livres.
- Testar fonte/render real das24 contas com `shein-intraday-report.py --slot <slot> --validate-only`: estado de validação isolado, zero Discord POST e nenhuma antecipação de rodada futura. O próximo cron deve coletar fontes novas em seu próprio estado.
- Exercitar suíte `test_shein_report_*.py` no interpretador Hermes atual. Para refatorar o coletor comum, comparar também D-1 antes/depois com fontes preservadas: modelos, texto, partes e receipts byte a byte das24 contas; sem novas consultas nem publicações.
- Instalar via backup→candidato→`crontab -n`→diff→write único→readback exato→auditoria pós-write excluindo somente as próprias entradas novas. Inventariar, registrar autoridade/checkpoint e publicar um REPORT-INFRA com GET de confirmação.
- Distinguir agenda ativa e teste de coleta live de execução agendada entregue. Não publicar reports extras como smoke nem alegar que o primeiro fire futuro já ocorreu.
