# Catálogo live de blocos — guia

Fonte autenticada `GET /v1/blocks/catalog`, nas duas credenciais em 2026-11-17. Snapshot completo com schemas/defaults: `blocks-catalog.json`. Foram observados 19 keys únicas, iguais entre as duas chaves. Reconsultar antes de escrita. Todos os schemas observados proíbem propriedades adicionais; não adicionar campos por conveniência. Não tratar defaults vazios como instâncias válidas.

1. `paragraph`: texto content até 3000 e align left/center/right; ambos obrigatórios no live.
2. `heading`: level inteiro 2–4, text 1–200, align left/center/right.
3. `options`: 1–6 opções, text 1–120, link obrigatório e cta opcional até 30; button_color opcional.
4. `accordion`: mode default/faq, 1–30 itens com title e description não vazios.
5. `related-content`: subject, title, link obrigatórios; description, image_asset_id, button_text, button_color opcionais.
6. `landing-page`: intro, headline, image_asset_id, first_paragraph, benefits (1–6), second_paragraph, cta, link e três flags boolean show_ad_top/show_ad_first/show_ad_second. footnote e secondary_link estão deprecated/ignorados pelo componente; não usar. Flags locais de conteúdo não são gestão global de monetização.
7. `offer`: product, name, description, image_asset_id, tags (até 5 objetos com label e icon), link, button_text. icon aceita star/fire/check/lightning/gift ou null; button_color opcional.
8. `custom-html`: html 1–65536 caracteres; sanitização/JS/escopo global não garantidos. Não inserir scripts/trackers/ads por inferência.
9. `image`: asset_id, size thumb/medium/large/original, alignment left/center/right/full; opcionais alt_override, caption e link {href,target,rel}; target _self/_blank.
10. `image-button`: asset_id, href, target _self/_blank e alignment; alt_override e max_width inteiro positivo opcionais.
11. `button`: label 1–60, href, variant primary/secondary/ghost/link, size sm/md/lg, target _self/_blank, alignment left/center/right, width auto/sm/md/lg/xl/full; button_color e label_bold opcionais.
12. `list`: ordered boolean, marker_style default/circle, 1–50 itens com text 1–2000.
13. `spotlight`: image_asset_id, title, description, cta_label e link não vazios; button_color opcional.
14. `table`: content string HTML 1–10000.
15. `title-anchor`: data {}, sem propriedades adicionais.
16. `video`: provider exatamente youtube, videoId de 11 caracteres [A-Za-z0-9_-]; start inteiro >=0 e title até 200 opcionais. Não supor upload de vídeo.
17. `coupon`: brand, code, discount e url não vazios; expires_at string (pode vazia no default).
18. `deal-grid`: items até 6; title, price, old_price, image_asset_id, url por item; old_price/image_asset_id podem ser strings vazias segundo schema/default.
19. `price-tag`: price não vazio, old_price string, currency string default USD. Não trocar moeda automaticamente por preferência BRL do usuário.

## Cores e links

Vários blocos aceitam button_color opcional string 1–64 ou null com pattern do schema. Obedecer regex real; não chamar isso de CSS arbitrário/global. Preservar URLs/UTMs/IDs; validar links e compliance. Edição de bloco pode alterar monetização/render; limites MGS continuam válidos.

## Composição e validação

Cada instância tem `{id, type, data}`. Preservar ordem e IDs existentes. Validar `data` pelo schema da key, depois validar links/assets e ler o artigo renderizado. Esses blocos possibilitam landing pages, ofertas, comparativos, CTAs e conteúdo editorial dentro do CMS, não um site arbitrário sem limites.
