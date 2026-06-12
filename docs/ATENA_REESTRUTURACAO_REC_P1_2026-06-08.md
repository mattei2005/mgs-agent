# Atena — Reestruturação REC/P1 de cartões

Data: 2026-06-08
Responsável executivo: Rodolfo Mattei
Agente coordenador: Zeus
Escopo: Atena / Content Operations / fluxo REC+P1 para artigos de cartão de crédito

## Objetivo

Reestruturar os contratos editoriais e a execução técnica da Atena para produção REC+P1 de cartões de crédito, garantindo que:

- O REC seja curto, consultivo, persuasivo e funcione como recomendação inicial.
- A P1 aprofunde benefícios reais do cartão, sem repetir o REC.
- A Atena evite alucinação, promessa indevida, benefício inventado e repetição de texto.
- O pipeline técnico entregue o que os contracts prometem: estrutura, SEO, LazyBlocks, imagens, Yoast e validações.
- A diferença entre imagem do card isolado e imagem destacada fique clara.

## Arquivos analisados

- `/root/.hermes/profiles/atena/SOUL.md`
- `/root/mgs-agent/skills/content-generate-rec-p1/SKILL.md`
- `/root/mgs-agent/skills/content-generate-rec-p1/contracts/cc-rec.md`
- `/root/mgs-agent/skills/content-generate-rec-p1/contracts/cc-p1.md`
- Arquivos enviados por Rodolfo/Raquel:
  - `rec.txt`
  - `p1.txt`

## Decisões editoriais aprovadas

| Tema | Decisão |
|---|---|
| REC | Manter nova estrutura curta, consultiva e orientada à decisão. |
| P1 | Manter nova estrutura aprofundada, evitando replicar frases/textos do REC. |
| REC meta description | 130 a 140 caracteres. |
| P1 keyword count | 5 a 8 usos da keyword/cartão. |
| Slug REC | `rec-{sigla-do-pais}-cc-{nome-do-cartao}`. |
| Slug P1 | `apply-now-{sigla-do-pais}-cc-{nome-do-cartao}`. |
| LazyBlock | A imagem do card pode repetir no REC e na P1. |
| Featured image | REC e P1 precisam ter imagens destacadas diferentes. |

## Alterações aplicadas em contracts/reference

### REC contract

Arquivo:

- `/root/mgs-agent/skills/content-generate-rec-p1/contracts/cc-rec.md`

Principais mudanças:

- REC reposicionado como recomendação curta e consultiva.
- Regras reforçadas contra alucinação e benefícios não confirmados.
- Meta description ajustada para 130–140 caracteres.
- Slug REC corrigido.
- Seção de imagem destacada passou a apontar para diretriz visual compartilhada.
- Separação explícita entre card isolado e imagem destacada final.

Trecho-chave:

```text
Usar a imagem do card isolado apenas como referência/base visual para preservar o cartão; ela não é a imagem destacada final.
```

### P1 contract

Arquivo:

- `/root/mgs-agent/skills/content-generate-rec-p1/contracts/cc-p1.md`

Principais mudanças:

- P1 reposicionada como página de aprofundamento e aplicação.
- Obrigação de aprofundar benefícios reais do cartão.
- Proibição prática de repetir texto/frases do REC.
- Keyword count definido como 5–8 usos.
- Slug P1 corrigido.
- Regras específicas de imagem destacada P1 adicionadas.

Trecho-chave:

```text
A imagem do card isolado pode ser a mesma usada no LazyBlock do REC/P1, mas ela não é a imagem destacada final.
```

### Reference visual compartilhada

Arquivo criado/ajustado:

- `/root/mgs-agent/skills/content-generate-rec-p1/references/featured-image-visual-contract.md`

Função:

- Concentrar a diretriz completa de composição visual para imagens destacadas REC/P1.
- Evitar duplicar texto longo nos contracts principais.
- Separar claramente:
  - imagem do card isolado;
  - imagem destacada REC;
  - imagem destacada P1.

Regras centrais:

- REC usa imagem destacada contextual própria.
- P1 usa outra imagem destacada contextual própria, obrigatoriamente diferente da REC.
- Card isolado é ativo separado usado no LazyBlock REC/P1.
- Card isolado pode servir como referência visual para gerar featured images.
- Mesmo cartão pode ser usado como referência, mas REC/P1 devem ter pessoa, cenário, composição e campanha visual diferentes.

## Alterações aplicadas nos runners/validators

### REC runner

Arquivo:

- `/root/mgs-agent/scripts/mgs-rec-runner.py`

Mudanças:

- Geração local alinhada ao REC v2.
- Estrutura REC com recomendação curta, benefícios em H3, pontos a considerar, perfil indicado, prós/contras e CTA suave para P1.
- Removida dependência estrutural de tabela comparativa como corpo principal.
- Meta description validada em 130–140 caracteres.
- Ajustes para passar gates de estilo e semantic QA.

### P1 runner

Arquivo:

- `/root/mgs-agent/scripts/mgs-p1-runner.py`

Mudanças iniciais:

