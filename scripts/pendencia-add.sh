#!/bin/bash
# pendencia-add.sh — adiciona nova pendência ao DB
# Uso: ./pendencia-add.sh "titulo" --categoria infra --prioridade alta [--tempo "30min"] [--tags "tag1,tag2"] [--contexto "..."] [--bloqueio "..."]

set -e

DB="/root/mgs-agent/data/pendencias.db.json"
[[ ! -f "$DB" ]] && { echo "ERRO: $DB não existe"; exit 1; }

# Defaults
TITULO=""
CATEGORIA="infra"
PRIORIDADE="media"
TEMPO=""
TAGS=""
CONTEXTO=""
BLOQUEIO=""
CRIADA_POR="${USER:-claude}"

# Parse args
TITULO="$1"
shift

while [[ $# -gt 0 ]]; do
  case "$1" in
    --categoria) CATEGORIA="$2"; shift 2 ;;
    --prioridade) PRIORIDADE="$2"; shift 2 ;;
    --tempo) TEMPO="$2"; shift 2 ;;
    --tags) TAGS="$2"; shift 2 ;;
    --contexto) CONTEXTO="$2"; shift 2 ;;
    --bloqueio) BLOQUEIO="$2"; shift 2 ;;
    --por) CRIADA_POR="$2"; shift 2 ;;
    *) echo "Arg desconhecido: $1"; exit 1 ;;
  esac
done

[[ -z "$TITULO" ]] && { echo "ERRO: título obrigatório"; exit 1; }

# Validações categoria/prioridade
VALID_CATS="app seguranca infra conteudo skills agente lovable monitor documentacao externo pessoal"
VALID_PRIO="alta media baixa"

if ! echo "$VALID_CATS" | grep -qw "$CATEGORIA"; then
  echo "ERRO: categoria inválida. Use uma de: $VALID_CATS"
  exit 1
fi

if ! echo "$VALID_PRIO" | grep -qw "$PRIORIDADE"; then
  echo "ERRO: prioridade inválida. Use uma de: $VALID_PRIO"
  exit 1
fi

# Próximo ID + timestamp
TIMESTAMP=$(date -Iseconds)

python3 <<PYEOF
import json
from datetime import datetime

with open("$DB") as f:
    data = json.load(f)

next_id = data["metadata"]["proximo_id"]
new_pend = {
    "id": f"PEND-{next_id:03d}",
    "titulo": "$TITULO",
    "categoria": "$CATEGORIA",
    "prioridade": "$PRIORIDADE",
    "status": "aberta",
    "tempo_estimado": "$TEMPO" or None,
    "bloqueio": "$BLOQUEIO" or None,
    "criada_em": "$TIMESTAMP",
    "criada_por": "$CRIADA_POR",
    "tags": "$TAGS".split(",") if "$TAGS" else [],
    "contexto": "$CONTEXTO" or None
}

data["pendencias"].append(new_pend)
data["metadata"]["proximo_id"] = next_id + 1
data["metadata"]["total_abertas"] = sum(1 for p in data["pendencias"] if p["status"] == "aberta")
data["metadata"]["ultima_atualizacao"] = "$TIMESTAMP"

with open("$DB", "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"✅ Adicionada: PEND-{next_id:03d} - $TITULO")
print(f"   Categoria: $CATEGORIA | Prioridade: $PRIORIDADE")
PYEOF
