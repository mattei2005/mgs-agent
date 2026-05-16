#!/usr/bin/env python3
"""
generate-rec-api.py — API REST isolada pra geração de RECs (Recommendation articles).

Endpoint: POST /generate
Input:    {site, card_slug, card_name, card_official_url?, overrides?}
Output:   {article_html, post_metadata, cost_usd, duration_sec, tokens_used}

Arquitetura:
- Recebe pedido HTTP de Atena
- Consulta cache (card-cache.db) → puxa dados se HIT
- Se MISS, retorna instrução pra Atena pesquisar (não pesquisa por conta)
- Carrega template do REC
- 1 chamada Anthropic Sonnet com prompt MINI + dados do cartão
- Retorna HTML pronto + metadata
- Loga tudo (custo, tempo, tokens)

Por que isolada da Atena:
- Sem agent loop (60+ tools = 35K tokens overhead por turn)
- Prompt MINI (~2K tokens) vs prompt agent (~35K)
- Cache automático Anthropic entre chamadas (~30% economia)
- 1 call Sonnet vs 60+ calls

Custo esperado: $0.10-0.20/REC (vs $3.16 do agent atual)
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import anthropic
import sqlite3
import json
import time
import os
import logging
from datetime import datetime, timezone
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────

API_PORT = 8001
CACHE_DB = "/root/mgs-agent/data/card-cache.db"
SITES_JSON = "/root/mgs-agent/data/sites.json"
TEMPLATES_DIR = "/root/mgs-agent/skills/content-generate-rec/templates"
LOGS_DIR = "/root/mgs-agent/api/logs"
USAGE_DB = "/root/mgs-agent/api/usage.db"

# Anthropic config
def _load_anthropic_api_key():
    """Load ANTHROPIC_API_KEY with fail-fast validation.

    Order:
    1. Environment variable (set by systemd EnvironmentFile)
    2. Parse from /root/.hermes/profiles/atena/.env

    Raises RuntimeError with clear message if not found or invalid.
    """
    # 1. Env var (preferred, set by systemd EnvironmentFile)
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip().strip('"').strip("'")
    if key.startswith("sk-ant-"):
        return key

    # 2. Fallback: parse .env file directly
    env_path = "/root/.hermes/profiles/atena/.env"
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("ANTHROPIC_API_KEY="):
                    parsed = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if parsed.startswith("sk-ant-"):
                        return parsed
    except FileNotFoundError:
        raise RuntimeError(
            f"ANTHROPIC_API_KEY not in env and .env not found at {env_path}"
        )

    # Both methods failed — fail fast at startup, not on first request
    raise RuntimeError(
        "ANTHROPIC_API_KEY not found or invalid. "
        "Expected env var or 'ANTHROPIC_API_KEY=sk-ant-...' line in "
        "/root/.hermes/profiles/atena/.env"
    )

ANTHROPIC_API_KEY = _load_anthropic_api_key()

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4000  # artigo final ~3500 tokens (HTML 450-500 palavras)

# Pricing (USD per million tokens)
# ⚠️  SINGLE SOURCE OF TRUTH: skills/content-generate-rec/references/pricing.md
# Se atualizar aqui, atualizar TAMBÉM em scripts/track-article-cost.sh + SKILL.md
PRICE_INPUT = 3.00
PRICE_OUTPUT = 15.00
PRICE_CACHE_READ = 0.30
PRICE_CACHE_WRITE = 3.75

# ─────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────

Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(f"{LOGS_DIR}/api.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("mgs-rec-api")

# ─────────────────────────────────────────────────────────────
# USAGE DB (tracking)
# ─────────────────────────────────────────────────────────────

def init_usage_db():
    conn = sqlite3.connect(USAGE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            site TEXT,
            card_slug TEXT,
            cache_hit BOOLEAN,
            input_tokens INTEGER,
            output_tokens INTEGER,
            cache_read_tokens INTEGER,
            cache_write_tokens INTEGER,
            cost_usd REAL,
            duration_sec REAL,
            success BOOLEAN,
            error_msg TEXT
        )
    """)
    conn.commit()
    conn.close()

