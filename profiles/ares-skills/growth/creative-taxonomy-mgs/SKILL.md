---
name: creative-taxonomy-mgs
description: "Taxonomia operacional de criativos MGS para aquisição paga: nomenclatura de arquivos, campos obrigatórios, P_ORIENT, inventário, status, validação e regras de classificação antes de usar assets em campanhas."
version: 1.0.0
author: Ares
license: internal
metadata:
  hermes:
    tags: [mgs, ads, creatives, taxonomy, naming, drive, meta-ads]
    related_skills: [paid-acquisition-operations]
---

# Creative Taxonomy MGS

## Objetivo

Padronizar a taxonomia de criativos usados em aquisição paga da MGS para que Ares consiga organizar, auditar, renomear, inventariar e comparar performance de assets sem depender de nomes soltos, gestores ou sites.

Esta skill consolida a regra recebida no arquivo de taxonomia Empire e adapta para o padrão operacional MGS.

## Quando usar

Use esta skill quando Rodolfo pedir para:

- organizar criativos por vertical/operação;
- validar nomenclatura de arquivos;
- renomear assets antes de campanha;
- montar inventário de criativos;
- classificar ângulo, pessoa/orientação, idioma, país ou formato;
- preparar criativos para Meta Ads / Google Ads;
- comparar performance por criativo, ângulo, formato, país ou idioma;
- criar ou revisar estrutura de Drive de criativos.

Não use esta skill para conteúdo editorial/REC/SEO. Isso fica fora do escopo do Ares.

## Modelo oficial do nome de arquivo

Modelo base:

```text
{VERTICAL}_{COUNTRY}_{LANG}_{FORMAT}_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}
```

Exemplos:

```text
CC_CA_FR_IMG_APPROBATION_NV_01.jpg
CC_CA_FR_IMG_WALLET_NH_01.png
CC_CA_FR_VID_SANS_VERIFICATION_PV_01.mp4
CC_US_ES_IMG_APROBACION_NV_01.jpg
CC_US_ES_VID_LIMITE_ALTO_PH_01.mp4
```

## Campos do nome

```text
Campo      | Regra
-----------|----------------------------------------------------------
VERTICAL   | Código da vertical: CC, CAR, EMP, JOB, APP, GAME etc.
COUNTRY    | País alvo: US, CA, MX, BR etc.
LANG       | Idioma do criativo: EN, ES, FR, DE, PT etc.
FORMAT     | IMG ou VID
ANGLE      | Ângulo controlado por operação/idioma
P_ORIENT   | Código compacto de pessoa + orientação
VARIANT    | Sequência 2 dígitos: 01, 02, 03...
ext        | Extensão real do arquivo: jpg, png, mp4 etc.
```

Regras importantes:

- O nome deve ser uppercase, limpo, sem acento e com underscore.
- Não colocar status no nome.
- Não colocar site no nome.
- Não colocar gestor/origem no nome.
- Não colocar IDs longos no nome.
- `drive_id`, `page_id`, `meta_creative_id`, `origin_campaign_id` e origem ficam no inventário/metadados.

## Verticais

Códigos iniciais aceitos:

```text
Código | Vertical
-------|-------------------------
CC     | Credit Card / cartão de crédito
CAR    | Car / auto
EMP    | Employment / emprego
JOB    | Jobs / vagas
APP    | Apps
GAME   | Games
```

Se a vertical não for evidente, não inventar. Usar `UNKNOWN` no inventário e marcar para revisão antes de renomear para uso em campanha.

## FORMAT

```text
Código | Regra
-------|------------------------------------------------
IMG    | Imagem estática: jpg, jpeg, png, webp etc.
VID    | Vídeo/animação exportada como mp4/mov etc.
```

Nunca inferir `IMG` vs `VID` só pelo nome vindo do Canva. Validar pelo arquivo real, MIME type, extensão e/ou metadado técnico.

## ANGLE

`ANGLE` deve vir de dicionário controlado por operação/idioma.

Regras:

- Não inventar ângulo confiante sem evidência textual/visual.
- Se houver dúvida, usar `UNKNOWN` no plano de renomeação e preencher `notes`.
- Padronizar por idioma quando fizer sentido, mas manter comparabilidade operacional.

Exemplo inicial para CC em espanhol:

