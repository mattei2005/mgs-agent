# Runtime e comandos — acompanhamento independente

## Componentes e fronteiras

- CLI: `/root/mgs-agent/scripts/ares-direct-traffic-followup.py`.
- Intake read-only nativo: `ares_campaign_v3.landing_intake`, serviço/timer `ares-landing-intake`.
- Fila, amostras e notificações: `ares_campaign_v3.landing_followup`, serviço/timer `ares-landing-followup`.
- Coletor de screenshots: `/root/mgs-agent/scripts/ares-direct-traffic-sample.py`; captura sem imagem tem uma repetição read-only limitada; série tem deadline de45s e continua exigindo10s reais, sem somar trechos desconexos.
- Confiabilidade e retenção: `ares_campaign_v3.landing_reliability` e `landing_screenshot_cleanup`. Após COMPLETE + recibo de entrega VERIFIED, a limpeza usa allowlist de raízes/imagens por linhagem, protege referências de jobs incompletos e preserva metadados/recibos antes de apagar. Nunca executar validação por imagens já purgadas nem reabrir PASSED para substituí-las.
- Abertura/fechamento: esperar readbacks curtos e limitados de registro da janela sem repetir hotkey ambíguo; ler verdict estruturado inclusive quando aninhado. No Chrome, distinguir o botão Close da aba do Close nativo pela linha/posição dos botões Minimize/Restore, não apenas pelo rótulo. A correção é do observador, sem alterar driver compartilhado ou proteção do navegador.
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

### Vincular a sessão real em execução foreground autorizada

Antes de qualquer input, conferir a identidade da sessão corrente. Se for necessário resolvê-la pelo estado nativo, abrir `state.db` em `mode=ro`/`query_only` e consultar apenas a conversa atual:

```sql
SELECT s.id, s.source, s.thread_id
FROM session_turn_leases AS l
JOIN sessions AS s ON s.id = l.conversation_id
WHERE l.expires_at > ?
  AND s.source = 'discord'
  AND COALESCE(NULLIF(s.thread_id, ''), s.chat_id, '') = ?;
```

Vincular os parâmetros à hora real e à thread atual; exigir uma única sessão viva e identidade compatível com a origem do turno. Propagar esse ID comprovado para o ambiente do subprocesso e para `--pc1-session-id`, então conferir o readback de `acquire --agent ares --session-id <sessão real> --thread-id <thread atual>`. Não gerar um ID para satisfazer o guard nem reutilizar o ID de um worker encerrado. Resolver a sessão não autoriza ignorar gates de prioridade ou tomar a lease de outro trabalho.

Reservar o job existente com `Queue.claim(owner, ttl=...)`, conferir que a chave retornada é exatamente a pendência autorizada e só então persistir `begin`. Se outra tarefa for selecionada, usar `defer` e liberar a lease sem navegar. O rótulo `owner` é apenas a reserva lógica, nunca a prova de identidade nativa. Depois do `result`, reutilizar `flush(q, Discord())` do controlador existente para fechar o aviso coletivo e exigir `messages.state=VERIFIED` mais GET de conteúdo/autor/destino. Liberar a lease física em `finally` após fechamento seguro; se houver erro antes do registro, conservar as provas e o estado necessário à reconciliação.

## Recuperar uma entrada ignorada após mensagem durante a execução

- Antes de reparar uma entrada `IGNORED`, reler o mesmo `native_intake`, o job por request e a evidência terminal canônica. Uma mensagem corretiva durante a execução pode existir no banco nativo como `role=user` sem `platform_message_id`, embora seu envelope e o pedido canônico preservem a origem. Isso faz `origin_for_delivery` retornar `None`; não significa campanha incompleta nem ausência de pedido.
- Para recuperar somente o pedido expressamente autorizado, usar a origem exata do `request` terminal salvo, exigir estado concluído e posterior ao `activation_epoch`, e fazer GET do ID exato da conclusão informado pelo operador. Conferir ID, conteúdo contra `delivery_obligations` entregue, autor, thread e pai. Não inferir a mensagem apenas pelo horário nem preencher recibo sem GET real.
- Reutilizar `build_from_source` e `Intake.arm`, com gate de domínio e recibo verdadeiro do mesmo pedido. Preservar o estado ignorado anterior em evento; registrar a recuperação nos registros pai/filho de `native_intake`. Não alterar banco nativo, estado de campanha, cursor global, marco de ativação nem outras entradas ignoradas. Conferir em nova conexão read-only o job, todos os links, o recibo e os IDs. Uma segunda execução deve reconciliar o mesmo job, nunca criar outro.
- Conferir consumidor e reserva vigentes sem iniciar outro observador. `RUNNING` com links `READY` significa somente executor reservado/preparando; não afirmar que houve abertura nem validação. Essa recuperação pontual não corrige, por si, o reconhecimento automático de mensagens durante a execução.

