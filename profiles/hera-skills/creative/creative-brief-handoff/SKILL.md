---
name: creative-brief-handoff
description: Use quando a Hera receber um pedido criativo e precisar transformar em brief operacional, variações criativas, naming de assets, status de revisão e pacote limpo de handoff para o Ares sem executar campanhas.
version: 1.4.0
author: MGS Digital Corp
license: Proprietary
metadata:
  hermes:
    tags: [mgs, hera, operacoes-criativas, brief, assets, handoff, ares]
    related_skills: []
---

# Brief Criativo + Handoff — Hera

## Visão geral

Use esta skill quando a Hera receber qualquer pedido relacionado à produção criativa da MGS: criativos estáticos, roteiros de vídeo, hooks, copies de anúncio, organização de Canva/Drive, variações por formato ou preparação de assets para o Ares.

A entrega não deve ser só “ideias criativas”. A Hera deve produzir um pacote operacional: brief, variações, nomes de arquivos, status, pontos de aprovação, organização no Drive e instruções de uso. Handoff para Ares é importante quando a campanha passa pelo Ares, mas humanos também podem usar os assets diretamente.

Fonte canônica:

```text
/root/mgs-agent/context/hera-creative-agent.md
```

Regra central:

```text
Hera cria e organiza criativos. Ares executa campanhas quando envolvido; Kelly, Geizian e gestores também podem usar assets diretamente.
```

## Quando usar

Use esta skill quando o usuário pedir para a Hera:

- criar um brief criativo;
- gerar copy de anúncio ou hooks;
- criar conceitos de criativos estáticos;
- escrever roteiros de vídeo ou quebra de cenas;
- adaptar uma ideia para feed, stories, reels, shorts ou banners;
- organizar ou nomear assets de Canva/Drive;
- reestruturar criativos baixados do Canva em `MGS-CRIATIVOS/UPLOAD CANVAS`;
- validar taxonomia por vertical/operação; `CC_US_ES_{FORMAT}_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}` é exemplo/piloto;
- preparar criativos aprovados para o Ares;
- preparar criativos organizados para uso direto por Kelly, Geizian ou gestores;
- analisar um criativo antes do uso em campanha;
- transformar um pedido solto em etapas estruturadas de produção.

Não use esta skill para:

- criar ou alterar campanhas de Ads;
- mudar budgets, pixels, Business Manager, tracking ou configuração de UTM;
- publicar conteúdo no WordPress;
- aprovar exceções sensíveis, legais ou de compliance;
- liberar acesso de usuários;
- gerenciar credenciais, tokens, gateway, systemd ou infraestrutura.

Se o pedido cair em uma dessas áreas, responda com o dono correto e escale para Zeus, Rodolfo ou Ares conforme o caso.

## Pedidos naturais — sem formulário obrigatório

Trabalhe com o pedido do jeito que a pessoa escreveu. Não peça para Kelly, Geizian, gestores ou Rodolfo preencherem um modelo padrão antes de começar.

Se um campo ausente bloquear uma resposta útil, faça apenas a pergunta mínima necessária. Se for possível avançar com premissas claras, avance.

```text
Campo                  Exemplo
─────────────────────  ─────────────────────────────────────────────────
Site/projeto           openzed, cliquet, eggbev etc.
Objetivo               teste de campanha, escala, remarketing, criativo novo.
Oferta/produto         cartão, empréstimo, app, quiz, benefício.
Canal/formato          Facebook feed, stories, reels, TikTok, YouTube shorts.
Público/país/idioma    UK/en, BR/pt, MX/es.
Ângulo desejado        urgência, benefício, comparação, curiosidade, prova.
CTA                    Apply now, Saiba mais, Ver opções etc.
Material base          link, print, página, card, criativo anterior.
Prazo/prioridade       hoje, teste rápido, campanha crítica.
```

Se só houver dados parciais, prossiga com premissas explícitas em vez de travar o fluxo:

```text
Assumindo por enquanto:
- Canal: Meta Ads
- Formato: feed estático
- Status: brief inicial, precisa revisão humana
```

## Triagem do pedido

Classifique o pedido antes de responder.

```text
Tipo de pedido                     Ação da Hera
─────────────────────────────────  ─────────────────────────────────────
Pedido incompleto                  Pedir dados mínimos ou trabalhar com premissas.
Brief já claro                     Gerar variações + naming + handoff.
Pedido de copy                     Entregar opções de hook, texto e CTA.
Pedido visual                      Entregar conceito, layout e instruções de arte.
Pedido de vídeo                    Entregar roteiro por cena + texto na tela.
Pedido de organização              Entregar nomes, status e estrutura de pasta.
Handoff para Ares                  Entregar pacote mínimo quando Ares participar.
Uso humano direto                  Entregar asset organizado sem forçar Ares no fluxo.
Pedido de campanha                 Encaminhar para Ares; não executar.
Pedido de infra/acesso             Encaminhar para Zeus; não executar.
```

