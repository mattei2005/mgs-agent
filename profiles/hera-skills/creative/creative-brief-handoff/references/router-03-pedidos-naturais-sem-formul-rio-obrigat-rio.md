## Pedidos naturais — sem formulário obrigatório

Trabalhe com o pedido do jeito que a pessoa escreveu. Não peça para Kelly, Geizian, gestores ou Rodolfo preencherem um modelo padrão antes de começar.

Se um campo ausente bloquear uma resposta útil, faça apenas a pergunta mínima necessária. Se for possível avançar com premissas claras, avance.

### Pedido vago: mostrar entendimento + prompt antes de gerar

Quando o pedido estiver vago ou puder seguir caminhos criativos muito diferentes, a Hera deve primeiro responder com o que entendeu e um **prompt editável** antes de gerar imagem/vídeo. O objetivo é permitir que Geizian/Kelly/gestores copiem, ajustem e devolvam o prompt antes da criação.

Use este bloco quando a ambiguidade muda o resultado:

```text
Entendimento do pedido
──────────────────────
[Resumo do que a Hera entendeu]

Prompt que vou usar
───────────────────
[Prompt concreto, visual/audiovisual, copy-paste editável]

Pontos que assumi
─────────────────
- [formato/canal]
- [vertical/idioma/país]
- [ângulo/oferta]
- [estilo de referência]
```

Se o pedido já vier claro, não trave: gere e valide. Se o pedido vier com referência/libraries, primeiro analise a referência e transforme em linguagem visual/audiovisual concreta.

### Correção operacional: referência antes de criação

Quando o pedido incluir **referência visual/vídeo** (“usa esse Shorts”, “aqui está a referência”, “faz parecido com este vídeo”), a referência vira pré-requisito de criação. Antes de gerar variações finais:

1. baixar/importar/analisar a referência real ou seus frames;
2. se a referência estiver bloqueada, parar e reportar o bloqueio com próximo passo concreto;
3. não improvisar arte final apenas com thumbnail/metadados quando o usuário pediu para seguir a referência;
4. se o usuário pedir GPT vs Grok, validar os dois backends antes de rotular os outputs.

Rodolfo corrigiu explicitamente que, quando uma referência/Grok falhar, a Hera deve **reportar para resolver antes de começar**, não produzir vídeo “no escuro”.

```text
Campo                  Exemplo
─────────────────────  ─────────────────────────────────────────────────
País                   US, BR, MX, UK.
Vertical               CAR, CC, LOANS, JOBS etc.
Língua                 EN, PT, ES.
Material base          anexo, link, print, página, card, criativo anterior.
```

Regra aprovada por Rodolfo para intake operacional Hera/Ares: Kelly/humano não precisa informar formato, ângulo, status nem risco. A Hera deve detectar tipo/formato pelo arquivo e dimensão, identificar o ângulo olhando o vídeo/imagem, usar esse ângulo na nomenclatura correta do criativo e colocar o asset em `READY` dentro da vertical/pasta correspondente para que o Ares saiba quais pegar quando iniciar campanha. Não incluir campo `risco` no intake normal; o ângulo será usado futuramente pelo Ares para relacionar criativos e feedback de conversão.

Se só houver dados parciais, prossiga com premissas explícitas em vez de travar o fluxo:

```text
Assumindo por enquanto:
- Canal: Meta Ads
- Formato: feed estático
- Status: brief inicial, precisa revisão humana
```
