# MGS Router — divisão igual, retorno à lista e cliques

## Autoridade e supersessão

Pedido novo de Rodolfo `1556896726403514390`, thread `1555381168894115912`, autoriza os três recursos. Esta decisão sucede a exclusão de contagem de cliques em `docs/mgs-router-scope-and-hosting-v2.md`, sem ampliar para Keitaro, conversões, postbacks, identificação de visitantes ou relatórios de performance. Hosting e contas permanecem os mesmos. Para recursos anteriores, preservar `docs/mgs-router-domain-date-dns-dialog.md`, `docs/mgs-router-domain-layout-top-pagination.md`, `docs/mgs-router-bulk-actions-pagination.md` e `docs/mgs-router-scoped-groups.md`.

## Contratos

1. **Distribuir igualmente (100% ÷ destinos)**: botão na edição das campanhas multidestino. Preenche todos os pesos com o mesmo valor de 100 dividido pelo número de destinos, com até 12 casas decimais. 20 destinos:5; 23 destinos:4.347826086957. Usa pesos relativos, logo arredondamento não favorece um destino e a soma literal não precisa ser100. É uma probabilidade igual por acesso, não alternância ou cota exata em amostras pequenas. O operador pode editar manualmente. Só `Salvar e aplicar` altera o tráfego; cancelar ou clicar no menu não grava. Nenhuma campanha existente é normalizada automaticamente pelo deploy. Landing Pages desativadas continuam excluídas da distribuição efetiva conforme contrato anterior.
2. **Campanhas volta à lista**: clicar no menu fecha o editor mesmo quando a aba já está selecionada. Preserva pesquisa, grupos e paginação; descarta somente edição ainda não salva. Landing Pages segue o mesmo padrão.
3. **Cliques**: cada GET de uma rota válida que gera redirecionamento302 incrementa uma vez o total do seu link público. HEAD, métodos rejeitados,404,500 de origem e rotas sem destino ativo não contam. Repetições, previews e robôs contam: não é visitante único nem prova de pessoa humana. Filtros Hoje, Ontem, últimos7/30dias, todo período ou intervalo inclusivo De/Até, em America/New_York, com DST. Ordenação por cliques independente do filtro. Não há importação ou reconstrução de históricos Keitaro.

## Armazenamento e segurança

- Totais por dia e identidade imutável host+path em `/var/lib/mgs-router/clicks.sqlite`, WAL, synchronous FULL, uma conexão e incrementos atômicos. Não armazenar IP, user-agent, identificador de visitante, cookie, query, referrer ou URL do destino.
- Endpoint `/api/clicks` somente autenticado no host administrativo; sem endpoint para zerar ou modificar cliques. Mesmo link recriado mantém totais históricos; nova cópia com novo caminho começa sem eventos.
- Início real de coleta em metadado persistente `since`, exposto no painel. Zero anterior não representa histórico reconstruído. UI mostra `—`, e não zero, quando consulta falha.
- Falha na gravação nunca bloqueia redirect; registra erro sanitizado e contador failed_writes, deixa health em `degraded_clicks`, avisa no painel. Contagem sob falha pode ficar incompleta; não inventar eventos nem repetir UPSERT de resultado ambíguo.
- Limites de espera na escrita350ms e na consulta3s. Processo continua na unidade/restrições originais. A atualização não edita `/etc`, DNS, SSL, credenciais ou gateways.
- `--check` e `--init-users` não criam nem abrem o banco de cliques. Testes guardam estado somente em scratch privado.
- Backup SQLite deve usar online backup API e integrity_check, não copiar apenas arquivo principal com WAL ativo. Counter store fica fora do Git e não é restaurado para trás em rollback de código.

## Estado de publicação e evidência

Publicado e validado em produção: receipt `data/mgs-router-campaign-features-validation.json` com status `complete_verified`, 85 testes, race/vet/JS/build, 985 verificações públicas e QA das duas contas. Início real da coleta: `2026-10-06T05:37:49Z`. Um GET técnico de canário em `jobs.amazingxjobs.com/lpamazing` foi contabilizado (0→1) e mantido, sem ocultação. Banco preservou totals/since após restart real; online backup com integrity_check=ok. Todos os quatro arquivos de estado anterior, unidade e redes Cloudflare mantiveram os hashes; PIDs dos gateways não mudaram. Executor `scripts/mgs-router-campaign-features-deploy.py` single-use não deve ser reexecutado como comando genérico.

Gates: suíte completa, race, vet, JS, build; browser local salva pesos de20/23; público testa preview/cancelamento nas duas contas sem POST; varredura HEAD de todas as rotas com/sem parâmetros evita poluição de cliques; um GET público de canário demonstra incremento real e fica honestamente contabilizado; restart real confirma persistência; rotas/catálogo/grupos/usuários/domínios/cache permanecem byte a byte; PIDs dos agentes preservados. Rollback automático somente com estado protegido intacto; gravação concorrente exige reconciliação, pois binário antigo não aceita pesos fracionários.
