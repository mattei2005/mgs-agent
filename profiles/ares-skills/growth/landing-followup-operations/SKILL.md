---
name: landing-followup-operations
description: "Use when observing landing ads after campaign completion."
version: 0.5.1
author: Rodolfo Mattei / Ares
license: internal
platforms: [linux]
metadata:
  hermes:
    tags: [mgs, growth, landing, pc1, recovery, queue]
    related_skills: [computer-use, direct-traffic-cbo-operations]
---

# Acompanhamento de landings — operação enxuta

Observar anúncios depois da conclusão de uma criação/duplicação, sem acrescentar etapas ao criador de campanhas. Receitas de execução, intake, reconciliação e notificações ficam em [runtime-and-recovery](references/runtime-and-recovery.md).

## When to Use

- Executar ou acompanhar a observação pós-criação de landings com UTMs novas.
- Recuperar intake, tentativa, fechamento, fila ou entrega do acompanhamento.
- Auditar pedidos e pendências, distinguindo criação/ativação, acompanhamento PC1 e entrega de avisos, sem transformar consulta em execução.
- Executar replay expressamente autorizado, preservando os resultados históricos.
- Não carregar como etapa da criação/clone de campanhas.

## 1. Fixar escopo e preparar tudo antes de abrir

1. Ler o contrato canônico `data/ares/meta-ads/policies/direct-traffic-landing-followup.json`, o checkpoint e a fila real. Usar runtime para estado e contrato para autoridade; não inferir execução por testes ou documentação.
2. Congelar o conjunto de pedidos, contas, campanhas e combinações landing + UTMs da rodada. Resolver todos os destinos reais e preparar o mapa antes da primeira navegação; reutilizá-lo entre itens, sem repetir investigação/configuração a cada URL.
3. Validar o domínio pelo gate MGS. Obter a landing da configuração ativa ou prova canônica, nunca adivinhar slug nem abrir quiz/chat como destino. Preservar país, origem, IDs e query literalmente; destinos A/B distintos exigem cobertura própria.
4. Aplicar o flag bare `nocache` conforme a regra ativa: `?nocache` sem query; `&nocache` depois das UTMs existentes. Não acrescentar `=1`, duplicar o flag, reordenar/decodificar parâmetros ou incorporar `?nocache` ao valor da última UTM. Alterar somente a URL da observação, nunca a URL da campanha na Meta. Preservar o endereço de origem na linhagem. Não atribuir um PASS posterior ao cache ou ao modo do navegador apenas por coincidência: se as tentativas sem anúncio já usavam as mesmas opções, o resultado não identifica a causa nem garante entrega futura.
5. Definir antes do início o destino dos informes. Quando solicitado, enviar **uma atualização por item concluído**, no canal/thread indicado, não por um intervalo fixo. Em replay autorizado sem novo aviso ao gestor, registrar essa exceção no contrato/checkpoint da rodada; não estendê-la aos pedidos normais.

## 2. Executar sem trabalho intermediário

Fluxo preferido de Rodolfo: **links preparados → aba nova normal → identificar anúncio → rolar → observar 10 segundos → fechar/verificar → próximo link em outra aba nova**.

