#!/bin/bash
# migration-2026-05-14-proximo-id-collision-fix.sh
#
# CONTEXTO:
# Bug detectado 14/05: pendencia-add.sh lê metadata.proximo_id (linha 63),
# enquanto pendencia-historico-add.sh lê root .proximo_id. Renumeração Fase 3
# atualizou só o root, deixando metadata=74 desatualizado. Primeira nova add
# após Fase 3 (PEND-074 "Monitorar Tier 4 Anthropic") colidiu com o PEND-074
# já existente em resolvidas[] (marco histórico renumerado).
#
# ESTADO ESPERADO ANTES:
#   .proximo_id (root)     = 86
#   .metadata.proximo_id   = 75
#   Colisão: PEND-074 em pendencias[] E em resolvidas[]
#
# AÇÃO:
#   1) Backup .bak-pre-migration-<timestamp>
#   2) Renumera PEND-074 (em pendencias[]) → PEND-086 (preserva TODOS os campos)
#   3) Sincroniza .proximo_id e .metadata.proximo_id para 87
#   4) Write atômico (tmp + rename)
#   5) Validação pós-write: zero colisões, IDs únicos, ambos proximo_id iguais
#
# IDEMPOTENTE: se não há colisão PEND-074, sai limpo sem alterar nada.
#
# ROLLBACK: em caso de falha pós-write, restaura backup.

set -euo pipefail

DB="/root/mgs-agent/data/pendencias.db.json"
TS=$(date +%Y%m%d-%H%M%S)
BACKUP="${DB}.bak-pre-migration-${TS}"

[[ ! -f "$DB" ]] && { echo "❌ ERRO: $DB não existe" >&2; exit 1; }

echo "🔧 Migration: proximo_id collision fix (PEND-074 ↔ resolvidas)"
echo "   DB:      $DB"
echo "   Backup:  $BACKUP"
echo ""

cp -p "$DB" "$BACKUP"
echo "✅ Backup criado"
echo ""

python3 - "$DB" "$BACKUP" <<'PYEOF'
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone, timedelta

DB, BACKUP = sys.argv[1], sys.argv[2]

def fatal(msg, rollback=False):
    print(f"❌ {msg}", file=sys.stderr)
    if rollback:
        print(f"⏪ Rollback: restaurando {BACKUP} → {DB}", file=sys.stderr)
        shutil.copy2(BACKUP, DB)
    sys.exit(1)

with open(DB) as f:
    data = json.load(f)

# ------------------------------------------------------------------
# PASSO 1: estado ANTES
# ------------------------------------------------------------------
root_pid = data.get("proximo_id")
meta_pid = data.get("metadata", {}).get("proximo_id")

abertas_ids = [p["id"] for p in data["pendencias"]]
resolv_ids  = [p["id"] for p in data["resolvidas"]]
colisoes    = sorted(set(abertas_ids) & set(resolv_ids))

print("📊 Estado ANTES:")
print(f"   .proximo_id (root)    = {root_pid}")
print(f"   .metadata.proximo_id  = {meta_pid}")
print(f"   Colisões abertas↔resolvidas: {colisoes if colisoes else 'NENHUMA'}")
print()

# Idempotência: nada pra fazer
if "PEND-074" not in colisoes:
    print("ℹ️  Sem colisão PEND-074 detectada. Migration já aplicada ou desnecessária.")
    print("   Removendo backup desnecessário…")
    os.remove(BACKUP)
    sys.exit(0)

# ------------------------------------------------------------------
# PASSO 2: localizar PEND-074 em pendencias[] (a entry nova)
# ------------------------------------------------------------------
idx = next((i for i, p in enumerate(data["pendencias"]) if p["id"] == "PEND-074"), None)
if idx is None:
    fatal("PEND-074 não encontrada em pendencias[] (estado inconsistente).")

old_entry = dict(data["pendencias"][idx])
print("📌 Entry a renumerar (preservando todos os campos):")
for k in ("id", "titulo", "criada_em", "criada_por", "categoria", "prioridade"):
    print(f"   {k:14s} = {old_entry.get(k)}")
print()

