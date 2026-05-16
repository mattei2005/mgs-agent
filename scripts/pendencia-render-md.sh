#!/bin/bash
# pendencia-render-md.sh — gera docs/PENDENCIAS.md a partir do JSON
# Roda via cron diário 8 AM EST OU manual após mudanças

set -euo pipefail

DB="/root/mgs-agent/data/pendencias.db.json"
OUT="/root/mgs-agent/docs/PENDENCIAS.md"
HISTORICO="/root/mgs-agent/docs/PENDENCIAS-HISTORICO.md"

[[ ! -f "$DB" ]] && { echo "ERRO: $DB não existe"; exit 1; }

mkdir -p "$(dirname "$OUT")"

python3 <<'PYEOF'
import json
from datetime import datetime
from collections import defaultdict

DB = "/root/mgs-agent/data/pendencias.db.json"
OUT = "/root/mgs-agent/docs/PENDENCIAS.md"
HISTORICO = "/root/mgs-agent/docs/PENDENCIAS-HISTORICO.md"

with open(DB) as f:
    data = json.load(f)

now = datetime.now().isoformat()
abertas = data["pendencias"]
resolvidas = data["resolvidas"]

# Agrupar por prioridade
por_prio = defaultdict(list)
for p in abertas:
    por_prio[p.get("prioridade", "media")].append(p)

# === PENDENCIAS.md ===
md = []
md.append("# 📋 Pendências MGS Digital Corp")
md.append("")
md.append(f"> ⚠️ **NÃO EDITAR ESTE ARQUIVO MANUALMENTE.**  ")
md.append(f"> Gerado automaticamente a partir de `data/pendencias.db.json`.  ")
md.append(f"> Para adicionar/resolver: use scripts em `scripts/pendencia-*.sh`")
md.append("")
md.append(f"**Última atualização:** {data['metadata']['ultima_atualizacao']}  ")
md.append(f"**Total abertas:** {len(abertas)}  ")
md.append(f"**Total resolvidas:** {len(resolvidas)}")
md.append("")
md.append("---")
md.append("")

# Stats rápidas
md.append("## 📊 Resumo")
md.append("")
md.append("| Prioridade | Quantidade |")
md.append("|---|---|")
for prio in ["alta", "media", "baixa"]:
    icon = {"alta": "🔴", "media": "🟡", "baixa": "🟢"}[prio]
    md.append(f"| {icon} {prio} | {len(por_prio[prio])} |")
md.append("")

# Por categoria
cats = defaultdict(int)
for p in abertas:
    cats[p.get("categoria", "?")] += 1
md.append("**Por categoria:**")
md.append("")
for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
    md.append(f"- `{cat}`: {count}")
md.append("")
md.append("---")
md.append("")

# Pendências por prioridade
icons_prio = {"alta": "🔴 ALTA", "media": "🟡 MÉDIA", "baixa": "🟢 BAIXA"}

for prio in ["alta", "media", "baixa"]:
    items = por_prio[prio]
    if not items:
        continue
    md.append(f"## {icons_prio[prio]} ({len(items)} itens)")
    md.append("")
    md.append("| ID | Título | Categoria | Tempo | Bloqueio |")
    md.append("|---|---|---|---|---|")
    for p in items:
        bloq = p.get("bloqueio") or "—"
        if bloq and len(bloq) > 50:
            bloq = bloq[:47] + "..."
        tempo = p.get("tempo_estimado") or "?"
        titulo = p["titulo"].replace("|", "\\|")
        md.append(f"| `{p['id']}` | {titulo} | `{p.get('categoria', '?')}` | {tempo} | {bloq} |")
    md.append("")

md.append("---")
md.append("")
md.append("## 📚 Como usar")
md.append("")
md.append("```bash")
md.append("# Adicionar nova pendência")
md.append('./scripts/pendencia-add.sh "Título da tarefa" --categoria infra --prioridade alta --tempo "30min"')
md.append("")
md.append("# Marcar como resolvida")
md.append('./scripts/pendencia-done.sh PEND-001 --como "Como foi resolvido"')
md.append("")
md.append("# Listar com filtros")
md.append("./scripts/pendencia-list.sh --prioridade alta")
md.append("./scripts/pendencia-list.sh --categoria seguranca")
md.append("./scripts/pendencia-list.sh --stats")
md.append("./scripts/pendencia-list.sh PEND-001  # ver uma específica")
md.append("```")
md.append("")
md.append("## 🏷️ Categorias")
md.append("")
for cat, desc in data["categorias"].items():
    md.append(f"- **`{cat}`** — {desc}")
md.append("")

with open(OUT, "w") as f:
    f.write("\n".join(md))

# === HISTORICO.md ===
hist = []
hist.append("# 📚 Histórico de Pendências Resolvidas — MGS Digital Corp")
hist.append("")
hist.append(f"> Arquivo gerado automaticamente. Total: {len(resolvidas)} resolvidas.")
hist.append("")
hist.append("---")
hist.append("")

# Ordenar por data de resolução, mais recente primeiro
sorted_res = sorted(resolvidas, key=lambda x: x.get("resolvida_em", ""), reverse=True)

for r in sorted_res:
    hist.append(f"### ✅ [{r['id']}] {r['titulo']}")
    hist.append("")
    hist.append(f"- **Categoria:** `{r.get('categoria', '?')}`")
    hist.append(f"- **Resolvida em:** {r.get('resolvida_em', '?')}")
    hist.append(f"- **Resolvida por:** {r.get('resolvida_por', '?')}")
    hist.append(f"- **Como:** {r.get('como', '?')}")
    hist.append("")

with open(HISTORICO, "w") as f:
    f.write("\n".join(hist))

print(f"✅ Gerado: {OUT}")
print(f"   Tamanho: {len(open(OUT).read())} bytes")
print(f"✅ Gerado: {HISTORICO}")
print(f"   Tamanho: {len(open(HISTORICO).read())} bytes")
PYEOF
