# Fechamento técnico de performance pós-update

Autoridade: Rodolfo, mensagem 1555776138440343603, thread 1555578276708356108.
Estado: validação técnica concluída; observação natural de 24h continua como coleta complementar já agendada, não como mudança técnica pendente.

## Update e preservação
- Runtime ativo /root/.hermes/hermes-agent-port-main-46904a3b-mgs, SHA 1da62dd8d142bf732e1acaa61d88c233d238aa5e; launcher, PIDs e recibo de ativação reconciliados com o update autorizado na thread 1555704911805808712. Não repeti update ou restart.
- Hashes dos cinco fontes do rollout e do teste de admissão iguais ao recibo anterior: budget e os quatro consumidores sobreviveram ao update sem mudança de negócio.
- Zeus, Atena e Ares ativos; compressão 90%; budget 3 total/2 batch e vaga interativa protegida.

## Correções seguras executadas
1. O coletor mgs-performance-status.py falhou com ModuleNotFoundError: yaml no novo Python de runtime/install-store. Distro /usr/bin/python3 tinha PyYAML e o JSON real já funcionou. Adicionei re-exec de CLI somente quando falta essa dependência, com os argumentos preservados, sem instalação, mistura ABI ou alteração de configs. A segunda regressão de teste detectou virtualenv SB compartilhando o binário Python da distro; guard corrigido para considerar invocation/site loading, não só symlink resolvido. Testado também com -S.
2. O watchdog ignorava DTR como SKIP porque o root cron descarta stdout, apesar de o wrapper escrever seu próprio log. Adicionado somente o alias wrapper→log canônico em CUSTOM_LOG. Explicit redirect continua prioritário e outras rotinas silenciosas não foram incorporadas. Dry-run real agora mostra DTR/SMS/Messenger/monitor de tokens OK. Freshness não equivale a confirmação de apply.
- Backup dos dois scripts e root crontab em /root/mgs-agent/backups/performance-close-1555776138440343603. Nenhum comando de negócio, agenda, modelo, credencial, sistema ou gateway foi alterado/reiniciado por esta execução.

## Validação no runtime novo
- 295 testes aprovados: 223 no runtime e 72 dos consumidores, incluindo 6 novos de fechamento. RED reproduzido, correções aplicadas e GREEN; nenhuma falha final.
- 4/4 canários autenticados somente de leitura, com queued/admitted/released success explícitos. Tempos e contadores atuais:
  - tokens: 11.250 s; {"ok": true, "mode": "noop", "alerts_seen": 193, "new_alerts": 0}
  - revenue: 9.411 s; {"status": "DRY_RUN_OK", "publishers": 51, "sheet_named_rows": 213, "matched_rows": 151, "auth": "mgs-core-prod Service Account"}
  - sms: 3.107 s; {"status": "FETCH_OK", "target_date": "2026-10-02"}
  - dtr: 19.154 s; {"ok": true, "mode": "dry-run", "sheet_active_users": 73, "matched_1p_users": 73, "sb_rows": 2711, "sb_active_restricted_start": 373, "stats": {"users_scanned": 1, "dtr_accounts": 1, "dtr_pages": 1, "skipped_already_restricted_sb": 0, "step1_VALID_FOR_STEP2": 1, "no_campaign_data_yet": 1, "no_match": 1}, "writes": 0}
- Receita Messenger hoje retornou 151 matches (antes 152), alertas 193 (antes 194), e a data SMS mudou para 2026-10-02; são leituras diferentes de fonte viva, não um input congelado. Consumidores retornaram seus critérios atuais OK; não atribuí as diferenças a uma causa funcional não investigada nem as usei como benchmark.
- Canário local 4 Chromium: máximo 3 workflows e 2 batch; terceiro batch esperou 3.697 s; interativo 0.000 s. Locks isolados, nenhuma sessão protegida tocada.
- Ledger completo instrumentado do monitor tinha 19 releases success e espera máxima 0.000 s no momento do recibo; não significa que todos ocorreram após o cutover Hermes.
- Três amostras finais de CPU: 32.91%–54.77%, média 41.58%; load1 2.41, memória disponível 12.45 GiB. Amostras ainda variam com trabalho concorrente; não são um ganho percentual causal. A primeira amostra recuperada pós-update foi 7,02% e não foi apresentada como carga constante.
- Horários do cron de negócio comprovadamente iguais ao backup desta execução.

## Encerramento e limite honesto
- Não há implementação técnica desta rodada aguardando o fim da atualização. Não há justificativa, nestas evidências, para comprar mais RAM ou alterar modelo; CPU pode continuar variando com outras tarefas, já separadas do budget de browsers.
- Não executei apply extra em SB/Sheets para fabricar conclusão de produção. DTR 07:30/15:30, SMS 08:00 e receita Messenger 08:17 ET ainda terão seus primeiros ciclos naturais pós-rollout no dia seguinte.
- Job 595070de2460 segue enabled, once, repeat 1, para 2026-10-03 19:04:25 ET, nesta thread. Mantive essa observação suplementar sem criar outro job, mudar cadência ou alegar 24h já decorridas. O checkpoint de acompanhamento mantém esta coleta distinta do fechamento técnico.
- Prevenção permanente de auth SB e validação máxima de janela de contexto não foram executadas sob a autorização específica dos quatro consumidores; não há promessa de aceleração percentual nem troca de modelo.
- Aprendizado salvo em hermes-agent-operations/browser-performance-admission-budget.md e log-monitor-discord-alert/route-pack-03.md; fonte ativa e espelho de cada referência com hashes iguais.
- Evidências: /root/mgs-agent/reports/performance-postupdate-1555776138440343603-evidence.
