#!/bin/bash
# pendencia-historico-add.sh
# Adiciona item direto em 'resolvidas' (sem passar por 'abertas')
# Útil para catalogar histórico retroativo
#
# Uso:
#   ./scripts/pendencia-historico-add.sh "Título" \
#     --categoria infra --como "descrição da resolução" \
#     [--prioridade alta|media|baixa] [--data YYYY-MM-DD] \
#     [--tags tag1,tag2] [--contexto "..."] [--por nome]

set -euo pipefail

DB="/root/mgs-agent/data/pendencias.db.json"

if [ $# -lt 1 ]; then
  echo "Uso: $0 \"Título\" --categoria CAT --como \"como foi resolvida\" [opções]"
  echo "Categorias: app, seguranca, infra, conteudo, skills, agente, lovable, monitor, documentacao, externo, pessoal"
  exit 1
fi

TITULO="$1"
shift

CATEGORIA=""
COMO=""
PRIORIDADE="media"
DATA_RESOLUCAO=""
TAGS=""
CONTEXTO=""
POR="claude-web"

while [ $# -gt 0 ]; do
  case "$1" in
    --categoria) CATEGORIA="$2"; shift 2 ;;
    --como) COMO="$2"; shift 2 ;;
    --prioridade) PRIORIDADE="$2"; shift 2 ;;
    --data) DATA_RESOLUCAO="$2"; shift 2 ;;
    --tags) TAGS="$2"; shift 2 ;;
    --contexto) CONTEXTO="$2"; shift 2 ;;
    --por) POR="$2"; shift 2 ;;
    *) echo "Opção desconhecida: $1"; exit 1 ;;
  esac
done

if [ -z "$CATEGORIA" ] || [ -z "$COMO" ]; then
  echo "ERRO: --categoria e --como são obrigatórios"
  exit 1
fi

if [ -z "$DATA_RESOLUCAO" ]; then
  DATA_RESOLUCAO=$(date +%Y-%m-%d)
fi

TIMESTAMP=$(date -Iseconds)

python3 << PYEOF
import json
from datetime import datetime

with open("$DB", "r") as f:
    db = json.load(f)

proximo_id = db.get("proximo_id", 1)
pend_id = f"PEND-{proximo_id:03d}"

tags_list = [t.strip() for t in "$TAGS".split(",") if t.strip()] if "$TAGS" else []

novo_item = {
    "id": pend_id,
    "titulo": "$TITULO",
    "categoria": "$CATEGORIA",
    "prioridade": "$PRIORIDADE",
    "criado_em": "$DATA_RESOLUCAO" + "T00:00:00-04:00",
    "criado_por": "$POR",
    "contexto": "$CONTEXTO",
    "tags": tags_list,
    "resolvido_em": "$TIMESTAMP",
    "resolvido_por": "$POR",
    "como_foi_resolvido": "$COMO",
    "tipo": "historico_retroativo"
}

if "resolvidas" not in db:
    db["resolvidas"] = []

db["resolvidas"].append(novo_item)
db["proximo_id"] = proximo_id + 1
db["ultima_atualizacao"] = "$TIMESTAMP"

with open("$DB", "w") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

print(f"✅ Histórico registrado: {pend_id} - $TITULO")
print(f"   Categoria: $CATEGORIA | Data resolução: $DATA_RESOLUCAO")
print(f"   Como: $COMO"[:200])
PYEOF
