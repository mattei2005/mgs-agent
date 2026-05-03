#!/bin/bash
# pendencia-list.sh — lista pendências com filtros
# Uso:
#   ./pendencia-list.sh                              # todas abertas
#   ./pendencia-list.sh --prioridade alta            # só alta prioridade
#   ./pendencia-list.sh --categoria infra            # só infra
#   ./pendencia-list.sh --tag rec                    # com tag específica
#   ./pendencia-list.sh --resolvidas                 # ver resolvidas
#   ./pendencia-list.sh --stats                      # estatísticas
#   ./pendencia-list.sh --json                       # output JSON puro
#   ./pendencia-list.sh PEND-001                     # uma pendência específica

set -e

DB="/root/mgs-agent/data/pendencias.db.json"
[[ ! -f "$DB" ]] && { echo "ERRO: $DB não existe"; exit 1; }

PRIORIDADE=""
CATEGORIA=""
TAG=""
SHOW_RESOLVIDAS=false
SHOW_STATS=false
SHOW_JSON=false
SPECIFIC_ID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prioridade) PRIORIDADE="$2"; shift 2 ;;
    --categoria) CATEGORIA="$2"; shift 2 ;;
    --tag) TAG="$2"; shift 2 ;;
    --resolvidas) SHOW_RESOLVIDAS=true; shift ;;
    --stats) SHOW_STATS=true; shift ;;
    --json) SHOW_JSON=true; shift ;;
    PEND-*) SPECIFIC_ID="$1"; shift ;;
    *) echo "Arg desconhecido: $1"; exit 1 ;;
  esac
done

python3 <<PYEOF
import json

with open("$DB") as f:
    data = json.load(f)

pendencias = data["pendencias"]
resolvidas = data["resolvidas"]

# Filtros
if "$SPECIFIC_ID":
    pendencias = [p for p in pendencias if p["id"] == "$SPECIFIC_ID"]
    if not pendencias:
        # Tentar em resolvidas
        pendencias = [p for p in resolvidas if p["id"] == "$SPECIFIC_ID"]

if "$PRIORIDADE":
    pendencias = [p for p in pendencias if p.get("prioridade") == "$PRIORIDADE"]

if "$CATEGORIA":
    pendencias = [p for p in pendencias if p.get("categoria") == "$CATEGORIA"]

if "$TAG":
    pendencias = [p for p in pendencias if "$TAG" in p.get("tags", [])]

if "$SHOW_RESOLVIDAS" == "true":
    pendencias = resolvidas

if "$SHOW_JSON" == "true":
    print(json.dumps(pendencias, indent=2, ensure_ascii=False))
    exit(0)

if "$SHOW_STATS" == "true":
    abertas = data["pendencias"]
    print(f"📊 ESTATÍSTICAS PENDÊNCIAS MGS")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Total abertas: {len(abertas)}")
    print(f"Total resolvidas: {len(resolvidas)}")
    print()
    print("Por prioridade (abertas):")
    for prio in ["alta", "media", "baixa"]:
        c = sum(1 for p in abertas if p.get("prioridade") == prio)
        print(f"  {prio:8s} {c:3d}")
    print()
    print("Por categoria (abertas):")
    cats = {}
    for p in abertas:
        c = p.get("categoria", "?")
        cats[c] = cats.get(c, 0) + 1
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat:15s} {count:3d}")
    print()
    print(f"Última atualização: {data['metadata']['ultima_atualizacao']}")
    exit(0)

# Listagem normal
icons = {"alta": "🔴", "media": "🟡", "baixa": "🟢"}

if not pendencias:
    print("Nenhuma pendência encontrada com esses filtros.")
    exit(0)

print(f"📋 {len(pendencias)} pendência(s) encontrada(s)")
print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

for p in pendencias:
    prio = p.get("prioridade", "?")
    icon = icons.get(prio, "⚪")
    print(f"\n{icon} [{p['id']}] {p['titulo']}")
    print(f"   Categoria: {p.get('categoria', '?')} | Prioridade: {prio} | Tempo: {p.get('tempo_estimado', '?')}")
    if p.get("bloqueio"):
        print(f"   ⚠️  Bloqueio: {p['bloqueio']}")
    if p.get("contexto"):
        ctx = p["contexto"][:120] + "..." if len(p["contexto"]) > 120 else p["contexto"]
        print(f"   📝 {ctx}")
    if p.get("tags"):
        print(f"   🏷️  {', '.join(p['tags'])}")
    if "resolvida_em" in p:
        print(f"   ✅ Resolvida: {p['resolvida_em']} por {p.get('resolvida_por', '?')}")
        print(f"   ✓  Como: {p.get('como', '?')}")
PYEOF
