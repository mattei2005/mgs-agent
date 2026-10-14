# Acompanhamento de landing após criação — contrato comum

## Autoridade e limites

Fonte única: `/root/mgs-agent/data/ares/meta-ads/policies/direct-traffic-landing-followup.json`. Ler nessa fonte a autoridade vigente, o destino `all_problem_destination_thread` e a mensagem de sucesso; não copiar IDs de conversa para o procedimento nem interpretar “aqui” como a sessão atual. Aplica-se a TODA estratégia de tráfego direto: CAR, SHEIN e futuros nichos. Não BOT/Messenger. Não herda budget, evento, conta, horário ou lifecycle de outro nicho. Não cria campanhas de teste nem faz backfill sem autorização própria; não escreve GAM, WordPress, Router, financeiro, quiz, credenciais ou Meta.

A observação é visita técnica pontual autorizada, sem cliques em anúncios e sem tentativas de contornar filtros de tráfego inválido, CAPTCHA ou autenticação. Não trocar proxy/fingerprint/extensões, desativar bloqueadores, usar perfis pessoais como fallback ou gerar impressões adicionais para buscar um resultado. Uma segunda tentativa só cabe na ausência prevista de anúncio; outro erro vai à thread de problemas.

## Isolamento vigente — prioridade absoluta dos pedidos

Rodolfo corrigiu expressamente: o acompanhamento é TOTALMENTE SEPARADO e não pode comprometer velocidade/performance de criação. A rota de pedidos não prepara handoff, não carrega esta referência, não chama fila/PC1, não troca o transporte de resposta e não possui callback síncrono nem etapa adicional, inclusive depois do envio enquanto o runner ainda está retornando. O pedido termina e responde pelo caminho nativo existente. Somente um processo independente posterior pode descobrir/enfileirar a conclusão já entregue, sem disputar lanes/quota Meta nem recursos críticos com campanhas. Falhas desse processo nunca reabrem ou atrasam criação.

Estado atual: consultar `status` no contrato. `HELD_FOR_FULL_ASYNC_ISOLATION` significa somente acompanhamento suspenso, sem hold de campanhas. Não reativar o timer/worker nem restaurar o wrapper até validar gatilho realmente externo e isolamento de recursos. O callback antigo foi removido e a rota do diário comparada byte a byte com a baseline anterior à mudança; isso prova remoção do acréscimo, não um benchmark universal de latência.

## Fila única PC1 — todos os gestores

A política `pc1_queue_policy` do contrato, reafirmada por Rodolfo, exige UMA fila FIFO global para G001–G006, contas, canais e futuros gestores; nunca uma fila/worker por gestor. Pedidos G001 e G006 simultâneos preservam a criação paralela existente e geram somente tarefas de acompanhamento em espera. Há no máximo uma tarefa ativa no PC1, protegida também pela lease física comum entre agentes. A tarefa mais antiga mantém a ordem durante os 60s da retentativa e conclui/fecha suas próprias abas antes de liberar a seguinte. Fechamento incerto bloqueia o acompanhamento para readback, não os pedidos de campanha. Validar disputa real de duas conexões de fila simultâneas e ordem FIFO entre duas contas/canais; não inferir exclusão global de um teste com apenas um pedido.

## Histórico supersedido — NÃO EXECUTAR a integração acoplada

Os passos e o handoff abaixo são preservados apenas como histórico da versão retirada. NÃO executar stage/publish-creation nem qualquer desses preparativos na rota de pedidos. A ordem de observação e as provas do worker continuam contratadas, mas o gatilho independente ainda precisa ser validado.

