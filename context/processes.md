# Processos e fluxos de trabalho

## Fluxo de criação de conteúdo

### REC (Recommender)
1. Definir: site, vertical, card/tema
2. Pesquisar o produto (cartão, serviço)
3. Gerar artigo seguindo template da vertical
4. Gerar imagem do produto (Gemini 2.5 Flash Image)
5. Publicar como rascunho no WordPress
6. Revisão editorial (Raquel ou gestor de conteúdo)
7. Publicar ao vivo
8. Configurar pagination pra P1

### P1 (Page 1)
Similar ao REC, mas:
- Conteúdo mais detalhado
- Dispara interstitial ad no clique de pagination
- CTA final leva ao site oficial do banco/serviço
- Linkado a partir do REC

### REC+P1 (combo)
- Pipeline que cria REC e P1 em sequência
- Configura pagination automática entre eles
- Fluxo mais comum quando lança cartão novo

### Artigo SEO
- 1200+ palavras
- Foco em long-tail keywords
- Sem CTA pra banco (tráfego orgânico puro)
- Sem pagination

## Fluxo de revisão de conteúdo

Raquel cuida da maioria das revisões:
- Checagem de plágio
- Ajustes editoriais
- Verificação de links
- Conferência de imagens
- Aprovação final antes de publicar

## Fluxo de campanha (aquisição)

1. Kelly prepara criativos (imagens/vídeos)
2. Gestor recebe criativos e pede Geizian/CEO se precisa ajuste
3. Gestor cria campanha no FB Ads ou Google Ads
4. Configura:
   - Pixel da vertical
   - UTMs com seu ID de gestor (g001-d, g003-d, etc)
   - Segmentação
   - Budget
5. Lança campanha
6. Monitora diariamente
7. Otimiza (pausa/escala/ajusta)

## Fluxo de análise de sites

Atena também atua como auditora de conteúdo. Checks que ela deve saber fazer:

- **Links quebrados** — scanning
- **Cartões expirados** — produto fora do ar, CTA morto
- **Plágio** — conteúdo duplicado com outros sites
- **SEO básico** — meta tags, alt text
- **Conformidade regulatória** por país:
  - UK: FCA compliance
  - US: TILA compliance
  - EU: GDPR
  - BR: BACEN
  - MX: CNBV
- Sugestões de melhoria baseadas em análise

## Comunicação interna

- **Discord** é o canal principal de operação dos agentes
- **Server:** MGS Digital Corp
- **Canais dos agentes:**
  - `#zeus-admin-agent`
  - `#atena-content-agent`
  - (futuros: `#ares-ads-agent`)

## Infraestrutura

### Servidores
- VPS Hetzner (CPX11)
- IP: 87.99.151.107

### Código
- GitHub: https://github.com/mattei2005/mgs-agent (privado)

### Credenciais
- 1Password vault: "MGS Conteúdo"
- Service account configurado no VPS
