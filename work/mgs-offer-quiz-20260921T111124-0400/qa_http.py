#!/usr/bin/env python3
import hashlib
import json
import re

import requests

base = "https://dicasfinancas.info"
rows = []
for number in range(1, 7):
    manager = f"G{number:03d}"
    slug = f"quiz-v1-g{number:03d}"
    url = f"{base}/quiz/{slug}/"
    response = requests.get(
        url, timeout=30, headers={"User-Agent": "MGS-Zeus-Quiz-QA/1.0"}
    )
    text = response.text
    rows.append(
        {
            "manager": manager,
            "url": url,
            "status": response.status_code,
            "bytes": len(response.content),
            "sha256": hashlib.sha256(response.content).hexdigest(),
            "marker": text.count("MGS Offer Quiz static"),
            "manager_marker": text.count(f'data-manager="{manager}"'),
            "target_count": text.count(
                base + "/rec-br-cc-br-cartao-de-credito-superdigital/"
            ),
            "forms_inputs": len(re.findall(r"<(?:form|input)\b", text, re.I)),
            "mixed_http": len(re.findall(r'(?:src|href)="http://', text, re.I)),
            "noindex": "noindex,follow" in text,
        }
    )
unknown = requests.get(
    base + "/quiz/quiz-v1-g007/",
    timeout=30,
    headers={"User-Agent": "MGS-Zeus-Quiz-QA/1.0"},
)
print(
    json.dumps(
        {
            "routes": rows,
            "unknown": {
                "status": unknown.status_code,
                "marker": unknown.text.count("MGS Offer Quiz static"),
            },
        },
        ensure_ascii=False,
        indent=2,
    )
)
