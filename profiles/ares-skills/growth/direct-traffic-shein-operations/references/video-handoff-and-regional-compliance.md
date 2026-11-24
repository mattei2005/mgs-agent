# SHEIN — handoff de vídeo e compliance regional

## Metadata e miniaturas separadas

Para dependências técnicas reconhecidas, faça GET do vídeo com `fields=id,title,status` e GET de `<video_id>/thumbnails` com `fields=id,uri,width,height`; não peça `thumbnails` como expansão no nó quando o guard só autoriza o edge. Exija HTTP200, ready/linhagem válidos e `data[0].uri` não vazia. Separe manutenção do executor da campanha, preserve guard/credencial/reservas e retome o mesmo request-ready após regressões e dry-run real. `test_shein_media_qa.py` cobre consultas exatas e rejeita HTTP403, lista vazia e URI ausente; mantenha os negativos de idioma/checksum/uso/Drive. Falha recuperável desse consumidor não exige nova autorização de campanha.

## Compliance regional ausente na cópia de conjunto

Diante de `adset_copy` com `100/3858634` e `compliance_section`, interrompa retries idênticos e leia targeting e `regional_regulated_categories/regional_regulation_identities` da fonte real; rótulo US não prova segmentação EUA. Confirme campaign IDs parciais PAUSED e paginação dos edges de conjuntos/anúncios antes de declarar ausência de filhos. Se a fonte segmentar BR sem identidade regional, não troque país, invente verified identity, envie DSA como solução ou altere a fonte por inferência. Inspecione identidades existentes somente na conta autorizada e confirme o contrato oficial de AdSet Copies: ele não declara campos regionais como overrides de criação. Sem rota central suportada ou identidade/decisão comprovadas, preserve request/manifests/shells e peça somente decisão material de país ou regularização exata do anunciante. Não substitua clone por criação direta nem repita campaign copy para sondar.

Fonte técnica pública para parâmetros de cópia: `facebook/facebook-python-business-sdk`, `facebook_business/adobjects/adset.py`, método `create_copy`; documentação/código não comprovam aceitação live de campo não declarado.
