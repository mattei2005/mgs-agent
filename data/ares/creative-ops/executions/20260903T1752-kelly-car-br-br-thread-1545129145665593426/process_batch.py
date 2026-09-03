#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import Any

from PIL import Image

EXECUTOR = Path('/root/mgs-agent/scripts/ares-execute-creative-copy-clean.py')
SANITIZER = Path('/root/mgs-agent/scripts/clean-creative-metadata.sh')
ROOT_ID = '0AEwt4Ye690ocUk9PVA'
EXPECTED_DRIVE = 'MGS-AGENTS'
EXPECTED_EMAIL = 'mgsagent@mgs-core-prod.iam.gserviceaccount.com'
EXPECTED_PROJECT = 'mgs-core-prod'
OPERATION = 'CAR_BR_BR'
THREAD_ID = '1545129145665593426'
INVENTORY = Path('/root/mgs-agent/data/ares/creative-ops/inventory/assets.jsonl')
REPORT_DIR = Path('/root/mgs-agent/data/ares/creative-ops/executions/20260903T1752-kelly-car-br-br-thread-1545129145665593426')
BASE_DIR = REPORT_DIR / 'runtime'
WORK_DIR = BASE_DIR / 'work'
STATE_PATH = BASE_DIR / 'state.json'
DRY_PATH = BASE_DIR / 'dry-run.json'
FOLDER_MIME = 'application/vnd.google-apps.folder'

CLASSIFICATION = {
    '1_202  BR_CAR__BR_28-08 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SCORE_BAIXO', 'person': 'NO_PERSON',
        'claim': 'APROVA NEGATIVADO; 100 DE ENTRADA; PARCELAS DE R$ 299',
    },
    '2_192  BR_CAR__BR_28-08 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SEM_ENTRADA', 'person': 'NO_PERSON',
        'claim': 'CARRO NOVO; R$ 299 NA PARCELA; SEM ENTRADA',
    },
    '3_188  BR_CAR__BR_28-08 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SCORE_BAIXO', 'person': 'PERSON',
        'claim': 'APROVADO MESMO NEGATIVADO; SEM ENTRADA; TANQUE CHEIO; IPVA PAGO; 1ª PARCELA R$ 299',
    },
    '4_205  BR_CAR__BR_28-08 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SCORE_BAIXO', 'person': 'NO_PERSON',
        'claim': 'APROVA NEGATIVADO; 100 DE ENTRADA; PARCELAS DE R$ 299',
    },
    '5_196  BR_CAR__BR_28-08 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SEM_ENTRADA', 'person': 'NO_PERSON',
        'claim': 'GOL COM OFERTA; ZERO DE ENTRADA; R$ 299/MÊS; TODO REVISADO',
    },
    '6_193  BR_CAR__BR_28-08 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SEM_ENTRADA', 'person': 'PERSON',
        'claim': 'BYD DOLPHIN MINI SEMINOVO; R$ 399 NA PARCELA; SEM ENTRADA; ATÉ PARA NEGATIVADO',
    },
    '7_199  BR_CAR__BR_28-08 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SEM_ENTRADA', 'person': 'PERSON',
        'claim': 'MAIS DE 10 MIL CARROS; SEM ENTRADA; PARCELAS DE ATÉ R$ 499',
    },
    '8_200  BR_CAR__BR_28-08 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SEM_ENTRADA', 'person': 'PERSON',
        'claim': 'MAIS DE 10 MIL CARROS; SEM ENTRADA; PARCELAS DE ATÉ R$ 499',
    },
    '9_191  BR_CAR__BR_28-08 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SEM_ENTRADA', 'person': 'NO_PERSON',
        'claim': 'R$ 299 NA PARCELA; SEM ENTRADA',
    },
    '10_195  BR_CAR__BR_28-08 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SEM_ENTRADA', 'person': 'NO_PERSON',
        'claim': 'GOL COM OFERTA; ZERO DE ENTRADA; R$ 299/MÊS; TODO REVISADO',
    },
    '11_198  BR_CAR__BR_28-08 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SEM_ENTRADA', 'person': 'PERSON',
        'claim': 'MAIS DE 10 MIL CARROS; SEM ENTRADA; PARCELAS DE ATÉ R$ 499',
    },
    '12_197  BR_CAR__BR_28-08 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SEM_ENTRADA', 'person': 'NO_PERSON',
        'claim': 'GOL COM OFERTA; ZERO DE ENTRADA; R$ 299/MÊS; TODO REVISADO',
    },
    '13_190  BR_CAR__BR_28-08 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SCORE_BAIXO', 'person': 'PERSON',
        'claim': 'APROVADO MESMO NEGATIVADO; SEM ENTRADA; TANQUE CHEIO; IPVA PAGO; 1ª PARCELA R$ 299',
    },
    '14_206  BR_CAR__BR_28-08 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SEM_ENTRADA', 'person': 'NO_PERSON',
        'claim': 'OFERTA R$ 349/MÊS; SEM ENTRADA; ECONOMIA E TECNOLOGIA',
    },
    '15_204  BR_CAR__BR_28-08 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SCORE_BAIXO', 'person': 'NO_PERSON',
        'claim': 'APROVA NEGATIVADO; PARCELAS DE R$ 299',
    },
    '16_201  BR_CAR__BR_28-08 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SEM_ENTRADA', 'person': 'PERSON',
        'claim': 'MAIS DE 10 MIL CARROS; SEM ENTRADA; PARCELAS DE ATÉ R$ 499',
    },
    '17_194  BR_CAR__BR_28-08 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SEM_ENTRADA', 'person': 'PERSON',
        'claim': 'CARRO ELÉTRICO SEM ENTRADA; R$ 349/MÊS; ECONOMIA E TECNOLOGIA',
    },
    '18_189  BR_CAR__BR_28-08 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SCORE_BAIXO', 'person': 'PERSON',
        'claim': 'APROVADO MESMO NEGATIVADO; SEM ENTRADA; TANQUE CHEIO; IPVA PAGO; 1ª PARCELA R$ 299',
    },
    '19_208  BR_CAR__BR_28-08 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SEM_ENTRADA', 'person': 'NO_PERSON',
        'claim': 'OFERTA R$ 349/MÊS; SEM ENTRADA; ECONOMIA E TECNOLOGIA',
    },
    '20_207  BR_CAR__BR_28-08 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SEM_ENTRADA', 'person': 'NO_PERSON',
        'claim': 'OFERTA R$ 349/MÊS; SEM ENTRADA; ECONOMIA E TECNOLOGIA',
    },
    '21_203  BR_CAR__BR_28-08 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SCORE_BAIXO', 'person': 'NO_PERSON',
        'claim': 'APROVA NEGATIVADO; PARCELAS DE R$ 299',
    },
}

