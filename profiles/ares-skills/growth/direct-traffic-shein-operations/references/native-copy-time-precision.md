# Precisão de horário nativo em recuperação SHEIN

Use quando `campaign schedule mismatch` ocorrer ao cruzar o horário explícito do próprio dia. Antes de qualquer write, siga a continuação em `campaign-runtime-recovery.md` e confronte IDs/selos e horários vivos com o checkpoint.

- Compare o segundo inteiro da Graph com a janela local fracionária usando `w0.replace(microsecond=0)` somente no limite inferior, como em `shein_copy_schedule.normalized_schedule_proof`. Preserve limite superior, segundo observado, identidade, dia, autoridade, seals e QA exatos. Não use tolerância genérica, altere timestamps ou aceite o segundo anterior.
- Exija que `test_native_second_precision_at_fractional_copy_start` aceite o segundo coincidente, rejeite o anterior e preserve as entradas. Rode elapsed schedule e batch continuation; reporte separadamente fixtures históricas incompatíveis com o runtime.
- Vincule recibo imutável de leitura PAUSED, autoridade live e grant exato por `shein_elapsed_continuation`, sem NOW retrospectivo, schedule write ou recopy. Retome somente a camada pendente do mesmo request.
- Audite o receipt terminal contra o snapshot pré-ativação genuíno: a admissão pode rejeitar corretamente o state já concluído. Não rebaixe a fase nem reexecute o writer para auditar.
