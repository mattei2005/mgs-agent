# SHEIN D-1 e intraday — agendamento determinístico

## Fontes e autoridade

- D-1: `data/ares/meta-ads/policies/shein-daily-report.json`.
- Intraday: `data/ares/meta-ads/policies/shein-intraday-report.json`, autorizado por Rodolfo na thread `1565155357074923732`, confirmação `1565157065234710681`.
- Resolver contas/threads e contagens por gestor de cada política vigente, validando IDs únicos e cardinalidade; não fixar24 nem presumir igualdade D-1/intraday após extensões autorizadas. Boostingecon e Growpowerhub continuam excluídos. Não herdar o catálogo36 como cobertura automática. Observadores de saúde também devem ler `expected_reports` e as listas aprovadas, fail-closed se ausentes/inconsistentes; nunca deduzir a cobertura esperada do próprio recibo. Antes de retry por divergência de contagem, reconciliar matrícula autorizada, request congelado, completion, intents e GETs: entrega íntegra requer corrigir o observador, não republicar o relatório.
- `SHEIN-US-DIRECT.json#/reporting` aponta as duas políticas. O dispatcher único é root crontab; não criar um segundo job Hermes.

## Semântica e isolamento

- Preservar o diário07:47→publicação>=08h, referente ao dia fechado anterior.
- Intraday inicia09:32,14:11,16:02,20:02,23:31 America/New_York, com stagger físico25s. São horários de início, não promessa de entrega instantânea.
- Coletar o dia corrente, marcando somente a última das sete datas como parcial. Exibir os horários efetivos de cada fonte/conta; não rotular a coleta distribuída como corte simultâneo.
- Não apontar uma nova entrada cron diretamente para o runner D-1: ele fixa D-1, cacheia por data e encerra após completion. Usar runner intraday com estado `YYYY-MM-DD/HHMM` e nonce incluindo data+slot+conta+parte+hash.
- Compartilhar `shein-daily-report/run.lock` com D-1 para impedir coletores/publishers paralelos. O scheduler intraday possui `ares-shein-intraday-scheduler.lock` próprio, timeout2400s e até3 tentativas internas limitadas, retomando fontes/partes sem POST cego.
- Usar contexto Chromium efêmero, sessão Ares intraday protegida e preset UI Today; default UI Yesterday do diário permanece intacto. RPS é DOM visível, nunca fórmula/API substituta.
- Resolver o interpretador em cada fire pelo helper stdlib canônico `/root/mgs-agent/scripts/mgs-hermes-runtime-resolve.py` (`resolve(...)["python"]`), sem LLM nem diretório de versão fixo. Nunca tratar o shebang do launcher como Python: launchers PM nativos usam `/bin/sh`; isso executa o relatório como shell e falha antes da coleta. O helper distingue launcher legado de PM e consulta a fronteira nativa `--print-runtime-command` e o ambiente selecionado. Testar os dois wrappers, forwarding de argumentos e journal, depois exercitar o scheduler real e conferir os recibos Discord. Preservar horários, locks e escopo; intraday fora da janela só `--validate-only`, nunca catch-up implícito.
- Se um retry exceder a janela real do transporte de terminal, reconciliar processo, fontes e intents antes de retomar; um timeout pode encerrar o processo sem gravar o journal final. Usar execução acompanhada silenciosa quando a duração observada superar a janela, consumir o resultado antes de encerrar e não reenviar partes sem readback.
- No runner D-1, fazer refresh/materialização uma única vez no caminho de publicação, após o gate08h; prepare-only continua validando o snapshot sem enviar. Não executar um refresh completo antes e outro imediatamente depois desse gate quando já passou08h. Intents existentes congelam modelos/partes: após timeout com entregas parciais, retomar somente o runner canônico e seus GETs/nonces, sem refazer refresh/coleta. Validar publicação, prepare-only, espera pré08h, freeze e completion por testes isolados de main.

## Data visível versus consulta inicial SB na virada UTC