# Current batch classification from multi-frame visual review.
CLASSIFICATION = {
    '1_242 BR_CAR__BR_02-09 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SCORE_BAIXO', 'person': 'PERSON',
        'claim': 'APROVA NEGATIVADO; SEM ENTRADA; PARCELAS DE R$ 299',
    },
    '2_233  BR_CAR__BR_02-09 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SCORE_BAIXO', 'person': 'PERSON',
        'claim': 'APROVA NEGATIVADO; R$ 299/MÊS; SEM ENTRADA',
    },
    '3_244 BR_CAR__BR_02-09 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SCORE_BAIXO', 'person': 'PERSON',
        'claim': 'APROVA NEGATIVADO; PARCELAS DE R$ 299',
    },
    '4_245 BR_CAR__BR_02-09 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SEM_ENTRADA', 'person': 'PERSON',
        'claim': 'SEM ENTRADA; PARCELAS DE ATÉ R$ 499; PROCESSO ONLINE',
    },
    '5_243 BR_CAR__BR_02-09 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SCORE_BAIXO', 'person': 'PERSON',
        'claim': 'APROVA NEGATIVADO; PARCELAS DE R$ 299',
    },
    '6_240 BR_CAR__BR_02-09 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SCORE_BAIXO', 'person': 'PERSON',
        'claim': 'APROVA NEGATIVADO; R$ 299/MÊS; SEM ENTRADA',
    },
    '7_237 BR_CAR__BR_02-09 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SCORE_BAIXO', 'person': 'PERSON',
        'claim': 'APROVA NEGATIVADO; R$ 299/MÊS; SEM ENTRADA',
    },
    '8_251 BR_CAR__BR_02-09 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SEM_ENTRADA', 'person': 'PERSON',
        'claim': 'R$ 349/MÊS; SEM ENTRADA',
    },
    '9_235 BR_CAR__BR_02-09 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SCORE_BAIXO', 'person': 'PERSON',
        'claim': 'APROVA NEGATIVADO; R$ 299/MÊS; SEM ENTRADA',
    },
    '10_247 BR_CAR__BR_02-09 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SEM_ENTRADA', 'person': 'PERSON',
        'claim': 'SEM ENTRADA; PARCELAS DE ATÉ R$ 299; PROCESSO ONLINE',
    },
    '11_241 BR_CAR__BR_02-09 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SCORE_BAIXO', 'person': 'PERSON',
        'claim': 'APROVA NEGATIVADO; ENTRADA DE R$ 100; PARCELAS DE R$ 299',
    },
    '12_238 BR_CAR__BR_02-09 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SEM_ENTRADA', 'person': 'PERSON',
        'claim': 'OFERTA R$ 299/MÊS; SEM ENTRADA; APROVA NEGATIVADO',
    },
    '13_248 BR_CAR__BR_02-09 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SEM_ENTRADA', 'person': 'PERSON',
        'claim': 'SEM ENTRADA; PARCELAS DE ATÉ R$ 299; PROCESSO ONLINE',
    },
    '14_234  BR_CAR__BR_02-09 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SCORE_BAIXO', 'person': 'PERSON',
        'claim': 'APROVA NEGATIVADO; R$ 299/MÊS; SEM ENTRADA',
    },
    '15_236 BR_CAR__BR_02-09 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SCORE_BAIXO', 'person': 'PERSON',
        'claim': 'APROVA NEGATIVADO; R$ 299/MÊS; SEM ENTRADA',
    },
    '16_249 BR_CAR__BR_02-09 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'PARCELA_BAIXA', 'person': 'PERSON',
        'claim': 'BYD SEMINOVO; PARCELA DE R$ 399; ATÉ NEGATIVADO; SEM COMPROVANTE DE RENDA',
    },
    '17_246 BR_CAR__BR_02-09 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'SEM_ENTRADA', 'person': 'PERSON',
        'claim': 'SEM ENTRADA; PARCELAS DE ATÉ R$ 499; PROCESSO ONLINE',
    },
    '18_Cópia de 253 BR_CAR__BR_02-09 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'PARCELA_BAIXA', 'person': 'NO_PERSON',
        'claim': 'HB20 NOVO; PARCELA DE R$ 299; SEM ENTRADA',
    },
    '19_250 BR_CAR__BR_02-09 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'PARCELA_BAIXA', 'person': 'PERSON',
        'claim': 'PAGAMENTO DE R$ 349; ECONOMIA PARA A ROTINA DE VENDEDORES',
    },
    '20_253 BR_CAR__BR_02-09 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'PARCELA_BAIXA', 'person': 'NO_PERSON',
        'claim': 'HB20 NOVO; PARCELA DE R$ 299; SEM ENTRADA',
    },
    '21_252 BR_CAR__BR_02-09 - IA - Story (BRASIL).mp4': {
        'vehicle_type': 'CARRO', 'angle': 'PARCELA_BAIXA', 'person': 'PERSON',
        'claim': 'HB20 NOVO; PARCELA DE R$ 299; SEM ENTRADA',
    },
}

