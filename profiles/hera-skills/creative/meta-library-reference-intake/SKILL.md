---
name: meta-library-reference-intake
description: Use quando Rodolfo/Kelly/Geizian enviarem uma ou várias URLs da Meta/Facebook Ad Library para a Hera baixar imagens/vídeos, limpar metadados, padronizar nomenclatura, inventariar e preparar ZIP/Drive como referências criativas, sem tratar como assets finais de campanha.
version: 1.0.0
author: MGS Digital Corp
license: Proprietary
metadata:
  hermes:
    tags: [mgs, hera, creative-ops, meta-library, facebook-ads-library, referencias, sanitizacao, drive]
    related_skills: [creative-brief-handoff, local-browser-automation]
---

# Meta/Facebook Ad Library — Intake de Referências Criativas

## Overview

Use esta skill quando Rodolfo mandar uma ou várias URLs da Meta/Facebook Ad Library e pedir para a Hera baixar criativos de referência, organizar, limpar metadados, nomear e preparar pacote/Drive.

Objetivo: transformar Librarys soltas em um acervo limpo e rastreável de **referências/inspiração criativa** para Kelly, Geizian, Hera e gestores criarem variações próprias.

Regra central:

```text
Criativo baixado da Library = referência/inspiração.
Não é asset MGS final para campanha e não deve ser copiado direto.
```

## When to Use

Use quando o pedido mencionar:

- “baixa essa Library”, “tenho várias Librarys”, “pega os criativos da Library”;
- Meta/Facebook Ad Library com URLs, keywords, anunciantes ou páginas;
- baixar imagens/vídeos de anúncios para benchmark;
- limpar metadados antes de entregar/Drive;
- padronizar nomenclatura e inventário de referências;
- montar ZIP com assets baixados da Library;
- subir referências no Drive para Creative Ops.

Não use para:

- copiar criativo concorrente direto para campanha;
- subir campanha, budget, pixel ou Business Manager;
- burlar login, permissão ou proteção de conteúdo privado;
- tratar referência como asset aprovado em `01_READY`;
- usar arquivo sem sanitização como entregável final.

## Entrada esperada

Rodolfo pode mandar linguagem natural ou lista. Trabalhe com o que vier.

```text
Campo                 Exemplo
────────────────────  ─────────────────────────────────────────────
Library URL(s)        https://www.facebook.com/ads/library/...
Operação/vertical     CC_US_ES, CAR_US_EN, LOANS_US_ES etc.
Keyword/anunciante    utua, competitor/page name
Quantidade            10 imagens, 5 vídeos, tudo disponível, primeiros 50
Destino               ZIP, Drive, ambos
Uso                   referência para criação de variações próprias
```

Se faltar operação/vertical, pode baixar e entregar ZIP + inventário usando `UNKNOWN_OP` ou nome do anunciante, mas **não suba no Drive final** sem destino aprovado.

## Fluxo operacional

```text
1. Importar/entender o pedido e as URLs.
2. Validar acesso via Chromium/Playwright renderizado.
3. Detectar resultados, cards, Library IDs, imagens e vídeos.
4. Baixar só mídia de criativo real, evitando ícones/perfis/thumbnails pequenos.
5. Deduplicar por URL, Library ID e hash.
6. Limpar metadados com sanitizer oficial.
7. Verificar `clean=true` e `harmful_tags_after=0`.
8. Aplicar nomenclatura de referência.
9. Gerar inventário JSON/TXT/CSV quando útil.
10. Entregar ZIP ou preparar Drive conforme autorização.
```

## Acesso à Library

Preferir browser renderizado via Playwright/Chromium, porque `curl` puro costuma retornar challenge/403.

Validações mínimas antes de dizer que funcionou:

```text
Item                         Evidência
───────────────────────────  ─────────────────────────────────────────────
Página renderizou            title/texto da Meta Ad Library
Resultados apareceram        “~N results” ou cards visíveis
Cards carregaram             Library ID(s) detectados
Mídia carregou               img/video tags com dimensões reais
Download real                HTTP 200 e arquivo salvo
Arquivo válido               `file`, dimensão, MIME ou container MP4
```

