## Correção aprendida com playbook externo de clone

Rodolfo trouxe um playbook de outro agente para criação/clonagem Meta. A diferença crítica contra a primeira implementação local é:

```text
Rota antiga local                | Rota correta para Messenger/replacement
---------------------------------|------------------------------------------------
Reaproveitar object_story_spec bruto | Não usar object_story_spec bruto de campanha antiga
Reaproveitar asset_feed_spec bruto   | Recriar creative a partir de video_id ou image_hash
Fallback com creative_id legado      | Evitar como rota padrão, especialmente cross-page
Graph v20.0                          | Preferir v25.0 para o fluxo de criação se validado
Recriar messenger_doc como link      | Não usar messenger_doc como destino externo
```

Para `clone-source` na mesma página:
1. Ler ads ativos da source.
2. Extrair `video_id` para vídeos ou `image_hash` para imagens.
3. Criar novos adcreatives com `object_story_spec` mínimo contendo `page_id` e asset (`video_data.video_id` ou `link_data.image_hash` quando aplicável), mais `degrees_of_freedom_spec` e `page_welcome_message` seguro.
4. Em Messenger, `page_welcome_message` deve usar `is_user_editing=true` e não enviar `template_id` nem `template_version`.
5. Não enviar `standard_enhancements`.
6. Exigir 3 ads utilizáveis; se criar menos de 3, arquivar/deletar a campanha parcial.

Read-only em 2026-06-18 confirmou que os 3 creatives winners atuais possuem `asset_feed_spec.videos` com `video_id` disponível, então há insumo para trocar o script para uma rota baseada em `video_id`, não em `messenger_doc`/creative bruto. Auditoria: `/root/mgs-agent/data/ares/meta-ads/audit/clone/creative-asset-inspect-readonly.json`.

Tentativa controlada posterior criou com sucesso campanha PAUSED, adset PAUSED e adcreative novo usando `video_id + image_url` de thumbnail, sem `messenger_doc`. O bloqueio remanescente ficou no `POST /ads`: `code=31/subcode=3858385`. Ou seja, a rota de criativo foi corrigida; a camada de criação do ad via API continua bloqueada para o token/app atual. Auditoria principal: `/root/mgs-agent/data/ares/meta-ads/audit/clone/clone-videoid-failed-20260618T044855Z.json`. Campanha parcial `120248892823990604` foi marcada `DELETED` e verificada via GET.
