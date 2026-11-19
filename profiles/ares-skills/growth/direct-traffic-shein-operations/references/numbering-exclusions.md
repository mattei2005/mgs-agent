# Exclusão de campanha de teste da sequência

Quando o operador autorizado mandar ignorar uma campanha de teste na numeração, autentique a mensagem e resolva o ID exato na conta vinculada. Preserve o objeto Meta: ignorar para sequência não autoriza renomear, pausar ou excluir.

Registre `campaign_numbering_exclusions` somente no profile canônico daquela conta, com conta/canal/origem/autoridade e pares `campaign_id + number`. O helper central `shein_single_clone.numbering_inventory` aplica a exclusão apenas ao cálculo do próximo número; o inventário completo continua alimentando identidade e colisões.

Não use teto numérico, exclusão global pelo prefixo, `target_number` de reposição ou renomeação como atalho. ID, número ou conta divergente falha fechado; outra campanha com o mesmo número continua contando.

Se o pedido estiver PREPARED e sem checkpoint/objetos, preserve o request e a mídia e refaça dry-run próximo do execute. Com efeitos existentes, reconcilie antes de alterar qualquer camada. Valide ausência de política, escopo cruzado, identidade divergente, outro objeto homônimo e preservação do inventário com `tests/test_shein_numbering_exclusions.py`. Conclua somente após a rota normal e readback do lote.
