# Variação de copy em vídeo existente mantendo o carro/produto

Use quando Ares receber um vídeo base/anexo e o pedido for criar uma variação mantendo o mesmo produto/carro/cenas, trocando apenas a oferta/copy.

## Fluxo validado

1. Importar/baixar o anexo real da thread antes de editar.
2. Gerar contact sheet do vídeo original e analisar visualmente:
   - produto/carro principal;
   - cenas e enquadramentos;
   - textos existentes;
   - áreas seguras para nova copy sem esconder rosto, logo, faróis, volante/painel ou produto.
3. Montar a nova sequência de mensagens em blocos curtos, alinhada à oferta do pedido.
4. Editar por overlay/tarja quando o objetivo for variação rápida de copy mantendo o vídeo original.
5. Gerar contact sheet da variação e validar com visão antes de entregar.
6. Corrigir qualquer divergência de oferta antes do handoff. Exemplo crítico: valor `R$299` não pode aparecer como `R99` ou `R$99`.
7. Sanitizar metadata e entregar apenas o arquivo `.metadata-clean.*`.

## Checklist de validação visual

```text
Item                         Validar
---------------------------  ------------------------------------------------
Oferta                       Todos os valores e claims batem com o pedido.
Idioma                       Português BR quando público for Brasil.
Produto/carro                Continua visível e protagonista.
Texto                        Legível em mobile, alto contraste, sem cortes.
Áreas sensíveis              Não cobre logo, faróis, rosto, volante/painel.
CTA                          Presente e coerente com botão/campanha.
Metadata                     clean=true antes da entrega final.
```

## Observações práticas

- Para criativos automotivos BR, usar frases curtas em caixa alta funciona bem: `COMPRE SEM ENTRADA`, `PARCELAS A PARTIR DE R$299`, `MESMO COM SCORE BAIXO`, `TOQUE EM SAIBA MAIS`.
- Ao usar `ffmpeg drawtext`, valide o símbolo de moeda no preview/contact sheet. Escaping incorreto pode remover `$` ou dígitos e alterar a oferta.
- Se a edição for apenas overlay/copy, deixe o status como `needs_review`/`precisa_revisao` até aprovação humana; não marque como aprovado.
