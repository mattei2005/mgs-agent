# Landing follow-up — processo independente pós-resposta

## Fonte e escopo

Fonte única de autoridade, estado, duração, mensagem de sucesso e destino de incidentes: `/root/mgs-agent/data/ares/meta-ads/policies/direct-traffic-landing-followup.json`. O padrão é de tráfego direto — CAR, SHEIN e futuros nichos com contrato direto registrado — e exclui BOT/Messenger. Não copiar IDs de thread para procedimentos nem interpretar “aqui” como a sessão corrente; resolver `all_problem_destination_thread` no contrato.

A autorização original permanece válida. A suspensão técnica anterior foi uma decisão de implementação do Ares, não uma instrução de Rodolfo. O desenho acoplado de stage/publish-creation e callback síncrono está APOSENTADO, não é fallback. Histórico/supersessão: registry e audit da iniciativa apontados pelo contrato.

## Fronteira inegociável: pedido inalterado até o final

- Na rota de criação/duplicação: NÃO carregar esta referência, preparar fila/handoff/landing, trocar transporte de resposta, chamar acompanhamento, esperar PC1 nem acrescentar callback, mesmo depois do POST da resposta enquanto o runner ainda está retornando. Criar, validar, pós-processar e responder pelo caminho nativo existente, sem etapa nova.
- Somente DEPOIS da conclusão e da resposta entregue ao gestor, outro processo descobre o resultado já existente e cria sua tarefa em fila própria. Uma falha nesse processo nunca reabre, trava, retoma ou repete criação.
- O leitor não escreve no banco nativo, no audit/state do criador, em campanha, GAM, WordPress, Router ou financeiro. Não usa quota/lane da Meta e não consulta a Graph para descobrir links: reutiliza provas finais já salvas.
- Runners, mídia, manifest, orçamento, lance, estratégia, início e isolamento de contas/canais permanecem os originais. O gatilho não depende do início programado da campanha.

## Gatilho externo implantado

Runtime: `ares_campaign_v3.landing_intake`, CLI `ares-direct-traffic-followup.py intake`, serviço/timer próprio `ares-landing-intake`. O consumidor PC1 continua em outro serviço/timer, `ares-landing-followup`. Nenhum é um job Hermes com entrega origin/all; stdout e logs são locais.

1. Ler o `state.db` do próprio Ares por SQLite `mode=ro` e `query_only=ON`. Usar o outbox nativo já existente `delivery_obligations`, estado `delivered`; não adicionar hook, coluna, trigger ou write ao gateway.
2. Reconciliar a resposta final exata com a sessão e o mesmo turno humano; procurar os request IDs terminais nos resultados de ferramentas desse turno. Mensagem local final, status de campanha ou timer ativo, isoladamente, NÃO provam entrega da resposta.
3. Ler somente os arquivos canônicos desses requests: estado final SHEIN, audit diário ou request-state/manifest/readback final CAR. Exigir família de tráfego direto registrada, status terminal, conta única, campaign IDs completos e origem consistente. Não promover BOT, fonte ambígua, estado parcial ou IDs inferidos.
4. Fazer GET das mensagens reais de resposta e conferir IDs, autor Ares, thread/pai e conteúdo completo, inclusive chunks. O cursor derivado de tempo é apenas limite de paginação, nunca um message ID observado. Preservar um recibo agregado com os IDs efetivamente retornados; não fabricar resposta API.
5. Congelar a evidência validada no armazenamento do próprio observador, preservando o hash da fonte, sem escrever nada na fonte da campanha. Deduplicar cada combinação de destino + UTMs exatas. Só a confirmação de entrega/readback libera READY na fila.
6. No diário autônomo CAR, ler o audit COMPLETE e seu `discord_readback` nativo já existente. Conferir a mensagem final `V3 CONCLUÍDO`; um message ID anterior de resposta PARCIAL não conclui o pedido. Nenhum callback é necessário no diário.
7. O marco persistido `intake_settings.activation_epoch` exclui mensagens e requests históricos. Não fazer backfill, replay, campanha canário ou navegação histórica porque o leitor foi ligado. Testes com evidência antiga são apenas calibração de parser, sem jobs/navegação.
8. Cursores, recibos e estados de intake são próprios e duráveis. Erro transitório retoma o mesmo evento; depois de possível stage parcial, reutilizar a prova já congelada e o mesmo job. Nunca repetir o POST da resposta original: o leitor NÃO publica a conclusão da criação.

Comandos administrativos do processo separado:

```text
python3 /root/mgs-agent/scripts/ares-direct-traffic-followup.py activate-intake
python3 /root/mgs-agent/scripts/ares-direct-traffic-followup.py intake
python3 /root/mgs-agent/scripts/ares-direct-traffic-followup.py tick
python3 /root/mgs-agent/scripts/ares-direct-traffic-followup.py status
```

