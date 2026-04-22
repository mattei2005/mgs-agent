# Monetização

## Fonte primária de receita

A receita principal vem de **publicidade display** nos sites MGS, monetizados via redes parceiras do Google.

### Como funciona

1. Sites MGS são aprovados nas redes parceiras do Google (AdX/GAM360)
2. Redes parceiras dão acesso a dashboards web
3. MGS configura blocos de anúncio nos sites através dessas dashboards
4. Impressões e cliques geram receita (RPM/CPM)

### Parceiros principais
- Google AdSense
- Google AdX via GAM360

### Pico histórico
Operação chegou a ~$2M/mês de receita em momentos de alta.

## Dashboards das redes parceiras

As redes parceiras fornecem **dashboards web** pra:
- Configurar blocos de anúncio
- Ver relatórios de performance
- Ajustar wrappers/pixels/bids
- Gerenciar campanhas push, SMS, email

**Importante:** essas dashboards **NÃO têm API pública**. São acessadas manualmente pela equipe MGS. Agentes AI **não interagem** com elas diretamente.

## Canais adicionais de monetização

Além de display, a receita também vem de:

- **Push notifications** — retargeting de usuários
- **SMS marketing** — captura e follow-up
- **Email marketing** — via Active Campaign

## Estratégias de receita

- **REC → P1 pagination:** força impressão adicional (interstitial ad no pagination)
- **Push subscribers:** coleta no primeiro acesso, retarget depois
- **SMS lead capture:** formulário captura, envia campanhas
- **Email list growth:** via opt-in nos formulários

## Stack WordPress pra monetização
- Blocos de anúncio customizados (Lazy Blocks)
- Active Campaign pra email
- Integração com redes push
- Tags e pixels via GTM