# Current batch classification from six contact sheets / 72 real frames.
CLASSIFICATION = {
    '1_39 BR_CAR__BR_ MOTO 03-09 - IA - Story (BRASIL)) .mp4': {
        'vehicle_type': 'MOTO', 'angle': 'SCORE_BAIXO', 'person': 'PERSON',
        'claim': 'APROVADO MESMO NEGATIVADO; SEM ENTRADA; PRIMEIRA PARCELA EM 120 DIAS; RETIRE HOJE',
    },
    '2_38 BR_CAR__BR_ MOTO 03-09 - IA - Story (BRASIL)) .mp4': {
        'vehicle_type': 'MOTO', 'angle': 'SCORE_BAIXO', 'person': 'PERSON',
        'claim': 'APROVADO MESMO NEGATIVADO; SEM ENTRADA; PRIMEIRA PARCELA EM 120 DIAS; RETIRE HOJE',
    },
    '3_40 BR_CAR__BR_ MOTO 03-09 - IA - Story (BRASIL)) .mp4': {
        'vehicle_type': 'MOTO', 'angle': 'SCORE_BAIXO', 'person': 'PERSON',
        'claim': 'APROVADO MESMO NEGATIVADO; SEM ENTRADA; PRIMEIRA PARCELA EM 120 DIAS; PARCELAS DE R$ 149',
    },
    '4_31 BR_CAR__BR_ MOTO 03-09 - IA - Story (BRASIL)) .mp4': {
        'vehicle_type': 'MOTO', 'angle': 'SEM_ENTRADA', 'person': 'PERSON',
        'claim': 'MAIS DE 10 MIL MOTOS; SEM ENTRADA; PARCELAS DE ATÉ R$ 199; TUDO ONLINE',
    },
    '5_30 BR_CAR__BR_ MOTO 03-09 - IA - Story (BRASIL)) .mp4': {
        'vehicle_type': 'MOTO', 'angle': 'SEM_ENTRADA', 'person': 'PERSON',
        'claim': 'MAIS DE 10 MIL MOTOS; SEM ENTRADA; TUDO ONLINE',
    },
    '6_52 BR_CAR__BR_ MOTO 03-09 - IA - Story (BRASIL)) .mp4': {
        'vehicle_type': 'MOTO', 'angle': 'SEM_ENTRADA', 'person': 'NO_PERSON',
        'claim': 'HONDA POR R$ 149 MENSAIS; SEM ENTRADA',
    },
    '7_48 BR_CAR__BR_ MOTO 03-09 - IA - Story (BRASIL)) .mp4': {
        'vehicle_type': 'MOTO', 'angle': 'SEM_ENTRADA', 'person': 'PERSON',
        'claim': 'HONDA POR R$ 149 MENSAIS; SEM ENTRADA; LINK PARA CONFERIR',
    },
    '8_29 BR_CAR__BR_ MOTO 03-09 - IA - Story (BRASIL)) .mp4': {
        'vehicle_type': 'MOTO', 'angle': 'SEM_ENTRADA', 'person': 'PERSON',
        'claim': 'MAIS DE 10 MIL MOTOS; SEM ENTRADA; TUDO ONLINE',
    },
    '9_42 BR_CAR__BR_ MOTO 03-09 - IA - Story (BRASIL)) .mp4': {
        'vehicle_type': 'MOTO', 'angle': 'SCORE_BAIXO', 'person': 'PERSON',
        'claim': 'APROVADO MESMO NEGATIVADO; SEM ENTRADA; PRIMEIRA PARCELA EM 120 DIAS; RETIRE HOJE',
    },
    '10_44 BR_CAR__BR_ MOTO 03-09 - IA - Story (BRASIL)) .mp4': {
        'vehicle_type': 'MOTO', 'angle': 'SCORE_BAIXO', 'person': 'PERSON',
        'claim': 'APROVADO MESMO NEGATIVADO; SEM ENTRADA; RETIRE HOJE',
    },
    '11_49 BR_CAR__BR_ MOTO 03-09 - IA - Story (BRASIL)) .mp4': {
        'vehicle_type': 'MOTO', 'angle': 'SEM_ENTRADA', 'person': 'PERSON',
        'claim': 'HONDA POR R$ 149 MENSAIS; SEM ENTRADA; LINK PARA CONFERIR',
    },
    '12_47 BR_CAR__BR_ MOTO 03-09 - IA - Story (BRASIL)) .mp4': {
        'vehicle_type': 'MOTO', 'angle': 'SEM_ENTRADA', 'person': 'PERSON',
        'claim': 'HONDA POR R$ 149 MENSAIS; SEM ENTRADA',
    },
    '13_33 BR_CAR__BR_ MOTO 03-09 - IA - Story (BRASIL)) .mp4': {
        'vehicle_type': 'MOTO', 'angle': 'SEM_ENTRADA', 'person': 'PERSON',
        'claim': 'MAIS DE 10 MIL MOTOS; SEM ENTRADA; PARCELAS DE ATÉ R$ 199; TUDO ONLINE',
    },
    '14_36 BR_CAR__BR_ MOTO 03-09 - IA - Story (BRASIL)) .mp4': {
        'vehicle_type': 'MOTO', 'angle': 'SCORE_BAIXO', 'person': 'PERSON',
        'claim': 'APROVADO MESMO NEGATIVADO; SEM ENTRADA; PRIMEIRA PARCELA EM 120 DIAS; RETIRE HOJE',
    },
    '15_51 BR_CAR__BR_ MOTO 03-09 - IA - Story (BRASIL)) .mp4': {
        'vehicle_type': 'MOTO', 'angle': 'SEM_ENTRADA', 'person': 'PERSON',
        'claim': 'HONDA POR R$ 149 MENSAIS; SEM ENTRADA',
    },
    '16_43 BR_CAR__BR_ MOTO 03-09 - IA - Story (BRASIL)) .mp4': {
        'vehicle_type': 'MOTO', 'angle': 'SCORE_BAIXO', 'person': 'PERSON',
        'claim': 'APROVADO MESMO NEGATIVADO; SEM ENTRADA; PARCELAS DE R$ 149; RETIRE HOJE',
    },
    '17_34 BR_CAR__BR_ MOTO 03-09 - IA - Story (BRASIL)) .mp4': {
        'vehicle_type': 'MOTO', 'angle': 'SCORE_BAIXO', 'person': 'PERSON',
        'claim': 'APROVADO MESMO NEGATIVADO; SEM ENTRADA; PRIMEIRA PARCELA EM 120 DIAS; PARCELAS DE R$ 149',
    },
    '18_32 BR_CAR__BR_ MOTO 03-09 - IA - Story (BRASIL)) .mp4': {
        'vehicle_type': 'MOTO', 'angle': 'SEM_ENTRADA', 'person': 'PERSON',
        'claim': 'MAIS DE 10 MIL MOTOS; SEM ENTRADA; TUDO ONLINE',
    },
    '19_46 BR_CAR__BR_ MOTO 03-09 - IA - Story (BRASIL)) .mp4': {
        'vehicle_type': 'MOTO', 'angle': 'SEM_ENTRADA', 'person': 'PERSON',
        'claim': 'HONDA POR R$ 149 MENSAIS; SEM ENTRADA',
    },
    '20_50 BR_CAR__BR_ MOTO 03-09 - IA - Story (BRASIL)) .mp4': {
        'vehicle_type': 'MOTO', 'angle': 'SEM_ENTRADA', 'person': 'PERSON',
        'claim': 'HONDA BIZ POR R$ 149 MENSAIS; SEM ENTRADA; LINK PARA CONFERIR',
    },
    '21_45 BR_CAR__BR_ MOTO 03-09 - IA - Story (BRASIL)) .mp4': {
        'vehicle_type': 'MOTO', 'angle': 'SEM_ENTRADA', 'person': 'PERSON',
        'claim': 'HONDA POR R$ 149 MENSAIS; SEM ENTRADA',
    },
    '22_35 BR_CAR__BR_ MOTO 03-09 - IA - Story (BRASIL)) .mp4': {
        'vehicle_type': 'MOTO', 'angle': 'SCORE_BAIXO', 'person': 'PERSON',
        'claim': 'APROVADO MESMO NEGATIVADO; SEM ENTRADA; PRIMEIRA PARCELA EM 120 DIAS; PARCELAS DE R$ 149; RETIRE HOJE',
    },
    '23_37 BR_CAR__BR_ MOTO 03-09 - IA - Story (BRASIL)) .mp4': {
        'vehicle_type': 'MOTO', 'angle': 'SCORE_BAIXO', 'person': 'PERSON',
        'claim': 'APROVADO MESMO NEGATIVADO; SEM ENTRADA; PRIMEIRA PARCELA EM 120 DIAS; RETIRE HOJE',
    },
    '24_41 BR_CAR__BR_ MOTO 03-09 - IA - Story (BRASIL)) .mp4': {
        'vehicle_type': 'MOTO', 'angle': 'SCORE_BAIXO', 'person': 'PERSON',
        'claim': 'APROVADO MESMO NEGATIVADO; SEM ENTRADA; PRIMEIRA PARCELA EM 120 DIAS; RETIRE HOJE',
    },
}


