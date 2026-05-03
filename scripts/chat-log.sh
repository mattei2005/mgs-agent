#!/bin/bash
# chat-log.sh — registra eventos importantes da sessão atual
# Uso:
#   ./chat-log.sh "Decisão: migrei wp_app_password pra pgsodium"
#   ./chat-log.sh --tipo decisao "..."
#   ./chat-log.sh --tipo contexto "..."
#   ./chat-log.sh --tipo licao "..."
#   ./chat-log.sh --tipo pend-add "PEND-XXX: título"
#   ./chat-log.sh --tipo pend-done "PEND-XXX: como"
#   ./chat-log.sh --tipo proximo "..."
#   ./chat-log.sh --nova-sessao "Sessão tarde 03/05"
#   ./chat-log.sh --listar
#   ./chat-log.sh --rebuild-index
#   ./chat-log.sh --fechar  # marca sessão atual como fechada

set -e

LOG_DIR="/root/mgs-agent/data/chat-logs"
INDEX="$LOG_DIR/INDEX.md"

mkdir -p "$LOG_DIR"

TIPO="evento"
TEXTO=""
NOVA_SESSAO=""
LISTAR=false
REBUILD=false
FECHAR=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tipo) TIPO="$2"; shift 2 ;;
    --nova-sessao) NOVA_SESSAO="$2"; shift 2 ;;
    --listar) LISTAR=true; shift ;;
    --rebuild-index) REBUILD=true; shift ;;
    --fechar) FECHAR=true; shift ;;
    *) TEXTO="$1"; shift ;;
  esac
done

# === LISTAR ===
if [[ "$LISTAR" == "true" ]]; then
  echo "📚 Sessões registradas:"
  echo ""
  ls -lht "$LOG_DIR"/sessao-*.md 2>/dev/null | awk '{print "  ", $9, "(" $5 " bytes)"}' | head -30
  echo ""
  echo "Index: $INDEX"
  exit 0
fi

# === REBUILD INDEX ===
if [[ "$REBUILD" == "true" ]]; then
  export LOG_DIR INDEX
  python3 <<'PYEOF'
import os
from datetime import datetime

LOG_DIR = os.environ["LOG_DIR"]
INDEX = os.environ["INDEX"]

sessoes = sorted(
    [f for f in os.listdir(LOG_DIR) if f.startswith("sessao-") and f.endswith(".md")],
    reverse=True
)

lines = []
lines.append("# 📚 Index — Chat Logs MGS Digital Corp")
lines.append("")
lines.append(f"> Atualizado: {datetime.now().isoformat()}")
lines.append(f"> Total sessões: {len(sessoes)}")
lines.append("")
lines.append("---")
lines.append("")
lines.append("## Como retomar próximo chat")
lines.append("")
lines.append("Cole no início do próximo chat:")
lines.append("")
lines.append("```")
lines.append("Lê /root/mgs-agent/data/chat-logs/INDEX.md e o arquivo da sessão mais")
lines.append("recente listado abaixo, para retomar contexto sem search profundo.")
lines.append("Em seguida, lê /root/mgs-agent/docs/PENDENCIAS.md para saber o que está aberto.")
lines.append("```")
lines.append("")
lines.append("---")
lines.append("")
lines.append("## Sessões (mais recentes primeiro)")
lines.append("")

for s in sessoes:
    path = os.path.join(LOG_DIR, s)
    with open(path) as f:
        first_line = f.readline().strip().lstrip("#").strip()
    size = os.path.getsize(path)
    mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")
    lines.append(f"- **`{s}`** — {first_line} _({size}B, mod {mtime})_")

lines.append("")

with open(INDEX, "w") as f:
    f.write("\n".join(lines))

print(f"✅ Index regenerado: {INDEX}")
print(f"   {len(sessoes)} sessões indexadas")
PYEOF
  exit 0
fi