## Captador automático — mensagens durante execução e pedidos agrupados

- `origin_for_delivery` aceita o ID nativo da linha e, quando ele estiver ausente, somente o envelope midturn exato do runtime no início/fim da mensagem de usuário. Conferir plataforma, thread/chat, pai e igualdade de `message_id`/`source_message_id`; conteúdo citado ou envelope de outra partição falha fechado. Isso apenas identifica a origem: prova terminal salva, domínio e resposta real no Discord continuam obrigatórios.
- `request_payloads` resolve o pedido simples ou a conclusão agregada salva em `audit/shein/campaigns/intake/<request_id>/final-verification.json`. Para agregado, enumerar todos os grupos declarados; validar a identidade literal dos filhos, conta, origem, IDs únicos, quantidades e total contra cada estado terminal/readback salvo. Não escolher o primeiro filho nem fazer glob aproximado para adivinhar evidência. Validar a cobertura inteira antes de armar jobs.
- Vincular todos os filhos ao mesmo `native_obligation_id`/recibo real. O pai `native_intake` só fica `READY` depois da enumeração completa; isso preserva a confirmação única do pedido humano, sem notificações prematuras. Reexecutar o intake deve reutilizar os jobs, não repetir criação, navegação ou postagem.
- Reconsiderar entradas antigas `IGNORED` uma vez por geração da correção, em lotes limitados, somente se a entrega ocorreu após `activation_epoch`. Priorizar `PENDING` e selecionar apenas registros pai; filhos não podem ocupar essa rodada nem provocar loop de revisão. Marcar ignorados já avaliados com a geração corrente. Não resetar cursor, ativação, contadores ou `PASSED`, e não alterar banco nativo ou fluxo de criação.
- Testar os dois casos positivos e seus negativos: envelope citado/malformado/fora da partição, fonte antiga, grupo faltante/incompleto, conta/origem divergente, IDs repetidos, total inconsistente, idempotência e recuperação sem starvation. Testes usam fixtures offline; prova operacional exige GET e nova leitura da fila real.

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

NO_AD: exigir identidade/fechamento/preservação reais, screenshot de fechamento e **observation_screenshot da abertura atual**, `network_ad_confirmed=false` e `visual_review` explícita da ausência. O código confere a ordem abertura → imagem de ausência → fechamento. Falha de captura, imagem antiga ou página não verificada é erro técnico, não ausência. Política vigente: 3 ausências iniciais, **sem espera artificial entre elas**; após result NO_AD/WAIT_RETRY, chamar `retry-now --key <key> --owner <owner> --index <idx> --pc1-session-id "$HERMES_SESSION_ID"`, novo begin e nova janela na mesma sessão. O código impede ultrapassar o limite. Provas são isoladas por key/idx/attempt sob a pasta da execução; não reutilizar o arquivo de abertura anterior. Depois da terceira ausência, `DEFERRED_NO_AD` e próximos links. Ao terminar a fase inicial, 1 tentativa final por pendente; nova ausência vira `REVIEW_REQUIRED`. Somente ao terminar a fase final, outbox reporta aqui os links para revisão de Rodolfo, com GET. As duas ausências anteriores não são zeradas. Regra antiga de 2 tentativas explicitamente supersedida; histórico no audit.

ERROR: diagnosis concreta e estado parcial. Fechamento comprovado ou no_tab_opened verdadeiro libera retry técnico; estado ambíguo exige recovery. No-tab em reconcile também exige browser_inputs_zero_verified com leitura da sessão. Não alegar screenshot/visibilidade sem arquivo real.

Intervenção imediata: human_action_required=true, required_action concreta e diagnosis. O outbox registra o vínculo e só publica nesse caso, exceto o relatório final de revisão após 3+1 expressamente autorizado por Rodolfo. Não transformar dificuldade do agente em necessidade humana presumida. Se a aba continuar incerta, WAITING_HUMAN_UNCLOSED impede outros inputs.

