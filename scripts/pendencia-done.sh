#!/bin/bash
# pendencia-done.sh — marca pendência como resolvida
# Uso: ./pendencia-done.sh PEND-001 --como "Publicado via Play Console"

set -e

DB="/root/mgs-agent/data/pendencias.db.json"
[[ ! -f "$DB" ]] && { echo "ERRO: $DB não existe"; exit 1; }

ID="$1"
shift

COMO=""
RESOLVIDA_POR="${USER:-rodolfo}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --como) COMO="$2"; shift 2 ;;
    --por) RESOLVIDA_POR="$2"; shift 2 ;;
    *) echo "Arg desconhecido: $1"; exit 1 ;;
  esac
done

[[ -z "$ID" ]] && { echo "ERRO: ID obrigatório (ex: PEND-001)"; exit 1; }
[[ -z "$COMO" ]] && { echo "ERRO: --como obrigatório"; exit 1; }

TIMESTAMP=$(date -Iseconds)

python3 <<PYEOF
import json

with open("$DB") as f:
    data = json.load(f)

# Buscar pendência
found = None
for i, p in enumerate(data["pendencias"]):
    if p["id"] == "$ID":
        found = (i, p)
        break

if not found:
    print(f"❌ Pendência $ID não encontrada")
    exit(1)

idx, pend = found

# Mover para resolvidas
resolved = {
    "id": pend["id"],
    "titulo": pend["titulo"],
    "categoria": pend["categoria"],
    "resolvida_em": "$TIMESTAMP",
    "resolvida_por": "$RESOLVIDA_POR",
    "como": "$COMO"
}
data["resolvidas"].append(resolved)

# Remover de abertas
data["pendencias"].pop(idx)

# Atualizar metadata
data["metadata"]["total_abertas"] = len(data["pendencias"])
data["metadata"]["total_resolvidas"] = len(data["resolvidas"])
data["metadata"]["ultima_atualizacao"] = "$TIMESTAMP"

with open("$DB", "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"✅ Resolvida: {pend['id']} - {pend['titulo']}")
print(f"   Como: $COMO")
print(f"   Por: $RESOLVIDA_POR")
PYEOF