init_usage_db()

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def calculate_cost(usage) -> float:
    """Calcula custo USD a partir de Anthropic usage object."""
    input_tok = usage.input_tokens or 0
    output_tok = usage.output_tokens or 0
    cache_read = getattr(usage, 'cache_read_input_tokens', 0) or 0
    cache_write = getattr(usage, 'cache_creation_input_tokens', 0) or 0
    
    cost = (
        input_tok * PRICE_INPUT / 1_000_000 +
        output_tok * PRICE_OUTPUT / 1_000_000 +
        cache_read * PRICE_CACHE_READ / 1_000_000 +
        cache_write * PRICE_CACHE_WRITE / 1_000_000
    )
    return round(cost, 6)


def lookup_cache(card_slug: str) -> Optional[Dict[str, Any]]:
    """Consulta card-cache.db. Retorna dict se HIT (válido), None se MISS."""
    conn = sqlite3.connect(CACHE_DB)
    conn.row_factory = sqlite3.Row
    
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
    cur = conn.execute("""
        SELECT * FROM card_cache 
        WHERE card_slug = ?
          AND (expires_at IS NULL OR expires_at > ?)
    """, (card_slug, now))
    
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    
    # Atualizar usage
    conn.execute("""
        UPDATE card_cache 
        SET usage_count = usage_count + 1, last_used_at = ?
        WHERE card_slug = ?
    """, (now, card_slug))
    
    # Log access
    conn.execute("""
        INSERT INTO cache_access_log (card_slug, accessed_at, hit, site, notes)
        VALUES (?, ?, 1, 'rec-api', 'lookup HIT via API')
    """, (card_slug, now))
    
    conn.commit()
    conn.close()
    
    data = dict(row)
    # Parse JSON fields
    if data.get('benefits_json'):
        data['benefits'] = json.loads(data['benefits_json'])
    if data.get('competitors_json'):
        data['competitors'] = json.loads(data['competitors_json'])
    
    return data


def load_template(template_key: str) -> str:
    """Carrega template REC do disco."""
    path = f"{TEMPLATES_DIR}/rec-{template_key}.md"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Template not found: {template_key}")
    with open(path) as f:
        return f.read()


def load_site_config(site_key: str) -> Dict[str, Any]:
    """Carrega config de site de sites.json."""
    with open(SITES_JSON) as f:
        sites = json.load(f)
    
    if isinstance(sites, dict):
        site = sites.get(site_key)
    elif isinstance(sites, list):
        site = next((s for s in sites if s.get('site_key') == site_key or s.get('key') == site_key), None)
    else:
        site = None
    
    if not site:
        raise HTTPException(status_code=404, detail=f"Site not found: {site_key}")
    return site


