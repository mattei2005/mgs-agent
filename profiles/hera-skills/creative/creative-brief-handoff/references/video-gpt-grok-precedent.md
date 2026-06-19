# Precedente operacional — variação de vídeo GPT + Grok

Use esta referência quando Rodolfo/Geizian/Kelly/gestores pedirem variação de vídeo com GPT, Grok ou comparação entre providers.

## Aprendizado central

Antes de afirmar que “não há caminho GPT para vídeo” ou pedir autorização excepcional para Grok, a Hera deve verificar o precedente operacional e a forma real de entrega possível.

Em operação anterior, registrada na thread `1516611205517807680` / `Variações de vídeo com GPT e Grok`, a Hera entregou um pacote comparativo com estes sinais visíveis nos screenshots de Rodolfo:

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

Isso não significa que todo preview GPT seja vídeo cinematográfico real. O precedente mostra que o GPT funcionou como **peça/preview polido com keyframe forte e visual premium**, enquanto o Grok foi descrito como o caminho mais **dinâmico/social**. Para não repetir erro, a Hera deve separar claramente:

```text
GPT keyframe/preview polido      aceitável como direção visual/capa/peça premium, se rotulado.
GPT imagem com zoom              não aceitável como “vídeo real” nem como tentativa final.
Grok vídeo dinâmico              caminho preferencial quando o objetivo é movimento/showroom.
Grok com TTS robótico externo    não aceitável para vídeo de vendedor falando.
```

Grok tende a servir melhor para motion/dinâmica social quando disponível, mas só deve ser entregue se a voz/cena respeitar o pedido. Se a pessoa precisa falar, não mascarar com TTS robótico por cima.

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