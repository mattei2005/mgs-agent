# Contagem de Sites MGS — Guia de Contextos

**Data:** 2026-04-27
**Fonte de verdade:** `/root/mgs-agent/context/sites.md` (32 sites oficiais MGS)

## 📊 Os números

| Número | Significado | Fonte | Quando usar |
|---|---|---|---|
| **32** | Sites MGS oficiais | `context/sites.md` | **Sempre** que perguntar "quantos sites MGS temos?" |
| **27** | Sites MGS em RunCloud | `sites.md` ∩ `inventario-webapps.json` | Operações em massa via RunCloud (deploys, mu-plugin) |
| **5** | Sites MGS em SFTP (não-RunCloud) | `sites.md` − RunCloud | Operações manuais via SFTP/elFinder |
| **107** | Total webapps RunCloud | `inventario-webapps.json` | Auditoria geral do servidor (informativo, não MGS) |

## 🗂️ Os 5 sites MGS em SFTP (fora do RunCloud)

- openzed.com
- finanzas.openzed.com
- cliquet.com
- finanzas.cliquet.com
- fincgriffin.com

Esses 5 estão em sites.md mas rodam fora do RunCloud (SFTP-only). Operações precisam ser via SFTP/elFinder.

## 📦 Sobre os 80 "RunCloud não-MGS"

Dos 107 webapps RunCloud, 80 NÃO são MGS-content — são:
- Backups (bkp.*)
- Sites pessoais (jislainemattei.com, revistacafe.com.br)
- Outros negócios (prospectcleaning.com, sunshinebeautysupplier.com)
- Parcerias / staging
- Domínios paralelos antigos

Não tratar como sites MGS. A fonte de verdade pra contagem MGS é sempre sites.md.

## 🎯 Resposta rápida

- "Quantos sites MGS temos?" → 32 (fonte: context/sites.md)
- "Em quantos sites posso rodar deploy via RunCloud?" → 27 (32 − 5 SFTP)
- "Quantos webapps tem no RunCloud?" → 107, mas 80 não são MGS

## 📝 Histórico de discrepâncias

- 2026-04-24: Briefing dizia "34 sites" → Zeus questionou, chegou em 26 → 0 sites tocados incorretamente.
- 2026-04-27: Recontagem completa = 32 em sites.md, 27 em RunCloud, 5 em SFTP.

---

Regra de ouro: Se houver dúvida em contagem, sempre rodar os comandos. Nunca confiar em valores cacheados.