Se Playwright falhar por challenge, tente:

1. novo contexto com user-agent/locale/timezone;
2. scroll/lazy load;
3. snapshot URL ou URL específica do anúncio;
4. API `/ads_archive` se houver app autorizado;
5. pedir export manual/prints/IDs se tudo bloquear.

Reporte bloqueio com erro curto, sem inventar que baixou.

## Seleção de criativos

Evite baixar elementos que não são criativos:

```text
Baixar                       Ignorar
───────────────────────────  ─────────────────────────────────────────────
Imagens >= 250px reais        ícones 60x60, avatar da página, logo isolado
Vídeos com currentSrc MP4     poster duplicado se o vídeo já foi baixado
Cards com Library ID          imagens soltas fora de card de anúncio
Mídia HTTP 200                URLs expiradas, 403, HTML ou binários inválidos
```

Para “primeiros N”, use ordem visual dos cards carregados na página, mas dedupe por `library_id` para evitar múltiplos assets do mesmo card salvo quando Rodolfo pedir todos os assets de cada anúncio.

## Sanitização obrigatória

Todo arquivo baixado deve passar pelo gate oficial antes de entrega, ZIP ou Drive.

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh batch /path/raw --out-dir /path/clean --agent hera
/root/mgs-agent/scripts/clean-creative-metadata.sh verify /path/clean/arquivo.ext
```

Critério para pacote final:

```text
clean=true
harmful_tags_after=0
arquivo limpo é o que entra no ZIP/Drive
```

Se o sanitizer marcar `clean=false` por tag estrutural claramente não-privada, pare, ajuste o sanitizer somente se for seguro e reporte `REPORT-INFRA` ao Zeus. Nunca entregue arquivo bruto como “limpo”.

## Naming

Referências da Library não devem usar o mesmo status/naming de criativo pronto para campanha.

Modelo recomendado:

```text
{OPERATION}_REF_META_{FORMAT}_{ANGLE}_{ORIENT}_{VARIANT}.{ext}
```

Quando ainda não houver operação/ângulo/orientação confiável:

```text
{SOURCE}_LIBRARY_REF_{FORMAT}_{SEQ}_{LIBRARY_ID}.{ext}
```

Exemplos:

```text
UTUA_LIBRARY_REF_IMG_001_1722197295788906.jpg
UTUA_LIBRARY_REF_VID_001_1563755145269943.mp4
CC_US_ES_REF_META_IMG_PRESTAMO_NV_001.jpg
CC_US_ES_REF_META_VID_APROBACION_NV_001.mp4
```

Regras:

```text
Campo       Regra
──────────  ─────────────────────────────────────────────
FORMAT      IMG ou VID
ANGLE       sugerir pelo criativo; usar UNKNOWN se incerto
ORIENT      PV/NV/PS/NS quando aplicável; senão H/V/SQ provisório
VARIANT     sequência por operação/lote
LIBRARY_ID  preservar no inventário mesmo se não entrar no filename final
```

## Estrutura local de trabalho

Use diretório temporário por lote:

```text
/tmp/hera-meta-library/<slug>_<timestamp>/
├── raw/                 # downloads brutos, nunca entregar como final
├── clean/               # arquivos limpos e verificados
├── package/
│   ├── creatives/ ou videos/
│   ├── README.txt
│   └── inventory.json
├── sanitizer-batch.json
├── library-capture.png  # evidência visual opcional
└── pacote_final.zip
```

## Estrutura Drive sugerida

Antes de subir em Drive, peça/valide com Rodolfo a estrutura. Sugestão segura:

```text
MGS-CRIATIVOS/
└── {OPERATION}/
    └── REFERENCES/
        └── META_LIBRARY/
            ├── IMG/
            │   └── 01_ORIGINAL_CLEAN/
            ├── VID/
            │   └── 01_ORIGINAL_CLEAN/
            └── inventory/
