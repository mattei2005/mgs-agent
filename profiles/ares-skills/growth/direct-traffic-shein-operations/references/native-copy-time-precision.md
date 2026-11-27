# Precisão de horário nativo em recuperação SHEIN

Use quando uma duplicação iniciada antes do horário explícito terminar depois dele e o QA apontar `campaign schedule mismatch`. Esta receita complementa a continuação de `campaign-runtime-recovery.md`; não cria autorização, tolerância global ou writer alternativo.

## 1. Classificar com as provas existentes

1. Leia request/resolved_request, ambos manifests selados, checkpoint de todos os bundles e horários vivos de campanha/conjunto. Separe horário humano, início configurado e confirmação da ativação; o último não é comprovado pelo primeiro.
2. Confronte cada slot com seu próprio `bundle.timings.adset_copy`, IDs, idempotency key e primeiro readback. Não use o horário do primeiro bundle para os demais: a Meta pode manter o início literal nos primeiros e normalizar somente os posteriores.
3. Quando a Graph retornar segundos inteiros e a janela local tiver frações, compare o limite inferior como `w0.replace(microsecond=0)`, conforme `shein_copy_schedule.normalized_schedule_proof`. Preserve o limite superior, segundo observado, identidade, dia/fuso, autoridade, seals e QA exatos. Não altere timestamps persistidos nem aceite o segundo anterior à janela; isso distingue precisão de transporte de mudança material de horário.
4. Confira a política canônica de horário explícito vencido no mesmo dia. Se ela não cobrir o caso, recupere o review específico exigido; não invente NOW retrospectivo nem escreva um início passado como teste.

## 2. Vincular a continuação instalada

1. Congele campaign/adset/ad IDs do checkpoint e arquive o state pré-ativação genuíno antes de retomar. Preserve request, resolved_request, fonte, relógio e manifests integralmente; esse snapshot será necessário para auditar a admissão depois da conclusão.
2. Faça o readback read-only dos mesmos objetos, com paginação completa e todos ainda PAUSED. Monte o recibo canônico de leitura com identidade do request/conta, horário real da coleta, campanhas na ordem dos bundles, horários, orçamento, lance, conjuntos, anúncios e contagens. Não apresente o horário de gravação como uma coleta anterior.
3. Use as funções instaladas, sem reimplementar o gate:

```python
bound = shein_elapsed_continuation.binding(
    state, checkpoint, original_readback, policy, profile, now=now)
authority = shein_elapsed_continuation.live_authority(
    state['request'], profile, operation, policy)
receipt = {'kind': shein_elapsed_continuation.KIND,
           'binding': bound, 'authority': authority, 'issued_at': issued_at}
shein_elapsed_continuation.validate_receipt(
    receipt, state, checkpoint, original_readback, policy, profile,
    now=now, authority=authority)
```

4. Persista leitura, receipt e grant exato apenas pela governança da capacidade canônica, sob lock/CAS, com backup e preservação dos outros grants. Revalide o digest e a prova real antes de retomar o mesmo runner. Um receipt que valida offline não substitui autoridade live nem QA.
5. Se a capacidade instalada divergir da precisão já representada no validador comum, separe a manutenção da transação: reprodução, menor correção, testes, inventário e REPORT-INFRA. Não monkeypatch o comparador nem altere manifests para obter PASS. Volte ao runner central somente após a validação.

## 3. Testar e fechar sem replay

- Exija que `test_native_second_precision_at_fractional_copy_start` aceite o segundo coincidente, rejeite o anterior e preserve integralmente as entradas. Execute também as regressões de elapsed schedule e batch continuation; reporte separadamente fixtures incompatíveis com o runtime, sem chamá-las de regressão verde ou enfraquecer produção para acomodá-las.
- Audite a conclusão contra o snapshot pré-ativação e o receipt originais: a admissão pode rejeitar corretamente um state já terminal com summary. Não rebaixe a fase, remova summary ou reexecute o writer para auditar.
- Compare o GET fresco com as árvores terminais e os IDs congelados, cobrindo definição material, horários por slot, budget/lance, estados de todos os filhos e QA dos mesmos creatives. Conserve separadamente a prova de admissão histórica e a igualdade material atual.
- Informe atraso quando a habilitação ocorrer depois do horário solicitado, mesmo se alguns objetos mantiverem o start_time literal. Agrupe apenas horários iguais; intervalos devem ser identificados como intervalos. Não prometa início pontual ou entrega a partir de status ACTIVE.