## Diagnóstico por estado

- READY/WAIT_RETRY: consumidor deve retomar automaticamente quando due e recurso/prioridade permitirem.
- RUNNING: worker reservado para uma URL; pode ainda estar preparando ferramentas, sem input no PC1. Conferir claim vigente, lease e readback da mesma tentativa antes de afirmar observação em andamento. `OPEN_INTENT` é intenção durável anterior à navegação, não prova de página aberta.
- NEEDS_RECONCILIATION/ATTENTION: cleanup de aba incerta exige RECONCILING. Ausência com fechamento já comprovado segue os contadores da política finita 3+1; não repetir reconciliação do mesmo fechamento. A rodada congela os pares na primeira deferral para que pedidos posteriores não adiem indefinidamente o retorno final.
- RECONCILING: readback/cleanup somente; reconcile --resume após prova segura, depois a fila faz a nova observação separadamente. Quando `technical_probe_evidence_path` existir, o alvo exato é o probe, não uma landing antiga.
- TECHNICAL_REPAIR: três erros técnicos consecutivos atingiram uma trava real; sem nova abertura ordinária. Outros itens devidos seguem após cleanup seguro.
- REPAIRING: fase exclusiva de diagnóstico/correção local. Sob a lease real, executar pelo Python do Hermes `scripts/ares-direct-traffic-repair.py --key <key> --owner <owner> --index <idx> --pc1-session-id "$HERMES_SESSION_ID" --repair-note '<causa e reparo reais>'`. O runner testa e verifica janela vazia/captura/fechamento, sem URL; só o recibo real libera retry. Falha parcial exige ler technical-probe.json e preservar/reconciliar a janela; `defer` rejeita probe incerto.
- OBSERVED: todas as URLs do job técnico passaram; o pedido humano ainda pode ter outros jobs pares pendentes. Agrupar por native_obligation_id do recibo, exigir intake READY e todos os pares PASSED antes de uma única notificação. Não refazer navegações.
- COMPLETE: todos os PASS + confirmação ao gestor GET verificada.
- DEFERRED_NO_AD: três ausências iniciais já registradas e fechamento seguro; continuar os próximos links. O módulo `ares_campaign_v3.landing_retry_policy` ativa uma única tentativa final por pendente depois de acabar a fase inicial.
- REVIEW_REQUIRED: ausência também na tentativa final; sem nova visita automática. Quando terminar a rodada final, relatório durável nesta thread identifica pedido, conta, campanha/UTM e URL para revisão de Rodolfo. Evento `finite_review_report_authorized` libera somente esse relatório; entrega exige GET. Informes recorrentes encerram após os relatórios verificados, sem chamar pendência de PASS/COMPLETE.
- WAITING_HUMAN/WAITING_HUMAN_UNCLOSED: ação humana indispensável comprovada ou fase 3+1 esgotada com pedido explícito de revisão. Aba incerta continua bloqueando navegação; preservar tudo e nunca repetir postagem ambígua.

O consumidor usa timer existente; não criar cron Hermes com entrega origin/all. A conversa de controle/status do acompanhamento não bloqueia seu próprio worker; turnos de campanha nos demais canais mantêm prioridade. Após processo morrer, a liberação de reserva órfã exige source=tool da sessão, payload/owner ligados ao mesmo job e ausência de processo vivo; erro/ambiguidade não autoriza liberar.

## Prioridade temporária e informes solicitados

Ler `current_priority` e a permissão ativa antes de selecionar um alvo: modos legados com alvo nominal no runtime não são defaults permanentes. Uma nova instrução expressa pode superseder a ordem, mas não interrompe cleanup nem observador vivo, não zera tentativas e não reativa permissões aposentadas. Preservar o contrato anterior em auditoria e atualizar informe/checkpoint para a ordem real.

