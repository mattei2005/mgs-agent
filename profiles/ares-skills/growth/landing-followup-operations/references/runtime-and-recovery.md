# Runtime e comandos — acompanhamento independente

## Componentes e fronteiras

- CLI: `/root/mgs-agent/scripts/ares-direct-traffic-followup.py`.
- Intake read-only nativo: `ares_campaign_v3.landing_intake`, serviço/timer `ares-landing-intake`.
- Fila, amostras e notificações: `ares_campaign_v3.landing_followup`, serviço/timer `ares-landing-followup`.
- Coletor de screenshots: `/root/mgs-agent/scripts/ares-direct-traffic-sample.py`.
- Contrato, IDs de destinos e parâmetros: `data/ares/meta-ads/policies/direct-traffic-landing-followup.json`.
- Banco nativo Hermes só `mode=ro`/query_only. Nada escreve no criador, na resposta original ou nas lanes/quotas Meta. Sem stage/publish wrapper/callback em criação; esses comandos antigos estão aposentados.
- Sem backfill de pedidos anteriores ao marco de ativação. `activate-intake` nunca redefine o marco. Não abrir pedidos históricos como canário.

## Comandos via terminal

```text
python3 /root/mgs-agent/scripts/ares-direct-traffic-followup.py status
python3 /root/mgs-agent/scripts/ares-direct-traffic-followup.py show --key <key>
python3 /root/mgs-agent/scripts/ares-direct-traffic-followup.py intake
python3 /root/mgs-agent/scripts/ares-direct-traffic-followup.py tick
python3 /root/mgs-agent/scripts/ares-direct-traffic-followup.py begin --key <key> --owner <owner> --index <idx> --pc1-session-id "$HERMES_SESSION_ID"
python3 /root/mgs-agent/scripts/ares-direct-traffic-followup.py defer --key <key> --owner <owner>
python3 /root/mgs-agent/scripts/ares-direct-traffic-followup.py result --key <key> --owner <owner> --index <idx> --pc1-session-id "$HERMES_SESSION_ID" --result PASS|NO_AD|ERROR --evidence <JSON>
python3 /root/mgs-agent/scripts/ares-direct-traffic-followup.py result --key <key> --owner <owner> --index <idx> --pc1-session-id "$HERMES_SESSION_ID" --result PASS --evidence <JSON completo da última tentativa> --recovered
python3 /root/mgs-agent/scripts/ares-direct-traffic-followup.py reconcile --key <key> --index <idx> --pc1-session-id "$HERMES_SESSION_ID" --evidence <JSON> --resume
python3 /root/mgs-agent/scripts/ares-direct-traffic-followup.py need-action --key <key> --owner <owner> --pc1-session-id "$HERMES_SESSION_ID" --evidence <JSON>
```

Usar key/owner/idx recebidos, não criar novos requests. `HERMES_SESSION_ID` precisa ser o ID REAL da execução que segura a lease física. `owner` da fila e ID da sessão podem ser diferentes; não confundir os dois. A lease física é administrada pelo script `mgs-pc1-computer-use-lock.py` com acquire/status/renew/release. Renovar antes de expirar e liberar em finally. Não liberar sessão viva de outro trabalho.

## Coletor de cadência

Depois de anúncio confirmado e aba ativa, executar pelo Python do Hermes (o Python de sistema não contém necessariamente as dependências do handler):

```text
$(dirname "$(readlink -f "$(command -v hermes)")")/python /root/mgs-agent/scripts/ares-direct-traffic-sample.py --key <key> --owner <owner> --pc1-session-id "$HERMES_SESSION_ID"
```

Exige job RUNNING/OPEN_INTENT, lease física e sessão reais. Sem as flags de fechamento descritas abaixo, faz somente `computer_use(action=capture, app=screen)` pelo handler existente e salva frames novos/tempos reais no armazenamento protegido. `CAPTURED_NOT_PASS` não atesta anúncio nem foco. O agente revisa todas as amostras que usará e só então preenche a evidência. `CADENCE_NOT_VALIDATED`/`CAPTURE_ERROR` não significam ausência de anúncio; recapturar na mesma aba, corrigir causa, fechar/verificar e registrar resultado seguro. Não retimar arquivos nem somar trechos desconexos.

Resolver primeiro o symlink de `hermes` com `readlink -f`; o launcher em `.local/bin` pode não ter um `python` irmão. Usar o `python` do diretório real do launcher, não o Python de sistema nem um path adivinhado. Essa resolução deve ocorrer antes da navegação, não como erro repetido por URL.

