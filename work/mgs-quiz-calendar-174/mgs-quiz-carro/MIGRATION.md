# MIGRATION — MGS Quiz Carro v1.1.1

## Objetivo

Substituir 100% a stack Lovable/Supabase do quiz por um plugin WordPress autônomo,
mantendo as URLs públicas existentes:

- `/quiz-car-parcelas/`
- `/quiz-car-parcelas/`
- `/quiz-car-parcelas-g003/`
- `/quiz-car-parcelas-g004/`
- `/quiz-car-parcelas-g005/`
- `/quiz-car-parcelas-g006/`

**Sem importação de leads históricos.** Começamos limpos no WordPress.

## Mapa de equivalência

| Antes (Lovable/Supabase)                          | Agora (Plugin WP)                                          |
| ------------------------------------------------- | ---------------------------------------------------------- |
| Tabela `public.quiz_config`                       | `{prefix}_mgs_quiz_config`                                 |
| Tabela `public.quiz_leads`                        | `{prefix}_mgs_quiz_leads`                                  |
| RPC `get_public_quiz_config`                      | `GET /wp-json/mgs-quiz/v1/config?slug=...`                 |
| Insert direto em `quiz_leads` + edge function     | `POST /wp-json/mgs-quiz/v1/lead`                           |
| Edge `sms-funnel-forward`                         | `MGS_Quiz_REST::create_lead()` → `wp_remote_post` JSON     |
| Edge `wp-create-quiz-folder`                      | Rewrite rule `^(quiz-[a-z0-9\-]+)/?$`                      |
| Página React `Quiz.tsx`                           | `templates/quiz-template.php` + `public/js/quiz.js`        |
| Painel `QuizAdminList.tsx` / `QuizAdmin.tsx`      | Menu `MGS Quiz` no admin do WP                             |

## Passo a passo de cutover

1. **Pré-deploy**
   - Backup do banco WP e dos arquivos da pasta `wp-content/uploads/quiz-car-parcelas*` (se houver).
   - Confirme PHP ≥ 7.2 e WordPress ≥ 5.6.

2. **Instalação**
   - Upload e ativação do plugin `mgs-quiz-carro`.
   - Em `Configurações → Links permanentes`, clique `Salvar`.

3. **Importar configs**
   - `MGS Quiz → Quizzes → Importar quiz_config.csv`.
   - Suba o arquivo `quiz_config.csv` deste pacote.
   - Confirme as 6 entradas listadas.

4. **Preencher SMS Funnel por gestor**
   - Para cada quiz, edite o campo `SMS Funnel por gestor (JSON)`:
     ```json
     [
       {"gestor_code":"G002","label":"G002","url":"https://v2.smsfunnel.com.br/integrations/lists/<ID>/add-lead"},
       {"gestor_code":"G003","label":"G003","url":"https://v2.smsfunnel.com.br/integrations/lists/<ID>/add-lead"}
     ]
     ```
   - Se for uma URL única, basta preencher `SMS Funnel URL (fallback)`.

5. **Pixels / GTM**
   - Preencha `meta_pixel_id` (apenas dígitos) e `gtm_id` (`GTM-XXXXX`) por quiz. Valores inválidos são ignorados.

6. **Remover stack antiga**
   - Apague qualquer pasta antiga `/quiz-car-parcelas*` no WordPress (arquivos físicos do antigo edge function). O rewrite do plugin assume essas URLs.
   - Confirme que não existe nenhum `.htaccess` ou `index.html` em `wp-content/uploads/...` interceptando as URLs.

7. **Teste de fumaça (uma URL)**
   - Abrir `https://creditoparaveiculo.com/quiz-car-parcelas-g002/?utm_source=fb&utm_medium=g002-s&utm_campaign=cut&fbclid=teste`.
   - Selecionar parcela → preencher → aguardar 3s → enviar.
   - `MGS Quiz → Leads`: lead com `sms_funnel_status = ok:G002`.
   - SMS Funnel dashboard: lead recebida.
   - Redirect final preserva todos os UTMs + fbclid.

8. **Liberar tráfego**
   - Repita 7 para `g003`, `g004`, `g005`, `g006`.
   - Acompanhe `MGS Quiz → Leads` nas primeiras horas.

## Anti-spam

- Campo honeypot `website` (oculto via CSS / `aria-hidden`). Se vier preenchido → 400.
- Campo `ts` com `Date.now()` no carregamento do form. Se a submissão chegar em menos de 3000ms → 400.
- Sem reCAPTCHA / Turnstile (pode ser adicionado depois sem alterar o REST).

## O que NÃO está incluído (intencional)

- Importação de `quiz_leads` históricos.
- Sincronização bidirecional com Supabase.
- Edge functions auxiliares (`wp-delete-quiz-folder`, etc.) — não são mais necessárias.

## Suporte / extensão

- Para adicionar um campo novo ao quiz: incluir coluna na tabela (via `dbDelta` no activator), adicionar input no form (`templates/quiz-embed.php`), enviar no payload (`public/js/quiz.js`) e gravar em `MGS_Quiz_REST::create_lead`.
- Para integrar outro provedor (Brevo, RDStation, etc.): adicionar nova classe `MGS_Quiz_<Provider>` e chamar dentro de `create_lead` após o `wp_remote_post` do SMS Funnel.
