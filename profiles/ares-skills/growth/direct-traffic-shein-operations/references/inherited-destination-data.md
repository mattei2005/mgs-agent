# Destino Meta herdado por referência expressa

Projetar campos antes de imprimir; truncar JSON bruto não sanitiza a fonte ou seus erros. Recovery geral: `campaign-runtime-recovery.md` nesta pasta.

Em `pure_clone`/`clone_prestaged` com campanha-fonte expressa na mesma conta, tratar o campo de destino selecionado por referência como dado Meta, não como administração do site. Usar a admissão central `validate_request_destinations` e o preflight read-only `preflight_inherited_destination`; não forjar `source_account`, trocar URL, promover host ou criar waiver. O profile isolado e o template implícito de from-zero não bastam para essa classificação. O checker de sites continua obrigatório para consulta/administração real do destino.

Antes de preparar mídia ou transferir reservas de pedido terminal, exigir autoridade/origem atuais, identidade corporativa/conta, fonte única com número completo e conta exata, evento SHEIN, Page/pixel/tarefas, pais/posts e tracking efetivo. Validar HTTP(S), host e ausência de credenciais de cada link, sem navegar. A admissão estática não é prova da fonte: `_prepare(source_only=True)` deve concluir essas leituras antes de assets ou manifest. Preservar fonte, localização contratada do tracking e rematerializar somente os tokens previstos por número-alvo pelo compiler normal.

Para manutenção read-only, manter URLs em memória e persistir apenas IDs/resultado sanitizado; não despejar source/profile/creative. Prova de preflight e testes não comprovam campanha criada ou serving. Não confundir com o canário experimental `shein_reference_destination`, que trata outro mecanismo de materialização de creative e não é necessário para classificar um campo URL.

Regressão: `tests/test_shein_inherited_destination_data.py` junto às suites de destino explícito, referência cross-account, grupos, runtime e fila. As fixtures usam destinos `.example`, nunca dados privados ou hosts recusados.
