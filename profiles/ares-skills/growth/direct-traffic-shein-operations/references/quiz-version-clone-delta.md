# Delta explícito de quiz na duplicação SHEIN

Use `target_quiz_version="v1|v2|v3"` no intake `pure_clone` somente quando o pedido determinar a troca de versão. O adapter `shein_quiz_delta` restringe a alteração ao caminho da rota HTTPS canônica do mesmo site/gestor e à versão no naming, preservando mídia, copy, query, localização do tracking e fonte. Não usar `website_url` da referência cross-account, mudar profile global ou modificar a fonte para simular o delta. Omissão do campo herda a versão real. Post-only/definição incompleta ou preservação expressa de post incompatível bloqueiam antes do write; são gerados posts novos.

Validar domínio/conta, destino público e `data-model` correspondente, dry-run, manifest e destinos de todos os anúncios no GET final, além do QA semântico/renderizado. Testes: `tests/test_shein_quiz_delta.py`; regressões do compiler, bids e Engine. Exercitados offline: oito testes próprios e regressão conjunta com 107 testes e 63 subtests; execução live validou três anúncios com V2 e tracking novo. Readback PAUSED/QA não significa ativação/serving.

## Drift de placements na cópia nativa

Se o alvo perder placements, dispositivos ou brand-safety expostos pela fonte, não aceitar isso como a normalização restrita de flags age/gender nem afrouxar QA. Fazer GET completo da fonte e alvo, comprovar o drift e preservar PAUSED. Em manutenção separada sob lock/lease da mesma conta/request, revalidar autoridade live e persistir pre-read/intenção. Restaurar somente o targeting comprovado da fonte no conjunto alvo existente, usando validate_only apenas no objeto direto antes do update, GET após o write e igualdade completa + PAUSED antes de retomar o mesmo runner. Não remover placements legados por inferência, editar manifests ou recriar objetos; rejeição da Meta exige resolver o delta autorizado, não omitir campos silenciosamente. Restauração do mapa completo confirmada ao vivo, sem mudar a fonte.

Preservar relógio/SLA e IDs; ACTIVATION_DEFERRED exige review humano específico mesmo quando o início futuro permanece inalterado. Descriptor de continuação usa a receita geral, preservando o horário comercial aprovado.
