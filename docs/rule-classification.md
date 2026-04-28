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

| Regra | Categoria correta | Estava onde | Foi ajustado? |
|---|---|---|---|
| Active voice 90%+ | Conteúdo | Template ✅ | Já correto |
| Sentence length 75% <20 | Conteúdo | Template ✅ | Já correto |
| Transition words ≥1 a cada 3-4 | Conteúdo | Template ✅ | Já correto |
| Word count 450-500 | Conteúdo | Template ✅ | Já correto |
| `lang_en` (tag por idioma) | Conteúdo | Template + SKILL (1×) | Manter em template, remover de SKILL |
| `atena_agent` (sempre quando publica) | Identidade | Em lugar nenhum | Adicionar ao SOUL.md + lembrete no template |
| `default_button_color` | Config + Pipeline | SOUL (2×) + SKILL (4×) + Template | Remover do SOUL, manter SKILL+template+sites.json |
| Delete imagem antes de delete post | Pipeline | SOUL ✅ | Manter (tem componente de identidade — "agente cuidadoso") |
| Cor de botão = default site | Identidade visual | SOUL ✅ | Manter no SOUL (overrides exigem L2 = é regra de identidade) |
| Yoast cinza pós-REST é OK | Pipeline | SOUL ✅ | Manter no SOUL (regra de NÃO entrar em pânico) |

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

