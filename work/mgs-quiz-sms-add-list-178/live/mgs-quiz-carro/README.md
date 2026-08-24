# MGS Quiz Carro — Plugin WordPress (v1.1.1)

Plugin autônomo para captação de leads de crédito veicular, com integração SMS Funnel.
Não depende de Lovable / Supabase / serviços externos além do SMS Funnel.

## Recursos

- Rewrite automático: `/quiz-car-parcelas/`, `/quiz-car-parcelas/`, ..., `/quiz-car-parcelas-g006/` (qualquer slug iniciando com `quiz-`).
- Shortcode: `[mgs_quiz slug="quiz-car-parcelas-g002"]` (carrega CSS, JS e injeta `window.MGS_QUIZ_REST` + `window.MGS_QUIZ_CFG`).
- Painel admin: criar / editar / listar quizzes, listar leads, exportar leads CSV, importar `quiz_config.csv`.
- REST: `GET /wp-json/mgs-quiz/v1/config?slug=...`, `POST /wp-json/mgs-quiz/v1/lead`.
- SMS Funnel: envio server-side somente com `name` e `phone`, roteamento por gestor (`G001`...`G006`) e opção `require_sms_success` ativa por padrão.
- Anti-spam: honeypot invisível + tempo mínimo de preenchimento (3s).
- Frontend: máscara de telefone, redirect ponderado, preservação total de UTMs / `fbclid` / `gclid`, eventos `fbq` e `dataLayer` disparados apenas após sucesso real. **Só redireciona se o servidor confirmar `ok: true`.**

## Requisitos

- WordPress 5.6+
- PHP 7.2+
- MySQL/MariaDB com suporte a `LONGTEXT`

## Instalação limpa

1. **Ativar plugin**
   - Faça upload do ZIP em `Plugins → Adicionar Novo → Enviar Plugin`.
   - Ative `MGS Quiz Carro`. As tabelas `wp_mgs_quiz_config` e `wp_mgs_quiz_leads` são criadas automaticamente.

2. **Importar / criar as 6 configs**
   - Vá em `MGS Quiz → Quizzes`.
   - Suba o arquivo `quiz_config.csv` (incluído neste pacote) no bloco "Importar quiz_config.csv".
   - As 6 entradas (`quiz-car-parcelas`, `-g002`, `-g003`, `-g004`, `-g005`, `-g006`) ficam cadastradas.
   - Para cada quiz, abra `Editar` e ajuste:
     - `SMS Funnel URL (fallback)` ou
     - `SMS Funnel por gestor (JSON)`, ex:
       ```json
       [{"gestor_code":"G002","label":"G002","url":"https://v2.smsfunnel.com.br/integrations/lists/.../add-lead"}]
       ```
     - `Redirect URL principal` + `Redirect variants (JSON)` (opcional, ponderado).
     - `Meta Pixel ID` (apenas dígitos) e `GTM ID` (formato `GTM-XXXXX`).

3. **Permalinks**
   - Acesse `Configurações → Links permanentes` e clique em `Salvar`. Isso garante o flush das rewrite rules. (A ativação do plugin já faz isso, este passo é só um seguro.)

4. **Testar um lead**
   - Abra, por exemplo, `https://seu-dominio.com/quiz-car-parcelas-g002/?utm_source=fb&utm_medium=g002-s&utm_campaign=teste`.
   - Escolha uma parcela.
   - Preencha nome `Teste` e telefone `(11) 99999-9999`.
   - Aguarde ≥ 3s antes de submeter (proteção anti-spam).
   - Confirme:
     - `MGS Quiz → Leads`: a lead aparece com `sms_funnel_status` começando com `ok:`.
     - Dashboard do SMS Funnel: lead recebida (atualize a página).
     - Você é redirecionado para o `redirect_url` com **todos os UTMs / fbclid / gclid preservados**.

5. **Validar SMS Funnel**
   - Status `ok:G002` → ok.
   - Status `fail:XXX` ou `error` → ver `sms_funnel_response` na lead (admin/leads). Causas comuns: URL errada, lista inexistente, payload bloqueado. O endpoint do SMS Funnel só aceita `{name, phone}`.

6. **Validar redirecionamento com UTMs**
   - Use uma URL com vários params: `?utm_source=fb&utm_medium=g002-s&utm_campaign=test&fbclid=abc&gclid=xyz&custom=1`.
   - Após submeter, o destino final deve conter todos esses params (sem sobrescrever os que já existirem no `redirect_url`).

## Shortcode

```
[mgs_quiz slug="quiz-car-parcelas-g002"]
```

Funciona em qualquer página/post comum. Não dispara erro fatal se o slug não existir — exibe mensagem amigável.

## Endpoints REST

- `GET /wp-json/mgs-quiz/v1/config?slug=...` — config pública (sem URLs SMS Funnel).
- `POST /wp-json/mgs-quiz/v1/lead` — corpo JSON:
  ```json
  { "slug": "...", "name": "...", "phone": "...", "parcela": "...",
    "utm_source": "...", "utm_medium": "...", "utm_campaign": "...",
    "utm_term": "...", "utm_content": "...",
    "fbclid": "...", "gclid": "...",
    "extra": { "...": "..." },
    "website": "",  
    "ts": 1719323456789 }
  ```
  Resposta:
  ```json
  { "ok": true, "lead_id": 123, "sms_funnel": "ok:G002",
    "redirect_url": "...", "redirect_variants": [...],
    "redirect_delay_ms": 1800, "redirect_url_weight": 1 }
  ```
  Em falha: `{ "ok": false, "error": "..." }` com HTTP 4xx/5xx — o frontend NÃO redireciona, mostra a mensagem e reabilita o botão.

## Exportar leads

`MGS Quiz → Leads → Exportar CSV` (respeita filtro por slug na URL).

## Desinstalação

Desativar não apaga dados. Para remover totalmente, apague o plugin e dropem manualmente:
```sql
DROP TABLE wp_mgs_quiz_config;
DROP TABLE wp_mgs_quiz_leads;
DELETE FROM wp_options WHERE option_name = 'mgs_quiz_db_version';
```

## Changelog

- **1.1.1**
  - `require_sms_success` por config, ativo por padrão; falha no SMS Funnel retorna `ok:false` e bloqueia redirect.
  - Pixel/evento Lead movido para depois de `ok:true`.
  - Timestamp anti-spam obrigatório, com expiração de 6h.
  - URLs documentadas corrigidas: `/quiz-car-parcelas/` é a variação G002/default.
- **1.1.1**
  - Shortcode passa a carregar CSS/JS via `wp_enqueue_*` e injetar `MGS_QUIZ_REST` + `MGS_QUIZ_CFG` via `wp_localize_script`.
  - SMS Funnel envia somente `{name, phone}` (sem fallback form-urlencoded).
  - Frontend só redireciona quando o servidor confirma `ok:true`; em erro reabilita o botão e mostra mensagem.
  - Anti-spam: honeypot invisível + timestamp (rejeita submissão < 3s).
  - Importador de `quiz_config.csv` no admin.
  - Removida importação de leads históricos.
  - PHP 7.2+ compatível, sem operadores recentes.
- **1.0.0** — versão inicial.
