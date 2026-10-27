# Liberação de canários com notas nativas e publicação

- Gere um plano imutável por ID real, vinculado à revisão independente, payload, mídia aprovada e cálculo genuíno. Exija ausência de blockers antes do commit.
- Preserve planos bloqueados. Se a reconciliação pré-commit detectar drift, confira primeiro a existência do write-intent: com intent, releia somente; nunca reexecute o commit para tentar obter sucesso.
- Um erro comprovadamente anterior à criação do intent não equivale a efeito parcial. Compare snapshots em leitura; quando somente o fingerprint da mídia mudou, confirme o mesmo attachment, ALT, URL large, transporte e aprovação, obtenha duas leituras nativas estáveis e então prepare um plano novo, sem alterar o anterior nem relaxar a preservação.
- Na rota nativa de postmeta, valide o sanitizador instalado com a representação que será gravada. Alguns sanitizadores Yoast aceitam o resultado calculado como string numérica e transformam o mesmo inteiro em zero. Não fixe notas: serialize o valor genuinamente calculado e confirme o resultado exato.
- Deixe o watcher instalado reconstruir indexables no shutdown normal. Não faça SQL UPDATE, dispatch manual de hooks, deploy, purge nem modificação de locale/role para fabricar persistência.
- Exija readback independente do corpo e das duas camadas: postmeta de SEO/legibilidade e indexable único com os mesmos valores. Só então abra o release do item e publique com payload exclusivo de status.
- Releia o post exato após a publicação e recalcule sobre o rendered/permalink reais. Exija igualdade entre o novo cálculo e ambas as camadas salvas; divergência é pendência, não motivo para regravar às cegas.
- Se um helper compartilhado aprovado mudar durante a execução, pare no fingerprint, leia a mudança e reconcilie efeitos já transmitidos. Atualizar a referência de código não autoriza replay de intents nem expansão de IDs.
- Verifique separadamente HTML canônico, presença no arquivo paginado da categoria, sitemap canônico, OG, idioma do template e biografia pública. Variante com query serve apenas para diagnóstico; presença nela não fecha ausência na URL canônica.
- Diferencie biografia cadastrada e validada por GET de biografia antiga ainda renderizada. Restrinja o write ao próprio campo description e não repita o POST para contornar cache.
- Persista resultado individual depois de cada alvo e agregue os conjuntos por código. Declare publicação, persistência e QA público como estados distintos; conserve limitações visuais/editor-parity e indexação real no buscador.
