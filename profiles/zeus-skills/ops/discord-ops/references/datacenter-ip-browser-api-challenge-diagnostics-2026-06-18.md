# Diagnóstico: challenges por IP de datacenter em fluxos MGS

## Quando usar

Use esta referência quando Rodolfo suspeitar que Hetzner/VPS/datacenter IP está causando bloqueios em:

- YouTube/Shorts/referências visuais para agente legado.
- Meta/Ads Manager/Marketing API para Ares.
- Browser automation que funciona no navegador humano/residencial, mas falha no VPS.

## Padrão observado

### agente legado / YouTube Shorts

Sinal forte de reputação de IP/datacenter:

- O link abre para Rodolfo em guia anônima/residencial.
- No Chromium/Playwright/yt-dlp do VPS, o YouTube carrega a página mas bloqueia o player com `Sign in to confirm you’re not a bot`.
- O objeto `<video>` não recebe stream (`currentSrc` vazio, `duration=null`, `readyState=0`).

Leitura operacional: proxy/browser com IP residencial ou sessão persistente é o caminho correto. Não pedir cookies a cada vídeo; se cookies forem usados, devem ser persistentes e tratados como segredo.

### Ares / Meta Marketing API

Não concluir automaticamente que é Hetzner quando a API falha em apenas uma camada.

Padrão observado:

- API cria `campaign`, `adset` e `adcreative` com sucesso.
- Bloqueia especificamente `POST /ads` com `code=31 / subcode=3858385` (`Autentica tu cuenta`).
- Manualmente, a mesma conta consegue duplicar/publicar via AdsPower com proxy.
- Token novo pode continuar falhando se o problema estiver em app/token/API trust ou endpoint específico.

Leitura operacional: Hetzner/IP pode contribuir, mas o teste conclusivo é rodar a mesma payload/token por um IP residencial/AdsPower antes de recomendar migração de VPS ou mudança de arquitetura.

## Teste de isolamento recomendado

Objetivo: mudar apenas a origem de rede, mantendo token, payload, conta e script iguais.

Fluxo atual:

```text
Ares/VPS Hetzner → graph.facebook.com → POST /ads bloqueia
```

Fluxo comparativo:

```text
Ares/VPS → proxy residencial do perfil AdsPower/Marcos → graph.facebook.com → mesmo POST /ads
```

Interpretação:

```text
Resultado pelo proxy                     | Conclusão
---------------------------------------- | ---------------------------------------------
POST /ads passa                          | origem/IP/reputação da VPS era fator crítico
POST /ads falha igual                    | causa provável é app/token/API trust/endpoint
Leitura Meta falha antes do write        | proxy inválido, bloqueado ou mal configurado
```

## Passo a passo seguro

1. Pedir ao Rodolfo para salvar o proxy do perfil AdsPower em 1Password, não colar no Discord.
2. Campos mínimos: `protocol`, `host`, `port`, `username`, `password`.
3. Validar primeiro só IP de saída, sem tocar na Meta:
   - sem proxy: IP Hetzner;
   - com proxy: IP do perfil AdsPower/residencial.
4. Rodar leitura/dry-run Meta com `HTTPS_PROXY`/`HTTP_PROXY` carregados internamente.
5. Antes de qualquer write real, reportar o dry-run e pedir confirmação.
6. Rodar o mesmo script/payload que falhou, mudando apenas env de proxy.
7. Reportar resultado com evidência de etapa e cleanup.

Exemplo de forma, sem imprimir segredo:

```bash
HTTPS_PROXY="http://user:pass@host:port" \
HTTP_PROXY="http://user:pass@host:port" \
python3 /root/mgs-agent/scripts/ares-meta-replacement-clone.py \
  --loser-campaign-id 120248290564280604 \
  --daily-budget-usd 25 \
  --creative-count 3
```

## Guardrails

- Nunca imprimir proxy password, token Meta, cookies ou headers.
- Não chamar System User se Rodolfo já descartou essa rota.
- Não mover VPS como primeira resposta; isolar tráfego sensível via proxy/browser backend antes.
- Se o teste real criar objetos parciais, cleanup e verificação GET são parte obrigatória do resultado.
- Para operações Meta write, parar após dry-run/leitura e pedir confirmação explícita antes de executar.
