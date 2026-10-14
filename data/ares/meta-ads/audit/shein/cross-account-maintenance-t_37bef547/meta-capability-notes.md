# Meta capability notes — t_37bef547

Consultadas antes das alterações, complementadas pelo GET live account-scoped. Nenhum teste de mutação live.

1. Meta Graph v26 — Ad Account Ads:
   https://developers.facebook.com/docs/marketing-api/reference/ad-account/ads/
   Extração real exibiu `POST /act_{ad_account_id}/ads`, campos `adset_id`, `creative`, `name`, `status` e `source_ad_id` (ID of the source Ad, if applicable).
   Essa documentação permite representar a lineage no create direto, mas não garante aceitação de um source_ad_id de outra conta nem entrega. Verificação live de API/serving permanece false.

2. Ad Copies:
   https://developers.facebook.com/docs/marketing-api/reference/adgroup/copies/
   Documenta `POST /{ad_id}/copies`, `adset_id` e `creative_parameters`. A implementação desta tarefa NÃO usa copies entre contas. Fonte read-only é referência, não um shell copiado.

3. Ad Account Campaigns:
   https://developers.facebook.com/docs/marketing-api/reference/ad-account/campaigns/
   Criação no edge account-scoped; listagem padrão omite DELETED/ARCHIVED. Inventário do alvo usado para next-number, fonte por ID exato e account_id real.

4. Ad Account Adsets:
   https://developers.facebook.com/docs/marketing-api/reference/ad-account/adsets/
   Create no edge account-scoped, com campaign_id do alvo, billing_event, optimization_goal, targeting/promoted_object e bid_amount no conjunto. CBO bid_strategy vem da campanha. Não usar ad_bid_amount para o cap.

5. Evidência read-only do caso:
   Fonte C129 tem OUTCOME_SALES/OFFSITE_CONVERSIONS/ADD_TO_WISHLIST, USD50 CBO/MAXVOL, duas referências de anúncio e Page/Instagram próprios. Alvo vazio USD/ET, ADVERTISE e pixel existentes validados separadamente.
   A Page padrão de onboarding Savings Spot retornou PBIA data=[]; nenhum PBIA foi criado. Sem delta expresso de Page, a rota preserva a identidade da referência exata. Leitura da Page/tarefas/pixel dessa identidade passou. Não converter a observação de onboarding em associação exclusiva.

Limites: associação de mídia ao alvo e clean metadata serão validados na preparação real. Os IDs sintéticos no template offline nunca são IDs Meta. HTTP200, static plan e COMPLETE_PAUSED fake não comprovam campanha criada/serving.