- **Sessão significa abertura do link em uma aba NOVA.** Fechar a aba anterior antes da próxima; isso vale também nas retentativas. Nunca substituir a URL de uma aba usada e nunca usar Incognito. Uma janela técnica normal de uma única aba pode assegurar propriedade e fechamento sem tocar no Chrome do usuário.
- Carregar `computer-use`; usar o handler e o transporte PC1 aprovados, sob a lease física compartilhada e com o ID real da sessão. Um observador por vez. Não tomar recurso de executor vivo nem confundir outra conversa Discord com ocupação física do PC1.
- O caminho automático ativo usa `ares-direct-traffic-batch-observe.py`: um worker de preparação por lote congelado e um executor mecânico serial, sem outro turno de modelo por URL. Preparar TODOS os destinos antes de obter o PC1; cachear o mapa ligado ao digest imutável de cada pedido e reutilizá-lo nos retornos. O batch e o CLI individual de compatibilidade `ares-direct-traffic-lean-observe.py` usam o mesmo núcleo `landing_lean.observe_prepared`, que persiste o resultado real. O runner persiste `begin`; não duplicar esse comando. Resolver o Python real do Hermes antes da primeira visita. Manter o backend durante o lote e liberar uma única vez ao final seguro, em vez de fazer teardown/reabertura entre links. Prazo de execução e sinais de pausa só encerram em limite seguro, após fechar a tentativa própria. Confirmar contrato + integração + execução; não confundir sucesso antigo supervisionado com a ativação do automático. Quando o executor tiver sido alterado, usar o primeiro item já autorizado para verificar o ciclo completo antes de ampliar o lote; testes offline não provam input, scroll e fechamento reais. Não acrescentar um canário ou visita extra.
- **Não deixar uma landing aberta enquanto escreve código, documentação, mensagens, inventário ou faz investigação.** Preparar o executor antes; durante a rodada, observar, fechar e seguir. Se precisar reparar, primeiro reconciliar e fechar a tentativa própria.
- Não impor série de screenshots, cadência de captura ou revisão offline de galeria à rota enxuta. Uma leitura visual mínima serve para identificar anúncio real; frame, script, HTTP 200, rótulo PUBLICIDADE ou CTA editorial isolado não provam renderização.
- Depois de uma leitura compositada `app=screen`, selecionar novamente a janela própria e o **Document** da página por captura AX fresca antes de rolar. A leitura de tela não mantém um alvo de input utilizável; scroll sem elemento pode ser recusado. Escalar somente após sinal real do driver e readback, sem repetir input confirmado ou ambíguo.
- Confirmar navegação após Enter. Página em carregamento ou New Tab não é ausência de anúncio: fazer releitura limitada na mesma aba, sem renavegar. Falha técnica é `ERROR`, não `NO_AD`.
- Registrar um recibo compacto com URL efetiva, identidade da nova aba normal, decisão visual, tempo medido e fechamento/preservação nativos. Fechar apenas o alvo próprio e verificar sua ausência antes de seguir; não repetir Close se já houve fechamento.
- Medir preparação do lote, navegação, leitura visual, observação, fechamento, liberação do backend e entrega separadamente. Os 10 segundos são permanência mínima, **não promessa de ciclo total de 10 segundos**. Calcular tempos e contagens em código; informar se a amostra inclui só PASS ou também ausências, erros, pausas e retentativas. Não somar medianas de etapas como se fossem a mediana do ciclo nem extrapolar tentativas aprovadas para o prazo de todo o lote. Medir também o período depois do fechamento: ele revela overhead local sem manter a landing aberta. Não alegar ganho de velocidade sem medição real.

## 3. Aplicar tentativas finitas e preservar histórico

- Até **3 ausências reais iniciais**, sem espera artificial entre fechar/verificar e abrir outra aba nova. Na terceira, marcar `DEFERRED_NO_AD` e seguir os outros links.
- Depois de processar toda a fase inicial, fazer **uma tentativa de retorno final por pendente**. Se ainda não houver anúncio, marcar `COOLDOWN_NO_AD`. Ao encerrar TODOS os itens e retornos do lote congelado, iniciar **um único prazo durável de60segundos** e fazer **uma recuperação automática adicional por link ainda sem anúncio**, sem exigir outro pedido do operador. Liberar PC1/backend durante a espera; o timer existente retoma quando vencer. Novo intake ou novo executor não reinicia o minuto e não posterga indefinidamente os pares congelados. Isso é **3iniciais +1retorno +60s +1recuperação**, no máximo5ausências reais; não é loop por minuto. Ausência na recuperação vira `REVIEW_REQUIRED`, reportada somente depois de encerrar a fase inteira. Falha técnica não consome ausências; PASS nunca é reaberto.
- Interpretar um novo pedido como “tenta de novo”, em resposta a um único pendente identificado, como autorização para **uma tentativa adicional desse alvo**, não para reiniciar o lote ou conceder novamente todas as fases automáticas. Registrar a autorização e preservar as ausências anteriores; usar nova aba normal e as opções de URL vigentes. Se passar, retirar a pendência dos totais, da verificação consolidada e do checkpoint, mantendo o retrato anterior como histórico. Se não passar, manter a revisão e não repetir de novo sem nova autorização. Não zerar contadores ou contornar guards para forçar a execução.
- Preservar contadores e provas já registrados; não conceder três tentativas novas a um item que já teve duas ausências. Congelar os pares da rodada para impedir que pedidos novos adiem indefinidamente o retorno final.
- Nunca reabrir `PASSED` por timeout, notificação atrasada, foto purgada ou necessidade de confirmar um status. Replay exige novo pedido explícito: criar uma rodada identificável, ligada aos mesmos originais, sem zerar nem sobrescrever a validação histórica e sem iniciar observador concorrente. Avaliar o ledger da rodada atual: um PASS antigo não aprova a nova visita, e uma ausência nova não rebaixa retroativamente a validação antiga.
- Três erros técnicos consecutivos do mesmo alvo exigem diagnóstico/reparo da camada local antes de outra abertura ordinária. Com fechamento seguro, seguir os outros itens devidos; janela incerta tem prioridade de reconciliação e mantém o bloqueio físico.

