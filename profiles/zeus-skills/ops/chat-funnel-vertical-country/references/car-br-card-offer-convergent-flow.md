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

## Validação obrigatória

1. Abrir a rota com cachebuster quando houver Cloudflare/APO:
   `https://dominio/chat/car/br1/?zeus_cache=TIMESTAMP&utm_source=zeusqa`
2. Avançar o gate.
3. Na pergunta final, escolher uma resposta qualquer.
4. Confirmar que aparecem os 3 cards juntos.
5. Confirmar que cada card tem imagem, nome, subtitle, texto verde e URL.
6. Confirmar UTM passthrough nos links finais.
7. Se a URL limpa mostrar versão antiga mas cachebuster/no-cache mostrar versão nova, tratar como cache Cloudflare/APO, não falha de deploy.