def log_usage(payload: Dict[str, Any]):
    """Persiste call no usage.db."""
    conn = sqlite3.connect(USAGE_DB)
    conn.execute("""
        INSERT INTO api_calls (
            timestamp, endpoint, site, card_slug, cache_hit,
            input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
            cost_usd, duration_sec, success, error_msg
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        payload.get('timestamp'),
        payload.get('endpoint'),
        payload.get('site'),
        payload.get('card_slug'),
        payload.get('cache_hit'),
        payload.get('input_tokens'),
        payload.get('output_tokens'),
        payload.get('cache_read_tokens'),
        payload.get('cache_write_tokens'),
        payload.get('cost_usd'),
        payload.get('duration_sec'),
        payload.get('success'),
        payload.get('error_msg')
    ))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="MGS REC Generator API",
    description="API isolada pra geração de RECs (Recommendation articles)",
    version="0.1.0"
)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# ─────────────────────────────────────────────────────────────
# REQUEST/RESPONSE MODELS
# ─────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    site: str
    card_slug: str
    card_name: str
    card_official_url: Optional[str] = None
    # Overrides opcionais (se não tiver no cache)
    annual_fee: Optional[str] = None
    apr: Optional[str] = None
    benefits: Optional[List[str]] = None
    competitors: Optional[List[Dict[str, str]]] = None


class GenerateResponse(BaseModel):
    success: bool
    article_html: Optional[str] = None
    cache_hit: bool
    cost_usd: float
    duration_sec: float
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    card_data: Dict[str, Any]
    error: Optional[str] = None


# ─────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "service": "MGS REC Generator API",
        "version": "0.1.0",
        "endpoints": ["/health", "/generate", "/stats"]
    }


@app.get("/health")
def health():
    """Health check + validação de dependências."""
    checks = {"api": True, "cache_db": False, "templates": False}
    
    if os.path.exists(CACHE_DB):
        checks["cache_db"] = True
    if os.path.isdir(TEMPLATES_DIR):
        checks["templates"] = True
    
    all_ok = all(checks.values())
    return {"status": "ok" if all_ok else "degraded", "checks": checks}


@app.get("/stats")
def stats():
    """Estatísticas de uso da API."""
    conn = sqlite3.connect(USAGE_DB)
    conn.row_factory = sqlite3.Row
    
    cur = conn.execute("""
        SELECT 
            COUNT(*) AS total_calls,
            SUM(success) AS successful_calls,
            SUM(cache_hit) AS cache_hits,
            ROUND(SUM(cost_usd), 4) AS total_cost_usd,
            ROUND(AVG(cost_usd), 4) AS avg_cost_usd,
            ROUND(AVG(duration_sec), 2) AS avg_duration_sec,
            SUM(input_tokens) AS total_input_tokens,
            SUM(output_tokens) AS total_output_tokens
        FROM api_calls
        WHERE timestamp > datetime('now', '-7 days')
    """)
    last_7d = dict(cur.fetchone())
    
    cur = conn.execute("""
        SELECT timestamp, site, card_slug, cache_hit, cost_usd, duration_sec
        FROM api_calls
        ORDER BY id DESC LIMIT 10
    """)
    last_calls = [dict(r) for r in cur.fetchall()]
    conn.close()
    
    return {
        "last_7_days": last_7d,
        "last_10_calls": last_calls
    }


@app.post("/generate", response_model=GenerateResponse)
def generate_rec(req: GenerateRequest):
    """
    Gera artigo REC.
    
    Flow:
    1. Lookup cache pelo card_slug
    2. Se HIT: usa dados cacheados
    3. Se MISS: usa dados do request (Atena já pesquisou)
    4. Carrega template + site config
    5. Monta prompt MINI
    6. 1 chamada Sonnet
    7. Retorna HTML + metadata
    """
    start = time.time()
    timestamp = datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
    
    log.info(f"Generate request: site={req.site} card_slug={req.card_slug}")
    
    try:
        # 1. Lookup cache
        cache_data = lookup_cache(req.card_slug)
        cache_hit = cache_data is not None
        
        # 2. Resolve dados do cartão (cache HIT > request override > MISS error)
        if cache_hit:
            card_data = {
                "card_name": cache_data['card_name'],
                "card_official_url": cache_data.get('card_official_url') or req.card_official_url,
                "annual_fee": cache_data.get('annual_fee'),
                "apr": cache_data.get('apr'),
                "benefits": cache_data.get('benefits', []),
                "competitors": cache_data.get('competitors', []),
                "tag10": cache_data.get('tag10'),
                "tag2": cache_data.get('tag2'),
                "descriptor": cache_data.get('descriptor'),
            }
            log.info(f"Cache HIT for {req.card_slug}")
        else:
            # MISS: usar dados do request (Atena tem que ter pesquisado antes)
            if not req.benefits or not req.annual_fee:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cache MISS for {req.card_slug} and request lacks card data. "
                           f"Atena must research card first via browser, then send full data."
                )
            card_data = {
                "card_name": req.card_name,
                "card_official_url": req.card_official_url,
                "annual_fee": req.annual_fee,
                "apr": req.apr,
                "benefits": req.benefits,
                "competitors": req.competitors or [],
            }
            log.info(f"Cache MISS for {req.card_slug}, using request data")
        
        # 3. Carregar site config + template
        site_config = load_site_config(req.site)
        template_key = site_config.get('template_key', 'gb-cc-en')
        template = load_template(template_key)
        
        # 4. Montar prompt MINI
        system_prompt = """You are a credit card content writer. Generate a REC (Recommendation) article in HTML/Gutenberg format following the EXACT template provided. Output ONLY the article HTML body. Target 465-475 visible words. Hard range 450-500 visible words. Count table text; exclude LazyBlock placeholders. No commentary, no markdown wrapping."""
        
        user_prompt = f"""# CARD DATA

card_name: {card_data['card_name']}
card_official_url: {card_data.get('card_official_url', 'N/A')}
annual_fee: {card_data.get('annual_fee', 'N/A')}
apr: {card_data.get('apr', 'N/A')}

benefits:
{json.dumps(card_data.get('benefits', []), indent=2, ensure_ascii=False)}

competitors:
{json.dumps(card_data.get('competitors', []), indent=2, ensure_ascii=False)}

# SITE CONFIG

site: {req.site}
domain: {site_config.get('domain', 'N/A')}
country: {site_config.get('country', 'gb')}
language: {site_config.get('language', 'en')}
default_category: {site_config.get('default_category', 'Credit Card')}

# TEMPLATE TO FOLLOW (STRICT)

{template}

# OUTPUT REQUIREMENTS

Generate ONLY the article body in Gutenberg HTML format. 450-500 words HARD LIMIT.

Structure:
1. <!-- wp:paragraph --> First paragraph with <strong>{card_data['card_name']}</strong>
2. (LazyBlock credit-card placeholder — Atena will replace)
3. Introduction paragraphs
4. <!-- wp:heading --> Key Benefits of the Card
5. <!-- wp:heading --> How Does It Work
6. <!-- wp:heading --> Comparative Table (with native wp:table)
7. <!-- wp:heading --> Who Is This Card Best For
8. (LazyBlock botao placeholder — Atena will replace)

Output the HTML now. No preamble."""
        
        # 5. Chamada Anthropic
        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"}  # Cache system prompt
                }
            ],
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        article_html = message.content[0].text
        
        # 6. Calcular custo
        cost = calculate_cost(message.usage)
        duration = time.time() - start
        
        log.info(f"Generated REC for {req.card_slug}: ${cost:.4f} in {duration:.1f}s")
        
        # 7. Log usage
        log_usage({
            'timestamp': timestamp,
            'endpoint': '/generate',
            'site': req.site,
            'card_slug': req.card_slug,
            'cache_hit': cache_hit,
            'input_tokens': message.usage.input_tokens or 0,
            'output_tokens': message.usage.output_tokens or 0,
            'cache_read_tokens': getattr(message.usage, 'cache_read_input_tokens', 0) or 0,
            'cache_write_tokens': getattr(message.usage, 'cache_creation_input_tokens', 0) or 0,
            'cost_usd': cost,
            'duration_sec': duration,
            'success': True,
            'error_msg': None
        })
        
        return GenerateResponse(
            success=True,
            article_html=article_html,
            cache_hit=cache_hit,
            cost_usd=cost,
            duration_sec=duration,
            input_tokens=message.usage.input_tokens or 0,
            output_tokens=message.usage.output_tokens or 0,
            cache_read_tokens=getattr(message.usage, 'cache_read_input_tokens', 0) or 0,
            cache_write_tokens=getattr(message.usage, 'cache_creation_input_tokens', 0) or 0,
            card_data=card_data
        )
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Generate failed for {req.card_slug}: {e}")
        log_usage({
            'timestamp': timestamp,
            'endpoint': '/generate',
            'site': req.site,
            'card_slug': req.card_slug,
            'cache_hit': False,
            'input_tokens': 0, 'output_tokens': 0,
            'cache_read_tokens': 0, 'cache_write_tokens': 0,
            'cost_usd': 0,
            'duration_sec': time.time() - start,
            'success': False,
            'error_msg': str(e)[:500]
        })
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    log.info(f"Starting MGS REC API on port {API_PORT}")
    uvicorn.run(app, host="127.0.0.1", port=API_PORT, log_level="info")