## 4. Recuperar pela tentativa exata, não repetir trabalho

1. Antes de qualquer write corretivo, reler o job, a última tentativa correspondente e seus efeitos reais. Reutilizar request/owner/index e arquivos já persistidos.
2. Selecionar a prova por **rodada + job + índice + número da tentativa**. Não usar “último arquivo do diretório” ou prova de uma abertura anterior: um fechamento antigo pode mascarar uma janela atual incerta.
3. Se a prova completa da tentativa atual já existe, registrar/reconciliar sem outra navegação. Fechamento não prova anúncio; prova parcial não vira PASS. Não fabricar arquivos, tempos, visibilidade ou fechamento para satisfazer um validador.
4. Entrada ambígua exige readback antes de retry. Liberar lease somente após fechamento seguro ou ausência de input comprovada; não liberar apenas porque o processo terminou. Preservar abas alheias e processos vivos.
5. Se uma recuperação gravou duplicata do mesmo evento, preservar o histórico por supersessão e excluir a duplicata das contagens; não tratá-la como outra visita ou outro erro técnico.
6. Corrigir defeitos recuperáveis somente no observador, com testes e readback. Não repetir indefinidamente o caminho quebrado nem transferir um erro local ao operador. O reparador atualizado seleciona, na rota ativa, uma janela vazia **NORMAL**, readbacks nativos e fechamento/preservação; não usa Incognito, série de imagens, galeria ou visita a URL. Provas privadas/cadência legadas permanecem somente legíveis para reconciliação histórica; o reparador não tem mais caminho de abertura anônima e falha fechado se faltar uma rota normal ativa. Probe standalone também deve respeitar observadores com janela incerta. Recibo normal completo da tentativa exata pode ser recuperado sem imagens nem nova visita; é obrigatório conferir vínculo temporal e identidade nativa.

## 5. Informar progresso e encerrar corretamente

- O modo ativo `PER_ITEM` prepara uma mensagem durável na própria transação do resultado, sem HTTP. O consumidor independente do intake entrega os cards e confere GET; o PC1 não espera Discord para abrir o próximo item. Não criar thread/agente por link nem usar intervalos de15min como modo atual. Usar card curto: item, resultado, concluídos/total, pendentes para retorno/revisão e próximo estado real. Preservar o conjunto da rodada nos retornos; deduplicar por job+índice+tentativa+estado. Limitar a drenagem do outbox e preservar INTENT/nonce em erro ou rate limit, sem repetir POST às cegas.
- Contar e deduplicar em código. Separar links, jobs técnicos e pedido humano; partes `OBSERVED` do mesmo pedido não são novos links pendentes.
- Exigir outbox e GET de ID, autor, conteúdo e destino antes de afirmar entrega externa. Reconciliar POST ambíguo por ID/nonce; não repetir envio às cegas. Respeitar rate limit em releituras e reutilizar recibos verificados, sem recapturar landings para conferir mensagens.
- Na operação normal, o sucesso ao gestor depende de todos os pares do pedido humano, da enumeração completa do intake e da entrega verificada. Não publicar sucesso parcial porque um dos grupos terminou.
- Distinguir **fase de execução encerrada** de **todos os links aprovados**. Se houver `REVIEW_REQUIRED`, informar a pendência e registrá-la no checkpoint; `round_complete` ou ausência de processo vivo não convertem revisão em PASS.
- Mais de duas mensagens equivalentes sem progresso real exigem diagnosticar o bloqueio, não enviar outra mensagem igual nem apenas silenciar o watchdog. Timestamp, claim, rótulo do worker e `OPEN_INTENT` não são avanço; PASS validado é.
- Detalhes técnicos ficam locais. Não despejar traceback, comandos, paths, IDs de processo ou avisos de atualização na conversa. Preparar a entrega sanitizada antes de iniciar um processo em background; não deixar a notificação genérica de saída competir com o outbox operacional.
- **Notificação interna de processo antigo não é novo pedido.** Correlacionar o ID com a rodada e o checkpoint; se o resultado já foi consumido, não responder ao operador de novo, reabrir PC1 ou revalidar links. Se necessário, fazer uma única conferência local delimitada e consumir o aviso pelo mecanismo suportado. Depois, encerrar sem recapitulações ou investigação repetitiva de uma tarefa fechada.