- Sempre reaplicar explicitamente o preset aprovado Today/Yesterday e Update, mesmo quando o input já mostra a data alvo. O estado inicial do dashboard pode exibir a data local e enviar timestamps UTC do dia seguinte; o label sozinho não prova a data efetiva da tabela.
- Validar DATE em todas as linhas DOM antes de filtrar conta/domínio. Linhas fora de escopo não podem ocultar uma data incorreta e produzir uma captura falsamente completa com zero linhas.
- Reproduzir a fronteira com relógio JS isolado, preservando o timezone NY e registrando somente datas do payload, datas DOM, paginação e contagens agregadas; não salvar tokens nem linhas de contas fora do escopo. Testar o helper implantado, não uma cópia equivalente.
- Se a rodada intraday expirou ou cruzou o dia civil sem fontes completas, preservar o journal e escalar a autorização de entrega histórica tardia. Uma rodada posterior saudável não comprova a entrega da rodada faltante; não alterar o relógio do runner, fazer catch-up implícito ou usar leitura de RPS posterior como corte histórico original.

## Recuperação de fontes arquivadas

- Se Insights selecionar uma campanha que gastou no período, mas o edge da conta omitir seus conjuntos/anúncios por estarem arquivados, consultar somente os IDs selecionados na campanha exata com `effective_status=["ARCHIVED"]`. Validar campaign_id e account_id, ausência de IDs duplicados e preservar a observação e a origem da recuperação. Não excluir a linha financeira, inferir lance/quiz, mudar status ou usar um vazio como configuração válida. O coletor compartilhado `recover_archived_configuration` deve valer tanto para D-1 quanto intraday e continuar fail-closed se o conjunto permanecer indisponível.

## Quiz de entrada versus domínio de receita

- Resolver o quiz pelo CTA real dos anúncios da conta/campanha exata. O domínio de entrada aprovado `lp-yolo.com` pertence às quizzes do Yolokfx (`context/acquisition.md`); aceitá-lo somente nessa família, sem substituir `yolokfx.com` como publisher ou origem financeira da SB. O coletor D-1 é compartilhado pelo intraday: manter a correção em `reporting_quiz`, não em cópias por rodada.
- Quando a coluna Nº estourar a largura fixa, diagnosticar os componentes antes de ampliar ou truncar. Um `n/d` causado por host de entrada não reconhecido pode ocupar mais espaço que o quiz confirmado. Corrigir a evidência, preservando IDs, COPY, largura aprovada e valores financeiros; host desconhecido ou evidência ambígua continua `n/d`/`misto`, nunca inferido do nome da campanha.
- Validar a correção com materialização offline das mesmas24 fontes e comparação dos campos financeiros; só depois retomar o runner canônico, no mesmo journal/data, sem tocar em intents já congeladas. Semântica de host não autoriza catch-up expirado nem mudança de layout.

## Produto independente: campanhas novas às 18h08

- Não confundir a contagem de criações (`shein-campaign-creation-daily.json`) com os relatórios financeiros D-1/Intraday ou a planilha mensal de criações. Cada produto tem seleção e autorização próprias; exclusões do financeiro não excluem automaticamente sites da contagem.
- Para uma expansão aprovada, congele as identidades exatas (ID, nome, gestor e responsável), prove que as contas anteriores foram preservadas e aceite somente o delta autorizado. Valide o catálogo contra esse manifesto, não apenas contra a nova cardinalidade: 38 linhas não comprovam as 38 contas certas.
- Some múltiplas contas da mesma célula gestor/site, preservando os seis gestores e seis sites. Se qualquer conta da célula estiver incompleta, mantenha `n/d` na célula e seus totais; teste duplicação de IDs, troca de identidade com mesma contagem, conta extra, denominador e soma horizontal/vertical.
- Exercite o wrapper real em `--validate-live` com zero publicação antecipada e zero hook de planilha. O modo de validação não pode chamar `update_creation_sheet`; confirme também a ausência de outbox, delivery e sheet-refresh no run real. Uma consulta das 38 contas valida seleção/coleta/renderização, não a entrega agendada nem a recuperação de um slot histórico.
- Preserve horário, destino, nonce e outbox existentes; não amplie a planilha independente nem faça catch-up de datas antigas pela simples aprovação de novas contas. Registre separadamente a correção do produtor e o saldo histórico da fila, sem fechar o incidente antigo por um teste atual.

