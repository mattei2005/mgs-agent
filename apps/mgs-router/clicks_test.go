package main

import (
 "encoding/json"
 "net/http"
 "os"
 "path/filepath"
 "strings"
 "sync"
 "testing"
 "time"
)

func TestClicksCountOnlySuccessfulGETAndPersist(t *testing.T) {
 a := fixture(t)
 if e:=a.apply(Config{Routes:[]Route{{Host:"go.example.com",Path:"/click",Destination:"https://example.com/a"},{Host:"go.example.com",Path:"/error",ResponseStatus:500}}});e!=nil{t.Fatal(e)}
 for _,method:=range []string{"GET","GET","HEAD","POST"}{send(a,method,"/click?private=value","go.example.com","",nil)}
 send(a,"GET","/missing","go.example.com","",nil);send(a,"GET","/error","go.example.com","",nil)
 a.clicks.db.Close()
 b,e:=newApp(a.dir,a.origin,true);if e!=nil{t.Fatal(e)};defer b.clicks.db.Close()
 day:=time.Now().In(b.clicks.zone).Format("2006-01-02")
 counts,e:=b.clicks.counts(day,day);if e!=nil || counts["go.example.com\n/click"]!=2 || len(counts)!=1 {t.Fatalf("bad persisted counts: %v %v",counts,e)}
 data,e:=os.ReadFile(filepath.Join(a.dir,"clicks.sqlite"));if e!=nil{t.Fatal(e)}
 if strings.Contains(string(data),"private=value") || strings.Contains(string(data),"https://example.com/a"){t.Fatal("visitor data stored")}
}
func TestClickDateBoundariesDSTAndConcurrent(t *testing.T) {
 a:=fixture(t);defer a.clicks.db.Close()
 before:=time.Date(2026,11,1,3,59,59,0,time.UTC);after:=before.Add(time.Second)
 if e:=a.clicks.record("go.example.com\n/a",before);e!=nil{t.Fatal(e)}
 var wg sync.WaitGroup
 for i:=0;i<100;i++{wg.Add(1);go func(){defer wg.Done();if e:=a.clicks.record("go.example.com\n/a",after);e!=nil{t.Error(e)}}()};wg.Wait()
 c,e:=a.clicks.counts("2026-10-31","2026-10-31");if e!=nil || c["go.example.com\n/a"]!=1{t.Fatal(c,e)}
 c,e=a.clicks.counts("2026-11-01","2026-11-01");if e!=nil || c["go.example.com\n/a"]!=100{t.Fatal(c,e)}
}
func TestClicksAPIAuthDatesReadOnly(t *testing.T) {
 a:=fixture(t);defer a.clicks.db.Close()
 if w:=send(a,"GET","/api/clicks",a.adminHost,"",nil);w.Code!=401{t.Fatal(w.Code)}
 cookie,_:=login(t,a);h:=map[string]string{"Cookie":cookie}
 for _,q:=range []string{"?from=2026-02-30&to=2026-03-01","?from=2026-10-07&to=2026-10-06","?from=bad","?from=2026-01-01","?to=2026-01-01"}{if w:=send(a,"GET","/api/clicks"+q,a.adminHost,"",h);w.Code!=400{t.Fatal(q,w.Code)}}
 w:=send(a,"GET","/api/clicks",a.adminHost,"",h);if w.Code!=200{t.Fatal(w.Code)}
 var v struct{Timezone string `json:"timezone"`;Counts map[string]int64 `json:"counts"`;Since string `json:"since"`};if e:=json.Unmarshal(w.Body.Bytes(),&v);e!=nil || v.Timezone!="America/New_York" || v.Counts==nil || v.Since==""{t.Fatal(v,e)}
 if w:=send(a,"POST","/api/clicks",a.adminHost,"{}",h);w.Code!=http.StatusMethodNotAllowed{t.Fatal(w.Code)}
 if w:=send(a,"GET","/api/clicks","go.example.com","",h);w.Code!=404{t.Fatal(w.Code)}
}
func TestClickStoreFailureDoesNotBreakRedirect(t *testing.T) {
 a:=fixture(t);if e:=a.apply(Config{Routes:[]Route{{Host:"go.example.com",Path:"/a",Destination:"https://example.com/a"}}});e!=nil{t.Fatal(e)}
 a.clicks.db.Close();w:=send(a,"GET","/a","go.example.com","",nil);if w.Code!=302 || w.Header().Get("Location")!="https://example.com/a"{t.Fatal(w.Code)}
 if a.clicks.failures.Load()!=1{t.Fatal("failure not visible")}
}
