# SHEIN review exato 008–015 IMG — t_fc58be96

## Problema, causa e correção

O review atual já estava autorizado por Rodolfo; o bloqueio era local. O módulo histórico de targeting aceita exclusivamente o selo/review das 004/005, a omissão de flags daquele caso e o lance herdado da fonte. Este pedido possui oito campanhas/8 conjuntos/16 anúncios IMG, outro review, fonte com somente `individual_setting.device=1`, `user_age_unknown=false` e bid90, enquanto o pedido/manifest aprovado exige COST_CAP95.

Foi adicionada a espécie tipada `shein-img-008-015-reviewed-targeting-v1` em `shein_reviewed_img.py`, integrada ao dispatch central de `shein_reviewed_targeting`. Nenhuma mudança na comparação global ou no selo histórico 004/005. A única mudança no runner é tornar o aviso de review correto para as duas espécies, sem alegar que o clone é literalmente idêntico.

## Evidência e vínculo imutável

- Request original: `shein-1565747351543480374`; conta `937846586033361`; fonte `120250750964580629` / adset `120250750970130629`.
- Origem Nicolas `1055570806945620030`, mensagem `1565747351543480374`, thread `1558134703565967394`, pai `1548150155184701440`.
- Quatro GETs frescos confirmaram texto, autor, ausência de edição, timestamps e referências: original, pergunta `1565772061119348747`, explicação `1565772455606493268`, review de Rodolfo `1565779731440468199`, com reply real à explicação que liga a pergunta. A decisão humana não foi solicitada novamente e source_message_id não foi substituído.
- Selo técnico do binding: `ce9bee4f8bab7d889dff36bb73f1f73f3b7330afd7d1a1f7552ee37099459df3` (calculado de dados reais). Inclui request, conta, fonte, todos os IDs/linhagem, dois manifests/digests/seals, relógio original, resolved_request e recibos de janelas/horários nativos por cópia. O selo não é autoridade genérica.
- Somente `user_age_unknown: false -> true` e retirada exata de `individual_setting={'device':1}` são aceitos. Todo o restante do targeting é comparado integralmente, inclusive tipos. Campos de conjunto não revisados permanecem iguais à fonte; lance/constraints e orçamento/estratégia são comparados ao manifest aprovado, não ao bid90 da fonte.
- Horários preservados. A reconciliação de horário usa o validador puro de provenance nativa existente; não introduz tolerância, ajuste, reset de SLA ou novo manifest.

## Validação

Stage e instalado: 553 testes +419 subtests, nenhuma exclusão, sem chamadas de rede externa, sem divergência de origem de módulo. Regressões incluem 004/005, continuation, schedule, activation, IMG/sourcing, engine, scope, prestage e QA.

Validação REAL do descriptor instalado executada em contexto Ares usando autoridade live `force=True`, domínio/conta permitidos e transporte comum guardado: 8 campanhas/8 conjuntos/16 anúncios com os mesmos IDs, todos PAUSED, USD25/dia cada, COST_CAP95. Dez requests HTTP de leitura (incluindo batch somente GET), além dos GETs Discord/autoridade. Fonte ainda com bid90 e targeting original. Quarenta e oito negativos reais locais rejeitados para IDs, conta, request, review, autoridade, conteúdo/reply, bid/budget, manifests, relógio e deltas extras. Nenhum mock de prova na validação positiva real.

Durante os testes negativos foi detectado que o validador genérico depende de `run()` para conferir `descriptor.account_id`; a espécie nova recebeu também seu próprio check explícito e o negativo passou. Dificuldades do harness (imports/Python do sistema sem pytest/caminho antigo de venv) foram corrigidas usando o venv ativo descoberto no entrypoint Hermes; nenhum pacote, runtime Hermes ou gateway foi alterado. Não confundir esses problemas do harness com falha de campanha ou autorização.

## Instalação, preservação e rollback

Pacote instalado por troca atômica `renameat2(RENAME_EXCHANGE)`, com locks originais de conta/request e ausência de subprocesso escritor comprovada. Recibo de instalação contém SHA256 dos três módulos, teste e descriptor. Backup do pacote anterior em `/root/mgs-agent/scripts/.ares_campaign_v3.review-img-t_fc58be96` e cópias dos arquivos editados em `work/t_fc58be96/backup/`.

State do runner e checkpoint core mantêm hashes iguais ao início desta manutenção. Intake original, manifest-sealed e state histórico006/007 conferem os hashes da manutenção anterior; fonte/manifests/request/relógio não foram editados. Sem alteração em credenciais, guard, budget, estratégia, SLA, reservas ou worker/gateway. Nenhuma skill do Ares foi alterada.

Rollback somente de código, sob coordenação/locks e após reconciliar a posição do Ares. Não restaurar snapshots operacionais antigos nem desfazer objetos/reservas/estado já avançados. Esta manutenção não autoriza exclusões.

## Handoff seco para Ares

Descriptor instalado:
`/root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/continuations/shein-1565747351543480374-review-1565779731440468199.json`

Somente Ares, como owner único de t_8f7a90a8 e no seu profile real, retoma:
`python3 /root/mgs-agent/scripts/ares-shein-recovery.py --continuation /root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/continuations/shein-1565747351543480374-review-1565779731440468199.json --confirm-execute`

Não repetir prepare-media, upload/reserva ou campaign creation; não criar novo request, reescrever manifests, reparar targeting ou estender a006/007/004/005. O comando central revalida mensagens/autoridade e executa somente a camada pendente com os mesmos IDs. Ares ainda deve concluir QA semântico, QA renderizado16, pós-processamento, activate_verified e readback ACTIVE de todos. Não declarar esse resultado antes da execução e readback reais.

## Limites desta entrega

Zeus: zero Meta write, Drive write, upload, reserva e ativação; nenhuma mensagem ao gestor. Não foi executado o recovery --confirm-execute, nem QA renderizado/semântico integral de campanha, nem fabricado qa_proof. A validação real testou o binding/targeting/schedule e o hook de validação pré-ativação somente em leitura. Serving não verificado. A conclusão desta card libera apenas a retomada da card Ares existente, não conclui as campanhas.

## Recibos locais

- `deployment-receipt.json`
- `real-readonly-installed.json`
- `regression-installed.json`
- `discord-get.json`
- `baseline-state-hashes.json`
- `preserved-state-readback.json`
- `inventory-readback.json`
- `report-infra-readback.json`

Aprendizado próprio: `meta-ads-api-operations/references/shein-static-image-prestage.md`, seção de review tipado exato, com readback e mirror iguais. Inventário/audit/checkpoint e REPORT-INFRA fechados separadamente antes do handoff terminal.