## Expansão da planilha mensal de criações

- Após aprovação específica da planilha, mantenha o mesmo spreadsheet ID,14abas,36células gestor/site e o gate00h15; 38contas não significam38células. Congele IDs/nomes/gestores da seleção e mantenha as36contas da baseline histórica separadas das duas inclusões.
- Em `snapshot_to_days`, some as campanhas das contas que caem na mesma célula; atribuir o contador de cada conta sobrescreve o anterior. Bloqueie escrita se qualquer conta faltar, repetir, mudar identidade ou estiver incompleta.
- Preserve a baseline original por contagem apenas para as contas que ela cobria; una IDs históricos sem duplicação, acrescente as campanhas posteriores ao corte dessas contas e todas as campanhas verificadas das inclusões. Campanhas de uma conta incluída que antecedam a baseline não pertencem automaticamente à contagem antiga. Teste a partição e a idempotência, preservando o histórico conhecido contra redução antes de qualquer write.
- Use exclusivamente `mgs_google_workspace_auth.py` e a SA canônica. Antes do lote, preserve metadados,valores e fórmulas das14abas, prove Drive/Sheets e faça canário reversível em célula vazia validada. Confira detalhes,resumos,totais,tabs/IDs e ACL depois do write, sem criar planilha nova ou alterar permissões.
- Uma recuperação manual do consumidor e readback das14abas comprova a atualização atual; mantenha o fechamentoD-1 e o hook após a contagem diária sem alegar que uma execução agendada futura já ocorreu.

## Validação e colisões

- Aplicar `context/cron-scheduling-policy.md`: oito datas civis, todos os profiles, root/system cron, timers e contratos de aplicação; considerar DST e o timezone real observado do daemon.
- Classificar por finalidade, não apenas por densidade: intake de criativos, reconciliação de arquivo/negócio e checker de reparo SB continuam operacionais. Baselines densas de infraestrutura podem coincidir, mas exigem registro de recursos/locks e não justificam afirmar ausência absoluta de concorrência.
- Após alterar a classificação, verificar que foi uma correção comprovada da finalidade, não reclassificação para fazer o gate passar.
- Separação de minuto não prova ausência de sobreposição pela duração. Avaliar API/throttle compartilhado, CPU/RAM, browser/session e writers; manter locks/idempotência mesmo em minutos livres.
- Testar fonte/render real das24 contas com `shein-intraday-report.py --slot <slot> --validate-only`: estado de validação isolado, zero Discord POST e nenhuma antecipação de rodada futura. O próximo cron deve coletar fontes novas em seu próprio estado.
- Exercitar suíte `test_shein_report_*.py` no interpretador Hermes atual. Para refatorar o coletor comum, comparar também D-1 antes/depois com fontes preservadas: modelos, texto, partes e receipts byte a byte das24 contas; sem novas consultas nem publicações.
- Fazer o readback independente de lotes grandes de mensagens sequencialmente, com pacing por destino e checkpoint de cada ID validado. Uma rajada concorrente pode esgotar as retentativas de429 mesmo depois de entrega correta; respeitar o `retry_after`, retomar somente GETs faltantes e nunca publicar novamente por falha da auditoria.
- Instalar via backup→candidato→`crontab -n`→diff→write único→readback exato→auditoria pós-write excluindo somente as próprias entradas novas. Inventariar, registrar autoridade/checkpoint e publicar um REPORT-INFRA com GET de confirmação.
- Distinguir agenda ativa e teste de coleta live de execução agendada entregue. Não publicar reports extras como smoke nem alegar que o primeiro fire futuro já ocorreu.