def utcnow() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def load_executor():
    spec = importlib.util.spec_from_file_location('ares_executor', EXECUTOR)
    if spec is None or spec.loader is None:
        raise RuntimeError('cannot load canonical Drive executor')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def jdump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, path)


def api_get(drive, file_id: str) -> dict[str, Any]:
    fields = 'id,name,mimeType,parents,driveId,size,md5Checksum,createdTime,modifiedTime,trashed,webViewLink,capabilities(canDownload,canEdit,canMoveItemWithinDrive,canModifyContent,canTrash,canDelete)'
    url = f'https://www.googleapis.com/drive/v3/files/{file_id}?' + urllib.parse.urlencode({'supportsAllDrives': 'true', 'fields': fields})
    return drive.request(url) or {}


def list_children(drive, parent_id: str) -> list[dict[str, Any]]:
    q = f"'{parent_id}' in parents and trashed=false"
    fields = 'files(id,name,mimeType,parents,driveId,size,md5Checksum,createdTime,modifiedTime,trashed,webViewLink)'
    url = 'https://www.googleapis.com/drive/v3/files?' + urllib.parse.urlencode({'q': q, 'supportsAllDrives': 'true', 'includeItemsFromAllDrives': 'true', 'pageSize': '1000', 'fields': fields, 'orderBy': 'name_natural'})
    return (drive.request(url) or {}).get('files', [])


def resolve_existing_path(drive, parts: list[str]) -> str:
    parent = ROOT_ID
    for name in parts:
        child = drive.find_child_folder(parent, name)
        if not child:
            raise RuntimeError(f'missing canonical folder: {name}')
        parent = child
    return parent


def move_file(drive, file_id: str, old_parent: str, new_parent: str) -> dict[str, Any]:
    params = {'supportsAllDrives': 'true', 'addParents': new_parent, 'removeParents': old_parent, 'fields': 'id,name,parents,driveId,trashed'}
    url = f'https://www.googleapis.com/drive/v3/files/{file_id}?' + urllib.parse.urlencode(params)
    return drive.request(url, method='PATCH', data=b'', headers={'Content-Type': 'application/json'}) or {}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def ffprobe(path: Path) -> dict[str, Any]:
    p = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,codec_name:format=duration', '-of', 'json', str(path)], capture_output=True, text=True, check=False, timeout=120)
    if p.returncode != 0:
        raise RuntimeError(f'ffprobe failed: {p.stderr[-300:]}')
    d = json.loads(p.stdout)
    if not d.get('streams'):
        raise RuntimeError('video has no visual stream')
    s = d['streams'][0]
    width, height = int(s['width']), int(s['height'])
    duration = float(d.get('format', {}).get('duration') or 0)
    if width != 1080 or height != 1920 or duration <= 0:
        raise RuntimeError(f'unexpected technical profile {width}x{height} duration={duration}')
    return {'width': width, 'height': height, 'duration': duration, 'codec': s.get('codec_name')}


def dhash(path: Path) -> str:
    with Image.open(path) as im:
        pixels = list(im.convert('L').resize((9, 8)).getdata())
    value = 0
    for y in range(8):
        for x in range(8):
            value = (value << 1) | int(pixels[y * 9 + x] > pixels[y * 9 + x + 1])
    return f'{value:016x}'


