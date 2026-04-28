# Rule Classification — Onde armazenar regras da Atena (e Zeus)

**Data:** 2026-04-27
**Por que existe:** Evitar bagunça de regras espalhadas em múltiplos lugares contraditórios. Cada regra tem UM lugar canônico definido pela sua categoria.

## 📋 As 4 categorias

| Categoria | Local canônico | Exemplo |
|---|---|---|
| **1. Identidade / Comportamento global** | `SOUL.md` | "Sempre mencionar Raquel ao publicar", "tag atena_agent em tudo" |
| **2. Pipeline / Orquestração** | `skills/<nome>/SKILL.md` | "Step 12 = yoast-score-post.sh", "delete imagem antes de delete post" |
| **3. Geração de conteúdo (formato/voz/estrutura)** | `skills/content-generate-rec/templates/<vertical>.md` | Active voice, transition words, word count, tags por idioma |
| **4. Configuração específica por site** | `data/sites.json` | URLs, pixel IDs, default_button_color, idioma do site |

## 🎯 Como decidir

**Pergunte-se: "Essa regra muda dependendo de QUÊ?"**

- Muda por **agente** (Atena vs Zeus) → SOUL.md
- Muda por **fluxo de trabalho** (publish vs delete vs update) → SKILL.md
- Muda por **idioma/vertical** (gb-cc-en vs mx-cc-es) → Template
- Muda por **site específico** (eggbev vs lyzmo) → sites.json

## 🚫 Onde NUNCA armazenar regras

- ❌ `memory.jsonl` — volátil, perdido em reset/upgrade
- ❌ Discord (chat) — não é fonte canônica
- ❌ Múltiplos lugares contraditórios — fonte única é regra de ouro

## 🔍 Auditoria de regras atuais (2026-04-27)

⚠️ **Nota importante:** Algumas regras pertencem a MÚLTIPLAS camadas (não é bagunça — é arquitetura). Exemplo: `default_button_color` está em 4 lugares com propósitos diferentes:
- **VALOR** (a cor hex específica) → `data/sites.json`
- **LÓGICA** (como buscar) → SKILL.md + `resolve-button-color.sh`
- **REGRA comportamental** (sempre seguir, override = L2) → SOUL.md
- **LEMBRETE** no prompt de geração → Template

Isso é **arquitetura por camadas**, e cada camada tem propósito distinto.

| Regra | Camadas onde está | Status |
|---|---|---|
| Active voice 90%+ | Template | ✅ Correto |
| Sentence length 75% <20 | Template | ✅ Correto |
| Transition words ≥1 a cada 3-4 | Template | ✅ Correto |
| Word count 450-500 | Template | ✅ Correto |
| `lang_{language}` (tag dinâmica por idioma) | SKILL (lógica) + Template (instância EN) | ✅ Correto — SKILL tem a lógica cross-template, template tem o lembrete |
| `atena_agent` (toda publicação Atena) | SOUL (regra) + Template (lembrete) | ✅ Adicionado ao SOUL em 2026-04-27 |
| `default_button_color` | sites.json (valor) + SKILL (lógica) + script (resolução) + SOUL (regra) + Template (lembrete) | ✅ Arquitetura em 4 camadas |
| Delete imagem antes de delete post | SOUL | ✅ Correto |
| Yoast cinza pós-REST é OK | SOUL | ✅ Correto |

## 📝 Política para regras NOVAS

Quando Rodolfo/Raquel pedir "registra essa regra":

1. **Categorizar** primeiro (qual das 4 categorias)
2. **Salvar** APENAS no local canônico da categoria
3. **Commitar** no git imediatamente
4. **Confirmar** ao usuário onde foi salva: "Salvei em `<path>` como regra de <categoria>"
5. **Nunca** salvar em memory.jsonl como única fonte

## 🔗 Skills relacionadas

- Atena tem skill `learning-persistence` que aplica esta política automaticamente
- Zeus tem skill `mgs-infra-inventory` que rastreia onde cada artefato vive