# === FECHAR ===
if [[ "$FECHAR" == "true" ]]; then
  if [[ ! -L "$LOG_DIR/_atual.md" ]]; then
    echo "⚠️  Nenhuma sessão ativa pra fechar"
    exit 1
  fi
  ARQUIVO=$(readlink -f "$LOG_DIR/_atual.md")
  sed -i 's/\*\*Status:\*\* ativa/**Status:** fechada/' "$ARQUIVO"
  echo "**Fim:** $(date -Iseconds)" >> "$ARQUIVO"
  rm "$LOG_DIR/_atual.md"
  echo "✅ Sessão fechada: $ARQUIVO"
  bash "$0" --rebuild-index >/dev/null
  exit 0
fi

# === NOVA SESSÃO ===
if [[ -n "$NOVA_SESSAO" ]]; then
  TIMESTAMP=$(date +%Y-%m-%d_%H%M)
  ARQUIVO="$LOG_DIR/sessao-${TIMESTAMP}.md"

  cat > "$ARQUIVO" <<EOF
# $NOVA_SESSAO

**Início:** $(date -Iseconds)
**Status:** ativa

---

## 🎯 Objetivo da sessão

## 📋 Decisões tomadas

## 📚 Contexto novo descoberto

## ⚠️ Lições aprendidas / PITFALLs

## ✅ Pendências adicionadas

## 🎉 Pendências resolvidas

## 🔜 Próximos passos

## 💬 Eventos diversos

EOF

  ln -sfn "$ARQUIVO" "$LOG_DIR/_atual.md"

  echo "✅ Nova sessão criada: $ARQUIVO"
  echo "   Symlink atualizado: $LOG_DIR/_atual.md"

  bash "$0" --rebuild-index >/dev/null
  exit 0
fi

# === APPEND ===
[[ -z "$TEXTO" ]] && { echo "ERRO: texto obrigatório"; exit 1; }

if [[ ! -L "$LOG_DIR/_atual.md" ]] || [[ ! -e "$LOG_DIR/_atual.md" ]]; then
  echo "⚠️  Nenhuma sessão ativa. Criando 'sessao-improviso'..."
  bash "$0" --nova-sessao "Sessão $(date +%Y-%m-%d_%H%M) (auto-criada)"
fi

ARQUIVO=$(readlink -f "$LOG_DIR/_atual.md")
TIMESTAMP=$(date +%H:%M)

case "$TIPO" in
  decisao)    SECAO="## 📋 Decisões tomadas" ;;
  contexto)   SECAO="## 📚 Contexto novo descoberto" ;;
  licao)      SECAO="## ⚠️ Lições aprendidas / PITFALLs" ;;
  pend-add)   SECAO="## ✅ Pendências adicionadas" ;;
  pend-done)  SECAO="## 🎉 Pendências resolvidas" ;;
  proximo)    SECAO="## 🔜 Próximos passos" ;;
  evento|*)   SECAO="## 💬 Eventos diversos" ;;
esac

export ARQUIVO SECAO TIMESTAMP TEXTO
python3 <<'PYEOF'
import os
ARQUIVO = os.environ["ARQUIVO"]
SECAO = os.environ["SECAO"]
TIMESTAMP = os.environ["TIMESTAMP"]
TEXTO = os.environ["TEXTO"]

with open(ARQUIVO) as f:
    content = f.read()

linha = f"- `{TIMESTAMP}` {TEXTO}"

if SECAO not in content:
    content += f"\n\n{SECAO}\n{linha}\n"
else:
    idx = content.find(SECAO)
    end_secao = content.find("\n## ", idx + len(SECAO))
    if end_secao == -1:
        content = content.rstrip() + f"\n{linha}\n"
    else:
        antes = content[:end_secao].rstrip()
        depois = content[end_secao:]
        content = f"{antes}\n{linha}\n{depois}"

with open(ARQUIVO, "w") as f:
    f.write(content)

display_secao = SECAO.lstrip("#").strip()
print(f"✅ [{TIMESTAMP}] {display_secao}: {TEXTO[:80]}{'...' if len(TEXTO) > 80 else ''}")
PYEOF