```

Alternativa global se a operação ainda não estiver definida:

```text
MGS-CRIATIVOS/
└── REFERENCIAS_LIBRARY/
    └── {SOURCE_OR_KEYWORD}/
        ├── IMG/
        ├── VID/
        └── inventory/
```

Não colocar referências baixadas da Library em:

```text
IMG/01_READY
VID/01_READY
```

Essas pastas são para criativos MGS adaptados/aprovados, não para concorrentes/referências.

## Inventário obrigatório

Criar pelo menos `inventory.json` e, para leitura rápida, `README.txt`.

Campos mínimos:

```text
source_url
search_keyword/page_name
library_id
format IMG/VID
filename_clean
original_filename/raw_file
mime_type
bytes
sha256
width
height
duration, se vídeo
copy/card_text, quando disponível
CTA, quando detectável
destination_url, quando detectável
angle_suggested
orientation_suggested
source = META_LIBRARY
status = reference_clean
usage = REFERENCE_ONLY
clean = true
harmful_tags_after = 0
notes
```

## Entrega ao usuário

Para ZIP:

```text
Pacote
────────────────────────────────────────────────────────
Arquivo              <nome>.zip
Quantidade           N imagens / N vídeos
Inventário           README.txt + inventory.json
Sanitização          clean=true nos N arquivos
harmful_tags_after   0 nos N arquivos
SHA256               <hash do zip>
Uso                  referência/inspiração; adaptar antes de campanha
```

Anexar com:

```text
MEDIA:/absolute/path/to/pacote.zip
```

Para Drive, só afirmar upload após evidência real: link, IDs, contagem e destino.

## Compliance criativo

- Tratar todo material como benchmarking/referência.
- Não copiar layout, marca, personagem, claims ou texto literalmente para campanha MGS.
- Recriar variações próprias com nova copy, composição, paleta e claims validados.
- Manter disclaimer no README quando entregar ZIP.

Texto padrão:

```text
Uso: referência/inspiração criativa. Não usar como cópia direta em campanha.
```

## REPORT-INFRA

Enviar `REPORT-INFRA` ao Zeus se:

- instalar dependência de sistema/browser/sanitizer;
- alterar script de sanitizer, collector, Drive ou perfil;
- criar cron/monitor/background job persistente;
- mudar config operacional compartilhada.

Não precisa REPORT-INFRA para downloads temporários e ZIPs sem alteração de infra.

## Common Pitfalls

1. **Dizer que baixou sem verificar arquivo.** Sempre validar HTTP, MIME/container e tamanho.
2. **Entregar raw.** O ZIP final deve conter apenas arquivos limpos/verificados.
3. **Confundir referência com criativo final.** Não colocar em `01_READY` nem entregar para Ares como asset aprovado.
4. **Baixar ícone/avatar.** Filtrar dimensões e proximidade de card com Library ID.
5. **Perder rastreabilidade.** Preservar Library ID, source URL e hash no inventário.
6. **Expor URLs sensíveis/cookies.** Nunca colar cookies, tokens, querystrings sensíveis ou headers de sessão.
7. **Forçar API quando browser resolve.** Para intake visual rápido, Playwright geralmente é primeiro caminho.
8. **Subir no Drive sem destino confirmado.** Drive muda organização permanente; confirmar estrutura quando a operação não estiver clara.

## Verification Checklist

- [ ] URLs/keywords recebidos e lote identificado.
- [ ] Library renderizada via browser ou bloqueio reportado.
- [ ] N criativos reais baixados.
- [ ] Arquivos deduplicados.
- [ ] `file`/MIME/dimensão/container validados.
- [ ] Sanitizer executado.
- [ ] `verify` retornou `clean=true` e `harmful_tags_after=0`.
- [ ] Naming aplicado.
- [ ] `inventory.json` criado.
- [ ] README com uso “referência/inspiração” criado.
- [ ] ZIP ou Drive validado antes de responder.
- [ ] Se houve infra/script/config, REPORT-INFRA enviado.
