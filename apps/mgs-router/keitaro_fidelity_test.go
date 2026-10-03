package main

import (
 "encoding/json"
 "testing"
)

func TestKeitaroRelativeWeightsExactAndPersistent(t *testing.T) {
 a:=fixture(t)
 var c Config
 json.Unmarshal([]byte(`{"routes":[{"host":"card.wantabrand.com","path":"/relative","relative_weights":true,"destinations":[{"url":"https://wantabrand.com/a","weight":14},{"url":"https://wantabrand.com/b","weight":14},{"url":"https://wantabrand.com/c","weight":14}]}]}`),&c)
 if e:=a.apply(c);e!=nil {t.Fatal(e)}
 counts:=map[string]int{}
 for i:=0;i<42;i++ {counts[targetAt(c.Routes[0],i)]++}
 for _,d:=range c.Routes[0].Destinations {if counts[d.URL]!=d.Weight {t.Fatal("ratio drift")}}
 b,e:=newApp(a.dir,a.origin,true);if e!=nil {t.Fatal(e)}
 for i:=0;i<100;i++ {if w:=send(b,"GET","/relative","card.wantabrand.com","",nil);w.Code!=302 {t.Fatal(w.Code)}}
}

func TestKeitaroLiteralFragmentQueryAndEmptyRoute(t *testing.T) {
 a:=fixture(t)
 const dest="https://wantabrand.com/page?utm_campaign=pg_#PAGE_ID#&utm_content=drip_m0-1"
 var c Config
 json.Unmarshal([]byte(`{"routes":[{"host":"card.wantabrand.com","path":"/fragment","keitaro_query":true,"destination":"`+dest+`"},{"host":"card.wantabrand.com","path":"/empty","response_status":500,"keitaro_query":true},{"host":"card.wantabrand.com","path":"/template","keitaro_query":true,"destination":"https://wantabrand.com/p?utm_source={utm_source}&utm_term={utm_term}&utm_content={utm_content}"}]}`),&c)
 if e:=a.apply(c);e!=nil {t.Fatal(e)}
 for _,method:=range []string{"GET","HEAD"} {
 w:=send(a,method,"/fragment?utm_campaign=received&fbclid=a%2Fb","card.wantabrand.com","",nil)
 if w.Code!=302||w.Header().Get("Location")!=dest {t.Fatal("literal fragment changed",w.Code,w.Header().Get("Location"))}
 w=send(a,method,"/empty","card.wantabrand.com","",nil)
 if w.Code!=500||w.Header().Get("Location")!="" {t.Fatal("empty source silently repaired",w.Code)}
 w=send(a,method,"/template?utm_source=face%62ook&utm_content=A%2BB&fbclid=x&x=1","card.wantabrand.com","",nil)
 if w.Code!=302||w.Header().Get("Location")!="https://wantabrand.com/p?utm_source=face%62ook&utm_term={utm_term}&utm_content=A%2BB" {t.Fatal("source query semantics lost",w.Header().Get("Location"))}
 }
 b,e:=newApp(a.dir,a.origin,true);if e!=nil {t.Fatal(e)}
 if w:=send(b,"GET","/empty","card.wantabrand.com","",nil);w.Code!=500 {t.Fatal("status not persistent")}
}

func TestKeitaroUnsafeModesRejected(t *testing.T) {
 for _,body:=range []string{
 `{"response_status":200}`,`{"response_status":500,"destination":"https://wantabrand.com/p"}`,`{"response_status":500,"relative_weights":true}`,`{"relative_weights":true,"destination":"https://wantabrand.com/p"}`,`{"relative_weights":true,"destinations":[{"url":"https://wantabrand.com/p","weight":0}]}`,`{"destination":"https://wantabrand.com/p#bad\r\nheader"}`,
 } {
 a:=fixture(t);var fields map[string]any;json.Unmarshal([]byte(body),&fields);fields["host"]="card.wantabrand.com";fields["path"]="/bad";b,_:=json.Marshal(map[string]any{"routes":[]any{fields}});var c Config;json.Unmarshal(b,&c)
 if a.apply(c)==nil {t.Fatal("unsafe config accepted",body)}
 }
}
