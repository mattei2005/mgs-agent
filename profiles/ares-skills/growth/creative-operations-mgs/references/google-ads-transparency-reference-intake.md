# Google Ads Transparency — coleta e análise de referências

## Recorte e autoridade

- Trate biblioteca de terceiro como pesquisa pública, não como domínio operacional MGS. Não use o catálogo SB para declarar propriedade do terceiro.
- Preserve país, domínio pesquisado, período, timezone exibido e instante da coleta. `preset-date=Today` é móvel: registre a data resolvida e não amplie silenciosamente para todo o histórico.
- Filtro por domínio reúne várias contas de anunciantes; conte IDs e nomes separadamente. Um anúncio dizer “Official” não autentica seu anunciante.

## Coleta verificável

1. Abra a URL real no browser, espere os filtros assentarem e expanda `See all ads`. O contador pode mostrar um total amplo antes de aplicar a data; confirme novamente após a resposta filtrada.
2. Inspecione a chamada pública real `SearchService/SearchCreatives` no contexto do navegador e preserve o payload `f.req`, sem cookies/credenciais. Não trate HTTP 200 com `{}` como página válida.
3. Reutilize somente o schema observado. Em uma implementação validada, `2` era tamanho da página, `3` filtros e `4` cursor; resposta `1` continha anúncios e `2` a continuação. Isso é schema observado, não contrato estável. Pedido de 100 itens funcionou; 1000 retornou vazio e não comprovou ausência de anúncios.
4. Salve cada página antes de avançar, dedupe por advertiser_id + creative_id e termine somente sem cursor. Metadados de contagem podem ser intervalos aproximados, não totais exatos.
5. A implementação observada usava formato `1=Text`, `2=Image`, `3=Video`; confirme na UI antes de apresentar essa classificação.
6. Baixe o conteúdo efetivamente exposto: prévia rasterizada, produto, thumbnail e vídeo são categorias diferentes. Preserve wrapper original e proveniência. Não anuncie que baixou o original editável ou o MP4 a partir de uma imagem de prévia.
7. Detalhes podem expor várias variações, mesmo quando a grade tem um único creative_id. Preserve índice da variação e sua linhagem, sem transformá-la em novo anúncio.

## Extração de mídia e validação

- Wrappers `displayads-formats.googleusercontent.com/.../content.js` podem conter HTML e URLs escapados. Decodifique texto sem executar JavaScript remoto no sistema operacional.
- Escape aninhado exige tratar sequências de uma ou mais barras antes de `xHH`/`uHHHH`; deixar uma barra solta pode truncar `shopping?q=...` e produzir falso 404. Teste a URL completa e a imagem real.
- Aceite URLs relativas de protocolo (`//...`) com HTTPS. Mídia de vídeo pode estar em VAST/CDATAs com `googlevideo.com/videoplayback`, sem extensão `.mp4`; thumbnail pode usar `i1.ytimg.com/vi/<id>/...`.
- Classificação Video não garante que a variação de prévia exponha vídeo: alguns wrappers mostram somente imagem/app card. Não invente MP4 para preencher a lacuna.
- Confirme imagens por decode e dimensões; vídeos por ffprobe/duração/streams. Deduplicate binários por SHA-256, preservando todos os vínculos anúncio/variação.
- Antes de entregar mídias, use o sanitizador canônico, preserve RAW e exija `clean=true`. Arquivos Google podem conter Encoder/GoogleStartTime/GoogleTrackDuration; remux limpo não deve alterar duração, resolução ou conteúdo audiovisual.

## Limites e recuperação

- Use pequenos lotes com persistência; não dispare consultas de detalhes em concorrência alta. O limite da biblioteca pode surgir mesmo após a paginação ter concluído.
- Ao primeiro 429, interrompa o lote e respeite o limite; não aumente concorrência nem tente outra identidade/rede para contornar. “Unusual traffic”/CAPTCHA é bloqueio real, não página do anúncio.
- Aproveite wrappers, páginas e variações já salvos para completar downloads dos recursos públicos disponíveis sem repetir chamadas da biblioteca. Não use arquivo histórico como prova do período atual.
- Se o bloqueio impedir o restante, registre checkpoint com IDs, pendências exatas e próxima ação humana (liberar navegação oficial/verificação, ou fornecer mídia/export). Entregue o parcial útil com contagens separadas e nunca marque “todos os vídeos concluídos”.

## Análise e entrega

- Compare gancho inicial, demonstração, clareza de oferta, movimento, legibilidade, adequação ao público e CTA. Separe vídeo assistido por frames/timeline de imagem de prévia.
- Use OCR para triagem, mas confirme visualmente toda oferta/ID relevante. Avaliação estética não prova CTR, CVR, CPA ou ROI.
- Separe B2B (vender no marketplace) de B2C (comprar moda); o melhor banner gráfico pode ser irrelevante para a operação.
- Não extrapole desconto, frete, recompensa, participação em programa ou relação oficial com SHEIN para uma campanha MGS. A oferta de terceiro serve de referência, não autoriza promessa local.
- Inclua índice local pesquisável, links oficiais, inventário por anúncio, checksums e pendências no pacote. Arquivos de referência permanecem inelegíveis para publicação automática.

## Testes mínimos da receita

- Fixture com `https://.../shopping?q\\u003dtbn:...` e escape aninhado deve manter `?q=` completo.
- Fixture VAST com `//...googlevideo.com/videoplayback?...` deve ser reconhecida mesmo sem `.mp4`.
- Duplicatas devem ter um binário e vários vínculos; contagem de anúncios não pode ser substituída pela contagem de arquivos únicos.
- Resposta `{}`, 429 ou CAPTCHA nunca deve aumentar o contador de páginas/variações válidas.