1. Execute criação/duplicação pelo Engine v3 da operação; termine TODO o QA/readback/postprocess existente. Guarde os IDs finais e o arquivo de prova canônico imutável. Não mude o hot path nem mantenha lease Meta enquanto observa páginas.
2. Materialize um handoff local da fila apenas com a conta/canal/thread do pedido atual e todas as combinações únicas de destino + UTMs novas dos conjuntos, a partir dos creatives realmente lidos. A ordem é estável. Parâmetros `url_tags` sobrescrevem duplicados da Website URL conforme o contrato Meta; materialize macros somente com os IDs reais do mesmo anúncio. Nunca use UTMs da fonte, preserve todos os parâmetros aprovados e valide o gate de domínio antes de guardar qualquer URL. Não descubra/globalize outros gestores ou contas.
3. A landing do acompanhamento é a página com a rede publicitária, nunca a quiz/chat. Registre `landing_url` e `mapping_source` somente quando a relação estiver provada por contrato/runtime read-only. Não infira o slug nem use uma URL parecida. Se o mapeamento ainda não estiver disponível, omita `landing_url`: o worker o resolverá depois da resposta, ou reportará o problema no destino definido pelo contrato. A resolução não pode atrasar a resposta normal de criação.
4. Stage é local/durável, sem navegador, sem Meta e sem mensagem: `python3 /root/mgs-agent/scripts/ares-direct-traffic-followup.py stage --input <handoff.json>`. A fila fica `WAITING_CREATION_REPLY`; ainda é proibido abrir qualquer landing.
5. Escreva o resumo NORMAL de conclusão do gestor em arquivo de texto, com fonte/quantidade/IDs ou números, budget, status, início e ressalvas reais. Envie essa resposta pela barreira comum: `python3 /root/mgs-agent/scripts/ares-direct-traffic-followup.py publish-creation --key <key retornada> --message-file <resumo.txt>`. Ela publica como Ares na thread original, faz GET do ID/conteúdo/autor e SÓ ENTÃO libera a fila. Não publique a conclusão uma segunda vez pela resposta final do chat. Se o ambiente exigir uma resposta final, use apenas uma confirmação curta, sem repetir o relatório.
6. O timer separado consome a fila após a resposta confirmada. Ares não espera a observação para concluir criação e não relaciona o trigger ao horário de início. Não crie cron Hermes origin/all nem gateway hook ad hoc. Não diga ao gestor que o acompanhamento terminou antes do outbox de sucesso real.
7. Se staging/integração falhar, preserve a criação validada, entregue seu resumo normal ao gestor e reporte somente a falha do acompanhamento ao destino `all_problem_destination_thread` do contrato, mantendo o handoff resumível. Nunca repita criação para corrigir a fila.

**SUPERSedido por isolamento total:** o wrapper de conclusão e o callback `landing_followup_adapters.after_daily_reply` não integram mais a rota de pedidos. O callback foi retirado do diário CAR/CPV e o comando publish-creation foi bloqueado pelo hold. Este desenho antigo não é modelo para novos runners; nenhum runner de campanha deve usar essa barreira.

### Handoff (campos obrigatórios, dados REAIS)

```json
{
  "strategy_family": "DIRECT_TRAFFIC",
  "creation_status": "COMPLETE_FUTURE_ACTIVE",
  "request_id": "ID literal do request já concluído",
  "operation": "operação exata",
  "account_id": "ID Meta",
  "source_channel_id": "pai real",
  "source_thread_id": "thread original do gestor",
  "campaign_ids": ["IDs confirmados de todas as novas campanhas"],
  "creation_proof": "/root/mgs-agent/data/ares/meta-ads/.../readback-final.json",
  "creation_proof_sha256": "SHA256 calculado do arquivo real",
  "links": [{
    "campaign_id": "ID confirmado",
    "effective_campaign_url": "destino efetivo + parâmetros novos lidos",
    "landing_url": "landing comprovada + query EXATA do link efetivo",
    "mapping_source": "fonte canônica/runtime read-only da relação",
    "destination_kind": "LANDING_PAGE"
  }]
}
```

O exemplo acima é schema explicativo, não payload executável. Nunca substitua por IDs ou resultados inventados. `creation_proof` deve ser JSON terminal do mesmo request e conter os IDs alvo; digest errado, estado parcial, UTM duplicada/macros não resolvidas, mudança dos bytes da query, conta/canal incorretos ou quiz como landing bloqueiam o staging. Deduplicate somente combinações idênticas; conjuntos distintos não podem desaparecer. Preserve o original do readback e sua proveniência.

## Worker de observação (uma tentativa por execução)

O consumidor é uma sessão CLI limitada do próprio Ares, com resultado técnico SOMENTE local. A fila é determinística; a decisão visual é feita pelo Ares usando capturas reais. Isto não é um detector automático de anúncio baseado apenas em iframe/slot. Provas de visibilidade não podem ser substituídas por flag de script carregado, iframe vazio, GPT inicializado, HTTP200 ou botões da própria página.

