# Ares Meta Library Collector

Runtime permanente para abrir URLs públicas da Meta/Facebook Ads Library com Chromium/Playwright, preservar o perfil do navegador e baixar mídia para validação.

## Caminhos canônicos

- Runtime: `/root/mgs-agent/tools/meta-library-collector/`
- Wrapper: `/root/mgs-agent/scripts/ares-meta-library-collector.sh`
- Perfil persistente: `/root/.hermes/profiles/ares/browser-profiles/meta-library-chromium/`
- Saídas: `/root/.hermes/profiles/ares/artifacts/meta-library/<timestamp>/`

O perfil pode conter cookies/sessão. Nunca versione, anexe ou imprima valores de cookies. O coletor reporta somente contagem e presença dos nomes `c_user`/`xs`.

O wrapper aplica lock exclusivo ao perfil; uma segunda execução simultânea termina com exit `75`. O coletor exige pelo menos três `Library ID`, mídia real, MIME/magic-byte válido e download HTTP 2xx para considerar uma coleta bem-sucedida. O status HTTP inicial isolado não define sucesso.

## Uso

```bash
/root/mgs-agent/scripts/ares-meta-library-collector.sh \
  --url 'https://www.facebook.com/ads/library/?...' \
  --download 1
```

O status HTTP inicial pode ser `403` enquanto o challenge da Meta executa no browser. A validação real é DOM com `Library ID`/mídia e download HTTP 200 dentro do mesmo contexto.
