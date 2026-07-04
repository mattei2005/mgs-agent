# Eggbev CAR BR — referência visual, troca de carro e blocos CTA (2026-07-02)

## Contexto

Rodolfo corrigiu dois pontos no REC longo de financiamento de veículos no Eggbev CAR BR:

1. Uma imagem baseada em referência estava visualmente muito parecida com a foto do site de referência.
2. O bloco de CTA do começo e o CTA final precisavam usar o mesmo layout azul já existente, mas com os três botões finais oficiais.

## Regra de imagem aprendida

Quando Rodolfo envia print/referência de artigo pronto, a referência define **estilo, composição e intenção visual**, não autoriza copiar a mesma foto.

Para imagens de financiamento de veículos:

- trocar o carro da referência por outro veículo coerente com o artigo;
- preferir compacto/popular plausível para financiamento no Brasil;
- não usar a mesma cor/modelo/composição exata da referência;
- remover/evitar placa legível e logotipo de montadora claramente legível;
- integrar `EGGBEV` como watermark/wordmark no canto, sem caixa branca ou recorte bruto;
- validar visualmente antes do upload/publicação.

Técnica usada no caso:

- Gemini gerou foto editorial de carro compacto em rua urbana;
- como a saída veio quadrada, foi feito crop 16:9 real preservando o carro;
- watermark `EGGBEV` foi redesenhado no canto inferior direito;
- validação pública confirmou a imagem nova no HTML e remoção da imagem antiga.

## Regra de CTA por screenshot

Quando Rodolfo pedir para substituir um bloco pelo bloco de três botões finais, manter o layout azul existente do artigo e trocar apenas texto/links:

- `SIMULE AGORA – ITAÚ →` → `https://www.itau.com.br/emprestimos-financiamentos/veiculos`
- `SIMULE AGORA – BANCO DO BRASIL →` → `https://www.bb.com.br/site/pra-voce/financiamentos/financiamento-de-carro/`
- `SIMULE AGORA – CREDITAS →` → `https://www.creditas.com/simule-emprestimo-garantia-veiculo`

Legenda abaixo de cada botão:

```text
Você será redirecionado para o site oficial.
```

Use o container único isolado contra Auto Ads (`mgs-car-options mgs-no-ad no-ad`, `data-no-ad="true"`) quando o bloco tiver botões empilhados.

## Pitfall técnico: substituição do CTA final

Ao trocar o CTA final `SAIBA MAIS` pelo bloco de três botões, não use regex amplo que começa em `<!-- wp:buttons -->` e atravessa outros blocos até `SAIBA MAIS`. Isso pode apagar FAQ/aviso por engano.

Procedimento seguro:

1. Buscar a última ocorrência textual de `SAIBA MAIS` no raw content.
2. Encontrar o `<!-- wp:buttons` imediatamente anterior a essa ocorrência.
3. Encerrar no `<!-- /wp:paragraph -->` da legenda imediatamente após esse botão.
4. Antes de aplicar, verificar que o slice não contém `FAQ — Dúvidas Frequentes`, `Atenção:` ou outro bloco que deve permanecer.
5. Salvar snapshot antes da troca e validar no HTML público:
   - `SAIBA MAIS` removido;
   - FAQ e aviso permanecem;
   - três CTAs aparecem no começo e no final;
   - cada URL final aparece duas vezes.

## Validações úteis

Depois de atualizar Eggbev publicado, validar com cache-buster ou `Cache-Control: no-cache`, porque Cloudflare/APO pode servir HTML antigo.

Checagens mínimas para este caso:

- `SIMULE AGORA – ITAÚ`, `BANCO DO BRASIL`, `CREDITAS` aparecem no HTML;
- URLs oficiais aparecem na contagem esperada;
- blocos antigos como `CARRO PARCELADO SEM ENTRADA`, `BANCOS LIBERADOS`, `VEÍCULOS DISPONÍVEIS` foram removidos quando o pedido era substituir o bloco inicial;
- `SAIBA MAIS` foi removido quando o pedido era substituir o CTA final;
- FAQ/aviso permanecem quando não foram explicitamente removidos;
- imagem nova está no HTML e URL antiga não está.
