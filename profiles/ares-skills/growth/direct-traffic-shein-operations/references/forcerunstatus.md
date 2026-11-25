# ForceRunStatus — reassociação autorizada

- Trate 1487083 como opaco; ele não prova reprovação editorial nem uma causa exclusivamente técnica.
- Para pedido expresso de remover e adicionar novamente, prefira testar a reassociação do mesmo creative ID em um único ad ID afetado, sem excluir arquivos, mídia ou anúncios. Antes, confirme autoridade live, escopo da conta, locks/lease e ausência de 2490468, DISAPPROVED ou feedback de reprovação.
- Preserve mídia/copy/CTA/UTMs, lineage, pais, orçamento, lance, programação e estado PAUSED. Registre intenção e baseline antes de um único POST; após erro ou incerteza, faça GET antes de decidir qualquer outra ação. Um intent já existente nunca permite repetir o POST como sondagem.
- No ensaio expressamente autorizado, limite o payload a `graph_post_once(ad_id, token, {'creative': json.dumps({'creative_id': creative_id})})`, com os mesmos IDs previamente conferidos; não acrescente `status` nem outro delta. Mantenha a lease do request original e os locks canônicos da conta/request durante o pre-read, a intenção e o POST. Persista separadamente resposta e releituras para que uma retomada com intent existente execute somente reconciliação, nunca outro teste.
- Separe aceite do reparo e convergência: HTTP200/success, IN_PROCESS e issues ausentes no primeiro GET não provam resolução. Releia o mesmo anúncio após processamento antes de estender o teste ao restante.
- Se surgir 2490468, DISAPPROVED ou feedback de reprovação, interrompa a extensão. Preserve IDs e retorno exato; revisão ou conteúdo corrigido são decisões distintas. Não repita reassociação, toggle de status ou recriação idêntica para contornar a avaliação.
- Não atribua a reprovação à reassociação só pela sequência temporal nem invente seu motivo editorial quando ad_review_feedback estiver ausente.
- Informe separadamente o anúncio testado e o saldo não alterado: uma reprovação observada no ensaio não comprova reprovação dos demais anúncios ou restrição da conta. No checkpoint e na resposta, diferencie reparo aceito pelo HTTP de erro resolvido após processamento; registre o ensaio que terminou em reprovação como resultado negativo, nunca como solução homologada. Preserve o aceite de omissões já validado e peça somente a decisão nova sobre revisão ou conteúdo corrigido.
- Retome QA/pós-processamento/ativação somente pela rota central e pelos mesmos objetos quando elegíveis. A tentativa de reparo não conclui o lote.

## Verificação do ensaio

Confronte baseline, intenção, resposta e releituras reais: erro1487083 inicial; um POST com payload limitado a creative_id; HTTP200/success; mesmo ad/creative e IN_PROCESS transitório; releitura posterior; interrupção sem writes em lote quando houver rejeição. Exija igualdade de tracking, pais e estados configurados e preserve todas as evidências anteriores. Esse replay valida a decisão de não expandir, não homologa a reassociação como solução do erro.
