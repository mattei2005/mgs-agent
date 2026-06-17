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
CC_CA_FR_IMG_APPROBATION_NV_001.jpg
CC_CA_FR_IMG_WALLET_NH_001.png
CC_CA_FR_VID_SANS_VERIFICATION_PV_001.mp4
CC_US_ES_IMG_APROBACION_NV_001.jpg
CC_US_ES_VID_LIMITE_ALTO_PH_001.mp4
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
VARIANT    | Sequência 3 dígitos: 001, 002, 003... até 999
ext        | Extensão real do arquivo: jpg, png, mp4 etc.
```

Regra operacional para `VARIANT`:

- Sempre gerar e corrigir variantes com **3 dígitos** (`001`-`999`), nunca `01`-`99`.
- Motivo: com 2 dígitos, arquivos como `_100` podem ficar fora da ordem alfabética/natural esperada em Drive, CSVs e revisões manuais.
- Ao corrigir assets já feitos, renomear o arquivo real no Drive e depois normalizar CSVs/propostas locais para refletir o novo nome.
- Manter evidência auditável da mudança com `old_name`, `new_name`, `verified_name`, `drive_id`, `status` e hash do relatório; não apagar a trilha de auditoria.

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

## Entrada operacional via Hera

Fluxo aprovado por Rodolfo para entrada de criativos novos:

- Gestores/Kelly enviam o criativo como anexo no Discord da Hera.
- A mensagem deve informar obrigatoriamente `PAIS`, `VERTICAL` e `LINGUA`.
- Hera não deve inventar esses campos; eles são fonte oficial vinda do gestor/Kelly.
- Se faltar qualquer campo obrigatório, Hera deve pedir correção antes de enviar para processamento.
- O nome original do arquivo pode ser livre/Canva; a nomenclatura oficial é gerada depois pelo Ares.
- Hera atua como porta de entrada e organização inicial; Ares atua no tratamento técnico, sanitização, classificação e nomenclatura de aquisição.
- Quando Hera receber um upload válido com `PAIS`, `VERTICAL`, `LINGUA` e anexo, ela deve fazer um único handoff mencionando o Ares (`<@1508864261504630925>`) com os campos estruturados e link/contexto do anexo/processamento.
- Quando Rodolfo pedir explicitamente para Ares acionar/pedir algo à Hera, Ares deve usar o **user mention real da Hera** (`<@1513006098133680290>`). Escrever `@Hera` em texto simples não acorda o bot nem garante leitura pelo gateway.
- Para evitar loop entre agentes, Hera não deve mencionar Ares para confirmações, agradecimentos, status sem ação ou mensagens sem anexo/campos obrigatórios; Ares não deve responder a confirmações da Hera. Depois que uma correção Drive/naming estiver validada e encerrada, thumbs-up, “confirmado”, “sem ação pendente” ou mensagens equivalentes da Hera exigem silêncio operacional, não uma nova resposta curta.

Formato recomendado para envio no Discord da Hera:

```text
País: US
Vertical: CC
Língua: ES
[anexo]
```

Formato curto aceito:

```text
US | CC | ES
[anexo]
```

Pasta de entrada recomendada no Drive:

```text
MGS-CRIATIVOS/
└── CRIATIVOS_ENVIADOS/
    └── <VERTICAL>_<COUNTRY>_<LANG>/
        ├── KELLY/
        └── GESTORES/
```

Destino final canônico no Drive, no fluxo atual aprovado:

```text
MGS-CRIATIVOS/
└── <VERTICAL>_<COUNTRY>_<LANG>/
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

Regra importante: como `<VERTICAL>_<COUNTRY>_<LANG>` já contém idioma e a nomenclatura já contém `IMG|VID`, `ANGLE` e `P_ORIENT`, Hera/Ares **não devem criar subpastas intermediárias** como `STORY/EN/01_READY` no fluxo atual, salvo aprovação explícita. Placement/formato (`STORY`, `FEED`, `REELS`) deve ficar no inventário/handoff e ser inferido por dimensão, mas o arquivo final vai direto em `<OPERATION>/<IMG|VID>/01_READY` quando estiver pronto.

