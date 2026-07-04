# Eggbev CAR BR — persuasão em rewrite e branding de imagem (2026-07-02)

## Contexto

Rodolfo revisou um REC-only longo de financiamento de veículos no Eggbev CAR BR e corrigiu dois pontos: tom editorial pouco persuasivo e aplicação ruim de branding em imagem reaproveitada de referência.

## Regra editorial: benefício antes da ressalva

Em artigos reescritos, especialmente de funil CAR/financiamento, não basta trocar palavras. O texto precisa vender melhor a ideia enquanto preserva os fatos.

### Exemplo de correção

Frase neutra/fria:

> O ponto importante é entender que rapidez não significa aprovação automática. Bancos e financeiras analisam renda, CPF...

Padrão preferido:

> Uma das principais vantagens do financiamento digital é conseguir descobrir rapidamente quais opções podem estar disponíveis para o seu perfil, sem enfrentar processos demorados. Naturalmente, cada instituição ainda realiza sua análise de crédito antes da aprovação final.

### Aplicação prática

- Comece pelo ganho para o leitor: rapidez, acesso, comparação, chance de avançar, menos espera, mais clareza.
- Depois inclua a ressalva necessária: análise de crédito, renda, CPF, condições da instituição.
- Evite abrir parágrafos com bloqueios ou negativas quando a intenção do bloco é conversão.
- Transforme características em benefício percebido.
- Preserve fatos e condições; não prometa aprovação, taxa, oferta, elegibilidade ou disponibilidade sem fonte.

## Regra de imagem: branding integrado, não recorte bruto

Quando adaptar uma imagem de referência com marca de outro site:

- remova completamente o nome/marca de terceiro;
- não cole o logo do Eggbev como recorte dentro de caixa branca;
- reproduza o estilo de assinatura da referência: palavra/wordmark bonito no canto, integrado à arte, com fundo transparente ou grafismo leve;
- se houver overlay colorido original, refaça o canto com paleta Eggbev e texto `eggbev` integrado;
- desfoque placa legível;
- valide com visão que não sobrou `wallet`, `wallet wisdoms` ou marca externa;
- publique só depois de validar o HTML público e remover mídia antiga escopada.

## Técnica aplicada no caso

- O bloco CTA foi mantido em HTML único isolado contra Google Auto Ads.
- A imagem interna antes da tabela foi refeita com canto amarelo/azul, texto `eggbev` integrado sem caixa branca e placa desfocada.
- O slug final foi alterado para evitar Cloudflare APO stale cache e validado sem cache-buster.