## Lotes nativos de abertura e fechamento

Preferir os helpers locais para retirar turnos de LLM entre inputs mecânicos, mantendo o handler `computer_use` aprovado e a mesma lease real. Não mudar o transporte compartilhado.

1. Persistir `begin` e chamar pelo Python do Hermes `scripts/ares-direct-traffic-ui.py --key <key> --owner <owner> --index <idx> --pc1-session-id "$HERMES_SESSION_ID" --url '<landing real com query exata>' --mapping-source '<fonte real>'`. O helper abre uma única janela privada técnica e salva `desktop-open.json` antes/depois dos efeitos. Ele não aprova anúncio; não criar guardas extras. Qualquer erro exige ler a prova parcial e reconciliar, nunca repetir o helper.
2. Conferir visualmente a página/anúncio/foco e a exclusividade da janela nova. Só então usar o coletor com `--close-owned-window --exclusive-window-reviewed`. Esse modo salva a série antes de fechar; somente com cadência completa usa um clique no Close nativo da janela comprovadamente nova, confere desaparecimento/preservação e salva `closure`. Sem prova válida da mesma abertura/owner/session/attempt, falha fechado. Não habilitar para abertura manual.
3. `closure.state=CLOSED_NOT_PASS` significa fechamento já feito: não enviar Ctrl+W/click novamente. Revisar offline todos os frames e a prova de fechamento. Depois, `result --use-captured-closure --use-captured-samples --frames-reviewed` mescla evidências reais com os metadados mínimos; sem revisão e anúncio confirmado não há PASS. Cadência inválida não fecha automaticamente e exige recaptura/cleanup seguro na mesma aba.
4. O helper rejeita janela preexistente, browser errado, fechamento sem controle nativo único e qualquer readback incerto; não repete inputs ambíguos. Uma janela já ausente retorna revisão necessária, não um novo sucesso de fechamento. Medir abertura, série, fechamento e registro por tempos reais, sem transformar testes offline em benchmark.

## Registro compacto — persistir antes de expirar

Não escrever um grande JSON narrativo nem reler o código por URL. Usar `result --evidence-json '<JSON mínimo real>'`, na mesma CLI e com os mesmos key/owner/index/session/result. O caminho antigo `--evidence <arquivo>` continua válido. Para PASS, `--use-captured-samples --frames-reviewed` incorpora a série real do coletor somente após confirmação explícita do agente de que TODOS os frames mostram anúncio e aba ativa. Cadência sem revisão visual é rejeitada. Metadados mínimos: observed_url, resolved_landing_url e mapping_source; new_tab_identity; tab_closed_verified, other_tabs_preserved e closed_screenshot; network_ad_confirmed e ad_description. As samples vêm do coletor, sem copiar manualmente cada hash/frame.

Para NO_AD normal, registrar identidade, fechamento e preservação reais com closed_screenshot. Guardar também observation_screenshot e visual_review para eventual recuperação. `--recovered` permite registrar PASS ou NO_AD da última tentativa sem revisitar; exige imagem da própria tentativa e fechamento posterior. Não transformar ausência em PASS. Um arquivo cujo write falhou não é evidência existente: o conteúdo proposto precisa ser reconstruído e conferido independentemente contra outputs/imagens reais antes de uso.

## Evidência mínima

PASS:
- observed_url exata; resolved_landing_url e mapping_source quando o worker resolveu destino;
- new_tab_identity real; tab_closed_verified=true, other_tabs_preserved=true e closed_screenshot real;
- network_ad_confirmed=true e descrição específica do criativo renderizado;
- pelo menos três samples novos com monotonic_seconds, screenshot, ad_visible=true e tab_active=true;
- imagens/relógios reais cobrem >=10s, gaps monotônicos <=10s e de arquivo <=12s; query igual à da campanha; caminho não quiz/chat.

NO_AD: identidade/fechamento/preservação reais e screenshot de fechamento. Política vigente: 3 ausências iniciais, com 60s entre tentativas; depois `DEFERRED_NO_AD` e próximos links. Ao terminar a fase inicial, 1 tentativa final por pendente; nova ausência vira `REVIEW_REQUIRED`. Somente ao terminar a fase final, outbox reporta aqui os links para revisão de Rodolfo, com GET. As duas ausências anteriores não são zeradas. Regra antiga de 2 tentativas explicitamente supersedida; histórico no audit.