```text
ANGLE              | Significado operacional
-------------------|--------------------------------------------------
APROBACION          | Aprovação / pré-aprovação
SIN_VERIFICACION    | Sem verificação / baixa fricção
LIMITE_ALTO         | Limite alto
SIN_CREDITO         | Público sem crédito / histórico limitado
MAL_CREDITO         | Público com crédito ruim / negativado
CASHBACK            | Cashback / recompensas
RECOMPENSAS         | Benefícios, pontos, milhas
COMPARACION         | Escolha/comparativo entre cartões
WALLET              | Uso cotidiano, carteira, pagamento do dia a dia
URGENCIA            | Urgência, aprovação rápida, necessidade imediata
UNKNOWN             | Ângulo incerto; exige note
```

Exemplo inicial para CC em francês:

```text
ANGLE                | Significado operacional
---------------------|--------------------------------------------------
APPROBATION           | Aprovação / pré-aprovação
SANS_VERIFICATION     | Sem verificação / baixa fricção
LIMITE_HAUT           | Limite alto
CHOIX                 | Escolha/comparativo
WALLET                | Carteira / uso cotidiano
UNKNOWN               | Ângulo incerto; exige note
```

## P_ORIENT

`P_ORIENT` combina presença de pessoa + orientação visual.

Regra oficial MGS definida por Rodolfo: usar **somente** `PV`, `PH`, `NV`, `NH`. Códigos de square ou orientação desconhecida ficam desconsiderados e não devem entrar em nome final.

```text
Código | Pessoa     | Orientação
-------|------------|------------
PV     | PERSON     | VERTICAL
PH     | PERSON     | HORIZONTAL
NV     | NO_PERSON  | VERTICAL
NH     | NO_PERSON  | HORIZONTAL
```

Códigos removidos/desconsiderados:

```text
PS, NS, PU, NU, UU
```

Para operações Meta comuns, tratar o placement como vertical ou horizontal para fins de nome:

```text
Código | Pessoa     | Orientação | Uso típico
-------|------------|------------|-------------------------
PV     | PERSON     | VERTICAL   | Story/Reels vertical
NV     | NO_PERSON  | VERTICAL   | Story/Reels vertical
PH     | PERSON     | HORIZONTAL | Feed/landscape/não vertical
NH     | NO_PERSON  | HORIZONTAL | Feed/landscape/não vertical
```

Se pessoa ou orientação não puderem ser determinados com segurança, marcar revisão no inventário em vez de criar nome final incorreto. Não usar código `UNKNOWN` no nome final.

## Orientation, placement e dimensões

Dimensão não entra no nome por padrão. Dimensão fica no inventário.

Mapeamento comum para Meta:

```text
Placement | Dimensão típica | Aspect ratio | Orientation
----------|-----------------|--------------|------------
FEED      | 1080x1080       | 1:1          | HORIZONTAL
STORY     | 1080x1920       | 9:16         | VERTICAL
LANDSCAPE | 1080x608        | ~16:9        | HORIZONTAL
UNKNOWN   | desconhecida     | desconhecido | REVIEW
```

## Status e ciclo de vida

Status não entra no nome. Status fica em pasta ou inventário.

Pastas/status recomendados:

```text
Status / Pasta       | Uso
---------------------|--------------------------------------------------
01_READY             | Pronto para teste/campanha
02_TESTING           | Em teste
03_TESTED            | Já testado
04_WINNERS           | Vencedores / bom desempenho
05_REJECTED          | Reprovados / baixo desempenho
99_LEGACY            | Legado / arquivo histórico
00_REVIEW            | Revisão manual antes de uso
01_READY_CANDIDATE   | Candidato pronto após organização automática
```

Para organização bruta de backlog, pode existir `UPLOAD_CANVAS` como RAW. Essa pasta deve ser preservada intacta salvo pedido explícito do Rodolfo para mover/deletar duplicatas.

## Estrutura Drive recomendada

Estrutura por operação, não por site:

