# QA de pacote SEO automotivo local

- Para entregas exclusivamente locais, use somente REST público para inventário e não consulte credenciais nem altere site_key, taxonomias ou runtime; registre essas operações como zero no manifesto.
- Inventarie todas as páginas REST de posts e preserve corpo integral, título, slug e `link`. Separe o corpus pelo mercado real: um domínio multilíngue pode misturar financiamento brasileiro com produtos dos EUA em EN/ES.
- Valide href interno com GET 200, URL final idêntica e canonical self; copie o `link` REST literal. Guarde a evidência por URL em JSON separado.
- Escreva lotes duráveis pequenos e rode QA no JSON final. Conte palavras visíveis removendo HTML e comentários; confira tanto whitespace quanto regex, usando o menor para o mínimo. Não conte ALT, metadados ou texto de prompt.
- Exija `<p>` de uma única frase seguido imediatamente pelo marcador editorial; o manifesto deve instruir a mesma mídia interna/destacada quando solicitado.
- Guarde os cálculos hipotéticos em Decimal e identifique cada exemplo como hipotético no artigo. Um percentual criado para demonstração não é oferta, taxa de mercado ou previsão.
- Diferencie texto consolidado e publicação original: para consórcio, a Resolução BCB 285 sofreu alterações e possui transição por data do grupo. Se a recuperação do texto consolidado falhar, não declare conferência integral; limite claims à lei consolidada e FAQ oficial efetivamente lidas e registre a checagem normativa pendente.
- Em ambientes sem `python` ou `bs4`, use `python3` e `html.parser` da biblioteca padrão para não bloquear a entrega com instalação desnecessária.
- Não confunda HTML GET 200 de SPA BCB com conteúdo normativo recuperado; registre separadamente a evidência textual obtida pelo extrator/renderização.
