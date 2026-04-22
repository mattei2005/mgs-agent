# Sites e verticais

## Como funciona

Cada domínio MGS é um **site**. Dentro de cada site, operamos uma ou mais **verticais** — combinação de **país + nicho + idioma**.

Formato da vertical: `{PAIS}-{NICHO}-{LINGUA}`

Exemplos:
- `US-CC-EN` = Estados Unidos / cartões de crédito / inglês
- `GB-CC-EN` = Reino Unido / cartões de crédito / inglês
- `MX-CC-ES` = México / cartões de crédito / espanhol
- `BR-GAME-BR` = Brasil / games / português brasileiro
- `DE-CC-DE` = Alemanha / cartões de crédito / alemão

## Convenção de idioma

- `EN` = inglês (variante depende do país: US-EN, GB-EN, CA-EN, ZA-EN)
- `ES` = espanhol (variante depende do país: US-ES, MX-ES, ES-ES, AR-ES)
- `DE` = alemão (Alemanha)
- `FR` = francês (Canadá ou Europa)
- `TR` = turco (Turquia)
- `PT` = português de Portugal
- `BR` = português do Brasil

## Sites ativos

### Nicho: Cartões de Crédito (CC)

#### Sites multi-idioma (mesmo domínio serve várias verticais)

| Domínio | Verticais |
|---------|-----------|
| lyzmo.com | US-CC-EN, GB-CC-EN |
| finanzas.lyzmo.com | US-CC-ES |
| eggbev.com | US-CC-EN, GB-CC-EN |
| finanzas.eggbev.com | US-CC-ES |
| ducapes.com | US-CC-ES |
| finance.ducapes.com | US-CC-EN |
| finance.topfeed.fun | US-CC-EN, GB-CC-EN |
| finanzas.topfeed.fun | US-CC-ES |
| zuout.com | US-CC-EN, GB-CC-EN |
| finanzas.zuout.com | US-CC-ES |
| zytiva.com | US-CC-EN, GB-CC-EN |
| finanzas.zytiva.com | ES-CC-ES, US-CC-ES |
| newsoun.com | US-CC-EN, GB-CC-EN |
| finanzas.newsoun.com | US-CC-ES |
| de.newsoun.com | DE-CC-DE |
| openzed.com | US-CC-EN, GB-CC-EN |
| finanzas.openzed.com | ES-CC-ES, US-CC-ES |
| cliquet.com | US-CC-EN, GB-CC-EN |
| finanzas.cliquet.com | US-CC-ES |
| wantabrand.com | US-CC-ES |
| finance.wantabrand.com | US-CC-EN, GB-CC-EN |
| fincgriffin.com | GB-CC-EN, TR-CC-TR, ES-CC-ES |
| financeadx.com | US-CC-EN, US-CC-ES, CA-CC-EN, CA-CC-FR, MX-CC-ES, ZA-CC-EN, AR-CC-ES |
| marevelx.com | DE-CC-DE, US-CC-EN, US-CC-ES, MX-CC-ES |
| helixenit.net | DE-CC-DE, US-CC-EN, US-CC-ES, MX-CC-ES |
| infinitynexx.com | US-CC-EN, US-CC-ES, MX-CC-ES |
| vizioid.com | US-CC-EN, US-CC-ES, MX-CC-ES |
| xyvlov.com | DE-CC-DE, US-CC-EN, US-CC-ES, MX-CC-ES |

### Nicho: Games (GAME)

| Domínio | Verticais |
|---------|-----------|
| gamezonead.com | BR-GAME-BR, MX-GAME-ES |

### Nicho: Vagas de Emprego (JOB)

| Domínio | Verticais |
|---------|-----------|
| seuprimeiroempregoam.com | US-JOB-EN |
| empleo.seuprimeiroempregoam.com | ES-JOB-ES |

### Nicho: Carros (CAR)

| Domínio | Verticais |
|---------|-----------|
| creditoparaveiculo.com | BR-CAR-BR |

## Observações sobre subdomínios

MGS tem histórico misto de organização de idiomas:
- **Sites novos (multi-idioma no mesmo domínio):** exemplo `financeadx.com` roda 7 verticais no mesmo domínio
- **Sites antigos (legacy, subdomínio por idioma):** exemplo `finanzas.eggbev.com` pra ES, `de.newsoun.com` pra DE

Não existe padrão rígido — cada site foi configurado quando foi criado e se manteve.

## Fonte de verdade programática

Para dados sempre atualizados (status ativo/inativo, configs técnicas, pixel IDs, etc), consulte:

```
/root/mgs-agent/data/sites.json
```

Agentes devem usar o JSON pra operações (criar artigo, subir campanha) e este arquivo markdown pra **contexto conceitual** (entender o domínio e a vertical).

## Stack técnica dos sites

- WordPress com tema custom
- Yoast SEO
- WP Rocket (cache)
- Lazy Blocks (blocos customizados)
- Cloudflare Pro (DNS/CDN)
- Active Campaign (email capture + automação)
- SMS lead capture
- Rec pages: `/rec-{vertical}-{card-name}/`
- P1 pages: páginas how-to-apply