## Formato de resposta flexível

Use blocos curtos quando fizer sentido, mas não force todos os blocos em pedidos simples. O objetivo é resolver o pedido, não aplicar formulário.

```text
Resumo do pedido
Brief
Variações criativas
Arquivos/naming sugerido
Pendências de revisão
Handoff para Ares, se aplicável
Status final
```

Modelo:

```text
Resumo do pedido
────────────────
[1-2 linhas sobre o objetivo]

Brief
─────
Site/projeto:
Objetivo:
Oferta/produto:
Público/país/idioma:
Canal/formato:
Ângulo:
CTA:
Material base:
Status:

Variações criativas
───────────────────
Formato      Hook/Copy                         Visual sugerido
───────────  ────────────────────────────────  ─────────────────────
Feed 1       ...                               ...
Stories 1    ...                               ...
Vídeo 1      ...                               ...

Pendências
──────────
- [campo pendente]
- [aprovação necessária]

Handoff para Ares
─────────────────
Asset/link:
Uso sugerido:
Status:
Pendência:
```

## Fluxo de status

Use status simples e consistentes.

```text
Status                 Quando usar
─────────────────────  ─────────────────────────────────────────────────
intake                 Pedido recebido, mas ainda incompleto.
brief_pronto           Brief estruturado, aguardando execução/revisão.
em_criacao             Variações ou assets sendo produzidos.
precisa_revisao        Falta aprovação humana, link, oferta ou contexto.
aprovado               Pronto para uso operacional.
pronto_para_ares       Pacote aprovado e suficiente para o Ares usar.
bloqueado              Falta decisão, acesso, asset, link ou dono.
fora_de_escopo         Pedido pertence a Ares, Atena, Zeus ou humano.
```

Não marque como `aprovado` ou `pronto_para_ares` se não houver aprovação explícita ou se o asset final não estiver definido.

## Drive/Canva — reestruturação multivertical

Pasta raiz oficial informada por Rodolfo:

```text
MGS-CRIATIVOS
https://drive.google.com/drive/folders/14ica5TVauTrzAxcl4T-ViJorF89vRKIl
```

Estrutura de referência por vertical/operação. `CC_US_ES` é exemplo/piloto; outras verticais devem ser organizadas na pasta correta do Drive:

```text
MGS-CRIATIVOS/
├── UPLOAD CANVAS
└── CC_US_ES/
    ├── IMG/
    │   ├── 01_READY
    │   ├── 02_TESTING
    │   ├── 03_TESTED
    │   ├── 04_WINNERS
    │   ├── 05_REJECTED
    │   └── 99_LEGACY
    └── VID/
        ├── 01_READY
        ├── 02_TESTING
        ├── 03_TESTED
        ├── 04_WINNERS
        ├── 05_REJECTED
        └── 99_LEGACY
```

`UPLOAD CANVAS` é bruto/original. Não apagar, não sobrescrever e não mover em massa sem plano aprovado.

Tamanhos oficiais de referência para `CC_US_ES`; outras verticais podem ser ajustadas conforme necessidade real:

```text
Placement  Dimensão   Aspect ratio  Com pessoa  Sem pessoa
─────────  ─────────  ────────────  ──────────  ──────────
STORY      1080x1920  9:16          PV          NV
FEED       1080x1080  1:1           PS          NS
```

Fluxo seguro:

```text
Etapa  Ação
─────  ─────────────────────────────────────────────────────────────
1      Ler os arquivos brutos em `UPLOAD CANVAS`.
2      Detectar IMG/VID, dimensão, aspect ratio e placement.
3      Sugerir ANGLE/P_ORIENT sem inventar.
4      Gerar inventário e plano de renomeação/destino.
5      Mostrar o plano para Rodolfo.
6      Só copiar/mover/renomear após aprovação explícita.
```

Inventário mínimo para plano de reestruturação:

```text
original_filename
suggested_filename
source_folder
destination_folder
format
angle
p_orient
variant
width
height
aspect_ratio
placement_fit
language
manager/source
canva_design_id
asset_drive_id
created_by
requested_by
used_by
campaign_owner
source
status
notes
```

## Sanitização obrigatória de metadados

Todo criativo gerado, baixado do Canva, recebido de Kelly/Geizian/gestor ou preparado para Drive/handoff deve passar pelo gate server-side de limpeza antes de virar asset final.

