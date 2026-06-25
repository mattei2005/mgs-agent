# Exemplos analisados — Chat Funnel MGS

## EMP-BR — FincFrog empréstimo pessoal

Fonte analisada: `https://fincfrog.com/chat/emp/br2/`

### Natureza

- Produto: empréstimo pessoal.
- País/idioma: Brasil / pt-BR.
- Tags JS observadas: `["br", "emp", "rec"]`.
- Interface: WhatsApp fake com consultor aleatório.
- Objetivo: REC interativo + monetização via P1/ofertas.

### Gate inicial

```text
Pergunta:
💰 Qual valor você precisa?

Botões:
- R$ 500 a R$ 3.000
- R$ 3.000 a R$ 10.000
- Acima de R$ 10.000

Final:
Oferta encontrada!
Um consultor foi identificado para te atender agora.
CTA: VER OFERTAS DE EMPRÉSTIMO →
```

### Chat principal

```text
Olá! Eu sou [Nome]. 💰
Sou consultor de empréstimo pessoal e estou aqui para te ajudar...
Vamos encontrar a oferta ideal para você?

Botões:
- ✅ Vamos lá!
- 👀 Quero conhecer as opções

Pergunta 1:
Para qual finalidade você precisa do empréstimo?
- Quitar dívidas
- Realizar um sonho
- Emergência

Pergunta 2:
Você tem nome restrito no SPC/Serasa?
- Sim, mas quero tentar mesmo assim
- Não, meu nome está limpo
- Não sei informar

Loading:
🔍 Estou pesquisando as melhores opções para você...

Final:
🎉 Encontrei 3 ofertas exclusivas para você!
Toque na que mais te interessa para ver as condições:
```

### Ofertas finais — modo cards

```text
Nubank      → https://fincfrog.com/br-chat-emp-nubank/
C6 Bank     → https://fincfrog.com/br-chat-emp-c6-bank/
Banco BV    → https://fincfrog.com/br-chat-emp-banco-bv/
```

### Observações operacionais

- As respostas não alteram as ofertas; a qualificação é psicológica.
- Links finais preservam parâmetros da URL via `mergeSourceParams`.
- Botão “Ligar agora” aponta aleatoriamente para uma das ofertas.
- Melhor para vitrine/comparador de ofertas.

## CAR-BR — FincPro financiamento de veículos

Fonte analisada: arquivo anexado `index_car_br.zip`, HTML `index car br (1).html`.

### Natureza

- Produto: financiamento de veículos.
- País/idioma: Brasil / pt-BR.
- Tags JS observadas: `["br", "car", "rec"]`.
- Interface: WhatsApp fake com especialista aleatório.
- Objetivo: gate com rewarded + recomendação sequencial de ofertas.

### Gate inicial

```text
Pergunta 1:
🚗 Você já tem um carro?
- Sim
- Não

Pergunta 2:
🔍 Qual tipo de veículo você quer financiar?
- Usado
- Seminovo
- Zero KM

Loading:
🔍 Buscando a melhor oferta para você...

Final:
🚗 Oferta encontrada!
Um especialista foi identificado para te atender agora.
CTA: TRANSFERIR PARA ESPECIALISTA →
```

### Chat principal

```text
Olá! Eu sou [Nome]. 🚗
Sou especialista em financiamento de veículos e estou aqui para te ajudar...
Vamos encontrar a oferta ideal para você?

Botões:
- ✅ Vamos lá!
- 👀 Quero conhecer as opções

Pergunta 1:
Quanto você pode pagar por mês?
- Até R$ 500
- Entre R$ 500 e R$ 1.000
- Acima de R$ 1.000

Pergunta 2:
Você tem preferência por algum tipo de veículo?
- Sim, já tenho um modelo em mente
- Não, estou aberto a sugestões
- Ainda estou decidindo
```

### Ofertas finais — modo sequential

```text
Oferta 1: Banco BV
Texto: taxas a partir de 1,32% ao mês, prazo até 60 meses, processo 100% digital.
CTA sim: Sim, quero simular →
CTA não: Não, mostre outra opção
URL: https://fincpro.com/br-chat-car-banco-bv/

Oferta 2: Santander Financiamentos
Texto: taxas a partir de 1,39% ao mês, aprovação rápida, sem ser correntista.
CTA sim: Sim, quero ver as condições →
CTA não: Não, mostre outra opção
URL: https://fincpro.com/br-chat-car-santander-financiamento/

Oferta 3: Bradesco
Texto: carros até 12 anos, até 100% do valor, contratar pelo app, até 20% de economia na taxa.
CTA sim: Sim, quero conhecer →
URL: https://fincpro.com/br-chat-car-bradesco-financiamento/
```

### Observações operacionais

- Inicia 5 leilões rewarded em background no gate.
- `showRewardedAds` é chamado no CTA final; se não existir, fecha o gate e libera o chat.
- Melhor para parecer atendimento humano e respeitar prioridade de oferta.
- Botão “Ligar agora” aponta aleatoriamente para uma das 3 ofertas.

## Decisão de modelo

```text
Cards finais:
- Melhor para EMP/CC quando a oferta é vitrine.
- Usuário escolhe rápido.
- Menos narrativa.

Sequential:
- Melhor quando há ranking de EPC/ROI.
- Parece consultor real.
- Permite empurrar oferta prioritária primeiro.
```