# ------------------------------------------------------------------
# PASSO 3: calcular novo ID (próximo livre acima de TODOS os usados)
# ------------------------------------------------------------------
def numeric(pid):
    m = re.match(r"PEND-(\d+)$", pid)
    return int(m.group(1)) if m else 0

used_nums = {numeric(p) for p in (abertas_ids + resolv_ids) if numeric(p) > 0}
max_used  = max(used_nums)
new_num   = max_used + 1
new_id    = f"PEND-{new_num:03d}"

print(f"🆔 Cálculo do novo ID:")
print(f"   max(numeric IDs usados) = {max_used}")
print(f"   novo ID                 = {new_id}")
print()

# Sanity: novo ID realmente não colide
all_ids = set(abertas_ids) | set(resolv_ids)
if new_id in all_ids:
    fatal(f"Novo ID {new_id} já existe — algo muito errado no estado.")

# ------------------------------------------------------------------
# PASSO 4: aplicar mudanças em memória
# ------------------------------------------------------------------
data["pendencias"][idx]["id"] = new_id

next_pid = new_num + 1
data["proximo_id"] = next_pid
if "metadata" in data:
    data["metadata"]["proximo_id"] = next_pid
    # ultima_atualizacao timestamp
    now = datetime.now(timezone(timedelta(hours=-4))).isoformat(timespec="seconds")
    data["metadata"]["ultima_atualizacao"] = now

# ------------------------------------------------------------------
# PASSO 5: validação em memória ANTES do write
# ------------------------------------------------------------------
new_abertas = [p["id"] for p in data["pendencias"]]
new_resolv  = [p["id"] for p in data["resolvidas"]]
new_colis   = sorted(set(new_abertas) & set(new_resolv))

if new_colis:
    fatal(f"Validação pré-write: ainda há colisões: {new_colis}")

# Duplicatas internas
for nome, lst in (("pendencias", new_abertas), ("resolvidas", new_resolv)):
    if len(lst) != len(set(lst)):
        dups = [x for x in set(lst) if lst.count(x) > 1]
        fatal(f"Validação pré-write: duplicatas em {nome}[]: {dups}")

# proximo_id sync
if data["proximo_id"] != data.get("metadata", {}).get("proximo_id"):
    fatal(f"Validação pré-write: proximo_id dessincronizado "
          f"(root={data['proximo_id']}, meta={data['metadata'].get('proximo_id')})")

# ------------------------------------------------------------------
# PASSO 6: write atômico (tmp → rename)
# ------------------------------------------------------------------
tmp = DB + ".tmp-migration"
try:
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, DB)
except Exception as e:
    if os.path.exists(tmp):
        os.remove(tmp)
    fatal(f"Erro durante write atômico: {e}")

# ------------------------------------------------------------------
# PASSO 7: validação pós-write (re-ler do disco)
# ------------------------------------------------------------------
with open(DB) as f:
    verify = json.load(f)

v_root = verify.get("proximo_id")
v_meta = verify.get("metadata", {}).get("proximo_id")
v_aber = [p["id"] for p in verify["pendencias"]]
v_reso = [p["id"] for p in verify["resolvidas"]]
v_col  = sorted(set(v_aber) & set(v_reso))

problems = []
if v_root != next_pid:
    problems.append(f"root proximo_id={v_root}, esperado {next_pid}")
if v_meta != next_pid:
    problems.append(f"meta proximo_id={v_meta}, esperado {next_pid}")
if v_col:
    problems.append(f"colisões ainda presentes: {v_col}")
if new_id not in v_aber:
    problems.append(f"novo ID {new_id} não encontrado em pendencias[]")
if "PEND-074" in v_aber:
    problems.append("PEND-074 ainda presente em pendencias[]")

if problems:
    fatal("Validação pós-write falhou:\n  - " + "\n  - ".join(problems), rollback=True)

# ------------------------------------------------------------------
# RESUMO
# ------------------------------------------------------------------
print("✅ Estado DEPOIS:")
print(f"   .proximo_id (root)    = {v_root}")
print(f"   .metadata.proximo_id  = {v_meta}")
print(f"   PEND-074 → {new_id}  (timestamp, autor, todos os campos preservados)")
print(f"   Colisões: NENHUMA")
print(f"   Backup preservado:    {BACKUP}")
PYEOF

echo ""
echo "✅ Migration concluída com sucesso."
