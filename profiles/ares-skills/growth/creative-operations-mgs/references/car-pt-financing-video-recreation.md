# CAR BR/PT — recriação de vídeo de financiamento com vendedor/concessionária

Use esta referência quando Rodolfo, Geizian, Kelly ou gestores pedirem variação/recriação de vídeo automotivo BR/PT com oferta de financiamento, especialmente quando houver correção de que o resultado anterior ficou como legenda, zoom, slideshow ou voz robótica.

## Aprendizado central desta classe de tarefa

Para CAR BR/PT, “variação de criativo” não significa reaproveitar o vídeo original com legenda nem transformar keyframes em zoom. O padrão aceito por Rodolfo é vídeo com **narrativa de anúncio de concessionária**:

```text
- vendedor(a)/consultor(a) em cena;
- pessoa aparentando falar para a câmera;
- carro branco protagonista, idealmente hatch compacto quando a referência for hatch;
- showroom/pátio de loja realista;
- cortes rápidos com função narrativa;
- close externo do carro;
- take do interior/volante/painel;
- interação humana quando fizer sentido: cliente, entrega, atendimento, aprovação;
- CTA final olhando para câmera;
- textos grandes em branco/amarelo com contorno/sombra, sem cobrir rosto/carro;
- voz natural integrada à pessoa em cena, não TTS robótico externo.
```

## Anti-padrões que devem ser reprovados internamente

```text
Anti-padrão                              Ação correta
───────────────────────────────────────  ─────────────────────────────────────────────
Mesmo vídeo + legenda nova               Reprovar, salvo se usuário pediu só trocar copy.
Imagem/keyframe com zoom                 Reprovar como vídeo final; no máximo direção visual.
Slideshow de imagens estáticas           Reprovar se o pedido for vídeo real/UGC.
TTS robótico por cima de pessoa falando  Reprovar; voz deve parecer integrada à cena.
Teorizar por provider                    Parar, importar thread de referência e ver assets reais.
Entregar sem contact sheet               Não entregar; validar visualmente antes.
```

## Workflow bom observado em thread de referência

Thread `1516611205517807680` mostrou um caminho melhor: quando Rodolfo pediu mais variações, o Ares gerou V003/V004 com narrativa em vez de discutir limitações por provider.

Elementos que funcionaram:

```text
V003 HYBRID
- visual premium + social;
- vendedora/apresentadora;
- SUV/showroom;
- oferta legível.

V004 TRUST
- vendedor + cliente;
- showroom;
- close do carro;
- interior;
- interação/atendimento;
- textos: NO DOWN PAYMENT / $299/mo / DRIVE TODAY / FAST APPROVAL;
- contact sheet com progressão narrativa, não mero zoom.
```

Lição: o critério decisivo é **qualidade de direção e cenas**, não desculpa sobre GPT/Grok. Se uma thread citada está gerando bom resultado, importe a thread, baixe os anexos, gere contact sheets e replique o workflow real.

## Prompt base BR/PT para financiamento de veículo

```text
Crie um vídeo vertical 9:16 de anúncio para concessionária brasileira, estilo Reels/TikTok/Meta Ads, aparência realista de celular, com cortes rápidos e movimento interno.

Um(a) vendedor(a) brasileiro(a) fala diretamente para a câmera ao lado de um hatch compacto branco em uma concessionária/showroom. A voz deve soar natural e integrada à pessoa em cena, como vendedor(a) falando, não narração robótica externa.

Cenas obrigatórias:
1. apresentador falando para câmera ao lado do carro;
2. close da dianteira do carro branco;
3. take lateral/diagonal do veículo;
4. interior mostrando volante, painel e multimídia;
5. apresentador apontando para o carro ou atendendo cliente;
6. CTA final olhando para câmera.

Textos na tela, grandes, caixa alta, branco/amarelo com contorno preto, terço inferior:
- FINANCIE SEU VEÍCULO
- COMPRE SEM ENTRADA
- PARCELAS A PARTIR DE R$299
- MESMO COM SCORE BAIXO
- TOQUE EM SAIBA MAIS

Fala natural em português brasileiro:
"Quer financiar seu veículo? Você pode comprar sem entrada, com parcelas a partir de R$299, mesmo com score baixo. Toque em Saiba Mais e consulte agora."

Evitar: poster estático, slideshow, Ken Burns/zoom, anúncio institucional genérico, TTS robótico de fundo.
```

## Validação antes de entregar

Gerar e analisar contact sheet. Só entregar se responder “sim” para a maioria:

```text
Pergunta de QA                              Esperado
──────────────────────────────────────────  ─────────────────────────────────────
Há mais de uma cena/plano útil?              Sim.
Há pessoa em cena com fala/gestos?           Sim.
Carro branco é protagonista?                 Sim.
Há close externo e interior do carro?        Sim.
Há CTA final?                                Sim.
Parece narrativa de loja/concessionária?     Sim.
Parece apenas zoom ou slideshow?             Não.
A voz parece robótica externa?               Não entregar se sim.
Textos críticos estão corretos?              R$299, sem entrada, score baixo, CTA.
Metadata limpa?                              clean: true.
```

## Nota de execução Grok/xAI

Ao gerar mais de um vídeo via wrapper Grok/xAI, evitar chamadas simultâneas: xAI pode retornar `429` por limite de 1 request/segundo. Se acontecer, repetir sequencialmente após poucos segundos. Capture o padrão de retry, não trate isso como incapacidade do provider.