1. Primeiro confira o contrato: enquanto `HELD_FOR_FULL_ASYNC_ISOLATION`, encerrar sem PC1, modelo, notificações ou retomada do acompanhamento. Quando o processo independente estiver devidamente liberado, consulte a fila e os checkpoints ativos/resumíveis AdsPower/PC1. Use a fila global já existente: não ultrapasse outro pedido anterior. Antes de qualquer input/captura operacional, adquira a lease comum `mgs-pc1-computer-use-lock.py` como Ares, usando o ID REAL da sessão e a thread de problemas. Renove antes de vencer; libere em `finally`. Se ocupado, `defer` na fila, sem tentativa nem alerta falso.
2. Carregue `adspower-segurador-token-collector/references/pc1-remote-adspower-operations.md` e `computer-use`. Use Chrome comum no PC1, não abra perfil AdsPower/Facebook para essa visita. Preserve outras abas. Uma janela técnica anônima com uma aba-guarda vazia é permitida; cada URL/tentativa precisa de uma ABA NOVA além da guarda, nunca reutilizada. Não exponha títulos/observações pessoais. Depois de input ambíguo, recapture antes de qualquer retry. Foreground é permitido pela observação com aba ativa, mas somente após sinal de escalação do driver.
3. Resolva a landing por evidência real antes da navegação. Não clique na quiz para chegar nela; leia sua configuração/destino publicamente ou pela fonte read-only autorizada. Passe domínio pelo gate. Use os parâmetros exatos da URL nova, sem reescrever o wrapper. Se não resolver, registre `begin` + `ERROR` com diagnóstico de mapeamento e nenhuma abertura; o outbox avisará no destino de problemas do contrato.
4. Antes do único open, persista `begin --key ... --owner ... --index ...` usando o CLI comum. A fila grava `OPEN_INTENT` antes do side effect. Capture a janela alvo e suas abas, abra a URL em ABA NOVA e registre sua identidade real (window/tab e evidência antes/depois). Identifique a URL real e a aba ativa, não somente o texto digitado. Nunca feche aba preexistente, nunca use close-all e nunca restaure browser incerto por restart.
5. Procure o anúncio renderizado da rede com espera limitada e rolagem de conteúdo se necessário, sem cliques nos anúncios. Se apareceu, comece o cronômetro SÓ ENTÃO. Mantenha a aba ativa e anúncio visível por pelo menos 10 segundos contínuos. Capture screenshots novos em intervalos de até 10 segundos; prefira 5. Use relógio real via ferramenta (`time.monotonic()`), não contagem mental. Se perder visibilidade/foco, reinicie a observação; nunca some trechos desconexos.
6. Feche APENAS a aba aberta para a tentativa e confirme seu desaparecimento + preservação das outras por nova captura/estado. Só então conclua o resultado. Janela técnica/guarda de propriedade exclusiva da tarefa pode ser fechada após confirmar que nenhuma aba alheia foi incorporada. Se não puder confirmar identidade/fechamento, reporte ERROR e preserve estado para reconciliação; não tente outra URL.
7. Primeira tentativa SEM anúncio: registre `NO_AD` + fechamento real. A fila aguarda 60 segundos completos e só então permite outra execução da MESMA URL em OUTRA aba nova. Não avise na primeira ausência. Não avance para o próximo link deste pedido durante essa espera.
8. Segunda ausência: registre `NO_AD` com outra identidade de aba. O outbox avisa SOMENTE o destino `all_problem_destination_thread` do contrato, com pedido, conta, URL e diagnóstico. Outros erros também vão somente a esse destino, nunca à origem do gestor. Não marque como sucesso e não reabra automaticamente um intent incerto. Reconciliar a mesma tarefa/IDs e continuar somente a camada faltante; gates críticos permanecem.
9. Sucesso de uma URL não é sucesso do lote. O outbox só publica na thread do gestor quando TODAS estiverem PASSED, exatamente: `Todas as landing pages deste pedido foram abertas, com anúncios visíveis por pelo menos 10 segundos em cada uma.` Não mencione PC1 e nunca declare cadastro GAM sem outro readback específico.

### Comandos internos do consumidor

```text
python3 /root/mgs-agent/scripts/ares-direct-traffic-followup.py show --key <key>
python3 /root/mgs-agent/scripts/ares-direct-traffic-followup.py begin --key <key> --owner <owner do dispatcher> --index <índice> --pc1-session-id <ID real desta sessão>
python3 /root/mgs-agent/scripts/ares-direct-traffic-followup.py defer --key <key> --owner <owner>
python3 /root/mgs-agent/scripts/ares-direct-traffic-followup.py result --key <key> --owner <owner> --index <índice> --pc1-session-id <ID real desta sessão> --result PASS|NO_AD|ERROR --evidence <arquivo-real.json>
```

