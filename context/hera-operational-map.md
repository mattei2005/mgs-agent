# Hera — Mapa Operacional HOT

> **ARQUIVADO EM 2026-07-12:** Hera foi desativada e consolidada no Ares. Este arquivo é histórico/read-only e não deve rotear novas operações. Fonte ativa: `/root/mgs-agent/context/ares-operational-map.md`.

> Status: proposta operacional v0.1  
> Dono executivo: Rodolfo Mattei  
> Agente: Hera  
> Função: reduzir `search_files` amplo e orientar a primeira fonte certa para Operações Criativas.

## 1. Regra de uso

Antes de buscar termos genéricos como `drive`, `CC_US_EN`, `UPLOAD`, `creative`, `ares`, `metadata`, `canva` ou nomes soltos de arquivos, Hera deve abrir este mapa e escolher a fonte específica.

Use `search_files` amplo apenas quando:

- o pedido trouxer termo novo que não esteja neste mapa;
- a fonte indicada não existir ou estiver incompleta;
- for auditoria de drift/inconsistência;
- Rodolfo pedir explicitamente para procurar em tudo.

## 2. Fontes principais da Hera

```text
Assunto                                Abrir primeiro
-------------------------------------- ------------------------------------------------------------
Arquitetura/missão/limites Hera         /root/mgs-agent/context/hera-creative-agent.md
Rotas e handoffs entre agentes          /root/mgs-agent/context/routes.md
Mapa de agentes                         /root/mgs-agent/context/agent-map.md
Creative Ops no MGS OS                  /root/mgs-agent/context/areas.md
SOUL vivo da Hera                       /root/.hermes/profiles/hera/SOUL.md
SOUL versionado da Hera                 /root/mgs-agent/profiles/hera-soul.md
Skill de brief/handoff                  /root/mgs-agent/profiles/hera-skills/creative/creative-brief-handoff/SKILL.md
Template de brief                       /root/mgs-agent/profiles/hera-skills/creative/creative-brief-handoff/templates/creative-brief.md
Template de handoff Ares                /root/mgs-agent/profiles/hera-skills/creative/creative-brief-handoff/templates/ares-handoff.md
Sanitizador de metadata                 /root/mgs-agent/docs/CREATIVE_METADATA_SANITIZER.md
Wrapper sanitizador                     /root/mgs-agent/scripts/clean-creative-metadata.sh
Implementação sanitizador               /root/mgs-agent/scripts/clean-creative-metadata.py
Logs Hera                               /root/.hermes/profiles/hera/logs/
Audit MGS                               /root/mgs-agent/logs/events-audit.jsonl
```

## 3. Pergunta/pedido → fonte certa

```text
Pedido do usuário                                   Primeira fonte
-------------------------------------------------- ------------------------------------------------------------
"faz um brief" / "me dá ideias"                   creative-brief-handoff/SKILL.md
"preciso de copy/hook/CTA"                         creative-brief-handoff/SKILL.md
"roteiro de vídeo"                                 creative-brief-handoff/SKILL.md
"organiza esse criativo"                           hera-creative-agent.md + creative-brief-handoff/SKILL.md
"pasta do Drive" / "MGS-CRIATIVOS"                 hera-creative-agent.md seção Drive/Canva
"UPLOAD CANVAS"                                    hera-creative-agent.md + creative-brief-handoff/SKILL.md
"handoff para Ares"                                routes.md + templates/ares-handoff.md
"Ares precisa usar isso"                           templates/ares-handoff.md + ares-operational-map.md
"campanha/budget/pixel"                            routes.md; Hera não executa, encaminha para Ares/Zeus
"artigo/REC/P1/WordPress editorial"                routes.md; pedir contexto da Atena quando necessário
"limpar metadata"                                  docs/CREATIVE_METADATA_SANITIZER.md + scripts/clean-creative-metadata.sh
"analisa imagem/vídeo"                             creative-brief-handoff/SKILL.md + visão/ffprobe conforme necessidade
"adiciona Kelly/gestor na thread"                  SOUL seção Administração de membros + discord-add-thread-member.sh
"lê esta thread"                                   import-discord-thread.py --profile hera
"erro da Hera"                                     /root/.hermes/profiles/hera/logs/ + journalctl filtrado se infra
```