- Geração de P1 alinhada ao contract v2.
- Keyword count validado em 5–8 usos.
- Contagem de keyword ajustada para texto visível, ignorando JSON/LazyBlock/figures.
- Título/meta ajustados para usar o nome completo do cartão quando couber.

Correção posterior após teste Tesco/Raquel:

- Removida a abordagem de `wp:details` / accordion / menu hambúrguer como padrão da P1.
- P1 deve conter exatamente 1 LazyBlock `credit-card_ANTIGO` e 1 LazyBlock final `botao normal`.
- O card da P1 usa o mesmo bloco aprovado do REC, mas com campos/copy próprios para aplicação/conversão externa; não copia automaticamente o conteúdo do REC.
- O botão final da P1 deve apontar para a URL oficial do emissor; o botão final do REC aponta para a P1 interna.
- P1 não duplica mais card no fim do artigo.

### Orchestrator

Arquivo:

- `/root/mgs-agent/scripts/mgs-rec-p1-orchestrator.py`

Resultado:

- Verificado. A lógica de separação de featured image REC/P1 já existia e permaneceu compatível.

## Validações executadas

### REC dry-run

Com cartão de teste `AIB Visa Gold Card`:

- `success=true`
- word count REC: 463
- meta chars: 136
- slug: `rec-gb-cc-aib-visa-gold-card`
- semantic QA: OK

### P1 unit generation

Com cartão de teste `AIB Visa Gold Card` na validação inicial:

- word count: 904
- Details blocks: 4
- LazyBlocks: 2
- keyword total: 5
- title: `AIB Visa Gold Card: How to Apply`
- meta chars: 150

Observação: essa validação foi supersedida pela revisão Tesco/Raquel posterior. O estado final aprovado remove `wp:details`/accordion como padrão e exige 1 LazyBlock `credit-card_ANTIGO` + 1 LazyBlock `botao normal` na P1.

### P1 semantic QA

Resultado:

- status: OK
- article_type: p1
- word_count_visible: 914
- blocks: []
- warnings: []

### Validações técnicas

- `python3 -m py_compile` nos scripts REC/P1/orchestrator: OK
- `git diff --check` nos arquivos alterados: OK
- HEAD e `origin/main` sincronizados na checagem final: OK

## Audit log

Eventos registrados em:

- `/root/mgs-agent/logs/events-audit.jsonl`

Eventos relevantes:

- Atualização dos contracts REC/P1 v2.
- Alinhamento dos runners REC/P1 aos contracts.
- Clarificação card isolado vs imagem destacada.

## Estado operacional confirmado

- Arquivos REC/P1 estão no repositório `/root/mgs-agent`.
- Git estava sincronizado com `origin/main` na validação final.
- `atena-gateway.service` estava ativo e rodando.
- Atena roda via systemd com:

```text
/root/.local/bin/hermes -p atena gateway run
```

## Próximo passo recomendado

Executar um teste controlado em draft REC+P1 real com um cartão e URL oficial, sem publicar em produção inicialmente.

Checklist do teste:

1. Gerar REC+P1 em draft.
2. Validar geração/upload da imagem do card isolado.
3. Validar geração/upload da featured image REC.
4. Validar geração/upload da featured image P1 diferente da REC.
5. Validar LazyBlocks REC/P1.
6. Validar Yoast title/meta/focus keyword.
7. Validar semantic QA e duplicidade.
8. Fazer verificação pública/preview do draft.
9. Só depois liberar publicação real.

## Addendum — Taxonomia WordPress / tags

Após revisão antes do primeiro teste real, foi identificado que a inclusão de tags WordPress existia nos runners, mas a regra não estava suficientemente explícita na SKILL REC+P1 e a P1 tinha uma tag comercial padrão arriscada.

Correção aplicada:

- Documentada a regra `WordPress taxonomy/tags` em `/root/mgs-agent/skills/content-generate-rec-p1/SKILL.md`.
- REC e P1 devem ter tags obrigatórias: `rec` ou `p1`, vertical, país, tag limpa do cartão/produto, `lang_<idioma>` e `atena_agent`.
- Tags comerciais opcionais só entram quando sustentadas por benefícios/fatos confirmados.
- P1 não adiciona mais `rewards credit card` por default.
- `purchase credit card` só entra quando houver oferta de compra 0%, interest-free, introdutória ou promocional confirmada.
- Validação por monkeypatch confirmou que cartão com “everyday purchases” não recebe tag falsa de rewards/purchase, enquanto cartão com oferta promocional de compra recebe `purchase credit card`.
- Revisão adicional após questionamento do Rodolfo removeu fallback visual falso na P1: LazyBlock não usa mais `Avios rewards`, `rewards credit card` ou travel/cashback como fallback quando o cartão não tem esse benefício confirmado. `tag10`, `tag2` e descriptor agora derivam dos benefícios confirmados do cartão.

## Observação de escopo

O arquivo abaixo pertence ao contexto/thread Ares `1508906079642456084` e não faz parte desta reestruturação Atena/REC-P1:

```text
data/ares/creative-inventory/upload-canvas-clean-copy-execution-report.csv
```

Ele não deve ser tratado como pendência deste assunto.