## 6. Responder sobre pedidos e pendências

1. Definir o alcance antes de concluir: **fila PC1 vazia e outbox vazio comprovam somente o acompanhamento**, não que todos os pedidos de campanha terminaram. Se a pergunta abranger os pedidos dos gestores, conferir também os pedidos humanos e os estados de criação/QA/ativação; seguir a receita de auditoria da referência.
2. Para pedidos feitos hoje, usar o fuso do operador e o timestamp da mensagem humana original, não a data do nome/início da campanha, a criação do job ou o horário de conclusão. Separar pedidos anteriores processados hoje de solicitações novas; não apresentar o replay anterior como resposta sobre novos pedidos.
3. Enumerar a origem pelo lado dos pedidos, não só pelos sucessos entregues ou jobs existentes. Solicitação ainda em recuperação, QA ou `ACTIVATION_DEFERRED` pode não ter entrado no observador; ausência na fila não é aprovação nem prova de falha do captador.
4. Apresentar por gestor/conta as camadas verificadas: criação, ativação/agendamento, landings e aviso. Uma mensagem humana com várias fontes continua sendo um pedido com vários grupos; contar campanhas e links únicos em código. Não responder que todos deram certo quando somente um gestor concluiu e outro aguarda ativação.
5. Confirmar estado atual da campanha por GET read-only dos IDs persistidos antes de afirmar que continua ativa/pausada. Usar a menor leitura necessária; para resultado histórico, identificar recibo e horário em vez de chamá-lo de estado live. ACTIVE com início futuro comprova habilitação/agendamento, não entrega atual.
6. Manter gates separados: recuperação automática de anúncio ausente não autoriza ativação tardia de campanha. Consulta de status não é aprovação para ativar, retomar writer ou recriar objetos. Informar a pendência e a confirmação exigida na origem, sem executar o write por inferência.
7. Separar resíduos de cadastro de trabalho não realizado. Registros pai/filho de intake podem referenciar pedidos já concluídos; não somá-los como novos links pendentes nem limpar uma divergência de origem apenas porque o request ID coincide. Se a verificação foi apenas do PC1, declarar esse limite na primeira frase, não depois de uma afirmação geral de ausência de pendências.

## Fronteiras e continuidade

- Não alterar criação/conclusão de campanhas, budget, estratégia, início, WordPress, GAM, Router ou financeiro neste fluxo. Não clicar em anúncios nem alterar cookies, proxy, fingerprint ou proteções do navegador. Não afirmar registro GAM sem prova separada.
- Consultas de status e revisões de fluxo/regras são read-only e não disputam o desktop. Conferir contrato, despachante, executor normal, retentativa, reparo, notificações e recibos reais; não validar só o caminho feliz. Separar regras desejadas, comportamento implementado e comportamento exercitado. Destacar ramificações legadas que ainda contradigam o modo ativo, mesmo quando os testes passam; não apresentar recomendações como correções instaladas nem iniciar outra rodada para produzir uma revisão. Banco nativo Hermes somente `mode=ro`/`query_only`; correção do intake não autoriza mudar cursor global, marco de ativação ou reabrir pedidos históricos.
- Preferir o consumidor/timer existente; não criar cron de agente para publicar detalhes técnicos ou concluir etapas diferidas na thread. Manter checkpoint no início, em mudanças materiais de regra/fase e no encerramento.
- Preservar JSON, IDs, UTMs, hashes e recibos. Para imagens legadas, purgar apenas pelo mecanismo autorizado após validação, conclusão e entrega por GET; proteger imagens de tarefas incompletas, outros fluxos e symlinks fora das raízes permitidas.
- Persistir decisões na fonte canônica e procedimentos nesta skill. Testar o comportamento alterado; scripts/configuração exigem inventário e REPORT-INFRA. Reportar na conversa alterações automáticas de skill com alvo, resumo e leitura de confirmação.