def fingerprint_video(path: Path, duration: float, frame_dir: Path, stem: str) -> str:
    frame_dir.mkdir(parents=True, exist_ok=True)
    hashes = []
    for i, frac in enumerate((0.2, 0.5, 0.8), 1):
        out = frame_dir / f'{stem}-{i}.jpg'
        p = subprocess.run(['ffmpeg', '-y', '-ss', f'{duration * frac:.3f}', '-i', str(path), '-frames:v', '1', '-q:v', '2', str(out)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=120)
        if p.returncode != 0 or not out.exists():
            raise RuntimeError('failed to extract fingerprint frame')
        hashes.append(dhash(out))
    return 'dhash64:' + '/'.join(hashes)


def clean_and_verify(raw: Path, out: Path) -> str:
    p = subprocess.run([str(SANITIZER), 'clean', str(raw), '--out', str(out), '--agent', 'ares'], capture_output=True, text=True, check=False, timeout=900)
    if p.returncode != 0:
        raise RuntimeError(f'sanitizer clean failed: {(p.stdout + p.stderr)[-500:]}')
    verify_clean(out)
    return sha256_file(out)


def verify_clean(path: Path) -> None:
    v = subprocess.run([str(SANITIZER), 'verify', str(path)], capture_output=True, text=True, check=False, timeout=300)
    if v.returncode != 0 or 'clean: true' not in v.stdout:
        raise RuntimeError(f'sanitizer verify failed: {(v.stdout + v.stderr)[-500:]}')


def load_inventory() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    by_source: dict[str, dict[str, Any]] = {}
    by_raw: dict[str, dict[str, Any]] = {}
    by_clean: dict[str, dict[str, Any]] = {}
    if INVENTORY.exists():
        for line in INVENTORY.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            rows.append(row)
            if row.get('source_drive_id'):
                by_source[row['source_drive_id']] = row
            if row.get('original_checksum'):
                by_raw[row['original_checksum']] = row
            if row.get('clean_checksum'):
                by_clean[row['clean_checksum']] = row
    return rows, by_source, by_raw, by_clean


def append_inventory(row: dict[str, Any]) -> None:
    INVENTORY.parent.mkdir(parents=True, exist_ok=True)
    lock_path = INVENTORY.with_suffix(INVENTORY.suffix + '.lock')
    with lock_path.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        existing = [json.loads(line) for line in INVENTORY.read_text(encoding='utf-8').splitlines() if line.strip()] if INVENTORY.exists() else []
        matches = [x for x in existing if x.get('source_drive_id') == row['source_drive_id']]
        if matches:
            if len(matches) != 1 or matches[0].get('asset_drive_id') != row.get('asset_drive_id'):
                raise RuntimeError('inventory source collision')
            return
        with INVENTORY.open('a', encoding='utf-8') as f:
            f.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
            f.flush()
            os.fsync(f.fileno())


def attach_duplicate_source(primary_source_id: str, duplicate_source_id: str, duplicate_filename: str) -> None:
    lock_path = INVENTORY.with_suffix(INVENTORY.suffix + '.lock')
    with lock_path.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        rows = [json.loads(line) for line in INVENTORY.read_text(encoding='utf-8').splitlines() if line.strip()]
        matched = 0
        for row in rows:
            if row.get('source_drive_id') != primary_source_id:
                continue
            matched += 1
            ids = list(row.get('duplicate_source_drive_ids') or [])
            if duplicate_source_id not in ids:
                ids.append(duplicate_source_id)
            row['duplicate_source_drive_ids'] = ids
            note = f' Fonte adicional {duplicate_filename} conciliada como duplicata exata após sanitização; nenhum candidato independente foi criado.'
            if note.strip() not in (row.get('notes') or ''):
                row['notes'] = (row.get('notes') or '') + note
        if matched != 1:
            raise RuntimeError(f'primary inventory row not uniquely found: {primary_source_id} matches={matched}')
        tmp = INVENTORY.with_suffix(INVENTORY.suffix + '.tmp')
        tmp.write_text(''.join(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n' for row in rows), encoding='utf-8')
        os.replace(tmp, INVENTORY)


def p_orient(person: str) -> str:
    return 'PV' if person == 'PERSON' else 'NV'


def canonical_group(cls: dict[str, str]) -> str:
    moto = '_MOTO' if cls['vehicle_type'] == 'MOTO' else ''
    return f"CAR_BR_BR_VID{moto}_{cls['angle']}_{p_orient(cls['person'])}"


def used_variants_for(group: str, live_ready: list[dict[str, Any]], inventory_rows: list[dict[str, Any]]) -> set[int]:
    rx = re.compile(r'^' + re.escape(group) + r'_(\d{3})\.mp4$')
    used: set[int] = set()
    for name in [x.get('name', '') for x in live_ready] + [x.get('canonical_filename', '') for x in inventory_rows]:
        m = rx.match(name or '')
        if m:
            used.add(int(m.group(1)))
    return used


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ['index','status','disposition','source_drive_id','source_filename','destination_drive_id','destination_filename','source_sha256','clean_sha256','drive_md5','bytes_clean','metadata_clean','drive_readback_verified','sha256_readback_verified','vehicle_type','person','p_orient','angle','variant','claim','perceptual_fingerprint','webViewLink']
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, '') for k in fields})


