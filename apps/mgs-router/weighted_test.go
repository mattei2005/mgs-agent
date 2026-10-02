package main

import (
 "encoding/json"
 "net/url"
 "strings"
 "testing"
)

func weightedFixture(t *testing.T, destination string, weights string) *App {
 t.Helper();a:=fixture(t)
 body:=`{"revision":0,"routes":[{"host":"card.wantabrand.com","path":"/aliasOriginal","name":"Original name","destinations":`+weights+`}]}`
 if destination!="" {body=`{"revision":0,"routes":[{"host":"card.wantabrand.com","path":"/aliasOriginal","destination":"`+destination+`"}]}`}
 var c Config;if e:=json.Unmarshal([]byte(body),&c);e!=nil {t.Fatal(e)}
 if e:=a.apply(c);e!=nil {t.Fatal(e)}
 return a
}
func TestWeightedRedirectAndPersistence(t *testing.T) {
 a:=weightedFixture(t,"",`[{"url":"https://wantabrand.com/one","weight":25},{"url":"https://wantabrand.com/two","weight":75}]`)
 counts:=map[string]int{}
 for i:=0;i<1000;i++ {w:=send(a,"GET","/aliasOriginal?fbclid=A%2FB&x=1&x=2","card.wantabrand.com","",nil);if w.Code!=302 {t.Fatal(w.Code)};loc:=w.Header().Get("Location");if !strings.HasSuffix(loc,"?fbclid=A%2FB&x=1&x=2") {t.Fatal("raw query lost")};u,_:=url.Parse(loc);counts[u.Path]++}
 if counts["/one"]<150 || counts["/one"]>350 || counts["/two"]<650 {t.Fatal("weights not reflected",counts)}
 b,e:=newApp(a.dir,a.origin,true);if e!=nil {t.Fatal(e)}
 if w:=send(b,"HEAD","/aliasOriginal","card.wantabrand.com","",nil);w.Code!=302 {t.Fatal("persisted weighted route not usable")}
}
func TestTemplateQueriesPreserveRawAndNoDuplication(t *testing.T) {
 a:=weightedFixture(t,"https://wantabrand.com/page?fixed=1&utm_source={utm_source}&utm_content={utm_content}","")
 raw:="utm_source=face%62ook&utm_content=A%2BB&x=1&x=2&fbclid=a%2Fb&blank="
 w:=send(a,"GET","/aliasOriginal?"+raw,"card.wantabrand.com","",nil)
 if w.Code!=302 || w.Header().Get("Location")!="https://wantabrand.com/page?fixed=1&"+raw {t.Fatal("template query corruption",w.Header().Get("Location"))}
 w=send(a,"GET","/aliasOriginal","card.wantabrand.com","",nil)
 if strings.Contains(w.Header().Get("Location"),"{") || w.Header().Get("Location")!="https://wantabrand.com/page?fixed=1&utm_source=&utm_content=" {t.Fatal("missing templates unresolved")}
}
func TestInvalidWeightsAndTargetsRejected(t *testing.T) {
 for _,targets:=range []string{`[]`,`[{"url":"https://wantabrand.com/one","weight":0}]`,`[{"url":"https://wantabrand.com/one","weight":99}]`,`[{"url":"https://wantabrand.com/one","weight":-1},{"url":"https://wantabrand.com/two","weight":101}]`,`[{"url":"https://127.0.0.1/","weight":100}]`,`[{"url":"https://card.wantabrand.com/loop","weight":100}]`,`[{"url":"https://wantabrand.com/{utm_source}","weight":100}]`,`[{"url":"https://wantabrand.com/?x={unknown}","weight":100}]`} {
  a:=fixture(t);var c Config;json.Unmarshal([]byte(`{"routes":[{"host":"card.wantabrand.com","path":"/original","destinations":`+targets+`}]}`),&c)
  if a.apply(c)==nil {t.Fatal("unsafe target accepted",targets)}
 }
}
