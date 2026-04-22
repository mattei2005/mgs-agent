# Aquisição de tráfego

## Canais de aquisição paga

MGS usa 2 canais principais pra trazer usuários aos sites:

### 1. Facebook Ads
Principal canal de aquisição. Campanhas geridas pelos gestores.

**Objetivos de campanha:**
- **Link clicks** — direciona direto pro site MGS
- **Messages (MSG)** — direciona pro Messenger (onde ChatPion opera — ver seção Conversão)

**Business Managers:**
- **Digital Trust** (#155263197283282) — linha de crédito US
- **Zion Media** (#1114638070120676) — Canada

### 2. Google Ads
Campanhas sempre direcionadas **direto pro site MGS** (sem bot intermediário).

**Contas:**
- Mattei MX 1
- Mattei MX 2
- Mattei MX3

## Ferramenta de conversão: ChatPion (Messenger bot)

**ChatPion não é canal de aquisição** — é **ferramenta de conversão** que opera junto com campanhas FB Ads de objetivo MSG.

### Como funciona

1. MGS tem páginas no Facebook por nicho/idioma
2. Campanhas FB Ads são configuradas com objetivo "mensagem" (MSG)
3. User clica no anúncio → abre conversa no Messenger
4. ChatPion intercepta → dispara fluxo montado previamente na ferramenta
5. Fluxo: mensagens sequenciais com botões/CTAs
6. User clica no botão → abre URL do site MGS
7. No site, consome conteúdo e gera receita (AdSense/AdX)

### Configuração

- Bot opera por página FB (uma página = um fluxo)
- Fluxo é montado dentro do ChatPion, conectado à página
- Primeiras 24h: sequência de mensagens agressiva
- Depois: 1 mensagem diária via MCT (Multi-Channel Tool)
- Idiomas: EN, ES, BR, DE, IT, TR, LV
- Nichos ativos: cartões de crédito, vagas de emprego

### Contas operacionais

Múltiplas contas de disparo por site (ex: `disparosconecta`, `disparosmarevelx`, `disparoshelixenit`).

## Ferramentas auxiliares

### AdsPower
Antidetect browser com proxies por instância. Usado pra operar múltiplas contas FB (contingência).

### Keitaro
Tracker/TDS. Exemplos:
- `tarjeta.wantabrand.com`

### Push alerts
Alertas push específicos para nicho de cartões de crédito.

## Funil de aquisição

### Via FB Ads direto pro site (link clicks)
```
Ad FB → clique → site MGS → REC → P1 → CTA → site final do produto
```

### Via FB Ads → Messenger (ChatPion)
```
Ad FB (MSG) → Messenger → bot dispara fluxo → user clica botão → site MGS → REC → P1 → site final
```

### Via Google Ads
```
Ad Google → clique → site MGS direto → REC → P1 → site final
```

## Operação típica do gestor

Os gestores trabalham com:
- Criação de campanhas (FB/Google)
- Criativos preparados pela Kelly (+ Geizian quando precisa)
- Segmentação por país, idade, interesse
- Otimização de budget por ROAS
- Monitoramento diário
- Ajustes em criativos e públicos

## Pixels e tracking

- GTM (Google Tag Manager) setado em cada site
- Pixels Meta por vertical
- Tracking de gestor via `utm_medium`:
  - `g001-d` = Ícaro
  - `g003-d` = Isliago
  - (outros mapeados)
- Anti-duplicação via `pageview_index=1` (sessionStorage)
- UTM propagation via WP Code Snippets