## 4. Drive/Canva e criativos

Fonte operacional: `context/hera-creative-agent.md`.

```text
Item                                Regra
----------------------------------- ------------------------------------------------------------
Pasta raiz                          MGS-CRIATIVOS
Folder ID raiz                      14ica5TVauTrzAxcl4T-ViJorF89vRKIl
UPLOAD CANVAS / UPLOAD MANUAL       Entrada pendente; após tratar/mover e validar READY, arquivar bruto em {OP}/{IMG|VID}/99_LEGACY; não apagar
CC_US_ES                            exemplo/piloto; não tratar como única vertical
Novos uploads via Hera              exigir País + Vertical + Língua + anexo antes de handoff técnico
Nome geral                          {VERTICAL}_{COUNTRY}_{LANG}_{FORMAT}_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}
Asset final                         usar versão com metadata limpa quando virar entregável
```

Quando o pedido for apenas criação de ideia/copy/brief, não precisa varrer Drive. Quando o pedido envolver arquivo/anexo real, primeiro identificar o arquivo entregue na thread; só depois consultar Drive/scripts.

## 5. Handoff Hera → Ares

Usar quando o criativo vai para campanha via Ares ou quando Rodolfo pedir handoff explícito.

Primeira fonte: `profiles/hera-skills/creative/creative-brief-handoff/templates/ares-handoff.md`.

Campos mínimos:

```text
Asset/link
Formato
Site/projeto
Objetivo da campanha
Ângulo criativo
Copy principal
CTA
Status de aprovação
Created_by
Used_by
Campaign_owner
Observações/risco
```

Regra anti-loop: mencionar Ares só em handoff real com ação, usando o bot ID correto. Não mencionar Ares para agradecimento/status sem ação.

## 6. Sanitização de metadata

Primeira fonte: `docs/CREATIVE_METADATA_SANITIZER.md`.

Comandos canônicos:

```text
/root/mgs-agent/scripts/clean-creative-metadata.sh verify /path/to/asset
/root/mgs-agent/scripts/clean-creative-metadata.sh clean /path/to/asset --agent hera
```

Reporte no Discord somente status resumido, sem despejar metadata bruta.

## 7. Limites rápidos

```text
Hera pode                               Hera não pode
--------------------------------------  ---------------------------------------------------------
Criar brief/copy/roteiro/variações       Subir/alterar campanhas
Organizar assets/nomes/status            Mexer em budget, billing, pixel, BM ou tracking
Preparar handoff para Ares/humanos       Configurar ChatPion, quiz, SMS ou WordPress
Analisar criativos                       Liberar usuários/permissões
Limpar metadata de entregáveis           Expor credenciais/tokens
```

## 8. Quando escalar

```text
Situação                              Escalar para
------------------------------------- --------------------------
Pedido de campanha/budget/pixel        Ares/Zeus
Permissão/acesso/usuário                Zeus
Mudança de padrão Drive/Canva           Rodolfo/Kelly/Geizian
Risco jurídico/compliance               Rodolfo/Zeus
Infra, gateway, systemd, token          Zeus
Conteúdo editorial/REC/P1               Atena como contexto, via rota aprovada
```

## 9. Validação antes de responder

- Se disser que criou/alterou arquivo: validar path real.
- Se disser que limpou metadata: validar `verify clean=true`.
- Se disser que leu thread: informar que foi importação read-only e contagem/período.
- Se disser que notificou Ares: confirmar envio/target real.
- Se não houver dado real: declarar lacuna em vez de inventar.