`activate-intake` inicializa o marco uma única vez e o preserva em reinícios. Os comandos antigos `stage` e `publish-creation` retornam RETIRED e não podem voltar ao atendimento de pedidos.

## Prioridade de recursos e fila global

O worker consulta, somente para leitura, a lease de turno nativa já existente. Enquanto houver um turno Discord do Ares ativo, ele aguarda; o criador não recebe nenhuma trava nova. Serviços próprios usam prioridade CPU/IO mínima e limites de recursos declarados no contrato/runtime. Não aplicar essas limitações ao gateway ou às lanes de campanha. Igualdade do código do runner prova remoção do acréscimo síncrono, não é benchmark universal de latência.

Há UMA fila FIFO de acompanhamento para todos os gestores, contas, canais e futuros nichos, com no máximo UMA tarefa ativa no PC1; nunca um worker por gestor. A ordem é a de entrada das conclusões elegíveis. G001 e G006 podem criar simultaneamente pelo fluxo normal, mas suas visitas técnicas aguardam na fila única. A tarefa anterior mantém a vez durante o retry de 60s e conclui/fecha suas abas antes da próxima. Fechamento incerto bloqueia somente acompanhamento para readback, não campanhas.

A fila transacional não substitui a lease física cross-agent: Zeus, Ares e outras operações autorizadas podem usar o mesmo desktop. Antes do primeiro input, conferir fila/checkpoints PC1/AdsPower e adquirir `mgs-pc1-computer-use-lock.py` com o ID REAL da sessão. Renovar antes de expirar e liberar em finally; nunca contornar dono ativo ou inferir liberdade por ausência momentânea de input.

## Observação: uma tentativa por execução

1. Ler o contrato ativo e o job recebido. Carregar `computer-use` e a referência de operações PC1 da skill AdsPower. Se PC1 estiver ocupado, `defer` sem começar tentativa e sem alerta falso.
2. Identificar a LANDING PAGE correspondente por fonte canônica/runtime read-only, nunca a quiz/chat. Não inventar slug nem clicar na quiz para chegar nela. Validar domínio antes de guardar/abrir; manter todos os parâmetros exatos da campanha/conjunto novos. `url_tags` tem a precedência validada no link efetivo. Macro não resolvida exige IDs reais da mesma evidência, não valor inventado.
3. Usar Chrome comum no PC1 sem abrir perfil AdsPower/Facebook para essa visita. Uma janela técnica anônima com aba-guarda vazia pode preservar a identidade das abas. Cada URL e cada retry usam uma ABA NOVA além da guarda; nunca reutilizar a anterior. Preservar janelas/abas alheias e não expor títulos pessoais.
4. Antes do open, persistir `begin`/OPEN_INTENT. Após entrada ambígua, recapturar antes de qualquer retry; seguir a escalação do driver, nunca repetir um input confirmado. Foreground para aba ativa só após o sinal aplicável do driver.
5. Confirmar ANÚNCIO DA REDE realmente renderizado. Iframe vazio, script/GPT carregado, HTTP200 e botões da própria página não bastam. Não clicar no anúncio, trocar proxy/fingerprint, desativar bloqueador ou contornar CAPTCHA/IVT/autenticação.
6. Somente após a confirmação visual iniciar **10 segundos contínuos**, com a aba ativa e anúncio visível. Confirmar que a janela/aba de propriedade da tarefa está efetivamente à frente, não apenas capturável em background. Após o sinal de escalação do driver, o `bring_to_front` autorizado pela observação pode manter esse alvo em foreground; não substituir pela janela pessoal/preexistente. Usar relógio real por ferramenta e pelo menos três screenshots distintos, preferindo amostras em 0/5/10 segundos. Timestamps reais dos arquivos e monotônicos devem cobrir >=10s; não somar trechos desconexos. Se perder visibilidade/foco, não declarar sucesso.
7. Fechar somente a aba da tentativa e confirmar desaparecimento + preservação das demais. Só então registrar o resultado e liberar outra URL. Fechamento/identidade incertos exigem erro e reconciliação, não outro open. Fechar guarda/janela técnica somente com propriedade exclusiva comprovada.
8. Primeira ausência de anúncio: NO_AD com fechamento real, sem aviso; fila espera 60s completos e abre a MESMA URL em OUTRA aba nova. Não avançar para o link seguinte durante essa espera.
9. Segunda ausência: NO_AD e incidente somente no destino canônico de problemas. Outros problemas também vão a esse destino, com pedido/URL permitida/diagnóstico, nunca ao gestor. Não marcar link pendente como concluído.
10. Só TODAS as URLs PASSED liberam a mensagem de sucesso exata do contrato na thread do gestor: `Todas as landing pages deste pedido foram abertas, com anúncios visíveis por pelo menos 10 segundos em cada uma.` Não mencionar PC1 e nunca afirmar cadastro GAM sem readback próprio do GAM.

