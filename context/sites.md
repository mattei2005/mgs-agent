# Sites e Verticais — MGS

> Status: proposta canônica v0.3
> Fonte-mãe: `context/company-os.md`
> Base operacional: `context/company-current-operating-model.md`
> Regra: este arquivo é conceitual. Dados técnicos/automação ficam em `data/sites.json`.

## Princípio

Cada domínio MGS é um site. Dentro de cada site, a empresa pode operar uma ou mais verticais, definidas por país, nicho e idioma.

```text
Formato de vertical: {PAIS}-{NICHO}-{IDIOMA}
Exemplo: GB-CC-EN = Reino Unido / cartão de crédito / inglês
```

Este arquivo serve para entender a operação e o portfólio. Ele não substitui:

```text
/root/mgs-agent/data/sites.json
```

`data/sites.json` é a fonte técnica usada por pipelines automatizados, credenciais, templates, WordPress e publicação. Atualmente ele pode conter apenas sites já integrados ao pipeline automatizado; isso não significa que os outros sites não existam operacionalmente.

Resumo operacional atual:

```text
Camada                         Status
------------------------------ ------------------------------------------------
Portfólio conceitual            Lista sites/domínios/subdomínios e verticais MGS.
Automação em data/sites.json    Lista apenas sites prontos para pipeline automático.
WordPress/dashboards externos   Vencem para estado técnico real quando validados.
```

---

## Convenção de vertical

```text
Código     Significado
---------  ------------------------------------------------
CC         Credit Cards / cartões de crédito
GAME       Games
JOB        Vagas de emprego / jobs
CAR        Carros / veículos
```

## Convenção de idioma

```text
Código     Idioma
---------  ------------------------------------------------
EN         Inglês; variante depende do país.
ES         Espanhol; variante depende do país.
DE         Alemão.
FR         Francês.
TR         Turco.
PT         Português de Portugal.
BR         Português do Brasil.
```

Observação: a operação usa histórico misto. Alguns sites usam domínio principal multi-idioma; outros usam subdomínios por idioma/mercado.

---

## Sites e verticais conceituais

### Cartões de Crédito — CC

```text
Domínio                         Verticais conceituais
------------------------------  ---------------------------------------------------
lyzmo.com                       US-CC-EN, GB-CC-EN
finanzas.lyzmo.com              US-CC-ES
eggbev.com                      US-CC-EN, GB-CC-EN
finanzas.eggbev.com             US-CC-ES
ducapes.com                     US-CC-ES
finance.ducapes.com             US-CC-EN
finance.topfeed.fun             US-CC-EN, GB-CC-EN
finanzas.topfeed.fun            US-CC-ES
zuout.com                       US-CC-EN, GB-CC-EN
finanzas.zuout.com              US-CC-ES
zytiva.com                      US-CC-EN, GB-CC-EN
finanzas.zytiva.com             ES-CC-ES, US-CC-ES
newsoun.com                     US-CC-EN, GB-CC-EN
finanzas.newsoun.com            US-CC-ES
de.newsoun.com                  DE-CC-DE
openzed.com                     US-CC-EN, GB-CC-EN
finanzas.openzed.com            ES-CC-ES, US-CC-ES
cliquet.com                     US-CC-EN, GB-CC-EN
finanzas.cliquet.com            US-CC-ES
wantabrand.com                  US-CC-ES
finance.wantabrand.com          US-CC-EN, GB-CC-EN
fincgriffin.com                 GB-CC-EN, TR-CC-TR, ES-CC-ES
financeadx.com                  US-CC-EN, US-CC-ES, CA-CC-EN, CA-CC-FR, MX-CC-ES
                                ZA-CC-EN, AR-CC-ES
marevelx.com                    DE-CC-DE, US-CC-EN, US-CC-ES, MX-CC-ES
helixenit.net                   DE-CC-DE, US-CC-EN, US-CC-ES, MX-CC-ES
infinitynexx.com                US-CC-EN, US-CC-ES, MX-CC-ES
vizioid.com                     US-CC-EN, US-CC-ES, MX-CC-ES
xyvlov.com                      DE-CC-DE, US-CC-EN, US-CC-ES, MX-CC-ES
wavesbee.com                    US-CC-EN
finanzas.wavesbee.com           US-CC-ES
conectageral.com                US-CC-EN
finanzas.conectageral.com       US-CC-ES
portalrelevante.com             US-CC-EN
finanzas.portalrelevante.com    US-CC-ES
```

### Games — GAME

```text
Domínio                         Verticais conceituais
------------------------------  ---------------------------------------------------
gamingadx.com                   US-GAME-EN, BR-GAME-BR, MX-GAME-ES
gamezonead.com                  US-GAME-EN, BR-GAME-BR, MX-GAME-ES
gamehubad.com                   US-GAME-EN, BR-GAME-BR, MX-GAME-ES
```

### Carros / Veículos — CAR

