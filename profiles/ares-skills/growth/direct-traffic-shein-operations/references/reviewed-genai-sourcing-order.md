# Sourcing GenAI reordenado sob review tipado

Quando o review de público estiver validado e o QA ainda rejeitar mídia estática herdada, compare o sourcing inteiro antes de pedir outro aceite. A Meta pode retornar as mesmas variantes GenAI em outra ordem com AFS exclusivamente textual.

Use `reviewed_copy_targeting.preserved_sourcing` somente no contexto real validado: exigir slot/creative/digest selados, imagem primária e story idênticos, feed textual completo, tracking literal e multiconjunto exato das entradas de imagens, incluindo multiplicidade, hash, origem, enrollment e demais chaves. Normalizar ordem não aceita imagem adicional/ausente, crop, texto, identidade ou configuração alterados. Fora desse contexto, o gate normal de mídia nova permanece estrito.

Se o runtime ainda comparar por posição ou excluir AFS textual, separar manutenção da transação: preservar primeira falha, fixtures protegidas, backup/inventário e CAS; provar vermelho→verde e negativos de mídia/identidade/tracking/contexto antes de instalar e emitir REPORT-INFRA. Retomar o mesmo descriptor pelo runner central, sem editar manifests, repetir criação ou mudar início. Exigir QA renderizado e readback ACTIVE dos mesmos IDs; igualdade semântica offline não comprova ativação.

Um `unittest discover` sem testes não é cobertura: conferir os arquivos reais e o total executado. A receita foi exercitada por 29 checks do binding real, 25 regressões de sourcing/review e readback terminal dos mesmos IDs. Esses totais são evidência de validação, não quotas futuras.