Congelar os pares da rodada quando houver adiamento, para que pedidos posteriores não posterguem indefinidamente a tentativa final. Contar pares `OBSERVED` como navegações concluídas para decidir o retorno: esperar `COMPLETE` criaria deadlock quando o aviso coletivo depende do próprio alvo adiado. Manter FIFO entre os demais e prioridade de cleanup para `NEEDS_RECONCILIATION` ou prova de fechamento ausente. Aplicar a política finita vigente `no_ad_retry_policy` de três ausências iniciais e uma tentativa final, preservando o histórico; autorizações históricas de ciclos extras não devem ser ressuscitadas.

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
5. Classificar com evidência: READY/WAIT_RETRY = aguardando; RUNNING exige claim vigente e consumidor/lease compatíveis, mas pode ser somente preparação; OPEN_INTENT = intenção persistida antes do input, ainda sem prova de abertura; navegação exige readback do desktop ligado à mesma tentativa. NEEDS_RECONCILIATION/ATTENTION = recuperação pendente, não execução normal; PASSED = URL validada; OBSERVED = URLs do job técnico validadas, exigindo conferir os pares do mesmo pedido humano antes de classificar como mera pendência de notificação; COMPLETE exige mensagem de sucesso do outbox verificada. Timer ativo, contador incrementado, teste aprovado ou migração para retry não provam visita nem avanço visual.
6. Fazer GET das respostas originais e de cada mensagem de sucesso já existente pelo transporte corporativo autorizado; conferir destino, autor e conteúdo. Se todas as URLs passaram mas o envio estiver pendente, relatar pendência de entrega e reconciliar o outbox, sem repetir POST ambíguo. Se ainda houver URLs não aprovadas, explicar que não é apenas falta de mensagem.
7. Conferir serviço/timer, claim e lease atuais para identificar gargalo, sem tocar no desktop de outro executor. Para espera por prioridade, conferir `native_busy` em `ares_campaign_v3.landing_intake` e as leases não expiradas de `session_turn_leases JOIN sessions ON sessions.id=session_turn_leases.conversation_id`, com `sessions.source='discord'`, excluindo a thread de controle conforme o contrato. Ler o banco nativo somente em `mode=ro`/`query_only`; retornar só campos necessários. Separar o último `WAITING_NATIVE_TURN` do gate atual: turno concorrente não é necessariamente criação nem uso do desktop. Uma URL incerta pode segurar gestores posteriores na FIFO global; explicar sem sugerir que a criação foi pausada. Não cancelar nem iniciar outro observador para acelerar a consulta.
8. Atualizar somente os estados que mudaram antes de fechar o relatório. Informar horário do snapshot, bullets por gestor/conta com campanhas e status, total de URLs por estado e exclusões anteriores à ativação. Validar que os totais agregados fecham e que todos os requests elegíveis têm correspondência antes de afirmar cobertura completa; não prometer prazo sem medição.

### Consulta curta de pendências ou tentativa recente

Para responder apenas quais links faltam, se houve nova visita ou o que existe além de um lote, começar por uma consulta curta; a auditoria completa da origem acima é necessária somente para afirmar cobertura de todo um período/canal.

1. Ler `progress_reporting.report_jobs` para o recorte do informe e comparar com todos os `jobs` da fila. Projetar `jobs.state`, `links.idx/state/attempt/due` e os últimos eventos `claimed`, `open_intent`, `observation_result` e reconciliação. Não despejar payload/evidência completos.
2. Para listar URLs, usar a landing resolvida da evidência ou do payload canônico, nunca inventar destino pelo slug. Aplicar o gate de domínio antes de mencionar qualquer alvo; preservar a query byte a byte. Deduplicar e contar em código, mantendo combinações de UTMs distintas mesmo quando a landing-base é igual. Preferir campanha + link clicável, sem anexo ou preview desnecessário.
3. Ler `messages` nos estados `PREPARED`/`INTENT` e agrupar jobs `OBSERVED` pelo `native_obligation_id` em `native_receipts`. Informar quando a confirmação coletiva depende dos próprios links já listados: não contar essa dependência como outra fila de navegação. Outbox vazio não significa pedido integral concluído.
4. Se a pergunta mencionar outros atendimentos, conferir o gate nativo atual conforme o passo 7. Limitar a conclusão: nenhum outro turno ativo agora não prova que não existam pedidos agendados ou trabalho fora do acompanhamento.
5. Responder primeiro à pergunta direta e depois dar estado e horário. Dizer explicitamente quando só houve enfileiramento/preparação; reservar abertura, anúncio visível e conclusão para suas provas próprias. Não aguardar o worker nem disputar sua lease apenas para melhorar uma resposta de status.
