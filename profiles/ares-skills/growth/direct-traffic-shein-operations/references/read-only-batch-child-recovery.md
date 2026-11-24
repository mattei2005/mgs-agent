# Recuperação read-only e encaminhamento de diagnóstico

Destino/URL herdados: carregar `references/inherited-destination-data.md`; esta referência preserva esse encaminhamento.

Quando um child de Graph Batch retornar `code=4` e `is_transient=true`, separe o limite real do app da recuperação do transporte. Um GET direto idêntico pode passar enquanto o batch falha; isso não prova ausência de quota nem permite trocar app/token.

A rota central `shein_single_clone._batch` preserva children bem-sucedidos e repete somente o GET rejeitado pela mesma identidade, endpoint, parâmetros e guard, usando o backoff canônico. Persistência do erro, erro de permissão, resposta inválida ou identidade divergente continuam bloqueando. Não aplicar a POSTs/copies nem declarar campanha criada por esse readback.

Antes de repetir uma preparação que falhou depois de uploads, releia a library da conta exata pelos títulos determinísticos e complete a paginação. Confirme os IDs e status existentes para a proveniência account-scoped e retome o preparador canônico; não reenvie arquivos apenas porque o registry ainda não teve commit. O readback da library e a retomada devem comprovar recuperação por título, ready e associação sem duplicar uploads.

Valide offline recuperação exata, zero replay de sucessos e negativos (code10, code4 não transiente, falha persistente, corpo inválido, identidades divergentes, HTTP externo falho). Manutenção separada exige backup/CAS, regressão e REPORT-INFRA antes de retomar o mesmo request. Não instalar nem ensaiar campanhas reais como teste técnico.
