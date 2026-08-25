# MGS Direct Quiz

Plugin WordPress simples para criar e duplicar landing pages de uma pergunta usadas em tráfego direto.

## Contrato

- LP2: `/quiz/{pais}/sh2-gNNN/`, por exemplo `sh2-g002`.
- LP1: `/quiz/{pais}/sh1-gNNN/`, por exemplo `sh1-g002`.
- O número após `sh` deve corresponder ao modelo visual selecionado.
- Modelos: LP1 (minimal escura) e LP2 (branded verde).
- Configuração por gestor no WordPress Admin, no menu `Landing SHEIN`.
- Interface visual em cards para criar, editar, ativar/desativar e duplicar landings.
- O logo pode ser informado por URL ou escolhido diretamente na Biblioteca de Mídia do WordPress, com preview e remoção.
- Cada opção pode ter um destino HTTPS; o segundo pode reutilizar o primeiro.
- Todos os parâmetros recebidos são preservados nos CTAs, incluindo `utm_source`, `utm_medium`, `utm_campaign`, `utm_adgroup`, `fbclid` e parâmetros personalizados.
- Parâmetros já definidos no destino vencem e não são duplicados.
- `page_id` e `p` não são encaminhados.
- Não coleta dados, não chama APIs externas e não implementa tracking de campanha.
- Duplicação copia somente a configuração, deixa a cópia inativa e exige novo gestor/slug.
- Não implementa exclusão; desative a landing quando ela não deve mais responder.

## Rollback

Desativar o plugin interrompe as rotas sem apagar a option `mgs_direct_quiz_landings`.
