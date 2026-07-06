# CAR-BR — fluxo convergente com cards de veículos

Use quando Rodolfo pedir para o chat de financiamento de carro imitar referência tipo `fmybc.com/chat/car/br/`.

## Comportamento esperado

- As perguntas existem para engajamento e qualificação percebida.
- A resposta escolhida aparece como balão do usuário.
- **Não ramificar** por resposta quando a referência for convergente.
- Qualquer resposta da pergunta final, por exemplo:
  - `Sim, já tenho um modelo em mente`
  - `Não, estou aberto a sugestões`
  - `Ainda estou decidindo`
  leva para o mesmo bloco final.

## Modelo final correto

Para CAR-BR nesse padrão, o fim do fluxo deve mostrar 3 cards juntos, não ofertas sequenciais.

Antes dos cards, o padrão validado pelo Rodolfo tem **3 falas editáveis**:

```text
🔍 Estou pesquisando as melhores condições para você...
🚗 Encontrei 3 ofertas exclusivas para você!
Toque na que mais te interessa para ver as condições:
```

No plugin/admin, essas falas devem aparecer como campos humanos separados, não escondidas só em JSON ou em um textarea técnico:

```text
Mensagem de busca antes das ofertas
Mensagem “ofertas encontradas”
Mensagem de instrução dos cards
```

Implementação importante: renderizar essas 3 falas no **mesmo passo final que contém `offers`**. Não transformar a primeira fala em uma pergunta/etapa separada sem `answers`, porque o template Ciro avança por clique/resposta; uma etapa sem botão pode travar antes de chegar aos cards.

Campos por card:

```text
image     imagem do carro
name      nome do carro
subtitle  texto abaixo do nome
bank      texto verde abaixo do subtitle
url       URL final / target
```

Exemplo estrutural:

```json
{
  "question": "🚗 Encontrei 3 ofertas exclusivas para você! | Toque na que mais te interessa para ver as condições:",
  "offers": [
    {
      "name": "Volkswagen Polo",
      "subtitle": "Taxa reduzida a partir de 1,29% ao mês",
      "bank": "Crédito de até R$50.000 em até 60 meses",
      "image": "https://.../polo.png",
      "url": "https://site.com/oferta-1/"
    }
  ]
}
```

## O que NÃO usar nesse padrão

- Não usar `messages`/“Mensagens da oferta” para cada oferta.
- Não mostrar `Sim, quero simular` + `Não, mostre outra opção` entre ofertas.
- Não apresentar oferta 1 → recusa → oferta 2 → recusa → oferta 3.
- Não criar personalização condicional se Rodolfo apontar que a referência converge para o mesmo lugar.

## Gate/quiz click hardening

Problema observado em CAR-BR: alguns sites ficavam travados no segundo passo do gate (`Qual tipo de veículo você quer financiar?`) ou no CTA `TRANSFERIR PARA ESPECIALISTA`. A causa foi uma combinação de race condition e dependência excessiva do wrapper:

- `quizStepLock` ainda ativo quando o usuário clicava rápido no segundo passo; o clique era descartado e os botões já tinham sido desabilitados visualmente.
- O CTA final dependia do callback de `window.jbftag.showRewardedAds`; quando o wrapper não chamava o callback, o modal não fechava.

Padrão robusto:

```js
const answerButton = e.target && e.target.closest ? e.target.closest(".aq-answer") : null;
if (answerButton) {
  if (quizStepLock) return;
  quizStepLock = true;
  const currentSlide = document.querySelector('.aq-slide[data-step="' + quizStep + '"]');
  if (currentSlide) currentSlide.querySelectorAll(".aq-answer").forEach(btn => btn.style.pointerEvents = "none");
  setTimeout(function () {
    nextQuizStep();
    quizStepLock = false;
  }, 500);
}

const ctaButton = e.target && e.target.closest ? e.target.closest("#aq-cta") : null;
if (ctaButton) {
  const safeCloseQuiz = function () {
    if (!quizAlreadyClosed) {
      quizAlreadyClosed = true;
      closeQuiz();
    }
  };
  setTimeout(safeCloseQuiz, 1200);
  try {
    window.jbftag = window.jbftag || { cmd: [] };
    window.jbftag.cmd.push(() => {
      if (window.jbftag.showRewardedAds) window.jbftag.showRewardedAds(safeCloseQuiz);
      else safeCloseQuiz();
    });
  } catch (err) {
    safeCloseQuiz();
  }
}
```

Validation for this bug must be real click progression, not just HTTP/HTML markers: step 1 button advances to step 2, step 2 button advances to final slide, CTA closes the modal and starts the chat.

## Validação obrigatória

1. Abrir a rota com cachebuster quando houver Cloudflare/APO:
   `https://dominio/chat/car/br1/?zeus_cache=TIMESTAMP&utm_source=zeusqa`
2. Avançar o gate.
3. Na pergunta final, escolher uma resposta qualquer.
4. Confirmar que aparece a fala de busca antes dos cards: `🔍 Estou pesquisando as melhores condições para você...`.
5. Confirmar que aparecem as falas `Encontrei 3 ofertas...` e `Toque na que...` imediatamente antes dos cards.
6. Confirmar que aparecem os 3 cards juntos.
7. Confirmar que cada card tem imagem, nome, subtitle, texto verde e URL.
8. Confirmar UTM passthrough nos links finais.
9. Validar no WP Admin que as 3 falas pré-card estão editáveis em campos separados, além dos campos dos cards.
10. Se a URL limpa mostrar versão antiga mas cachebuster/no-cache mostrar versão nova, tratar como cache Cloudflare/APO, não falha de deploy.