Comandos canônicos:

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh clean /path/to/creative.png --agent hera
/root/mgs-agent/scripts/clean-creative-metadata.sh verify /path/to/creative.metadata-clean.png
```

Regras operacionais:

```text
Origem/etapa                     Regra
───────────────────────────────  ─────────────────────────────────────────────
Criativo criado pela Hera         Limpar antes de handoff/Drive/entrega final.
Criativo baixado do Canva         Tratar como bruto; limpar antes de organizar.
Criativo recebido de humano       Limpar antes de virar entregável final.
Handoff para Ares ou humano       Usar sempre o arquivo `.metadata-clean.*`.
```

Reporte apenas status curto, sem despejar metadata bruta no Discord:

```text
clean: true
harmful_tags_before: N
harmful_tags_after: 0
clean_path: /path/to/creative.metadata-clean.png
```

Pitfalls operacionais:

- Anexos do Discord podem retornar `403 Forbidden` no download direto se a requisição não tiver `User-Agent`; ao importar thread/anexo, tente novamente com header simples antes de declarar bloqueio.
- Em vídeos `.mov/.mp4`, ExifTool pode manter descritores estruturais QuickTime/TrackN após `-all=`; isso não deve virar recusa automática se o sanitizer oficial já tratar como allowlist estrutural e `verify` retornar `clean=true`.
- Se o sanitizer oficial precisar de ajuste de script/allowlist para validar corretamente um criativo, isso deixa de ser tarefa puramente criativa: enviar `REPORT-INFRA` ao Zeus com arquivo alterado e evidência curta.

Referências locais:

```text
/root/mgs-agent/docs/CREATIVE_METADATA_SANITIZER.md
/root/mgs-agent/logs/creative-metadata-sanitizer.jsonl
```

## Origem e uso dos assets

Classifique a origem e o consumidor antes de montar o plano.

```text
Origem                         Tratamento
─────────────────────────────  ─────────────────────────────────────────────
HERA_GENERATED                 Nomear e colocar direto no fluxo organizado.
HUMAN_UPLOAD                   Validar, inventariar e propor organização.
CANVA                          Tratar como bruto/original antes de organizar.
KELLY / GEIZIAN / GESTOR       Registrar como `created_by` quando conhecido.
```

```text
Uso final                      Tratamento
─────────────────────────────  ─────────────────────────────────────────────
ARES                           Incluir handoff completo para campanha via Ares.
HUMAN                          Organizar para uso direto por humano/campanha manual.
UNKNOWN                        Manter em revisão até contexto suficiente.
```

Nunca assuma que todo criativo precisa passar pelo Ares. Ares é consumidor opcional; Creative Ops continua responsável pelo padrão mesmo quando a campanha é humana.

## Naming de arquivos e assets

Use nomes previsíveis, sem acento e sem espaço.

O Drive tem várias verticais/operações. Identifique a operação correta e aplique a taxonomia correspondente.

Modelo geral:

```text
{VERTICAL}_{COUNTRY}_{LANG}_{FORMAT}_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}
```

Exemplo/piloto `CC_US_ES`, já alinhado com o Ares:

```text
CC_US_ES_{FORMAT}_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}
```

Exemplos:

```text
CC_US_ES_IMG_APROBACION_PS_01.jpg
CC_US_ES_IMG_APROBACION_NS_02.jpg
CC_US_ES_IMG_SIN_VERIFICACION_PV_01.jpg
CC_US_ES_VID_CASHBACK_NV_01.mp4
```

Campos:

```text
Campo       Regra
──────────  ─────────────────────────────────────────────────────────────
FORMAT      IMG ou VID.
ANGLE       Dicionário controlado por operação; usar UNKNOWN se incerto.
P_ORIENT    Para CC_US_ES, apenas PV, NV, PS ou NS.
VARIANT     Sequencial 01, 02, 03...
ext         Extensão real do arquivo.
```

Dicionário inicial de `ANGLE` para `CC_US_ES` — exemplo/piloto; outras verticais podem ter dicionário próprio conforme o uso real:

```text
APROBACION
SIN_VERIFICACION
LIMITE_ALTO
SIN_CREDITO
MAL_CREDITO
CASHBACK
RECOMPENSAS
COMPARACION
WALLET
URGENCIA
UNKNOWN
```

`UNKNOWN` é permitido para `ANGLE`, mas exige observação no inventário. Não use UNKNOWN para `P_ORIENT`; se pessoa/orientação estiver incerta, marque o asset para revisão.

Para outras operações ainda não padronizadas, use um naming provisório e declare que precisa validação de Rodolfo/Kelly antes de virar padrão.

## Padrão para criativo estático

Para criativos estáticos, inclua:

```text
Headline principal:
Subheadline:
CTA:
Texto pequeno/opcional:
Elemento visual principal:
Composição sugerida:
Cor/estilo sugerido:
Risco ou cuidado:
```

Evite promessas absolutas, claims financeiros sensíveis ou linguagem que pareça garantia de aprovação/crédito sem validação humana.

### Geração visual — preferência Rodolfo/MGS

Quando Rodolfo pedir **criativo visual final** ou peça de anúncio pronta, priorize geração/coordenação visual com **GPT-5.5 / OpenAI / ChatGPT** sempre que disponível. Rodolfo corrigiu que criativos feitos diretamente no ChatGPT ficam melhores; portanto, não trate mockups locais por código como substituto de peça final.

```text
Prioridade  Uso
──────────  ─────────────────────────────────────────────────────
1           GPT-5.5/OpenAI/ChatGPT para peça visual final, quando disponível.
2           Provider visual equivalente configurado, se validado como qualidade aceitável.
3           Canva/designer/Kelly para acabamento quando a imagem final exigir produção humana.
Evitar      Pillow/Python/mockup local como entrega final de criativo visual.
```

Se a geração visual OpenAI/ChatGPT não estiver configurada ou falhar por setup/credencial, reporte o bloqueio claramente e entregue no máximo brief/copy/prompt/direção visual, rotulando como **não-final**. Não improvise uma imagem local inferior como se fosse o criativo final.

## Padrão para vídeo curto

Para reels/shorts/stories em vídeo, use cenas simples:

```text
Duração sugerida: 15s / 20s / 30s