`defer` é somente pré-open, nunca após OPEN_INTENT. Uma execução observa uma única tentativa e sai; timer faz a espera/retry sem sleeper longo na conversa. Não execute publish-creation/result de outro pedido.

### Prova de resultado

Para PASS: JSON com `observed_url`, opcional `resolved_landing_url` + `mapping_source` se resolvido no worker, `new_tab_identity` real, `tab_closed_verified=true`, `other_tabs_preserved=true`, `closed_screenshot` real, `network_ad_confirmed=true`, `ad_description` descritiva do criativo visto e `samples` de pelo menos três capturas distintas com `monotonic_seconds`, `ad_visible=true`, `tab_active=true`, `screenshot`. Os timestamps reais dos arquivos também precisam abranger >=10s sem lacuna >12s. Não invente observações, identificadores ou tempos. A fila calcula hashes e preserva imagens revisadas em artifacts protegidos; não manda anexos ao chat.

Para NO_AD: identidade real da aba nova + `tab_closed_verified`, `other_tabs_preserved`, `closed_screenshot`. Para ERROR: diagnóstico humano exato, sem trace/path/credencial, mais quaisquer provas/estado parcial disponíveis; use `no_tab_opened=true` SOMENTE se realmente nenhum open ocorreu. Não afirmar fechamento/URL visibilidade quando incertos.

`begin`, `result` e `reconcile` verificam mecanicamente que a lease física pertence ao Ares e ao mesmo `HERMES_SESSION_ID` real. Um estado NEEDS_RECONCILIATION bloqueia novos observadores; após readback e fechamento seguro da aba incerta, usar `reconcile --key ... --index ... --pc1-session-id ... --evidence ...`. Essa recuperação libera as demais URLs, mas mantém a afetada pendente/ATTENTION; nunca converte incerteza em sucesso nem reabre a URL às cegas. Preservar o incidente para recuperar somente a camada comprovadamente faltante.

## Durabilidade e manutenção

SQLite WAL + FULL, job imutável por operação/conta/request, links indexados, estados/intent e outbox transacionais. Um consumidor global, lease física cross-agent e IDs de mensagem com GET. POST ambíguo é reconciliado por ID/nonce, nunca repetido cegamente. Crash deixa NEEDS_RECONCILIATION e avisa no destino de problemas do contrato, sem replay de aba ou campanha. Saída CLI/stdout/log é local; nenhum `Cronjob Response`, job_id, PID ou trace chega à conversa. Sem fila pendente, o timer não abre navegador nem inicia modelo.

## Validação e comunicação por camada

1. Exercitar a máquina de estados e o outbox sem rede com `python3 -m unittest discover -s /root/mgs-agent/tests -p test_direct_traffic_landing_followup.py -v`. Cobrir resposta antes de open, tentativa silenciosa, 60s completos, aba diferente no retry, fechamento incerto, crash, POST ambíguo, isolamento de conta/canal e sucesso somente com cobertura integral.
2. Rodar a regressão dos adapters e do Engine pelo test runner/interpreter declarados pelo projeto. Se uma verificação falhar, comparar o mesmo teste com a baseline anterior à mudança antes de classificá-lo como preexistente. Documentar separadamente aprovados, falhos e desmarcados; excluir um teste da seleção não o transforma em aprovado. Não mudar regra de campanha ou credencial para satisfazer um assert histórico fora do escopo.
3. Conferir isolamento real do consumidor: nenhum import/callback/wrapper/etapa adicional nos runners de criação e nenhum preparo do acompanhamento na sessão de pedidos. Comparar o runner restaurado com a baseline anterior, testar ausência de dependência e validar separadamente o gatilho externo pós-resposta. Timer ativo, fila vazia e smoke CLI não provam essa integração nem preservação universal de latência. Congelar a prova de criação em arquivo do próprio observador, sem escrever no audit/state da campanha. Não liberar o acompanhamento até provar essa fronteira.
4. Distinguir o ensaio técnico de navegador da observação produtiva. Abrir/fechar uma aba vazia comprova apenas transporte, propriedade e cleanup; iframe, script carregado e testes com mocks não comprovam anúncio visível. Capturas reais e tempo contínuo sustentam a observação; somente readback próprio do GAM sustenta cadastro das UTMs.
5. Quando o primeiro teste produtivo tiver sido reservado ao pedido natural de um gestor, concluir a instalação técnica sem criar campanha canário ou abrir links históricos. Informar explicitamente que a validação ponta a ponta permanece para esse pedido, sem apresentar o fluxo inteiro como já observado em produção.
