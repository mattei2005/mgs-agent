# Deprecated yoast-scorer scripts

## yoast-score-updater.js

Movido para deprecated em 02/05/2026 (P1-13 fix).

Razões:
- Não é chamado por nenhum cron
- Não é referenciado por nenhuma SKILL ativa
- Único caller (`scripts/deprecated/update-yoast-scores.sh`) também está deprecated
- yoast-scorer.js (sibling) é o engine ativo, usado pela SKILL content-generate-rec

Diferenças do yoast-scorer.js (ativo):
- Argumentos em ordem diferente
- Output JSON com chaves diferentes (seo vs seo_score)
- Provavelmente tentativa abandonada de refactor (criada 31min após yoast-scorer.js)

Manter por enquanto pra referência histórica. Pode ser deletado após 6 meses se não houver retorno ao seu uso.
