# SHEIN — handoff de vídeo e compliance regional

Apelo de reprovações e gestão parcial posterior: `review-disapproved-and-selective-activation.md`.

## Metadata e miniaturas separadas

Para dependências técnicas reconhecidas, faça GET do vídeo com `fields=id,title,status` e GET de `<video_id>/thumbnails` com `fields=id,uri,width,height`; não peça `thumbnails` como expansão no nó quando o guard só autoriza o edge. Exija HTTP200, ready/linhagem válidos e `data[0].uri` não vazia. Separe manutenção do executor da campanha, preserve guard/credencial/reservas e retome o mesmo request-ready após regressões e dry-run real. `test_shein_media_qa.py` cobre consultas exatas e rejeita HTTP403, lista vazia e URI ausente; mantenha os negativos de idioma/checksum/uso/Drive. Falha recuperável desse consumidor não exige nova autorização de campanha.

## Compliance regional ausente na cópia de conjunto

Diante de `adset_copy` com `100/3858634` e `compliance_section`, interrompa retries idênticos e leia targeting e `regional_regulated_categories/regional_regulation_identities` da fonte real; rótulo US não prova segmentação EUA. Confirme campaign IDs parciais PAUSED e paginação dos edges de conjuntos/anúncios antes de declarar ausência de filhos. Se a fonte segmentar BR sem identidade regional, não troque país, invente verified identity, envie DSA como solução ou altere a fonte por inferência. Inspecione identidades existentes somente na conta autorizada e confirme o contrato oficial de AdSet Copies: ele não declara campos regionais como overrides de criação. Sem rota central suportada ou identidade/decisão comprovadas, preserve request/manifests/shells e peça somente decisão material de país ou regularização exata do anunciante. Não substitua clone por criação direta nem repita campaign copy para sondar.

## Correção expressa de país e continuação do mesmo clone

Mantenha a pesquisa de helpers dentro de SHEIN e do core compartilhado; não abra nem reutilize sanitizadores operacionais de CAR/CPV para um delta SHEIN. Uma busca genérica por função pode devolver um helper de outra operação que remove campos válidos e, portanto, não serve como contrato do update atual.

Para alteração de país explicitamente autorizada, leia todos os conjuntos exatos e envie o targeting vivo completo, trocando somente `geo_locations.countries`; preserve `age_range` e `brand_safety_content_filter_levels`, que foram aceitos e conservados pela Meta no update SHEIN. Compare o mapa inteiro por GET após cada write. Se um helper retirar esses campos, restaure-os pelo payload completo e confira novamente antes de prosseguir. Omissão de `individual_setting.age/gender` já reconhecida pelo QA deve ser registrada separadamente, nunca declarada igualdade literal. Não remova device nem aceite outros deltas por analogia.

Quando a fonte corrigida alimenta um request parcial cujos manifests de clone não carregam targeting, faça backup/receipt da emenda e atualize somente o targeting do snapshot-fonte conforme GET comprovado e autoridade expressa. Preserve request/relógio, assets/reservas, todos os IDs e os digests integrais de ambos manifests; não resele nem regenere shells. Se o manifest carregar targeting ou houver outro delta, esta receita não o cobre.

Para `clone_prestaged` SHEIN com campanhas confirmadas e conjuntos ainda ausentes, o recovery central reutiliza `shell_recovery.reconcile`: pagina os filhos, adota IDs já existentes e copia somente o conjunto comprovadamente ausente. Continue a normalização também quando os IDs dos conjuntos já estiverem persistidos mas o estágio ainda for anterior a `shells_normalized`. Em `shell_payloads`, passe a estratégia viva observada: estratégia igual usa cap no conjunto, sem `adset_bid_amounts`; troca real mantém o mapping atômico na campanha. `test_shein_cbo_same_id_recovery.py` cobre ausência/adoção de conjuntos, campanhas sem identidade, isolamento de operação, parent incorreto e cap na mesma estratégia. Nunca repita campaign copy nem afrouxe o guard para recuperar esses casos.

Encadeie validação de dados, REPORT-INFRA e retomada com `check=True` ou `&&`. Um Python abortado seguido de shell incondicional não comprova a alteração anunciada no report; registre a falha, faça o readback real e corrija o report antes de alegar sucesso.

Fonte técnica pública para parâmetros de cópia: `facebook/facebook-python-business-sdk`, `facebook_business/adobjects/adset.py`, método `create_copy`; documentação/código não comprovam aceitação live de campo não declarado.