Depois da entrada, Ares deve preservar o original/inbox, criar cópia limpa, classificar por OCR/visão, aplicar o nome final e enviar a cópia tratada para as pastas operacionais já existentes. Criativos vindos de `UPLOAD_CANVAS` já tratados continuam como backlog/artefato existente e não devem ser confundidos com novos uploads via Hera.

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
4. Para vídeos, não classificar por thumbnail/frame inicial apenas: amostrar múltiplos frames, porque conteúdo/CTA pode aparecer só depois de alguns segundos.
5. Script canônico para vídeos: `/root/mgs-agent/scripts/ares-drive-video-frame-sampler.py` com frames padrão em `0.5s`, `2.0s`, `3.2s`, `4.5s` e `6.0s`; usar `--discard-videos` em execução grande para não guardar MP4 local desnecessário.
6. Chamar o artefato visual de vídeo de **timeline de frames** ou **imagem de revisão**; evitar o termo “sheet” com Rodolfo, porque ele pode entender como Google Sheet/planilha.
7. Para piloto de nomenclatura, selecionar uma amostra balanceada pequena para validar o método; uma vez validado, escalar para o lote completo restante, não ficar repetindo novas amostras pequenas. Usar lotes apenas como detalhe técnico de estabilidade/auditoria.
8. Não criar Google Sheet/planilha para esse fluxo salvo pedido explícito; usar CSV/JSON local como log/plano técnico e explicar se algum arquivo é apenas evidência local.
9. Detectar idioma/país por texto visível, nome, pasta e/ou OCR quando disponível; evidência visual pode corrigir o guess automático. Para vídeos, o classificador OCR-assisted canônico é `/root/mgs-agent/scripts/ares-classify-video-timelines-ocr.py`.
10. Para escala completa de vídeos, seguir `references/upload-canvas-video-classification-scale.md`.
11. Classificar vertical por evidência visual/textual; se incerto, `UNKNOWN`.
12. Classificar pessoa/orientação usando apenas `PV`, `PH`, `NV`, `NH`; FEED 1:1 entra como `HORIZONTAL` para fins de nome.
13. Sugerir `ANGLE` somente com evidência suficiente; se incerto, `UNKNOWN` + baixa confiança.
14. Gerar plano de renomeação/cópia em CSV/JSON com `confidence` e `notes`.
14. Gerar plano de renomeação/cópia em CSV/JSON com `confidence` e `notes`.
15. Antes de executar qualquer rename/copy, validar que `VARIANT` está em 3 dígitos (`001-999`) em todos os nomes finais e corrigir qualquer saída legada de script que ainda gere `01`, `02`, etc.
16. Quando houver itens em `00_REVIEW`, revisar ativamente com evidência visual/contact sheet/timeline e tomar decisão operacional: promover para `01_READY_CANDIDATE`, mover para `05_REJECTED`, ou manter em review somente com motivo concreto. Não deixar `00_REVIEW` como pendência genérica se os arquivos estão acessíveis no Drive.
15. Antes de executar qualquer rename/copy, validar que `VARIANT` está em 3 dígitos (`001-999`) em todos os nomes finais e corrigir qualquer saída legada de script que ainda gere `01`, `02`, etc.
16. Mostrar proposta ao Rodolfo antes de qualquer alteração em Drive/campanha.
17. Após aprovação, executar cópia/renomeação com logs e validação.
18. Em fluxos RAW → clean-copy, preservar `UPLOAD_CANVAS` como fonte original. Ao agir sobre itens revisados, usar o ID da cópia limpa (`dest_drive_id` nos reports de copy-clean), não o `source_drive_id` do RAW, salvo pedido explícito para mexer no RAW.
19. Se Rodolfo pedir para corrigir criativos já feitos, executar a correção no Drive, validar por novo scan que não restam nomes finais com 2 dígitos, e atualizar artefatos locais/propostas para o mesmo padrão.
19. Para colisões de nome já existentes em `01_READY_CANDIDATE`, manter um nome canônico por variante e renomear as cópias conflitantes para a próxima variante livre com 3 dígitos. Simular antes para garantir zero colisões pós-plano e registrar `old_name`, `new_name`, `drive_id`, `verified_name` e relatório hash.

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
7. Deixar script legado emitir variantes `01-99`: isso quebra ordenação alfabética quando passa de 99 ou mistura lotes. O padrão MGS é sempre `001-999`; valide CSVs, propostas e reports antes de Drive write.
8. Usar `VARIANT` com 2 dígitos: quebra ordenação quando surgem `_100+`; corrigir para 3 dígitos em nomes reais, propostas e inventários.
8. Fazer replace global em relatórios de auditoria sem preservar `old_name`: pode destruir evidência da mudança. Ao normalizar logs, preservar ou reconstruir o valor antigo em campo próprio.
9. Confundir RAW com cópia final: `UPLOAD_CANVAS` é fonte original, enquanto pastas por operação carregam derivados limpos/renomeados. MD5 diferente entre RAW e final é esperado após limpeza de metadata; isso não significa que o asset não veio do RAW.
10. Agir no ID errado em revisão final: reports de copy-clean costumam ter `source_drive_id`=RAW e `dest_drive_id`=cópia limpa. Promoção para `01_READY`, rejeição e rename final devem usar `dest_drive_id`; se o RAW for movido por engano, restaurar o RAW antes de encerrar.
10. Dizer que não consegue revisar assets do Drive quando existe acesso/pipeline Drive: se os arquivos estão em `MGS-CRIATIVOS`, inventarie, gere evidência visual e revise. Só reporte bloqueio real de permissão/credencial.
11. Fechar `00_REVIEW` movendo RAW em vez da cópia limpa: `UPLOAD_CANVAS` é origem preservada; decisões finais devem agir sobre a cópia limpa em review/final. Conferir `source_drive_id` vs `dest_drive_id` nos relatórios antes de PATCH no Drive.

## Referências internas

- `paid-acquisition-operations`
- `references/source-taxonomy-empire.md` — resumo da taxonomia original enviada por Rodolfo e decisões incorporadas
- `references/upload-canvas-pilot-naming-review.md` — fluxo validado para testar nomenclatura em 3 IMG + 3 VID antes de escalar para o backlog
- `references/upload-canvas-video-multiframe-review.md` — regra operacional para classificar vídeos por timeline de frames, evitar erro de thumbnail inicial e escalar para lote completo
- `references/upload-canvas-video-classification-scale.md` — fluxo completo para processar todos os vídeos: timelines multi-frame, OCR-assisted classifier, CSV de proposta e guardrails de revisão
- `/root/.hermes/profiles/ares/skills/growth/paid-acquisition-operations/references/cc-us-es-setup.md`
- `/root/.hermes/profiles/ares/ops/cc_us_es_operating_spec.md`
- `/root/mgs-agent/docs/CREATIVE_METADATA_SANITIZER.md`