ERROR: diagnosis concreta e estado parcial. Fechamento comprovado ou no_tab_opened verdadeiro libera retry técnico; estado ambíguo exige recovery. No-tab em reconcile também exige browser_inputs_zero_verified com leitura da sessão. Não alegar screenshot/visibilidade sem arquivo real.

Intervenção imediata: human_action_required=true, required_action concreta e diagnosis. O outbox registra o vínculo e só publica nesse caso, exceto o relatório final de revisão após 3+1 expressamente autorizado por Rodolfo. Não transformar dificuldade do agente em necessidade humana presumida. Se a aba continuar incerta, WAITING_HUMAN_UNCLOSED impede outros inputs.

## Diagnóstico por estado

- READY/WAIT_RETRY: consumidor deve retomar automaticamente quando due e recurso/prioridade permitirem.
- RUNNING: uma tentativa de observação ativa; um worker, uma URL.
- NEEDS_RECONCILIATION/ATTENTION: cleanup de aba incerta exige RECONCILING. Ausência com fechamento já comprovado segue os contadores da política finita 3+1; não repetir reconciliação do mesmo fechamento. A rodada congela os pares na primeira deferral para que pedidos posteriores não adiem indefinidamente o retorno final.
- RECONCILING: readback/cleanup somente; reconcile --resume após prova segura, depois a fila faz a nova observação separadamente.
- OBSERVED: todas as URLs do job técnico passaram; o pedido humano ainda pode ter outros jobs pares pendentes. Agrupar por native_obligation_id do recibo, exigir intake READY e todos os pares PASSED antes de uma única notificação. Não refazer navegações.
- COMPLETE: todos os PASS + confirmação ao gestor GET verificada.
- DEFERRED_NO_AD: três ausências iniciais já registradas e fechamento seguro; continuar os próximos links. O módulo `ares_campaign_v3.landing_retry_policy` ativa uma única tentativa final por pendente depois de acabar a fase inicial.
- REVIEW_REQUIRED: ausência também na tentativa final; sem nova visita automática. Quando terminar a rodada final, relatório durável nesta thread identifica pedido, conta, campanha/UTM e URL para revisão de Rodolfo. Evento `finite_review_report_authorized` libera somente esse relatório; entrega exige GET. Informes recorrentes encerram após os relatórios verificados, sem chamar pendência de PASS/COMPLETE.
- WAITING_HUMAN/WAITING_HUMAN_UNCLOSED: ação humana indispensável comprovada ou fase 3+1 esgotada com pedido explícito de revisão. Aba incerta continua bloqueando navegação; preservar tudo e nunca repetir postagem ambígua.

O consumidor usa timer existente; não criar cron Hermes com entrega origin/all. A conversa de controle/status do acompanhamento não bloqueia seu próprio worker; turnos de campanha nos demais canais mantêm prioridade. Após processo morrer, a liberação de reserva órfã exige source=tool da sessão, payload/owner ligados ao mesmo job e ausência de processo vivo; erro/ambiguidade não autoriza liberar.

## Prioridade temporária e informes solicitados

`current_priority` identifica a URL e a ordem autorizada. `OTHER_CURRENT_WORK_BEFORE_C121` mantém os pares antes dela; uma instrução posterior expressa pode superseder esse modo por `C121_FIRST_THEN_FIFO`, usando `authorized_new_observation_cycle` uma vez por mensagem para processar a C121 agora e depois retomar FIFO. Não interromper cleanup/observador vivo; fechamento incerto continua antes de qualquer visita. Atualizar também o render dos informes e o checkpoint, preservando o contrato anterior na auditoria. A descrição a seguir trata do modo antigo de pares primeiro. O scheduler ignora sua ATTENTION fechada enquanto houver pares executáveis pendentes; NEEDS_RECONCILIATION continua exigindo cleanup seguro antes de qualquer outra visita. A instrução não cancela uma limpeza ativa. OBSERVED dos pares conta como URLs feitas, pois o aviso coletivo pode depender da URL reservada; COMPLETE continua exigindo a entrega final. A ordem dos demais permanece FIFO e a rodada é congelada para evitar que pedidos novos adiem o retorno para sempre. Quando a própria instrução autorizar voltar a observar a URL após os pares, `authorized_new_observation_cycle_after_peers` libera uma única nova rodada, com evento `priority_retry_cycle_started`; as tentativas antigas não são apagadas. Essa autorização histórica de duas ausências foi supersedida pela política finita vigente `no_ad_retry_policy` de 3 iniciais + 1 final; não reativar/resetar o ciclo antigo. Sem essa autorização, o retorno continua sendo diagnóstico/readback, não uma visita extra implícita.

