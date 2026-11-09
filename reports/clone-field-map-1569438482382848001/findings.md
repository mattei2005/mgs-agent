# Mapeamento por duplicações reais — fonte, payload e cópia

## Escopo verificado

- Mavroa Conta05 G005: C031 → C033, dois anúncios.
- Yolokfx Conta03 G005: C242 → C243, dois anúncios.
- Vínculo por IDs do manifesto e recibos de materialização do executor, não apenas pelo nome.
- Quatro pares / oito anúncios consultados ao vivo. Nenhuma criação, edição ou publicação nova.
- JSONs planejados e retornos de fonte/cópia foram mascarados com aliases explícitos. Tokens, URLs assinadas e links de paginação não foram persistidos.

## Prova do código efetivamente usado

A função pura `ares_campaign_v3.creative_copy_policy.effective` foi aplicada localmente ao payload preservado de cada slot. O digest do payload resultante coincidiu com o recibo original em quatro de quatro slots. O corpo produzido pela função pura `creative_media.creative_body` também coincidiu com o digest dos quatro requests CONFIRMED de criação do criativo no journal.

Nos parâmetros de recursos, a transformação explícita comprovada foi:

- `image_background_gen.enroll_status`: OPT_IN → OPT_OUT.
- Os demais recursos do payload planejado não foram alterados por essa transformação.

Isso prova os parâmetros do request registrado; não significa que todos os campos do GET posterior precisem ser idênticos.

## Comparação observada depois da criação

- Mavroa: a fonte atual retorna26 flags; a cópia78. São58 flags adicionais retornadas com OPT_OUT,6 campos que deixam de ser retornados e1 alteração explícita de enrollment.
- Yolokfx: a fonte atual retorna23 flags; a cópia79. São60 flags adicionais retornadas com OPT_OUT,4 campos que deixam de ser retornados e1 alteração explícita de enrollment.
- O snapshot original do Yolokfx tinha um campo a mais que sua fonte atual; esse detalhe está separado na comparação temporal, não atribuído à investigação.
- Ausência de campo não é OPT_OUT. Flags adicionais no retorno não provam que alguém acionou cada opção na interface.

## Correspondências úteis

Correspondências de rótulo explicitamente documentadas:

- `image_background_gen` → Generate backgrounds.
- `image_touchups` → Visual touch-ups para imagem.
- `video_auto_crop` → Visual touch-ups para vídeo.
- `image_templates` → Add overlays.
- `image_brightness_and_contrast` → Adjust brightness and contrast.
- `image_uncrop` → Expand image.
- `text_optimizations` → Text improvements.
- `enhance_cta` → Enhance CTA.
- `inline_comment` → Relevant comments.

Nos pares reais, `video_auto_crop`, `video_filtering`, `text_optimizations`, `enhance_cta` e `inline_comment` permaneceram OPT_IN. `image_background_gen` passou para OPT_OUT nas cópias. Os detalhes por slot estão em pair-1.json até pair-4.json.

As quatro fontes e quatro cópias retornam `object_type=VIDEO` e `object_story_spec.video_data`, inclusive a C031 cujo nome contém IMG. O nome humano não deve escolher a semântica de um campo de imagem versus vídeo. O ID de vídeo dentro de object_story_spec é igual em cada par; IDs de vídeo de nível superior diferem e não foram usados para afirmar alteração dos bytes da mídia.

## Contraprovas de aplicação

Foram consultadas12 funcionalidades documentadas em8 anúncios, total96 prévias GET. A geração de fundo retornou ineligible tanto na fonte quanto na cópia. `enhance_cta` e `video_filtering` retornaram eligible nos dois lados, demonstrando que a consulta não simplesmente classifica tudo como inelegível. Outros campos não retornaram transformação; isso foi preservado como tal, não convertido em OPT_OUT.

## Limites do mapeamento

A união dos retornos contém84 nomes de flags. Vinte têm rótulo de interface explicitamente documentado nesta investigação; outros quatro possuem semântica documentada sem rótulo visual exato confirmado. Os demais60 ficaram sem mapeamento semântico/UI confirmado. O dicionário distingue cada nível em vez de inventar um controle para todo campo.

Essas cópias tiveram omissões aceitas e outras alterações necessárias de identidade/tracking. Portanto, não são um experimento de interface com uma única variável isolada e não permitem atribuir causalmente cada diferença visual a uma flag.

## Evidências

- `lineage.json`: vínculos imutáveis dos quatro pares.
- `pure-payload-reconstruction-proof.json`: coincidência dos quatro payloads/corpos com recibos e journal CONFIRMED.
- `pair-1.json` … `pair-4.json`: respostas mascaradas e diff por caminho.
- `creation-time-comparison.json`: snapshot original, input selado, retorno atual da fonte e retorno da cópia.
- `feature-dictionary.json`:84 flags, confiança e descrição por campo.
- `provider-feature-labels.json`: descrições e estados retornados nas96 prévias.

Não foi aberto chamado à Meta. Não foram executados POSTs nem novas duplicações.
