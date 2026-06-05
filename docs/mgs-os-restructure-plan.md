# Plano de Reestruturação — MGS OS

> Status: plano de execução passo a passo.  
> Regra: nenhuma automação/agente/arquivo produtivo será removido ou movido sem etapa de inventário, aprovação e validação.

---

## Objetivo

Reestruturar a MGS como um sistema operacional empresarial antes de expandir agentes: áreas, rotas, fontes de verdade, permissões, dados, playbooks e agentes.

---

## Fase 0 — Captura do modelo real

```text
Status: iniciado
Saída: /root/mgs-agent/context/company-current-operating-model.md
```

A fala do Rodolfo vira a fonte primária do modelo atual. Antes de mudar qualquer estrutura, capturamos como a empresa funciona de verdade.

---

## Fase 1 — Diagrama alvo da empresa

Criar o mapa MGS OS com áreas reais:

```text
Executive / Management
Content Operations
Growth / Media Buying
Creative Operations
Revenue / AdOps
Finance / BI
Tech / WordPress / Infra
Security / Access
```

Saídas propostas:

```text
/root/mgs-agent/context/company-os.md
/root/mgs-agent/context/areas.md
/root/mgs-agent/context/agent-map.md
/root/mgs-agent/context/routes.md
/root/mgs-agent/context/sources-of-truth.md
/root/mgs-agent/context/permissions-matrix.md
```

---

## Fase 2 — Inventário classificado

Gerar inventário de arquivos estruturais atuais:

```text
Path | Classe | Área | Dono | Status | Ação recomendada
```

Classes:

```text
canônico | runtime | automação | skill | histórico | backup | legado | experimento | patch | segredo/não-versionar
```

---

## Fase 3 — Plano de migração

Para cada arquivo/pasta, decidir:

```text
manter | mover | renomear | consolidar | arquivar | remover depois | não tocar
```

Nenhum movimento em massa. Migração por blocos pequenos.

---

## Fase 4 — Criar camada canônica nova

Criar documentos organizacionais novos sem quebrar os antigos:

```text
context/areas.md
context/routes.md
context/sources-of-truth.md
context/agent-map.md
context/permissions-matrix.md
context/playbooks/
```

---

## Fase 5 — Ajustar agentes

Depois da aprovação da camada canônica:

```text
Zeus  -> ler MGS OS como fonte gerencial principal
Atena -> ler Content Operations + fontes de conteúdo/WordPress
Ares  -> ler Growth + Creative + Revenue/ROI conforme escopo aprovado
```

Regras:

- alterar um agente por vez;
- validar resposta no Discord;
- validar logs;
- manter rollback;
- não apagar contexto antigo até estabilidade.

---

## Fase 6 — Limpeza e consolidação

Só depois de tudo validado:

- arquivar backups antigos;
- consolidar docs duplicadas;
- remover scripts deprecated realmente mortos;
- padronizar nomes;
- documentar changelog final.

---

## Próximo passo imediato

Com a explicação do Rodolfo já capturada, o próximo passo é revisar e atualizar `/root/mgs-agent/context/company-os.md` para refletir a estrutura real da MGS, não a versão genérica inicial.
