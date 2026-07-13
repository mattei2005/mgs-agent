#!/usr/bin/env python3
"""Transactional store and CLI for MGS operational pendências.

The persisted ``proximo_id`` fields are compatibility outputs only. New IDs are
always allocated from max(PEND-NNN in open + resolved) + 1 while holding an
exclusive file lock. All mutators share the same lock and atomic writer.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

DEFAULT_DB = Path(os.environ.get("PENDENCIA_DB", "/root/mgs-agent/data/pendencias.db.json"))
NUMERIC_ID_RE = re.compile(r"^PEND-(\d+)$")
ANY_ID_RE = re.compile(r"^PEND-(?:\d+|R\d+)$")


class IntegrityError(RuntimeError):
    """Raised when the database violates ID or schema invariants."""


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _all_items(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    opened = data.get("pendencias")
    resolved = data.get("resolvidas")
    if not isinstance(opened, list) or not isinstance(resolved, list):
        raise IntegrityError("pendencias[] and resolvidas[] must both be lists")
    if not all(isinstance(item, dict) for item in opened + resolved):
        raise IntegrityError("every pending/resolved item must be an object")
    return opened + resolved


def validate_database(data: Dict[str, Any]) -> None:
    items = _all_items(data)
    ids: List[str] = []
    for item in items:
        pending_id = item.get("id")
        if not isinstance(pending_id, str) or not ANY_ID_RE.fullmatch(pending_id):
            raise IntegrityError(f"invalid pending ID: {pending_id!r}")
        ids.append(pending_id)
    duplicates = sorted({pending_id for pending_id in ids if ids.count(pending_id) > 1})
    if duplicates:
        raise IntegrityError("duplicate pending IDs: " + ", ".join(duplicates))


def next_numeric_id(data: Dict[str, Any]) -> tuple[str, int]:
    """Return (next_available_id, next_available_number), ignoring counters."""
    validate_database(data)
    numbers = []
    for item in _all_items(data):
        match = NUMERIC_ID_RE.fullmatch(item["id"])
        if match:
            numbers.append(int(match.group(1)))
    next_number = max(numbers, default=0) + 1
    return f"PEND-{next_number:03d}", next_number


def _refresh_derived(data: Dict[str, Any], timestamp: str) -> None:
    _, next_counter = next_numeric_id(data)
    metadata = data.setdefault("metadata", {})
    if not isinstance(metadata, dict):
        raise IntegrityError("metadata must be an object")
    data["proximo_id"] = next_counter
    metadata["proximo_id"] = next_counter
    metadata["total_abertas"] = len(data["pendencias"])
    metadata["total_resolvidas"] = len(data["resolvidas"])
    metadata["ultima_atualizacao"] = timestamp
    data["ultima_atualizacao"] = timestamp


@contextmanager
def _exclusive_lock(db_path: Path):
    lock_path = db_path.parent / ".pendencias.lock"
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _atomic_write_json(db_path: Path, data: Dict[str, Any]) -> None:
    mode = db_path.stat().st_mode & 0o777
    temp_name: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=db_path.parent,
            prefix=f".{db_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp:
            temp_name = temp.name
            os.chmod(temp_name, mode)
            json.dump(data, temp, ensure_ascii=False, indent=2)
            temp.write("\n")
            temp.flush()
            os.fsync(temp.fileno())
        os.replace(temp_name, db_path)
        temp_name = None
        dir_fd = os.open(db_path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if temp_name:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass


def _transaction(
    db_path: Path | str,
    mutator: Callable[[Dict[str, Any]], Dict[str, Any]],
    *,
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    path = Path(db_path)
    if not path.is_file():
        raise FileNotFoundError(f"database not found: {path}")
    ts = timestamp or _now_iso()
    with _exclusive_lock(path):
        data = json.loads(path.read_text(encoding="utf-8"))
        validate_database(data)
        result = mutator(data)
        _refresh_derived(data, ts)
        validate_database(data)
        _atomic_write_json(path, data)
        verify = json.loads(path.read_text(encoding="utf-8"))
        validate_database(verify)
        expected_next = next_numeric_id(verify)[1]
        if verify.get("proximo_id") != expected_next:
            raise IntegrityError("root proximo_id readback mismatch")
        if (verify.get("metadata") or {}).get("proximo_id") != expected_next:
            raise IntegrityError("metadata proximo_id readback mismatch")
        return result


def _normalize_tags(tags: Optional[Iterable[str]]) -> List[str]:
    return [str(tag).strip() for tag in (tags or []) if str(tag).strip()]


def _require_category(data: Dict[str, Any], category: str) -> None:
    categories = data.get("categorias") or {}
    if not isinstance(categories, dict) or category not in categories:
        allowed = ", ".join(sorted(categories)) if isinstance(categories, dict) else ""
        raise IntegrityError(f"invalid category {category!r}; allowed: {allowed}")


def add_open(
    db_path: Path | str,
    *,
    titulo: str,
    categoria: str,
    prioridade: str = "media",
    tempo_estimado: Optional[str] = None,
    tags: Optional[Iterable[str]] = None,
    contexto: Optional[str] = None,
    bloqueio: Optional[str] = None,
    criada_por: str = "zeus",
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    ts = timestamp or _now_iso()

    def mutate(data: Dict[str, Any]) -> Dict[str, Any]:
        pending_id, _ = next_numeric_id(data)
        item = {
            "id": pending_id,
            "titulo": titulo,
            "categoria": categoria,
            "prioridade": prioridade,
            "status": "aberta",
            "tempo_estimado": tempo_estimado or None,
            "bloqueio": bloqueio or None,
            "criada_em": ts,
            "criada_por": criada_por,
            "tags": _normalize_tags(tags),
            "contexto": contexto or None,
        }
        data["pendencias"].append(item)
        return item

    return _transaction(db_path, mutate, timestamp=ts)


def add_historical(
    db_path: Path | str,
    *,
    titulo: str,
    categoria: str,
    prioridade: str,
    data_resolucao: str,
    resolvida_por: str,
    como: str,
    tags: Optional[Iterable[str]] = None,
    contexto: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    ts = timestamp or _now_iso()

    def mutate(data: Dict[str, Any]) -> Dict[str, Any]:
        pending_id, _ = next_numeric_id(data)
        item = {
            "id": pending_id,
            "titulo": titulo,
            "categoria": categoria,
            "prioridade": prioridade,
            "tags": _normalize_tags(tags),
            "tipo": "historico_retroativo",
            "criada_em": f"{data_resolucao}T00:00:00-04:00",
            "criada_por": resolvida_por,
            "resolvida_em": ts,
            "resolvida_por": resolvida_por,
            "como": como,
        }
        if contexto:
            item["contexto"] = contexto
        data["resolvidas"].append(item)
        return item

    return _transaction(db_path, mutate, timestamp=ts)


def resolve_open(
    db_path: Path | str,
    *,
    pending_id: str,
    como: str,
    resolvida_por: str,
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    ts = timestamp or _now_iso()

    def mutate(data: Dict[str, Any]) -> Dict[str, Any]:
        matches = [(index, item) for index, item in enumerate(data["pendencias"]) if item["id"] == pending_id]
        if len(matches) != 1:
            raise IntegrityError(f"expected exactly one open item {pending_id}, found {len(matches)}")
        index, item = matches[0]
        resolved = {
            "id": item["id"],
            "titulo": item["titulo"],
            "categoria": item["categoria"],
            "resolvida_em": ts,
            "resolvida_por": resolvida_por,
            "como": como,
        }
        data["resolvidas"].append(resolved)
        data["pendencias"].pop(index)
        return resolved

    return _transaction(db_path, mutate, timestamp=ts)


def _tags_arg(raw: str) -> List[str]:
    return [tag.strip() for tag in raw.split(",") if tag.strip()]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add")
    add.add_argument("titulo")
    add.add_argument("--categoria", default="infra")
    add.add_argument("--prioridade", choices=("alta", "media", "baixa"), default="media")
    add.add_argument("--tempo", default="")
    add.add_argument("--tags", default="")
    add.add_argument("--contexto", default="")
    add.add_argument("--bloqueio", default="")
    add.add_argument("--por", default=os.environ.get("USER", "zeus"))

    done = sub.add_parser("done")
    done.add_argument("id")
    done.add_argument("--como", required=True)
    done.add_argument("--por", default=os.environ.get("USER", "rodolfo"))

    historical = sub.add_parser("historico-add")
    historical.add_argument("titulo")
    historical.add_argument("--categoria", required=True)
    historical.add_argument("--como", required=True)
    historical.add_argument("--prioridade", choices=("alta", "media", "baixa"), default="media")
    historical.add_argument("--data", default=datetime.now().astimezone().date().isoformat())
    historical.add_argument("--tags", default="")
    historical.add_argument("--contexto", default="")
    historical.add_argument("--por", default="zeus")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "add":
            item = add_open(
                args.db,
                titulo=args.titulo,
                categoria=args.categoria,
                prioridade=args.prioridade,
                tempo_estimado=args.tempo,
                tags=_tags_arg(args.tags),
                contexto=args.contexto,
                bloqueio=args.bloqueio,
                criada_por=args.por,
            )
            print(f"✅ Adicionada: {item['id']} - {item['titulo']}")
            print(f"   Categoria: {item['categoria']} | Prioridade: {item['prioridade']}")
        elif args.command == "done":
            item = resolve_open(
                args.db,
                pending_id=args.id,
                como=args.como,
                resolvida_por=args.por,
            )
            print(f"✅ Resolvida: {item['id']} - {item['titulo']}")
            print(f"   Como: {item['como']}")
            print(f"   Por: {item['resolvida_por']}")
        else:
            item = add_historical(
                args.db,
                titulo=args.titulo,
                categoria=args.categoria,
                prioridade=args.prioridade,
                data_resolucao=args.data,
                resolvida_por=args.por,
                como=args.como,
                tags=_tags_arg(args.tags),
                contexto=args.contexto,
            )
            print(f"✅ Histórico registrado: {item['id']}")
            print(f"   Título: {item['titulo'][:80]}")
            print(f"   Categoria: {item['categoria']} | Data resolução: {args.data}")
        return 0
    except (IntegrityError, FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        print(f"❌ ERRO: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
