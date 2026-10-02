package main

import (
 "encoding/json"
 "os"
 "net/url"
 "strings"
 "testing"
)

func TestApprovedWantabrandImportAllRoutesAndTargets(t *testing.T) {
 b,e:=os.ReadFile("../../data/mgs-router-wantabrand-import-plan.json");if e!=nil {t.Fatal(e)}
 var c Config;if e=json.Unmarshal(b,&c);e!=nil {t.Fatal(e)}
 if len(c.Routes)!=41 {t.Fatal("incomplete requested migration",len(c.Routes))}
 a:=fixture(t);if e=a.apply(c);e!=nil {t.Fatal("real source rejected",e)}
 raw:="utm_source=face%62ook&utm_medium=g001-d&utm_campaign=pg_123&utm_term=wantabrand&utm_content=A%2BB&fbclid=a%2Fb&gclid=g%2Bc&x=1&x=2&blank="
 targetCount:=0;multi:=0
 for _,r:=range c.Routes {
  targets:=r.Destinations;if len(targets)==0 {targets=[]Target{{URL:r.Destination,Weight:100}}}else {multi++}
  targetCount+=len(targets);want:=map[string]int{};actual:=map[string]int{}
  for _,target:=range targets {want[target.URL]+=target.Weight;resolved:=resolveQuery(target.URL,raw);if strings.Contains(resolved,"{") || strings.Contains(resolved,"}") || !strings.HasSuffix(resolved,raw) {t.Fatal("query loss",r.Path)};u,e:=url.Parse(resolved);if e!=nil {t.Fatal(e)};if len(u.Query()["fbclid"])!=1 || len(u.Query()["x"])!=2 {t.Fatal("raw extra parameters duplicated")}}
  for i:=0;i<100;i++ {actual[targetAt(r,i)]++}
  if len(want)!=len(actual) {t.Fatal("selection target drift")};for key,n:=range want {if actual[key]!=n {t.Fatal("source weights changed",r.Path)}}
  for i:=0;i<5;i++ {w:=send(a,"GET",r.Path+"?"+raw,r.Host,"",nil);if w.Code!=302 {t.Fatal(r.Path,w.Code)};allowed:=false;for _,target:=range targets {if w.Header().Get("Location")==resolveQuery(target.URL,raw) {allowed=true}};if !allowed {t.Fatal("wrong redirect",r.Path)}}
 }
 if targetCount!=117 || multi!=5 {t.Fatal("source target count drift",targetCount,multi)}
 reloaded,e:=newApp(a.dir,a.origin,true);if e!=nil || len(reloaded.cfg.Routes)!=41 {t.Fatal("import did not persist")}
 t.Logf("verified routes=%d targets=%d weighted=%d; all aliases and query preservation exercised",len(c.Routes),targetCount,multi)
}