def exact_name_matches(drive, ready_id: str, name: str) -> list[dict[str, Any]]:
    return [x for x in list_children(drive, ready_id) if x.get('name') == name]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('inventory_csv')
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    input_rows = [r for r in csv.DictReader(open(args.inventory_csv, encoding='utf-8')) if r.get('format') == 'VID']
    if len(input_rows) != 24:
        raise RuntimeError(f'expected 24 videos, found {len(input_rows)}')
    if set(r['original_filename'] for r in input_rows) != set(CLASSIFICATION):
        missing = sorted(set(CLASSIFICATION) - set(r['original_filename'] for r in input_rows))
        extra = sorted(set(r['original_filename'] for r in input_rows) - set(CLASSIFICATION))
        raise RuntimeError(f'live batch filenames do not match visual review missing={missing} extra={extra}')

    batch_key = hashlib.sha256('|'.join(sorted(r['drive_id'] for r in input_rows)).encode()).hexdigest()[:20]
    lock_path = Path('/root/mgs-agent/tmp/ares-intake-locks') / f'car_br_br-{batch_key}.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ex = load_executor()
        ex.load_env()
        sa = ex.service_account()
        if sa.get('client_email') != EXPECTED_EMAIL or sa.get('project_id') != EXPECTED_PROJECT:
            raise RuntimeError('canonical service account identity validation failed')
        token, auth_mode = ex.build_access_token()
        if auth_mode != 'service_account':
            raise RuntimeError('non-service-account auth refused')
        drive = ex.Drive(token)
        root = drive.preflight_destination(auth_mode)
        if root.get('driveId') != ROOT_ID:
            raise RuntimeError('canonical Shared Drive root mismatch')
        shared = drive.request(f'https://www.googleapis.com/drive/v3/drives/{ROOT_ID}?fields=id,name') or {}
        if shared.get('name') != EXPECTED_DRIVE:
            raise RuntimeError('Shared Drive name mismatch')

        upload_id = resolve_existing_path(drive, ['CRIATIVOS', 'UPLOAD MANUAL'])
        ready_id = resolve_existing_path(drive, ['CRIATIVOS', OPERATION, 'VID', '01_READY'])
        legacy_id = resolve_existing_path(drive, ['CRIATIVOS', OPERATION, 'VID', '99_LEGACY'])
        expected_ids = {r['drive_id'] for r in input_rows}
        direct_upload = {x['id']: x for x in list_children(drive, upload_id) if x.get('mimeType') != FOLDER_MIME}
        unexpected = set(direct_upload) - expected_ids
        if unexpected:
            raise RuntimeError(f'fresh queue has {len(unexpected)} unexpected direct file(s)')

        live_meta: dict[str, dict[str, Any]] = {}
        for row in input_rows:
            live = api_get(drive, row['drive_id'])
            live_meta[row['drive_id']] = live
            caps = live.get('capabilities') or {}
            if live.get('driveId') != ROOT_ID or live.get('parents') not in ([upload_id], [legacy_id]):
                raise RuntimeError(f'source outside canonical upload/legacy parent: {row["original_filename"]}')
            if live.get('parents') == [upload_id] and (not caps.get('canDownload') or not caps.get('canMoveItemWithinDrive')):
                raise RuntimeError(f'missing required source capability: {row["original_filename"]}')
            if str(live.get('size')) != str(row['size_bytes']):
                raise RuntimeError(f'source size drift: {row["original_filename"]}')

        inventory_rows, by_source, by_raw, by_clean = load_inventory()
        state = {'generated_at_utc': utcnow(), 'operation': OPERATION, 'batch_key': batch_key, 'items': {}}
        if STATE_PATH.exists():
            state = json.loads(STATE_PATH.read_text(encoding='utf-8'))
            if state.get('batch_key') != batch_key:
                raise RuntimeError('state belongs to another batch')
        already_inventory = expected_ids.intersection(by_source)
        if already_inventory and not already_inventory.issubset(state.get('items', {})):
            raise RuntimeError(f'source IDs already inventoried outside resumable state: {len(already_inventory)}')

        live_ready = list_children(drive, ready_id)
        groups = {canonical_group(CLASSIFICATION[r['original_filename']]) for r in input_rows}
        used_by_group = {g: used_variants_for(g, live_ready, inventory_rows) for g in groups}
        next_by_group = {g: max(v, default=0) + 1 for g, v in used_by_group.items()}

        raws = WORK_DIR / 'raw'
        frames = WORK_DIR / 'frames'
        cleans = WORK_DIR / 'clean'
        readback = WORK_DIR / 'readback'
        for d in [raws, frames, cleans, readback]:
            d.mkdir(parents=True, exist_ok=True)

        plan: list[dict[str, Any]] = []
        batch_by_clean: dict[str, dict[str, Any]] = {}
        for idx, row in enumerate(input_rows, 1):
            raw = raws / f'{idx:02d}.mp4'
            if not raw.exists() or raw.stat().st_size != int(row['size_bytes']):
                drive.download(row['drive_id'], raw)
            raw_sha = sha256_file(raw)
            tech = ffprobe(raw)
            fp = fingerprint_video(raw, tech['duration'], frames, f'{idx:02d}')
            clean = cleans / f'{idx:02d}.mp4'
            if not clean.exists():
                clean_sha = clean_and_verify(raw, clean)
            else:
                verify_clean(clean)
                clean_sha = sha256_file(clean)
            cls = CLASSIFICATION[row['original_filename']]
            group = canonical_group(cls)
            porient = p_orient(cls['person'])
            disposition = 'UNIQUE_READY'
            primary_source_id = row['drive_id']
            destination_drive_id = None
            existing = by_clean.get(clean_sha)
            if existing:
                disposition = 'DUPLICATE_EXISTING'
                primary_source_id = existing['source_drive_id']
                destination_drive_id = existing.get('asset_drive_id')
                final_name = existing.get('canonical_filename')
                variant = existing.get('variant') or '000'
                if not destination_drive_id or not final_name:
                    raise RuntimeError('existing duplicate inventory row missing destination identity')
            elif clean_sha in batch_by_clean:
                primary = batch_by_clean[clean_sha]
                disposition = 'DUPLICATE_SOURCE'
                primary_source_id = primary['source_drive_id']
                final_name = primary['destination_filename']
                variant = primary['variant']
            else:
                variant_int = next_by_group[group]
                next_by_group[group] += 1
                variant = f'{variant_int:03d}'
                final_name = f'{group}_{variant}.mp4'
                if any(x.get('name') == final_name for x in live_ready):
                    raise RuntimeError(f'live READY collision: {final_name}')
            item = {
                'index': idx, 'source_drive_id': row['drive_id'], 'source_filename': row['original_filename'],
                'source_sha256': raw_sha, 'clean_sha256': clean_sha, 'raw_path': str(raw), 'clean_path': str(clean),
                'destination_filename': final_name, 'destination_drive_id': destination_drive_id, 'variant': str(variant),
                'disposition': disposition, 'primary_source_drive_id': primary_source_id,
                'vehicle_type': cls['vehicle_type'], 'claim': cls['claim'], 'angle': cls['angle'], 'person': cls['person'],
                'p_orient': porient, 'width': tech['width'], 'height': tech['height'], 'duration_seconds': tech['duration'],
                'codec': tech['codec'], 'perceptual_fingerprint': fp,
                'source_created_time': live_meta[row['drive_id']].get('createdTime'),
            }
            plan.append(item)
            if disposition == 'UNIQUE_READY':
                batch_by_clean[clean_sha] = item

        dry = {
            'generated_at_utc': utcnow(), 'mode': 'apply' if args.apply else 'dry-run', 'operation': OPERATION,
            'auth_mode': auth_mode, 'shared_drive_validated': True, 'source_count': len(plan),
            'unique_ready_assets': sum(x['disposition'] == 'UNIQUE_READY' for x in plan),
            'duplicate_sources': sum(x['disposition'] != 'UNIQUE_READY' for x in plan),
            'by_group': {},
            'plan': [{k: v for k, v in x.items() if k not in {'raw_path', 'clean_path'}} for x in plan],
        }
        for x in plan:
            dry['by_group'].setdefault(canonical_group(CLASSIFICATION[x['source_filename']]), {'unique': 0, 'duplicate': 0})
            dry['by_group'][canonical_group(CLASSIFICATION[x['source_filename']])]['unique' if x['disposition'] == 'UNIQUE_READY' else 'duplicate'] += 1
        jdump(DRY_PATH, dry)
        if not args.apply:
            print(json.dumps({'done': True, 'dry_run': str(DRY_PATH), 'source_count': len(plan), 'unique_ready_assets': dry['unique_ready_assets'], 'duplicate_sources': dry['duplicate_sources'], 'by_group': dry['by_group']}, ensure_ascii=False, indent=2))
            return 0

        backup_stamp = dt.datetime.now(dt.UTC).strftime('%Y%m%dT%H%M%SZ')
        backup_dir = Path('/root/mgs-agent/backups/ares-creative-ops')
        backup_dir.mkdir(parents=True, exist_ok=True)
        inventory_backup = backup_dir / f'assets-before-kelly-car-br-br-{backup_stamp}.jsonl'
        if INVENTORY.exists():
            shutil.copy2(INVENTORY, inventory_backup)
        else:
            inventory_backup.write_text('', encoding='utf-8')
        state.setdefault('items', {})
        jdump(STATE_PATH, state)

        results: list[dict[str, Any]] = []
        for item in plan:
            key = item['source_drive_id']
            st = state['items'].setdefault(key, {})
            print(json.dumps({'processing': item['index'], 'source_filename': item['source_filename'], 'destination_filename': item['destination_filename'], 'disposition': item['disposition']}), flush=True)
            clean = Path(item['clean_path'])
            verify_clean(clean)
            if sha256_file(clean) != item['clean_sha256']:
                raise RuntimeError(f'clean SHA drift: {item["source_filename"]}')

            if item['disposition'] == 'UNIQUE_READY':
                dest_id = st.get('destination_drive_id')
                if not dest_id:
                    existing_names = exact_name_matches(drive, ready_id, item['destination_filename'])
                    if len(existing_names) > 1:
                        raise RuntimeError(f'multiple READY files with planned name: {item["destination_filename"]}')
                    if existing_names:
                        candidate_id = existing_names[0]['id']
                        rb_candidate = readback / f'adopt-{item["index"]:02d}.mp4'
                        drive.download(candidate_id, rb_candidate)
                        if sha256_file(rb_candidate) != item['clean_sha256']:
                            raise RuntimeError(f'planned name occupied by different content: {item["destination_filename"]}')
                        verify_clean(rb_candidate)
                        dest_id = candidate_id
                    else:
                        dest_id = drive.upload_resumable(ready_id, item['destination_filename'], clean, mimetypes.guess_type(item['destination_filename'])[0] or 'video/mp4')
                    st.update({'destination_drive_id': dest_id, 'clean_sha256': item['clean_sha256'], 'bytes_clean': clean.stat().st_size, 'uploaded_at_utc': utcnow()})
                    jdump(STATE_PATH, state)
                dest_meta = api_get(drive, dest_id)
                if dest_meta.get('name') != item['destination_filename'] or dest_meta.get('parents') != [ready_id] or dest_meta.get('driveId') != ROOT_ID or dest_meta.get('trashed'):
                    raise RuntimeError(f'destination Drive readback failed: {item["destination_filename"]}')
                rb = readback / item['destination_filename']
                drive.download(dest_id, rb)
                if sha256_file(rb) != item['clean_sha256']:
                    raise RuntimeError(f'destination SHA-256 readback failed: {item["destination_filename"]}')
                verify_clean(rb)
                st['destination_verified'] = True
                jdump(STATE_PATH, state)

                source_meta = api_get(drive, key)
                if source_meta.get('parents') == [upload_id]:
                    move_file(drive, key, upload_id, legacy_id)
                source_after = api_get(drive, key)
                if source_after.get('parents') != [legacy_id] or source_after.get('driveId') != ROOT_ID or source_after.get('trashed'):
                    raise RuntimeError(f'LEGACY source readback failed: {item["source_filename"]}')
                st['legacy_verified'] = True
                jdump(STATE_PATH, state)

                asset_id = 'asset_' + hashlib.sha256((key + ':' + dest_id).encode()).hexdigest()[:20]
                inventory_row = {
                    'asset_id': asset_id, 'original_filename': item['source_filename'], 'canonical_filename': item['destination_filename'],
                    'source_manager': 'KELLY', 'requested_by': 'Kelly Nice', 'created_by': 'KELLY',
                    'vertical': 'CAR', 'vehicle_type': item['vehicle_type'], 'country': 'BR', 'language': 'BR',
                    'strategy': None, 'ad_account_id': None, 'source_drive_id': key, 'asset_drive_id': dest_id,
                    'original_checksum': item['source_sha256'], 'clean_checksum': item['clean_sha256'],
                    'perceptual_fingerprint': item['perceptual_fingerprint'], 'format': 'VID', 'angle': item['angle'],
                    'person': item['person'], 'orientation': 'VERTICAL', 'p_orient': item['p_orient'], 'variant': item['variant'],
                    'status': '01_READY', 'reservation_status': 'RESERVADO_PELO_GESTOR', 'ares_eligible': False,
                    'used_by': None, 'campaign_owner': 'Kelly', 'meta_ad_id': None, 'meta_creative_id': None,
                    'meta_image_hash': None, 'meta_video_id': None, 'effective_object_story_id': None,
                    'width': item['width'], 'height': item['height'], 'aspect_ratio': '9:16', 'placement_fit': 'STORY',
                    'metadata_clean': True, 'first_seen_at': item['source_created_time'] or utcnow(), 'last_reconciled_at': None,
                    'performance_label': 'UNKNOWN',
                    'notes': f"Upload humano tratado por Ares. Claim visual dominante: {item['claim']}. Original preservado em 99_LEGACY. Fail-closed até liberação/conciliação Meta × Drive.",
                    'source_path': 'MGS-AGENTS/CRIATIVOS/CAR_BR_BR/VID/99_LEGACY',
                    'asset_path': 'MGS-AGENTS/CRIATIVOS/CAR_BR_BR/VID/01_READY',
                    'webViewLink': dest_meta.get('webViewLink'), 'local_clean_path': None, 'thread_id': THREAD_ID,
                }
                append_inventory(inventory_row)
                st['inventory_verified'] = True
                jdump(STATE_PATH, state)
            else:
                if item['disposition'] == 'DUPLICATE_EXISTING':
                    dest_id = item['destination_drive_id']
                    primary_source_id = item['primary_source_drive_id']
                else:
                    primary_source_id = item['primary_source_drive_id']
                    primary_st = state['items'].get(primary_source_id) or {}
                    dest_id = primary_st.get('destination_drive_id')
                    if not dest_id or not primary_st.get('destination_verified') or not primary_st.get('inventory_verified'):
                        raise RuntimeError(f'duplicate primary not fully verified: {item["source_filename"]}')
                dest_meta = api_get(drive, dest_id)
                if dest_meta.get('parents') != [ready_id] or dest_meta.get('driveId') != ROOT_ID or dest_meta.get('trashed'):
                    raise RuntimeError(f'duplicate destination readback failed: {item["source_filename"]}')
                rb = readback / f'duplicate-{item["index"]:02d}.mp4'
                drive.download(dest_id, rb)
                if sha256_file(rb) != item['clean_sha256']:
                    raise RuntimeError(f'duplicate destination SHA mismatch: {item["source_filename"]}')
                verify_clean(rb)
                source_meta = api_get(drive, key)
                if source_meta.get('parents') == [upload_id]:
                    move_file(drive, key, upload_id, legacy_id)
                source_after = api_get(drive, key)
                if source_after.get('parents') != [legacy_id] or source_after.get('driveId') != ROOT_ID or source_after.get('trashed'):
                    raise RuntimeError(f'duplicate LEGACY readback failed: {item["source_filename"]}')
                attach_duplicate_source(primary_source_id, key, item['source_filename'])
                st.update({'destination_drive_id': dest_id, 'clean_sha256': item['clean_sha256'], 'bytes_clean': int(dest_meta.get('size') or 0), 'destination_verified': True, 'legacy_verified': True, 'inventory_verified': True})
                jdump(STATE_PATH, state)

            dest_meta = api_get(drive, dest_id)
            results.append({
                'index': item['index'], 'status': '01_READY', 'disposition': item['disposition'],
                'source_drive_id': key, 'source_filename': item['source_filename'], 'destination_drive_id': dest_id,
                'destination_filename': dest_meta.get('name') or item['destination_filename'], 'source_sha256': item['source_sha256'],
                'clean_sha256': item['clean_sha256'], 'drive_md5': dest_meta.get('md5Checksum'),
                'bytes_clean': int(dest_meta.get('size') or 0), 'metadata_clean': True, 'drive_readback_verified': True,
                'sha256_readback_verified': True, 'vehicle_type': item['vehicle_type'], 'person': item['person'],
                'p_orient': item['p_orient'], 'angle': item['angle'], 'variant': item['variant'], 'claim': item['claim'],
                'perceptual_fingerprint': item['perceptual_fingerprint'], 'webViewLink': dest_meta.get('webViewLink'),
            })

        remaining_direct = [x for x in list_children(drive, upload_id) if x.get('mimeType') != FOLDER_MIME]
        if remaining_direct:
            raise RuntimeError(f'UPLOAD MANUAL still contains {len(remaining_direct)} direct file item(s)')
        ready_live = {x['id']: x for x in list_children(drive, ready_id)}
        legacy_live = {x['id']: x for x in list_children(drive, legacy_id)}
        final_rows, final_by_source, _, _ = load_inventory()
        duplicate_ids = {d for row in final_rows for d in (row.get('duplicate_source_drive_ids') or [])}
        unique_dest_ids = {r['destination_drive_id'] for r in results}
        for r in results:
            if r['destination_drive_id'] not in ready_live or r['source_drive_id'] not in legacy_live:
                raise RuntimeError('final Drive reconciliation failed')
            if r['disposition'] == 'UNIQUE_READY' and r['source_drive_id'] not in final_by_source:
                raise RuntimeError('final primary inventory reconciliation failed')
            if r['disposition'] != 'UNIQUE_READY' and r['source_drive_id'] not in duplicate_ids:
                raise RuntimeError('final duplicate inventory reconciliation failed')

        stamp = dt.datetime.now(dt.UTC).strftime('%Y%m%dT%H%M%SZ')
        csv_path = REPORT_DIR / f'ready-execution-{stamp}.csv'
        manifest_path = REPORT_DIR / f'ready-execution-{stamp}.json'
        latest_path = REPORT_DIR / 'ready-execution-latest.json'
        write_csv(csv_path, results)
        unique_results = [r for r in results if r['disposition'] == 'UNIQUE_READY']
        duplicate_results = [r for r in results if r['disposition'] != 'UNIQUE_READY']
        manifest = {
            'generated_at_utc': utcnow(), 'operation': OPERATION, 'requested_by': 'Kelly Nice', 'thread_id': THREAD_ID,
            'source_lineages': len(results), 'unique_ready_assets': len(unique_results), 'duplicate_sources': len(duplicate_results),
            'metadata_clean_verified': len(unique_dest_ids), 'raw_legacy_verified': len(results), 'upload_manual_remaining_files': 0,
            'reservation_status': 'RESERVADO_PELO_GESTOR', 'ares_eligible': False, 'inventory_backup': str(inventory_backup),
            'ready_parent_id': ready_id, 'legacy_parent_id': legacy_id, 'report_csv': str(csv_path),
            'items': [{
                'source_filename': r['source_filename'], 'destination_filename': r['destination_filename'],
                'disposition': r['disposition'], 'vehicle_type': r['vehicle_type'], 'claim': r['claim'],
                'angle': r['angle'], 'person': r['person'], 'p_orient': r['p_orient'],
            } for r in results],
        }
        jdump(manifest_path, manifest)
        jdump(latest_path, manifest)

        verification = {
            'all_pass': True, 'auth_mode': auth_mode, 'shared_drive': shared.get('name'),
            'source_lineages': len(results), 'unique_ready_assets': len(unique_dest_ids),
            'ready_destinations_downloaded_sha_verified_clean': len(unique_dest_ids),
            'legacy_sources_verified': len(results), 'inventory_primary_rows_verified': len(unique_results),
            'inventory_duplicate_links_verified': len(duplicate_results), 'reservation_fail_closed_verified': len(unique_results),
            'upload_manual_remaining_files': 0,
            'items': [{'source_filename': r['source_filename'], 'destination_filename': r['destination_filename'], 'verified': True} for r in results],
        }
        jdump(REPORT_DIR / 'independent-verification.json', verification)
        if WORK_DIR.exists():
            shutil.rmtree(WORK_DIR)
        print(json.dumps({'done': True, 'source_lineages': len(results), 'unique_ready_assets': len(unique_results), 'duplicate_sources': len(duplicate_results), 'upload_manual_remaining_files': 0, 'report_csv': str(csv_path), 'manifest': str(manifest_path)}, ensure_ascii=False, indent=2))
        return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({'done': False, 'error': str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise
