**MGS Ops Briefing**
Gerado em: `2026-06-04T12:24:33-04:00`

**Atenção executiva**
- 1 arquivo(s) dirty no repo MGS

```text
Service         Sinal  Detalhe                   
--------------  -----  --------------------------
zeus-gateway    OK     active | r=0 | pid=1025185
atena-gateway   OK     active | r=0 | pid=1025017
ares-gateway    OK     active | r=0 | pid=1025515
mgs-autocommit  OK     active | r=0 | pid=923538 
```

```text
Área          Sinal    Detalhe                                   
------------  -------  ------------------------------------------
Crons         OK       jobs=19 stale=0                           
Autorizações  OK       pendentes=0                               
REPORT-INFRA  OK       pendentes=0                               
Git dirty     ATENÇÃO  branch=main head=bba015f                  
Disco         OK       /dev/sda1        38G   19G   18G  51% / | 
```

```text
Agente  Sinal  Observação                       
------  -----  ---------------------------------
zeus    OBS    8 achado(s) no tail de errors.log
atena   OBS    8 achado(s) no tail de errors.log
ares    OBS    8 achado(s) no tail de errors.log
```

Arquivos locais:
- `/root/mgs-agent/data/mgs-ops-briefing-latest.md`
- `/root/mgs-agent/data/mgs-ops-control-plane-latest.json`
