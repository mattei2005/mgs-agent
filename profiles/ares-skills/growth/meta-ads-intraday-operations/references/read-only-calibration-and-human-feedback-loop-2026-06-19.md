# Calibração read-only com feedback do gestor

Use antes de liberar thresholds ou automação em uma nova operação Meta.

1. Fixar conta, período, timezone, moeda, objetivo e métricas.
2. Executar API read-only e salvar a evidência bruta.
3. Produzir recomendações em dry-run, sem write.
4. O gestor confere Ads Manager e fonte externa aplicável.
5. Registrar divergências por campanha e motivo: métrica, atraso, learning, criativo, monetização, tracking ou contexto comercial.
6. Ajustar fórmula/threshold somente com amostra suficiente definida no contrato.
7. Versionar a regra e preservar o contrato anterior como superseded/retired.
8. Liberar controlled-write ou autonomia apenas por decisão explícita do owner autorizado.

Não reaproveitar thresholds de país, site ou estratégia diferentes. BOT/Messenger e tráfego direto requerem calibrações próprias.
