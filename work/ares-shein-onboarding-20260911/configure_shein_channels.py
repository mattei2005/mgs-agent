#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import yaml

PROFILE = "ares"
CONFIG = Path("/root/.hermes/profiles/ares/config.yaml")
ENV = Path("/root/.hermes/profiles/ares/.env")
HERMES = "/root/.local/bin/hermes"
ZEUS = "1496296175014252634"
RODOLFO = "344196393512075265"
GEIZIAN = "321263240782807040"
CHANNELS = [
    ("1548149087206121613", "shein-g001", "G001", "Icaro", "409878085807112207"),
    ("1548149300826079333", "shein-g002", "G002", "Geizian", "321263240782807040"),
    ("1548149483039236137", "shein-g003", "G003", "Isliago", "432898782188011543"),
    ("1548149654926135486", "shein-g004", "G004", "Joe", "1214246869484576890"),
    ("1548150015275438220", "shein-g005", "G005", "Kelly", "1291113428982693940"),
    ("1548150155184701440", "shein-g006", "G006", "Nicolas", "1055570806945620030"),
]


def unique(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if value and value not in output:
            output.append(value)
    return output


def run_config_set(key: str, value: str) -> None:
    completed = subprocess.run(
        [HERMES, "-p", PROFILE, "config", "set", "--force", key, value],
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"config set failed for {key}: {completed.stderr[-400:]}")


def prompt(code: str, manager: str, manager_id: str, channel_name: str) -> str:
    return f"""INSTRUCAO DE THREAD Ares SHEIN {code}

- Canal privado de Campaign Ops da operacao SHEIN-US-DIRECT para Rodolfo, Zeus, Geizian, Ares e {manager}; rota `{channel_name}`. Nao adicionar outros gestores automaticamente.
- Escopo: trafego direto Meta para os EUA. Sites em ingles: yolokfx.com e vizioid.com. Site em espanhol: mavroa.com. O gestor pode rodar os sites simultaneamente com suas proprias contas de anuncio e perfis anunciantes.
- Gestor atribuido: {manager} ({code}, Discord ID {manager_id}). Pedidos neste canal so podem operar contas/perfis desse gestor; nunca usar conta, perfil, campanha, budget ou estado de outro canal sem nova autorizacao explicita de Rodolfo.
- Rodolfo concedeu ao gestor autonomia por pedido para criar, duplicar, clonar, relatar, organizar threads, otimizar, pausar, reativar, excluir/arquivar, definir/alterar budget, definir schedule e ativar campanhas. Budget deve trazer valor e moeda exatos; dentro deste escopo nao pedir uma segunda aprovacao de Rodolfo.
- Antes do primeiro write em cada conta/perfil, identificar o alvo exato e validar por API/readback nome da conta, moeda, timezone, acesso e saude. Registrar alias curto; usar somente o escopo solicitado e fazer GET/readback depois de toda mudanca.
- Billing, account_spend_limit, credenciais, ownership, permissoes de app, pixel/CAPI, WordPress, quiz, SMS Funnel, ChatPion, acesso cruzado entre gestores e automacao recorrente sem politica propria continuam fora da delegacao.
- Criacao/clone/lote Meta usa `direct-traffic-shein-operations` e `meta-campaign-engine-v3`. Nao carregar `direct-traffic-cbo-operations` como fonte unica nem herdar objetivo, bid, estrutura, copy, budget, schedule ou template de CAR/CPV, outra operacao ou outro gestor; resolver pelo pedido e estado Meta real.
- Criativos exigem idioma compativel, metadata limpa, reserva e reconciliacao Drive x Meta. `MGS-AGENTS/CRIATIVOS/SHEIN_US_EN` e o pool EN atual; `01_READY` nao prova elegibilidade ou ineditismo. Para mavroa/ES, nao usar asset EN como se fosse ES e nao inventar pool espanhol.
- Toda thread nova deve incluir Zeus, Rodolfo, Geizian e {manager}; validar a inclusao por readback real. Responda na thread atual; nao use send_message para resposta normal.
- Titulos de threads: etiqueta semantica curta de 3 a 6 palavras; nao sobrescrever titulo manual. Threads fixas/cadencias so sao criadas quando o gestor definir; evitar duplicar rota existente.
"""


def parse_env(path: Path) -> tuple[list[str], dict[str, str]]:
    raw_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    values: dict[str, str] = {}
    for raw in raw_lines:
        stripped = raw.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, value = stripped.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return raw_lines, values


def update_env_mapping(mapping: dict[str, list[str]]) -> None:
    key = "DISCORD_THREAD_AUTO_ADD_USERS_BY_CHANNEL"
    lines, _ = parse_env(ENV)
    serialized = json.dumps(mapping, separators=(",", ":"))
    replaced = False
    output: list[str] = []
    for raw in lines:
        if raw.strip().startswith(key + "="):
            output.append(key + "=" + serialized)
            replaced = True
        else:
            output.append(raw)
    if not replaced:
        output.append(key + "=" + serialized)
    mode = ENV.stat().st_mode & 0o777
    temp = ENV.with_suffix(".env.shein.tmp")
    temp.write_text("\n".join(output) + "\n", encoding="utf-8")
    os.chmod(temp, mode)
    os.replace(temp, ENV)


def main() -> int:
    current = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    discord = current.get("discord") or {}
    allowed = unique([part.strip() for part in str(discord.get("allowed_channels", "")).split(",")] + [row[0] for row in CHANNELS])
    free = unique([part.strip() for part in str(discord.get("free_response_channels", "")).split(",")] + [row[0] for row in CHANNELS])
    mapping = {str(key): [str(value) for value in values] for key, values in (discord.get("thread_auto_add_users_by_channel") or {}).items()}
    prompts = {str(key): str(value) for key, value in (discord.get("channel_prompts") or {}).items()}

    for channel_id, channel_name, code, manager, manager_id in CHANNELS:
        mapping[channel_id] = unique([ZEUS, RODOLFO, GEIZIAN, manager_id])
        prompts[channel_id] = prompt(code, manager, manager_id, channel_name)

    run_config_set("discord.allowed_channels", ",".join(allowed))
    run_config_set("discord.free_response_channels", ",".join(free))
    run_config_set("discord.channel_prompts", json.dumps(prompts, ensure_ascii=False))
    run_config_set("discord.thread_auto_add_users_by_channel", json.dumps(mapping))
    update_env_mapping(mapping)

    updated = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    d = updated.get("discord") or {}
    if d.get("allowed_channels") != ",".join(allowed):
        raise RuntimeError("allowed_channels readback mismatch")
    if d.get("free_response_channels") != ",".join(free):
        raise RuntimeError("free_response_channels readback mismatch")
    if {str(k): [str(v) for v in values] for k, values in (d.get("thread_auto_add_users_by_channel") or {}).items()} != mapping:
        raise RuntimeError("thread auto-add config readback mismatch")
    actual_prompts = {str(k): str(v) for k, v in (d.get("channel_prompts") or {}).items()}
    for channel_id, _, _, _, _ in CHANNELS:
        if actual_prompts.get(channel_id) != prompts[channel_id]:
            raise RuntimeError(f"channel prompt readback mismatch: {channel_id}")

    _, env_values = parse_env(ENV)
    env_mapping = json.loads(env_values["DISCORD_THREAD_AUTO_ADD_USERS_BY_CHANNEL"])
    if env_mapping != mapping:
        raise RuntimeError("environment bridge mapping readback mismatch")

    result = {
        "success": True,
        "channels_added": [row[0] for row in CHANNELS],
        "allowed_channel_count": len(allowed),
        "free_response_channel_count": len(free),
        "channel_prompt_count": len(actual_prompts),
        "auto_add_mapping_count": len(mapping),
        "env_bridge_readback": True,
    }
    Path("/root/mgs-agent/work/ares-shein-onboarding-20260911/channel-config-readback.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