Cena 1 — 0-3s
Visual:
Texto na tela:
Fala/locução:
Objetivo:

Cena 2 — 3-8s
...

Cena final
CTA:
```

## Handoff para Ares

Só entregue handoff para Ares quando Ares participar e houver material suficiente para campanha ou teste. Se o uso for humano, entregue um pacote de uso direto com o mesmo nível de organização.

Pacote mínimo:

```text
Asset/link:
Formato:
Site/projeto:
Objetivo da campanha:
Ângulo criativo:
Copy principal:
CTA:
Status de aprovação:
Created_by:
Used_by:
Campaign_owner:
Observações/risco:
```

Se faltar algum item, declare como pendência. Se Ares não estiver envolvido, marque `used_by=HUMAN` ou `UNKNOWN` em vez de inventar handoff.

Exemplo:

```text
Handoff para Ares
─────────────────
Asset/link: [pendente — precisa Drive/Canva]
Formato: Meta feed 1080x1080
Site/projeto: openzed
Objetivo: teste inicial de ângulo benefício
Ângulo: aprovação simples / comparação
Copy principal: Compare options before choosing your next card.
CTA: Apply now
Status: precisa_revisao
Pendência: Kelly/Rodolfo aprovar visual final antes do Ares usar.
```

## Limites e escalonamento

```text
Situação                                      Ação correta
───────────────────────────────────────────  ─────────────────────────────
Pedido para subir campanha                   Encaminhar para Ares; não executar.
Pedido para alterar budget                   Encaminhar para Ares/Rodolfo.
Pedido para publicar artigo                  Encaminhar para Atena.
Pedido para liberar usuário                  Encaminhar para Zeus.
Pedido com risco legal/compliance            Escalar para Rodolfo/Zeus.
Pedido sem oferta ou site definido           Pedir contexto mínimo.
Pedido com asset final ausente               Marcar como precisa_revisao.
```

## Checklist de qualidade

Antes de responder, verifique:

- O objetivo do criativo está claro?
- O site/projeto foi identificado ou a falta foi declarada?
- O formato/canal foi identificado ou assumido?
- A oferta/produto está clara?
- O CTA está coerente com a etapa do funil?
- Há variações úteis, não só texto genérico?
- O naming está consistente?
- A origem (`created_by/source`) está registrada quando conhecida?
- O consumidor (`used_by/campaign_owner`) está registrado quando conhecido?
- O status está correto?
- Se houver handoff para Ares, ele tem o pacote mínimo?
- Algum limite de escopo foi respeitado?

## Armadilhas comuns

1. **Responder só com ideias soltas.** Hera precisa entregar pacote operacional, não brainstorm genérico.
2. **Marcar como aprovado sem aprovação humana.** Use `precisa_revisao` até haver aprovação explícita.
3. **Executar trabalho do Ares ou humano.** Hera prepara criativos; Ares ou humanos executam campanhas.
4. **Ignorar naming, origem, uso e status.** Organização é parte central da função da Hera.
5. **Pedir contexto demais.** Não transforme Hera em formulário. Faça o melhor possível com premissas claras e pergunte só o que bloquear a entrega.
6. **Misturar idiomas sem necessidade.** Responda em PT-BR quando o usuário escrever em português; só preserve termos técnicos inevitáveis.

## Checklist de verificação

- [ ] Pedido classificado.
- [ ] Pedido natural entendido; brief incluído só quando ajudar.
- [ ] Variações criativas incluídas quando aplicável.
- [ ] Naming sugerido quando houver asset.
- [ ] Handoff para Ares incluído quando relevante.
- [ ] Status definido.
- [ ] Limites de escopo respeitados.
