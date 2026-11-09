# SHEIN — Cost per result goal em campanhas existentes

Pedido explícito para ajustar números publicados é otimização dos mesmos IDs: não duplicar nem reexecutar o runner de criação.

1. Autentique a mensagem exata e force `shein_channel_authority.verify`. Confira gates de conta/domínio, moeda, saúde e lease. Congele somente os números/IDs solicitados com pre-read da campanha, conjuntos e referências criativas. Inicialize a versão Graph pelo config antes de importar `ares-meta-common.py`.
2. Em CBO, para trocar MAXVOL por COCAP, envie no mesmo POST da campanha `bid_strategy=COST_CAP` e `adset_bid_amounts={adset_id: inteiro_em_centavos}` para todos os conjuntos. Não envie estratégia separada ao adset. Se COST_CAP já estiver vigente e somente o valor mudar, atualize `bid_amount` no conjunto: reenviar `adset_bid_amounts` sem troca de estratégia pode falhar com `100/2446030`.
3. Adquira `AccountWriterLeaseStore`, force autoridade e releia os IDs imediatamente antes dos writes. Use validate-only no edge direto quando suportado; nunca em `/copies`. Grave intenção e resposta separadamente e use `graph_post_once`. Depois de resposta incerta, faça GET/reconciliação antes de qualquer retry.
4. Exija batch GET final de todos os alvos com estratégia e cap exatos em todos os conjuntos. Compare campos não alvo com o pre-read, ordenando filhos por ID e excluindo apenas campos de lance autorizados: nomes, budgets, status, horários, público, evento, atribuição, IDs e creative IDs devem permanecer iguais. Não renomeie MAXVOL para COCAP por inferência num pedido somente de lance.
5. Persista receipt/checkpoint e libere a lease só após prova terminal. Preserve IDs e retome apenas alterações ausentes se houver falha parcial.

Aceite exercitado: validação direta, update CBO atômico e GET final de cinco campanhas existentes confirmaram COST_CAP e cap exato em todos os conjuntos, com igualdade dos campos não alvo. Isso valida a receita, mas não substitui as provas de pedidos futuros.
