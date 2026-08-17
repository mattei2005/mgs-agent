# Auditoria de artigos irrelevantes/spam em WordPress

Use quando Rodolfo perceber posts publicados que não combinam com o domínio, especialmente cassino/apostas, conteúdo adulto, idiomas inesperados ou clusters automatizados.

## Escopo e segurança

- A auditoria é read-only: não alterar status, autor, conteúdo, tags ou arquivos.
- Coletar diretamente de WordPress runtime: WP-CLI/DB para RunCloud e REST autenticado para externos.
- Para cada site, obter até 500 posts publicados recentes com ID, data, modificação, título, slug, autor e categorias.
- Salvar a evidência detalhada em `reports/wordpress-spam-audit/` e manter checkpoint da iniciativa.

## Detecção em camadas

1. Buscar termos fortes de spam: casino/cassino, slot, betting/bahis, poker, roulette, Mostbet, 1xBet, Betandreas, Chicken Road, conteúdo adulto/pharma etc.
2. Detectar idiomas e marcas incompatíveis com o domínio.
3. Agrupar por site, autor e janela temporal.
4. Revisar todos os posts recentes do autor/cluster, não apenas títulos que bateram em keywords.
5. Validar controles para evitar falso positivo:
   - `Aviator` pode ser cartão AAdvantage;
   - `Banque Casino` pode ser instituição financeira;
   - “betting on AI” pode ser expressão editorial;
   - “slot” pode ser microSD/card slot.
6. Confirmar títulos da evidência do usuário e relacioná-los ao domínio/IDs reais.

## Critério de site comprometido/sinalizado

Sinalizar somente quando houver cluster coerente de posts recentes e incompatíveis, por exemplo:

- muitos posts em poucos dias/semanas;
- mesmo autor em vários domínios;
- títulos em múltiplos idiomas sem relação com a vertical;
- cassino, apostas, conteúdo adulto ou links promocionais externos;
- categorias legítimas reutilizadas para conteúdo incompatível.

Relatar por site:

- quantidade confirmada;
- primeira e última data;
- autor comum;
- 2–5 títulos de exemplo;
- correspondência com screenshot/link fornecido.

## Contenção e remediação

A auditoria não autoriza contenção. Mudanças de senha, application password, usuário, permissão ou credencial exigem confirmação crítica. Exclusão de posts também exige confirmação crítica e alvo exato. Antes de propor exclusão:

1. exportar IDs/títulos/datas/autores;
2. decidir quarentena (`draft`) versus exclusão;
3. provar que controles legítimos foram excluídos do target set;
4. criar backup/rollback;
5. validar publicamente após a ação.

## Caso de referência 2026-08-17

Auditoria de 54 sites/12.950 posts detectou sete sites com 272 posts recentes incompatíveis, concentrados no autor `rodmaster`, entre 2026-07-20 e 2026-08-17. Três controles com o mesmo autor (`eggbev.com`, `zytiva.com`, `finanzas.newsoun.com`) tinham empréstimos legítimos e não foram sinalizados. Evidência: `reports/wordpress-spam-audit/20260817-irrelevant-posts.json`.