O módulo `ares_campaign_v3.landing_followup_reporting` usa os timers já existentes do intake/consumidor, sem cron novo nem callback de criação. `progress_reporting` contém autorização, escopo, intervalo e marcos. Informa contagens/estado reais, sem afirmar visita ou conclusão por timer ativo. As mensagens são registradas como `progress_update_authorized`, entregues pelo outbox e conferidas por GET; erros técnicos mantêm gate humano-only. Fechamentos de lote humano e retorno à URL reservada podem antecipar o próximo informe. Quando todo o escopo está COMPLETE, o último informe encerra automaticamente a série.

## Testes e prova operacional

```text
python3 -m unittest discover -s /root/mgs-agent/tests -p 'test_direct_traffic_landing*.py'
```

Testes offline não são resultado visual real. Validar separadamente: runner de criação preservado; intake/consumidor ativos; transição real da fila; anúncio/tempo/foco/fechamento reais; mensagem exata entregue/readback. GAM exige outra prova própria. Não chamar timer ativo de tarefa concluída.

## Auditoria de andamento por período e canais

Executar esta consulta fora da transação de criação, sem navegar nas landings e sem disputar o PC1 com um observador ativo.

1. Obter data/hora reais e construir o início do período em `America/New_York` quando o pedido for “hoje”; não usar a data UTC do host para cortar o dia do operador. Ler `intake_settings.activation_epoch` e manter o recorte anterior à ativação separado, sem transformar consulta de status em backfill.
2. Abrir a fila em SQLite `mode=ro`, `query_only=ON`; coletar `jobs`, `links`, `events`, `messages`, `native_intake` e `intake_settings`. Salvar um snapshot JSON protegido e calcular contagens/deduplicações em código, não pela leitura visual do output. Projetar somente campos úteis; não despejar os JSONs completos de evidência no chat.
3. Verificar cobertura pelo lado da origem: ler `delivery_obligations` entregues no período no banco nativo read-only e reconstruir o mesmo turno humano. Usar as funções existentes de `ares_campaign_v3.landing_intake`, após conferir suas assinaturas: `origin_for_delivery`, `terminal_references`, `source_paths` e `verify_native_reply`. Cruzar cada request terminal elegível com seu job; itens `IGNORED` e busca por palavras no texto não provam ausência de criação. Separar respostas sobre criativos, regras ou manutenção de conclusões reais de campanha.
4. Reconciliar três unidades distintas: pedido humano/resposta de origem, job técnico por request/conta e combinação única de landing + UTMs. Agrupar a apresentação por thread/conta/gestor usando o catálogo canônico por identidade técnica; não contar quatro jobs da mesma resposta como quatro pedidos humanos nem somar números iguais de campanhas de contas diferentes.
5. Classificar com evidência: READY/WAIT_RETRY = aguardando; RUNNING exige claim vigente e consumidor/lease compatíveis; OPEN_INTENT = tentativa iniciada, não sucesso; NEEDS_RECONCILIATION/ATTENTION = recuperação pendente, não execução normal; PASSED = URL validada; OBSERVED = URLs do job técnico validadas, exigindo conferir os pares do mesmo pedido humano antes de classificar como mera pendência de notificação; COMPLETE exige mensagem de sucesso do outbox verificada. Timer enabled/active, isoladamente, não prova que a fila avançou.
6. Fazer GET das respostas originais e de cada mensagem de sucesso já existente pelo transporte corporativo autorizado; conferir destino, autor e conteúdo. Se todas as URLs passaram mas o envio estiver pendente, relatar pendência de entrega e reconciliar o outbox, sem repetir POST ambíguo. Se ainda houver URLs não aprovadas, explicar que não é apenas falta de mensagem.
7. Conferir serviço/timer, claim e lease atuais para identificar gargalo, sem tocar no desktop de outro executor. Uma URL incerta pode segurar gestores posteriores na FIFO global; explicar esse efeito sem sugerir que a criação foi pausada. Não cancelar nem iniciar outro observador para acelerar a consulta.
8. Atualizar somente os estados que mudaram antes de fechar o relatório. Informar horário do snapshot, bullets por gestor/conta com campanhas e status, total de URLs por estado e exclusões anteriores à ativação. Validar que os totais agregados fecham e que todos os requests elegíveis têm correspondência antes de afirmar cobertura completa; não prometer prazo sem medição.
