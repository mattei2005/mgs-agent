# Diário D-1 SHEIN — operação determinística

## Fonte e autoridade

Resolver sempre `data/ares/meta-ads/policies/shein-daily-report.json` e `SHEIN-US-DIRECT.json#/reporting/daily_report_policy`; a aprovação de Rodolfo está na thread1561752465978818722. A política fixa24contas/threads,4por gestor, excluindo Boostingecon/Growpowerhub em todos os gestores. Os36bindings continuam existentes e disponíveis on-demand; a exclusão é de envios recorrentes, não remoção de conta/rota. Não criar novas threads nem mudar permissões/campanhas/dashboards.

## Agenda e execução

- Root cron determinístico, sem LLM: `47 7 * * *` America/New_York. O wrapper `scripts/shein-daily-cron.py` do profile Ares prepara e retoma; `scripts/shein-daily-report.py` bloqueia qualquer publicação antes08:00. A preparação antecipada preserva o horário pedido sem colidir com as outras rotinas das08h.
- Resolver o Python corporativo pelo shebang do launcher Hermes; o venv Playwright não contém necessariamente `requests` e não deve executar helpers HTTP Meta/SB. O filho UI usa exclusivamente `/root/mgs-agent/.venv-sb/bin/python`, sem instalar pacotes.
- Antes de alterar cron: inventário global root,/etc,systemd,Hermes de todos profiles e schedulers próprios; expandir8datas civis e comparar locks/duração/conta/API. `shein-daily-schedule-audit.py` do profile mantém a auditoria restrita desta agenda; não reaproveitar sua seleção como default de outro job. Backup→candidate→validate→single write→readback→postaudit→REPORT-INFRA.
- O cron publica diretamente as partes exatas renderizadas. Stdout é local, nenhuma moldura Hermes ou entrega `origin/all`. Preservar mensagens anteriores; sem deletes.

## Fontes e semântica

- A data é D-1 fechado; manter a data civil e o fuso Meta real de cada conta. Coletar Meta Insights do dia exato e seis datas anteriores para histórico. Status/Bid/budget são configuração atual, com horários reais separados; B.U.% divide gasto do dia fechado pelo budget vigente, não orçamento histórico inventado.
- Usar `closed_day_report` com policy_id e period since/until exatos. O renderer confere autorização da conta, D-1 pela data da coleta e ausência de partial. Não retroagir timestamps para atravessar o antigo gate intraday. O cabeçalho distingue dia fechado, coleta e atraso GAM/SB atual.
- RPS exige DOM renderizado da SB; a captura valida identidade Ares,data,USD,dimensões,paginação e conta/campanha/domínio. O calendário PrimeVue é readonly: selecionar **Yesterday** e verificar o intervalo exato; não tentar fill. O botão pode ter accessible-name diferente: resolver pelo texto Update do elemento button, aguardar rede e conferir a data das linhas.
- Preservar sessão Ares isolada/protegida em scratch, removendo somente sb:cache:; renovar autenticação com o item Ares corporativo se necessário. Nenhuma sessão/cookie/token em audit ou chat.
- Derivar Produto do nome bruto atual, usando o parser canônico e o fallback legacy do runner; não copiar label antigo. Remover wrappers de número/data/quiz/mídia/lance/escala, sem remover números pertencentes ao produto. `4-in-1` não é prefixo de campanha: validação de wrapper deve exigir separador estrutural com espaço.

## Retomada e testes

- Estado por data em `data/ares/meta-ads/state/shein-daily-report/YYYY-MM-DD`. Fontes concluídas não são reconsultadas após erro somente UI/layout. Paginação ads usa páginas pequenas e checkpoint de cursor/linhas sem URLs autenticadas; repetir somente a camada ausente.
- Antes do primeiro POST, congelar modelo/texto/partes. Depois de qualquer delivery-intent, não rematerializar nem renovar fontes do lote: reconciliar o mesmo journal/nonce/messageID. Resposta ambígua sem correspondência única não autoriza replay. Cada parte exige GET de autor/destino/conteúdo exatos; completion somente24contas/threads únicas e4por gestor.
- `--prepare-only` exercita coleta/render sem publicar; `--verify-only` faz GET das24rotas. A execução normal aguarda08h. Não usar um teste para antecipar os envios.
- Rodar `test_shein_report_daily_d1.py` e regressão `test_shein_report_*.py` no Python Hermes. Testar diafechado/timestamps,período/data/política inválidos,sem parcial,gate08h eDST,24destinos/exclusões,zero vs n/d,readback e replay sem novoPOST. Unitários não comprovam entrega: distinguir preparação validada,cron ativo e publicação GETverificada.
- Falhas preservam estado local; wrapper retoma bounded e em falha terminal emite REPORT-INFRA sanitizado sem mentions, com readback. Não alterar campanhas para recuperar relatório.