```text
MGS-CRIATIVOS/
└── <OPERATION>/
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

Para pipeline de backlog com placement/idioma como pastas intermediárias, usar quando aprovado:

```text
MGS-CRIATIVOS/<OPERATION>/<IMG|VID>/<FEED|STORY|LANDSCAPE|UNKNOWN>/<LANG>/<STATUS>/
```

## Inventário mínimo

Todo pipeline de classificação/renomeação deve manter inventário com pelo menos:

```text
filename
proposed_filename
vertical
country
language
format
angle
person
orientation
p_orient
variant
status
performance_label
source
source_manager
page_id
asset_drive_id
meta_creative_id
origin_campaign_id
width
height
aspect_ratio
placement_fit
checksum_md5
clean_metadata_status
created_at
notes
```

Valores usuais:

```text
person: PERSON, NO_PERSON, UNKNOWN
orientation: VERTICAL, HORIZONTAL, REVIEW
status: READY, TESTING, TESTED, WINNER, REJECTED, LEGACY, REVIEW
performance_label: GOOD, BAD, INCONCLUSIVE, UNKNOWN
```

## Procedimento seguro de classificação

1. Inventariar arquivos em modo read-only.
2. Validar formato real (`IMG`/`VID`) por arquivo, não por nome.
3. Extrair dimensão e calcular orientation/placement.
4. Para piloto de nomenclatura, selecionar amostra balanceada, gerar contact sheet e propor CSV antes do backlog completo; ver `references/upload-canvas-pilot-naming-review.md`.
5. Detectar idioma/país por texto visível, nome, pasta e/ou OCR quando disponível; evidência visual pode corrigir o guess automático.
6. Classificar vertical por evidência visual/textual; se incerto, `UNKNOWN`.
7. Classificar pessoa/orientação usando apenas `PV`, `PH`, `NV`, `NH`; FEED 1:1 entra como `HORIZONTAL` para fins de nome.
8. Sugerir `ANGLE` somente com evidência suficiente; se incerto, `UNKNOWN` + baixa confiança.
9. Gerar plano de renomeação/cópia em CSV/JSON com `confidence` e `notes`.
10. Mostrar proposta ao Rodolfo antes de qualquer alteração em Drive/campanha.
11. Após aprovação, executar cópia/renomeação com logs e validação.

## Sanitização antes de campanha

Antes de usar criativo em campanha/teste, validar metadados:

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh verify /path/to/creative.png
```

Se `clean: false`, limpar uma cópia:

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh clean /path/to/creative.png --agent ares
```

Usar o arquivo `.metadata-clean` como asset final. Não sanitizar RAW original in-place.

## Regras de segurança

- Não apagar, mover ou renomear RAW sem confirmação explícita.
- Não subir criativo em campanha sem metadata gate aprovado.
- Não inventar performance ou histórico de teste.
- Não expor tokens, cookies, IDs sensíveis sem necessidade, client secrets ou credenciais.
- Alterações em campanha, orçamento, tracking, pixel ou billing exigem confirmação explícita; billing exige double-confirm.

## Checklist de validação

Antes de finalizar uma taxonomia ou plano de renomeação:

```text
Check                                      | Exigência
-------------------------------------------|-----------------------------------------------
Modelo de nome completo                    | VERTICAL_COUNTRY_LANG_FORMAT_ANGLE_P_ORIENT_VARIANT
FORMAT validado por arquivo real           | Sim
ANGLE vem de dicionário controlado         | Sim ou UNKNOWN
P_ORIENT coerente com pessoa/orientação    | Sim
Status fora do nome                        | Sim
IDs fora do nome                           | Sim
Origem/gestor no inventário                | Sim
RAW preservado                             | Sim
Metadados verificados antes de campanha    | Sim
Plano aprovado antes de write              | Sim
```

## Pitfalls comuns

1. Separar por site no Drive: ruim porque o mesmo criativo pode rodar em múltiplos sites.
2. Colocar status no nome: gera renomeações constantes conforme ciclo de vida muda.
3. Inferir vídeo/imagem pelo nome do Canva: pode estar errado; validar arquivo real.
4. Forçar ângulo sem evidência: prejudica análise de performance por criativo.
5. Misturar RAW com assets limpos: manter original e versão final auditáveis.
6. Deixar pessoa/orientação desconhecida virar nome final: melhor revisar antes.

## Referências internas

- `paid-acquisition-operations`
- `references/source-taxonomy-empire.md` — resumo da taxonomia original enviada por Rodolfo e decisões incorporadas
- `references/upload-canvas-pilot-naming-review.md` — fluxo validado para testar nomenclatura em 3 IMG + 3 VID antes de escalar para o backlog
- `/root/.hermes/profiles/ares/skills/growth/paid-acquisition-operations/references/cc-us-es-setup.md`
- `/root/.hermes/profiles/ares/ops/cc_us_es_operating_spec.md`
- `/root/mgs-agent/docs/CREATIVE_METADATA_SANITIZER.md`
