#!/bin/bash
# pendencia-historico-add.sh (v2 — schema canônico + anti-duplicata)
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

# Passa via env pra evitar quebra com aspas/cifrão no input
export TITULO CATEGORIA COMO PRIORIDADE DATA_RESOLUCAO TAGS CONTEXTO POR TIMESTAMP DB

python3 <<'PYEOF'
import json
import os
import sys

DB = os.environ['DB']

with open(DB, 'r') as f:
    db = json.load(f)

# === ANTI-BUG 1: usar proximo_id, nunca resetar ===
proximo_id = db.get('proximo_id', 1)
pend_id = f"PEND-{proximo_id:03d}"

# === ANTI-BUG 2: validar que ID não colide com abertas nem resolvidas ===
ids_abertas = {p['id'] for p in db.get('pendencias', [])}
ids_resolvidas = {p['id'] for p in db.get('resolvidas', [])}

if pend_id in ids_abertas or pend_id in ids_resolvidas:
    print(f"❌ ERRO: ID {pend_id} já existe (proximo_id corrompido?)")
    print(f"   IDs em abertas: {len(ids_abertas)}, em resolvidas: {len(ids_resolvidas)}")
    sys.exit(1)

# Tags
tags_raw = os.environ.get('TAGS', '')
tags_list = [t.strip() for t in tags_raw.split(',') if t.strip()] if tags_raw else []

# === Schema canônico (feminino, igual PEND-R001 e pendencia-done.sh) ===
novo_item = {
    "id": pend_id,
    "titulo": os.environ['TITULO'],
    "categoria": os.environ['CATEGORIA'],
    "prioridade": os.environ['PRIORIDADE'],
    "tags": tags_list,
    "tipo": "historico_retroativo",
    "criada_em": os.environ['DATA_RESOLUCAO'] + "T00:00:00-04:00",
    "criada_por": os.environ['POR'],
    "resolvida_em": os.environ['TIMESTAMP'],
    "resolvida_por": os.environ['POR'],
    "como": os.environ['COMO'],
}

contexto = os.environ.get('CONTEXTO', '').strip()
if contexto:
    novo_item['contexto'] = contexto

if 'resolvidas' not in db:
    db['resolvidas'] = []
db['resolvidas'].append(novo_item)

# === ANTI-BUG 3: incrementar proximo_id de verdade ===
# Write em AMBOS os lugares (root + metadata) pra evitar drift — bug catch 14/05
db['proximo_id'] = proximo_id + 1
if 'metadata' in db:
    db['metadata']['proximo_id'] = proximo_id + 1
    db['metadata']['ultima_atualizacao'] = os.environ['TIMESTAMP']
db['ultima_atualizacao'] = os.environ['TIMESTAMP']

with open(DB, 'w') as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

print(f"✅ Histórico registrado: {pend_id}")
print(f"   Título: {os.environ['TITULO'][:80]}")
print(f"   Categoria: {os.environ['CATEGORIA']} | Data resolução: {os.environ['DATA_RESOLUCAO']}")
print(f"   proximo_id agora = {db['proximo_id']}")
PYEOF
