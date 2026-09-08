# Meses fechados nos menus nativos

Autoridade: Rodolfo1546894693135028234, explicitada/corrigida em1546896342805123125, thread1545426987756298340. Supersede o desenho de menu separado/redirecionamento do release1546884731436671056. Não supersede a importação imutável, isolamento, valores ou vínculo julho→agosto.

## Contrato
Janeiro–julho devem usar os mesmos menus e shell de agosto: Dashboard, Relatório Diário, domínios, despesas, parâmetros, Pagamentos e Visão de gestor. Somente valores fechados; não executar o motor financeiro com regras de agosto. Não criar outro menu, página de planilha ou histórico separado para selecionar esses meses. Saldo remanescente fica em Pagamentos. Conservar ausência de valores/datas e a divergência março→abril, sem ajuste inventado.

## Implementação
- `public/history-dashboard.js`: projeção de apresentação sobre snapshots já autorizados; cartões e painéis do shell existente, despesas originais, países, parâmetros fixados, inválidos e fechamento de site. `closedBlocks()` descobre calendários/headers/totais de cada mês, incluindo todos os blocos inferiores/G001...; não reutilizar offsets de agosto. Diários e totais mensais vêm das células efetivas; não re-somar dias para substituir ROI/fechamento pronto.
- `public/history-operations.js`: mesmos menus Pagamentos e Visão de gestor. Geizian usa previous/due/balance prontos e todos os lançamentos numéricos do fechamento; julho alimenta agosto pelo vínculo interno já existente. Remuneração sem comprovação datada não vira quitação nem dívida acumulada inventada. Ícaro Jan/Fev continua salário-only; referências Nicolas antes ignoradas ficam indisponíveis.
- `app.js`/`operations.js` carregam snapshot apenas quando período é histórico; navegação mantém mês via query/sessionStorage. Removido o item Histórico fechado. `/history` é compatibilidade302 para o menu nativo correto, com escopo de papel preservado. Arquivos antigos permanecem para rollback, sem exclusão autorizada.
- `finance-ops.mjs` apenas permite os dois JS estáticos aos gestores; APIs financeiras continuam limitadas ao próprio namespace. Novos JS não são nova autorização de leitura de outro gestor. Guardas409 de escrita histórica e grants SELECT-only permanecem.
- Contas de anúncio: o snapshot não contém cadastro histórico de IDs. Não projetar vínculos atuais de agosto sobre o passado nem inventar cadastros.
- Janeiro/fevereiro não têm o resumo moderno por país/consolidado de gestor; mostrar ausência explicitamente e todos os detalhes/totais originais por domínio. Não inventar esse consolidado usando regras atuais.

## Validação e rollout
Fonte de estado: `reports/finance-native-history-1546896342805123125.md`, evidências `apps/finance-system/private/history-ui-1546894693135028234/`.
- Unit64PASS; cobertura40documentos/504blocos/858headersGross/194814valoresdiários numéricos, sem omissão de colunaGross dos calendários.
- Stage PostgreSQL:40payloads/377906células exatas,217negações,85meses atuais de gestor, vínculoJulho→Agosto e cenários preservados.
- `tests/history-ui-public.mjs` usa recursos locais+APIs reais na fase stage, e recursos publicados na fase production. Nunca confundir stage com deploy. Matriz6logins×7meses, mesmos menus, pagamentos, desktop390/1440, isolamento e alternância agosto/julho.
- `deploy/history-ui-release.py`: prepare→exercise→publish→verify; cópias de backup local/remota, hashes iguais, restauração de banco isolado verificada. Nove arquivos publicados; nenhuma mutação de source_cells/scenarios/finance_ledger/finance_users/finance_history no cutover. Serviço financeiro/socket apenas; nunca gateway Hermes.
- Backup `/home/zeus/mgs-finance-backups/1546896342805123125`; stage `/var/tmp/mgs-finance-history-ui-1546896342805123125`; DB `mgs_finance_history_ui_1546896342805123125`. Rollback de código, nunca restaurar DB sobre escritas posteriores. Não apagar backups/arquivos antigos sem Critical Subset.

## Limite de autenticação em testes
Auth atual permite10logins/IP em15minutos (inclusive sucesso). Stage via domínio público também consome o limite. Dimensionar a campanha de testes para não gastar toda janela antes da validação publicada; preferir stage isolado ou reaproveitamento seguro de contextos ainda válidos. Se houver429, ler janela/Retry-After, preservar proteção e retomar somente perfis pendentes depois da expiração. Nunca zerar auth_limits, trocar IP para contornar, enfraquecer a regra ou fabricar sucesso. Runner aceita `production resume` com matriz/contadores anteriores validados.
