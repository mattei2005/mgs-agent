## Relatório final obrigatório — REC+P1

Ao finalizar REC+P1, responder em uma única mensagem.

Disciplina de formato para Rodolfo: usar o formato enxuto aprovado. Se o relatório mostra `subtitle <chars>` e `excerpt <chars>` na linha de validação, isso conta como evidência desses campos. Não adicionar linhas próprias `Subtitle: <texto>` ou `Excerpt: <texto>` no relatório padrão REC+P1, salvo pedido explícito de versão expandida para QA editorial.

Usar o renderer determinístico sempre que existir output JSON compatível:

```bash
python3 /root/mgs-agent/scripts/render-article-summary.py --type rec-p1 <rec-json> <p1-json>
```

Regra operacional: em REC+P1 normal, não montar relatório final manualmente se houver JSON dos runners. O renderer é obrigatório para evitar omissão de campos como Subtitle, Excerpt, tempo detalhado e custos. Se o renderer falhar, corrigir o JSON/renderer ou declarar o motivo antes de usar fallback manual.

O formato manual só é permitido se:

- o renderer não suportar algum campo ainda;
- o renderer falhar e o motivo for informado;
- ou a operação for auditoria/reparo sem JSON completo.

Formato mínimo obrigatório quando fallback manual for necessário:

```text
📄 REC Post ID: `<numero do post>`
🔗 REC: `<link>`
✏️ Edit REC: `<link>`
🔗 Slug: `<slug>`
📌 Status: `<status>`

📄 P1 Post ID: `<numero do post>`
🔗 P1: `<link>`
✏️ Edit P1: `<link>`
🔗 Slug: `<slug>`
📌 Status: `<status>`

📄 REC
📊 Yoast: SEO `<pontuacao>` / Readability `<pontuacao>`
• Validação: `<quantidade de palavras>` palavras / subtitle `<quantidade de chars>` chars / excerpt `<quantidade de chars>` chars / público HTTP `<codigo ou evidência draft>`
• Title: `<titulo>` — `<quantidade de chars>` chars
• Focus: `<palavra chave usada>`
• Meta Description: `<texto que foi inserido>` — `<quantidade de chars>` chars
• Tags: `<tags>`
• Imagem Card: `<link da imagem do card>`
• Imagem Featured: `<link da featured image>`
• Oferta final: `<link final utilizado>`

📄 P1
📊 Yoast: SEO `<pontuacao>` / Readability `<pontuacao>`
• Validação: `<quantidade de palavras>` palavras / subtitle `<quantidade de chars>` chars / excerpt `<quantidade de chars>` chars / público HTTP `<codigo ou evidência draft>`
• Title: `<titulo>` — `<quantidade de chars>` chars
• Focus: `<palavra chave usada>`
• Meta Description: `<texto que foi inserido>` — `<quantidade de chars>` chars
• Tags: `<tags>`
• Imagem Card: `<link da imagem do card>`
• Imagem Featured: `<link da featured image>`
• Oferta final: `<link final utilizado>`

⏱️ Tempo total dos runners: REC `<tempo>` + P1 `<tempo>`
💰 Custo estimado: REC `<custo REC>` + P1 `<custo P1>` = `<total>`
```

Se tempo passar de 60 segundos, exibir em minutos de forma legível.

Não reportar apenas duração do runner se retries, reparos, QA ou orquestração consumiram tempo adicional. Reportar tempo percebido da operação quando disponível.

---

## Quando bloquear

Bloquear antes de publicar/reportar sucesso quando:

- REC/P1 de referência ou oferta final não correspondem ao cartão;
- dado essencial não está confirmado;
- runner/orchestrator indica uso de cache editorial indevido;
- idioma de produção conflita com `data/sites.json`;
- o artigo mistura idiomas, por exemplo corpo em inglês com headings/details em português como `Benefícios` ou `Quem deveria usar`;
- imagem do card falha em identidade/qualidade;
- featured REC e P1 são iguais;
- a featured image mostra o cartão cortado, ocluído por pessoa/objeto/camada, ou sem bordas/cantos/logo críticos totalmente visíveis;
- REC e P1 repetem frases/parágrafos demais;
- benefícios aparecem como labels genéricos em vez de funcionalidades reais do produto, por exemplo `Main benefit`, `Financial value`, `Usage convenience` ou `Complementary benefit`;
- category/tag/descriptor interpreta mal um fato confirmado, por exemplo transformar `Clubcard points` em `Travel rewards` sem benefício de viagem confirmado;
- REC/P1 contêm `reader`, `readers` ou `users` como tratamento editorial ao público em vez de segunda pessoa (`you`/`your`), salvo ocorrência técnica inevitável fora do corpo editorial;
- REC ou P1 não contém exatamente um LazyBlock de card válido no fluxo normal;
- CTA final não renderiza como botão/LazyBlock válido ou aparece apenas como hyperlink simples/CSS solto;
- headings/details vazios aparecem no HTML final;
- title/subtitle/excerpt/meta ficam fora dos limites e não foram reparados;
- WordPress/Yoast/public HTTP ou evidência draft não confirma o estado esperado;
- runner/orchestrator retorna erro não resolvido.

---

## Quando consultar references antigas

Consultar `references/` e `references/archive/` apenas quando:

- Rodolfo/Zeus pedir auditoria;
- runner falhar e o erro parecer conhecido;
- uma regra antiga estiver sendo migrada para contract/SKILL/runner;
- for necessário validar histórico de decisão.

Não usar references antigas para substituir o contract ativo durante produção normal.

---

## Regra de encerramento

Só declarar concluído quando houver evidência real.

Se houve retry, reparo, warning, bloqueio, cleanup ou limitação, incluir no resumo final.

Não transformar falha parcial em sucesso total.

---