```text
Domínio                         Verticais conceituais
------------------------------  ---------------------------------------------------
fincgriffin.com                 US-CAR-EN
creditoparaveiculo.com          BR-CAR-BR, PT-CAR-PT
financiamentoautoadx.com        BR-CAR-BR, PT-CAR-PT
financiarveiculo.com            BR-CAR-BR, PT-CAR-PT
autocreditadx.com               US-CAR-EN, MX-CAR-ES
carcreditad.com                 US-CAR-EN, MX-CAR-ES
autolendpro.com                 US-CAR-EN, MX-CAR-ES
```

### Vagas de Emprego — JOB

```text
Domínio                         Verticais conceituais
------------------------------  ---------------------------------------------------
seuprimeiroempregoam.com        US-JOB-EN
empleo.seuprimeiroempregoam.com  ES-JOB-ES
```

---

## Sites na Smart Bidding e ActiveView

Smart Bidding e ActiveView são empresas parceiras Google com redes AdX/Ad Manager próprias. O site precisa estar adicionado à rede correta e ter blocos configurados para monetizar.

Regra operacional atual:

```text
Smart Bidding   Dashboard principal/preferida da MGS.
ActiveView      Exceção ativa para openzed, cliquet e seus subdomínios.
```

Sites/subdomínios AV conhecidos:

```text
openzed.com
finanzas.openzed.com
cliquet.com
finanzas.cliquet.com
```

Se houver dúvida entre este arquivo e dashboards externos validados, vence a fonte operacional validada: Smart Bidding, ActiveView ou planilha/relatório confirmado por Rodolfo.

---

## Relação com conteúdo

Atena usa sites/verticais para gerar e publicar conteúdo conforme escopo aprovado.

```text
Conteúdo                  Uso
------------------------  ------------------------------------------------------
REC                       Recomendação/artigo comercial.
P1                        Página de continuação/conversão.
REC + P1                  Fluxo combinado.
Artigo SEO                Conteúdo de apoio/categoria/long-tail.
```

Para operações automatizadas, Atena deve consultar `data/sites.json`. Se o site não estiver no JSON, não assumir que está pronto para pipeline automático.

Regra prática: ausência em `data/sites.json` bloqueia automação, não bloqueia existência operacional do site. Para ativar um site no pipeline, antes é necessário validar credenciais, WordPress, template, categoria, usuário publicador, caminho técnico e política de publicação.

---

## Relação com campanhas

Gestores e Ares usam sites/verticais como destino de campanhas.

```text
Item                       Regra
-------------------------  -----------------------------------------------------
UTM_medium                 Deve carregar código do gestor.
Criativos                  Devem vir do Google Drive de criativos aprovados.
Pixel/GTM/tracking          Escala Rodolfo/Tech quando houver risco.
ROI                        Deve conectar custo de campanha + receita do site.
```

Ares pode trabalhar com campanhas e análise de performance, mas não configura ChatPion/DigitalTrChat, quiz, SMS Funnel, blocos AdOps ou estrutura técnica do site sem escopo/aprovação.

---

## Stack técnica padrão dos sites

```text
Camada                     Uso
-------------------------  -----------------------------------------------------
WordPress                  CMS principal dos sites.
Tema custom                Estrutura visual/funcional.
Yoast SEO                  SEO editorial.
WP Rocket                  Cache/performance quando instalado.
Lazy Blocks                Blocos customizados, incluindo estruturas de anúncio.
Cloudflare                 DNS/CDN conforme site.
GTM / pixels               Tracking e integração com ads.
Blocos de anúncio          Monetização via Smart Bidding/ActiveView.
```

A stack real pode variar por site. A fonte técnica deve ser validada em `data/sites.json`, WordPress, RunCloud/VPS, Cloudflare ou dashboard externo conforme o caso.

Responsabilidade por camada:

```text
Camada                         Dono / fonte
------------------------------ ------------------------------------------------
Site WordPress / setup técnico  Rodolfo / Tech / WordPress.
Conteúdo editorial              Raquel / Atena / Content Operations.
Campanhas e tráfego             Gestores / Ares conforme escopo aprovado.
Criativos aprovados             Kelly / Ares / Google Drive.
Monetização / blocos            Smart Bidding ou ActiveView + Rodolfo/AdOps.
Financeiro / ROI                Rodolfo / planilha financeira.
```

---

## Observações operacionais

### Subdomínios e histórico

A MGS tem histórico misto de organização:

```text
Modelo novo / multi-idioma       Um domínio pode servir várias verticais.
Modelo legacy / subdomínio        Subdomínio por idioma/mercado.
```

Não existe padrão rígido universal. Cada site deve ser tratado conforme sua configuração real.

### fincgriffin.com

`fincgriffin.com` é uma exceção operacional em infraestrutura externa, sem SSH/SFTP conhecido para agentes. Desde 2026-08-17, Zeus possui acesso programático validado ao WordPress via WP Admin e REST usando o item `Fincgriffin Wordpress` no 1Password. Instalação/ativação de plugins deve usar REST autenticado; configurações devem usar o formulário real do WP Admin com readback autenticado. Operações de arquivo que dependam de SSH/SFTP continuam manuais até existir uma rota validada.
