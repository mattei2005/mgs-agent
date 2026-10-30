# SHEIN IMG — reconciliação de nome adimages (t_8364ae25)

## Resultado e limite

Correção central code-only instalada sob locks da conta937846586033361 e request `shein-1565747351543480374`, via troca atômica do pacote. `require_image` continua estrito. Ares permanece único writer; Zeus não executou campanha, pós-processamento, ativação, upload, reserva ou write Meta/Drive. Não respondeu ao gestor.

## Problema, causa e solução

- Problema confirmado:16 hashes exatos da conta estão ACTIVE/1080x1920, porém seus nomes são título determinístico original + `_105`; a comparação estrita de nome bloqueava `finalize_ready_assets`. Fonte do diagnóstico inicial: `work/t_8f7a90a8/postprocess-image-name-live.json`; repetido por GETs frescos.
- Causa técnica confirmada do bloqueio: tratar o label atual como identidade imutável mesmo depois de upload confirmado e materialização. A causa do sufixo `_105` NÃO foi comprovada; não atribuí a upload, renderer, copy ou pessoa.
- Solução: `image_identity.require_prepared_image` preserva a verificação estrita como padrão e só representa o nome como auxiliar quando a conta/hash/asset/SHA256 completos concordam entre registry associado READY, preparação canônica com asset único, caminho determinístico do intent e recibo READY exato, bytes locais estáticos/SHA256/MD5/dimensões/ACTIVE e identidade Drive disponível no chamador. Não há regex de sufixos nem whitelist `_105`; nenhum dado de produção foi reescrito para acomodar a diferença.
- O mesmo vínculo é usado antes da reserva agrupada, no cache hit de pre-stage, no handoff e antes de finalizar. Registry conhecido inválido deixa de ser tratado como cache miss; missing hash, intent não confirmado, nome ambíguo e provas alteradas bloqueiam sem reupload/reserva. Recuperação de resposta perdida SEM hash confirmado continua estrita e fail-closed.

## Evidências finais

- `regression-stage.json` e `regression-installed.json`:565 testes +455 subtests PASS em45 arquivos, sem exclusões, rede externa ou origem divergente. Inclui IMG/VID, upload ambiguity, reserva, prepare→handoff→finalize repetido com nome alterado, QA semântico/renderizado Chromium real local, activation/status-only e histórico/review exato.
- `real-readonly-installed.json`: ambiente autêntico de worker Ares existente herdado, sem sintetizar HERMES_PROFILE; módulo instalado comprovado. Conta/autoridade/reply/review/descriptor originais revalidados.30 GETs Meta, além dos readbacks Drive.16 imagens/16 registry hits com upload e receipt writes proibidos; função real `load_ready_assets` passou16, com Drive MD5/tamanho iguais aos bytes locais.80 negativos reais rejeitados.
- Mesmas8 campanhas/8conjuntos/16ads PAUSED; fonte002 com targeting/bid90 intactos e alvosCOST_CAP95/USD25.006/007 históricas PAUSED. Runner POSTPROCESS_PENDING, media_qa8; nenhum qa_proof/media_postprocess_complete/activation_result fabricado.28 hashes operacionais preservados (state/core/input/registry/intents/preparation/descriptor e histórico).
- Recibo da publicação e SHA256 de4módulos +2testes: `deployment-receipt.json`. Publicação intermediária e anterior preservadas em `deployment-initial.json` e rollback.

## Rollback

Pacote ORIGINAL anterior à manutenção: `/root/mgs-agent/scripts/.ares_campaign_v3.image-identity-t_8364ae25`. Cópia intermediária: `/root/mgs-agent/scripts/.ares_campaign_v3.image-identity-final-t_8364ae25`. Restaurar código apenas após coordenação com Ares, reconciliação do estágio corrente e aquisição dos mesmos locks. Nunca restaurar snapshots antigos de state/registry/inventory, liberar reservas, apagar/recriar objetos ou alterar manifests para rollback.

## Ocorrências durante validação

- Harness inicialmente contou fixtures importadas/paths duplicados; corrigido para45 arquivos/565 testes únicos, sem excluir casos. Falha local de leitura KeyError no utilitário de geração foi reconciliada pelo arquivo real; nenhum efeito operacional.
- Uma repetição da bateria encontrou `DevToolsActivePort` existente porém vazio e IndexError em `preview_renderer.py:39`. Renderer não foi modificado por esta manutenção; arquivo da falha preservado em `regression-stage-chromium-readiness-failure.{json,log}`. Repetição integral sem exclusões passou; instalado também passou integralmente. Hardening específico encaminhado para Ares em `t_8426333c`, gated após o pedido atual `t_8f7a90a8`, sem bloquear esse handoff ou substituir o QA obrigatório.
- Skill Hermes genérica estava desabilitada; nenhuma configuração/runtime Hermes foi alterada. Diagnóstico de perfil usou ambiente de worker Ares vivo e readback de HERMES_HOME, não variável de perfil inventada.

## Aprendizado e retomada

Aprendizado salvo exclusivamente na skill própria Zeus `meta-ads-api-operations/references/shein-static-image-prestage.md`, seção Materialized image names are auxiliary. Readback do conteúdo e SHA256 iguais ao mirror após sync; nenhuma skill Ares alterada.

Depois da parent done, Ares retoma EXCLUSIVAMENTE:

`python3 /root/mgs-agent/scripts/ares-shein-recovery.py --continuation /root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/continuations/shein-1565747351543480374-review-1565779731440468199.json --confirm-execute`

Descriptor SHA256 `cd5eb809237305eea55becdd565b4bdd711d5c6ed725177d2ad7a7bf66100411`; binding `ce9bee4f8bab7d889dff36bb73f1f73f3b7330afd7d1a1f7552ee37099459df3`. Sem novo prepare/upload/reserva/criação, sem campaign direto fora do contexto tipado e sem revisão histórica. Preservar8xUSD25, COST_CAP95,16IMG/copy, todos IDs e relógio original. Capacidade read-only instalada comprovada; aceitação final é do Ares: QA real16/reconciliação, pós-processamento, activate_verified e ACTIVE readback mesmos IDs, resposta curta na origem1558134703565967394. Não há alegação de ACTIVE/serving por Zeus.

Inventário/audit/REPORT-INFRA e checkpoint: ver `inventory-readback.json`, `report-infra-readback.json` e `preserved-state-readback.json`.