### Recuperação e evidência visual: distinções obrigatórias

- Se o transporte falhar antes de qualquer input de navegador, classificar como `no_tab_opened` por evidência da sessão, não como aba incerta. `OPEN_INTENT` sozinho não comprova navegação. Antes de uma retentativa explicitamente autorizada, conferir ações reais da sessão anterior e estado atual; preservar o mesmo job/request e registrar a reclassificação em evento, sem inventar fechamento ou criar outra campanha.
- Resolver o destino do quiz por leitura da configuração ativa exata do site quando o payload contiver somente a URL de aquisição. Em MGS Direct Quiz, ler somente o item ativo de `mgs_direct_quiz_landings` correspondente ao país/slug e seus destinos; `destination_a_url` e `destination_b_url` divergentes exigem cobertura própria. Usar WP-CLI com plugins/tema pulados para evitar hooks de sincronização, não clicar no quiz e preservar a query original byte a byte.
- Validar os intervalos reais das screenshots antes de PASS: análise auxiliar e round-trips podem exceder a cadência, mesmo com `wait(5)`. Usar timestamps reais e relógio monotônico, sem retimar arquivos nem somar trechos desconexos. Capture de janela não prova foreground: confirmar também pelo desktop compositado durante as amostras. `GetForegroundWindow` via SSH Windows Session 0 pode retornar zero e não diagnostica o desktop interativo.

## Comandos e provas do worker

```text
python3 /root/mgs-agent/scripts/ares-direct-traffic-followup.py show --key <key>
python3 /root/mgs-agent/scripts/ares-direct-traffic-followup.py begin --key <key> --owner <owner> --index <índice> --pc1-session-id <ID real desta sessão>
python3 /root/mgs-agent/scripts/ares-direct-traffic-followup.py defer --key <key> --owner <owner>
python3 /root/mgs-agent/scripts/ares-direct-traffic-followup.py result --key <key> --owner <owner> --index <índice> --pc1-session-id <ID real desta sessão> --result PASS|NO_AD|ERROR --evidence <JSON real>
```

PASS exige `observed_url` exata, `resolved_landing_url` + `mapping_source` se resolvida no worker, `new_tab_identity` real, `tab_closed_verified=true`, `other_tabs_preserved=true`, `closed_screenshot`, `network_ad_confirmed=true`, descrição do anúncio visto e samples novos com `monotonic_seconds`, `ad_visible`, `tab_active`, `screenshot`. O validador confere tempo real, calcula hashes e preserva imagens em artifacts protegidos; não enviar anexos sem pedido.

NO_AD exige identidade real da aba, fechamento/preservação confirmados e screenshot de fechamento. ERROR exige diagnóstico humano seguro e provas/estado parcial disponíveis. `no_tab_opened=true` só quando realmente nenhum open ocorreu. Não inventar IDs, tempos, visibilidade ou fechamento.

`begin`, `result` e `reconcile` conferem a lease física e o HERMES_SESSION_ID real. NEEDS_RECONCILIATION impede novos observadores. Após readback e fechamento seguro, usar `reconcile --key ... --index ... --pc1-session-id ... --evidence ...`: libera os demais links, mas nunca transforma a URL incerta em PASSED ou a reabre cegamente.

## Durabilidade, incidentes e validação

SQLite WAL/FULL, job por operação/conta/request, intake/cursor/recibos próprios, OPEN_INTENT antes de input e outbox idempotente com ID/nonce/GET. POST de notificação ambíguo é reconciliado antes de qualquer retry; nunca publicar outra conclusão da criação. Falha do intake retoma o evento após backoff; diagnóstico fica local e aviso curto sai somente no destino de problemas. Antes de enviar um alerta ainda PREPARED, reconciliar o estado: recuperação já confirmada cancela o alerta não enviado por compare-and-set; alerta com POST incerto exige readback e eventual resolução, nunca reenvio cego ou aviso obsoleto. Nenhum Cronjob Response, PID, path interno, trace ou cabeçalho automático chega ao gestor.

Testar: entrega antes de READY, origem real da mesma sessão/turno, DB nativo mecanicamente read-only, GET externo, chunks, resets, cursor com timestamps iguais, crash entre stage e recibo, ausência de duplicação/repost, exclusão de BOT/backfill, duas conexões simultâneas na fila global, espera do segundo gestor durante retry, 10s aceitos/9s rejeitados, fechamento incerto e sucesso somente integral.

Conferir quatro camadas separadas: (1) código do criador preservado, (2) intake/timers/limites ativos com readback, (3) observação visual real, (4) cadastro GAM específico. Mocks, timer ativo e parser de prova antiga não comprovam anúncio/GAM. O primeiro teste visual produtivo segue sendo o pedido natural de um gestor anunciado por Rodolfo; não criar canário nem abrir links históricos para adiantar essa etapa.
