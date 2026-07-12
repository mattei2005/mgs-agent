# Precedente operacional — variação de vídeo GPT + Grok

Use esta referência quando Rodolfo/Geizian/Kelly/gestores pedirem variação de vídeo com GPT, Grok ou comparação entre providers.

## Aprendizado central

Antes de afirmar que “não há caminho GPT para vídeo” ou pedir autorização excepcional para Grok, o Ares deve verificar o precedente operacional e a forma real de entrega possível.

Em operação anterior, registrada na thread `1516611205517807680` / `Variações de vídeo com GPT e Grok`, o Ares entregou um pacote comparativo com estes sinais visíveis nos screenshots de Rodolfo:

```text
Pedido original:
"faça uma variação desse vídeo, use o gpt e o grok, faça um de cada"

GPT preview:
CAR_US_EN_VID_NO_DOWN_PAYMENT_PV_001_GPT_PREVIEW
Descrição entregue: versão mais limpa/polida, estilo anúncio premium,
texto forte para "NO DOWN PAYMENT / $299/mo / APPLY TODAY".
Também houve keyframe limpo:
CAR_US_EN_IMG_NO_DOWN_PAYMENT_PV_001_GPT_KEYFRAME.png

Grok preview:
CAR_US_EN_VID_NO_DOWN_PAYMENT_PV_002_GROK_PREVIEW
Descrição entregue: versão mais dinâmica, mais próxima do vídeo original,
com movimento de showroom e CTA "DRIVE TODAY".

Validação na thread:
ambos marcados como clean: true.
```

Correção após nova auditoria da mesma thread em `2026-06-19`: Rodolfo pediu mais duas variações na thread `1516611205517807680`, e o Ares entregou corretamente `V003_HYBRID_PREVIEW` e `V004_TRUST_PREVIEW`, ambas como vídeos 9:16 com áudio, cerca de 8s, metadata limpa. Contact sheets importados e analisados mostraram que V004, principalmente, tinha narrativa real de anúncio: vendedor + cliente, SUV/showroom, close do carro, interior, caminhada/interação, `NO DOWN PAYMENT`, `$299/mo`, `DRIVE TODAY`, `FAST APPROVAL`. Ou seja: a teoria “GPT só pode ser keyframe/zoom” é uma conclusão errada quando existe workflow funcional na thread.

Para não repetir erro, o Ares deve separar claramente:

```text
Workflow funcional da thread 1516611205517807680
  usar a referência/thread real, continuar numeração, gerar variações com narrativa,
  validar contact sheet e áudio, sanitizar, entregar preview limpo.

GPT imagem com zoom
  não aceitável como “vídeo real” nem como tentativa final.
  Se acontecer, descartar/reprovar internamente.

Grok/TTS robótico externo
  não aceitável para vídeo de vendedor falando.
  Se a pessoa precisa falar, a voz deve parecer integrada à pessoa/cena,
  ou a entrega deve ser bloqueada/reprovada.

Variação boa de vídeo automotivo
  precisa ter narrativa/cenas: apresentador/cliente, carro, interior,
  interação, CTA e movimento interno — não apenas Ken Burns sobre uma imagem.
```

Regra prática: quando uma thread citada pelo usuário está gerando resultados bons, pare de teorizar por provider. Importe a thread, baixe os anexos, gere contact sheets e replique o workflow real daquela thread.

## Regra de resposta

Quando o usuário mencionar uma thread/precedente ou disser que algo já foi feito antes:

1. importar/ler a thread read-only;
2. localizar assets, nomes, resumo e padrão de entrega;
3. não contradizer o histórico sem checar;
4. explicar a diferença entre “preview GPT” e “vídeo real dinâmico” quando necessário;
5. repetir o workflow validado, adaptando ao novo pedido.

## Workflow recomendado

```text
Pedido: “faz com GPT e Grok”
────────────────────────────
1. Analisar referência real e extrair linguagem audiovisual.
2. GPT preview: versão polida/limpa, texto/oferta forte, visual premium.
3. Grok preview: versão dinâmica/social, movimento mais próximo de vídeo nativo.
4. Validar contact sheets dos dois.
5. Sanitizar metadata.
6. Entregar com rótulos explícitos: GPT/V001, Grok/V002, status preview/final.
```

## Pitfall evitado

Não responder “não tenho GPT vídeo disponível” de forma absoluta quando há precedente de GPT preview. A resposta correta é explicar a capacidade real:

```text
GPT disponível para preview polido/keyframes/peça visual;
Grok disponível para vídeo/motion mais dinâmico;
posso entregar comparação GPT preview + Grok preview se o pedido for comparação.
```

## Critério de qualidade

Se o resultado for slideshow, imagem com zoom ou sequência de keyframes, rotular como **preview estrutural/polido**, não como vídeo final profissional. Se o usuário pediu vídeo real no padrão da referência, validar se há movimento, cortes, câmera e energia compatíveis antes de entregar.