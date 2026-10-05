package main

import (
 "encoding/json"
 "os"
 "path/filepath"
 "reflect"
 "testing"
)

func domainGroupPost(t *testing.T,a *App,c DomainConfig,want int) {
 t.Helper();cookie,csrf:=login(t,a);b,_:=json.Marshal(c)
 w:=send(a,"POST","/api/domains",a.adminHost,string(b),map[string]string{"Cookie":cookie,"X-CSRF-Token":csrf,"Content-Type":"application/json","Origin":a.origin})
 if w.Code!=want {t.Fatalf("status=%d want=%d body=%s",w.Code,want,w.Body.String())}
}
func groupedDomainFixture(t *testing.T) *App {
 a:=fixture(t)
 domainGroupPost(t,a,DomainConfig{GroupSchema:1,Groups:[]string{"MGS","Other"},Domains:[]string{"one.example.com","two.example.com"},Metadata:map[string]DomainMetadata{"one.example.com":{Group:"MGS"},"two.example.com":{Group:"MGS"}}},200)
 return a
}
func TestDomainGroupsMigrationStableIDsPersistence(t *testing.T) {
 a:=fixture(t);if e:=a.apply(Config{Routes:[]Route{{Host:"one.example.com",Path:"/x",Destination:"https://example.com/offer"}}});e!=nil {t.Fatal(e)}
 before,_:=os.ReadFile(filepath.Join(a.dir,"routes.json"))
 domainGroupPost(t,a,DomainConfig{GroupSchema:1,Groups:[]string{"MGS"},Domains:[]string{"one.example.com","two.example.com"},Metadata:map[string]DomainMetadata{"one.example.com":{Group:"MGS"},"two.example.com":{Group:"MGS"}}},200)
 ids:=a.domains.Metadata;if ids["one.example.com"].ID<=0 || ids["two.example.com"].ID<=ids["one.example.com"].ID {t.Fatal("IDs not allocated")}
 next:=a.domains;next.Domains=append([]string{},next.Domains...);next.Domains=append(next.Domains,"three.example.com")
 domainGroupPost(t,a,next,200)
 if a.domains.Metadata["one.example.com"]!=ids["one.example.com"] || a.domains.Metadata["three.example.com"].ID<=ids["two.example.com"].ID {t.Fatal("unstable IDs")}
 b,e:=newApp(a.dir,a.origin,true);if e!=nil || !reflect.DeepEqual(a.domains,b.domains) {t.Fatal("persist",e)}
 after,_:=os.ReadFile(filepath.Join(a.dir,"routes.json"));if string(before)!=string(after) {t.Fatal("routes mutated")}
}
func TestDomainGroupsRejectDowngradeMissingRefsAndIDChange(t *testing.T) {
 a:=groupedDomainFixture(t)
 domainGroupPost(t,a,DomainConfig{Revision:a.domains.Revision,Domains:a.domains.Domains},400)
 old:=a.domains.Metadata["one.example.com"]
 for _,m:=range []DomainMetadata{{ID:old.ID,Group:"Missing"},{ID:old.ID+100,Group:"MGS"}} {
  c:=a.domains;c.Metadata=map[string]DomainMetadata{};for k,v:=range a.domains.Metadata {c.Metadata[k]=v};c.Metadata["one.example.com"]=m;domainGroupPost(t,a,c,400)
 }
 c:=a.domains;c.Domains=[]string{"one.example.com"};domainGroupPost(t,a,c,400)
 c=a.domains;c.Revision--;domainGroupPost(t,a,c,409)
}
func TestDomainGroupsRenameAndUngroupNoTrafficEffect(t *testing.T) {
 a:=groupedDomainFixture(t);if e:=a.apply(Config{Routes:[]Route{{Host:"one.example.com",Path:"/x",Destination:"https://example.com/offer"}}});e!=nil {t.Fatal(e)}
 c:=a.domains;c.Groups=[]string{"Renamed","Other"};c.Metadata=map[string]DomainMetadata{};for k,v:=range a.domains.Metadata {v.Group="Renamed";c.Metadata[k]=v};domainGroupPost(t,a,c,200)
 c=a.domains;c.Groups=[]string{"Other"};c.Metadata=map[string]DomainMetadata{};for k,v:=range a.domains.Metadata {v.Group="";c.Metadata[k]=v};domainGroupPost(t,a,c,200)
 w:=send(a,"GET","/x","one.example.com","",nil);if w.Code!=302 || w.Header().Get("Location")!="https://example.com/offer" {t.Fatal("traffic changed")}
}
func TestDomainGroupsCorruptStoreFailsClosed(t *testing.T) {
 a:=groupedDomainFixture(t);c:=a.domains;c.Metadata["one.example.com"]=DomainMetadata{ID:1,Group:"Unknown"};b,_:=json.Marshal(c);os.WriteFile(filepath.Join(a.dir,"domains.json"),b,0600)
 if _,e:=newApp(a.dir,a.origin,true);e==nil {t.Fatal("corrupt group loaded")}
}
