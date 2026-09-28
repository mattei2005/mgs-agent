# MGS Offer Quiz

Plugin WordPress interno da MGS para publicar quizzes/landings estáticas de oferta por gestor.

## Contrato

- Rotas: `/quiz/quiz-v1-g001/` a `/quiz/quiz-v1-g006/`.
- Entrega: `index.html` físico, sem inicializar WordPress no request público.
- Sem formulário, nome, email, telefone, lead, SMS ou evento de campanha.
- CTA único para o artigo configurado.
- Layout V1 replica geometria e copy visível da referência SoliciteFácil: card branco centralizado, cabeçalho verde com timer, hero `até / R$5.000 / aprovados na hora`, três benefícios numerados, CTA `Ver ofertas agora`, prova social, trust row, disclaimer e rodapé. O botão secundário/formulário de email foi removido integralmente.
- A prova social é um contador diário real compartilhado entre G001–G006: o primeiro page view do dia exibe `1.892 pessoas`, cada acesso seguinte soma `+1`, e uma nova linha diária reinicia automaticamente a base em `1.892` no fuso `America/Sao_Paulo`.
- Cada abertura faz um `POST` sem cache para `/wp-json/mgs-offer-quiz/v1/daily-view`; o servidor incrementa atomicamente a tabela `{prefix}mgs_offer_quiz_daily_views` com `LAST_INSERT_ID`, evitando perda de contagem sob concorrência. Se o endpoint falhar, o frontend mantém `1.892` como fallback.
- Preserva `utm_*`, `fbclid`, `gclid` e parâmetros personalizados; parâmetros já presentes no destino vencem.
- WordPress funciona como plano de controle para edição e duplicação.
- Páginas públicas usam `noindex,follow`.

## Configuração inicial

Ao ativar pela primeira vez, o plugin cria seis configurações para G001–G006. Somente G001 nasce ativa para o canário; G002–G006 permanecem inativas até o canário ser validado. O destino atual é:

`https://dicasfinancas.info/rec-br-cc-cartao-de-credito-nubank/`

## Validação

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```
