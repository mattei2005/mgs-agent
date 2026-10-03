package main

import (
 "testing"
)

func catalogFixture() Config {
 return Config{Routes: []Route{{Host:"go.example.com",Path:"/a",Name:"A",Group:"US-CC-ES",Destination:"https://example.com/a",DestinationID:"lp-1"}}, Groups:[]string{"US-CC-ES"}, Catalog:[]Destination{{ID:"lp-1",Name:"Landing A",URL:"https://example.com/a",Group:"US-CC-ES"}}}
}
func TestCatalogPersistsAndPreservesRedirect(t *testing.T) {
 a:=fixture(t); c:=catalogFixture(); if e:=a.apply(c);e!=nil {t.Fatal(e)}
 b,e:=newApp(a.dir,a.origin,true);if e!=nil {t.Fatal(e)}
 if len(b.cfg.Catalog)!=1 || len(b.cfg.Groups)!=1 {t.Fatal("catalog missing")}
 w:=send(b,"GET","/a?x=1&x=2&utm_content=A%2BB","go.example.com","",nil)
 if w.Code!=302 || w.Header().Get("Location")!="https://example.com/a?x=1&x=2&utm_content=A%2BB" {t.Fatal("redirect changed")}
}
func TestCatalogRejectsInvalidReferencesGroupsAndURLs(t *testing.T) {
 for _,kind:=range []string{"missing","mismatch","group","duplicate-id","duplicate-group","invalid-url","unused-invalid-url"} {
  t.Run(kind,func(t *testing.T){a:=fixture(t);c:=catalogFixture()
  switch kind {case "missing":c.Routes[0].DestinationID="absent";case "mismatch":c.Catalog[0].URL="https://example.com/b";case "group":c.Routes[0].Group="unknown";case "duplicate-id":c.Catalog=append(c.Catalog,c.Catalog[0]);case "duplicate-group":c.Groups=append(c.Groups,c.Groups[0]);case "invalid-url":c.Catalog[0].URL="https://127.0.0.1/";case "unused-invalid-url":c.Catalog=append(c.Catalog,Destination{ID:"bad",Name:"Bad",URL:"javascript:bad"})}
  if a.apply(c)==nil {t.Fatal("invalid catalog accepted")}
  if a.cfg.Revision!=0 {t.Fatal("partial effect")}
 })}
}
func TestCatalogWeightedReferencesAndAtomicSharedEdit(t *testing.T) {
 a:=fixture(t);c:=catalogFixture();c.Routes=append(c.Routes,Route{Host:"go.example.com",Path:"/b",Destinations:[]Target{{URL:"https://example.com/a",Weight:100,DestinationID:"lp-1"}}})
 if e:=a.apply(c);e!=nil{t.Fatal(e)}
 c.Revision=1;c.Catalog[0].URL="https://example.com/new";c.Routes[0].Destination=c.Catalog[0].URL;c.Routes[1].Destinations[0].URL=c.Catalog[0].URL
 if e:=a.apply(c);e!=nil{t.Fatal(e)}
 for _,path:=range []string{"/a","/b"}{if w:=send(a,"GET",path,"go.example.com","",nil);w.Header().Get("Location")!="https://example.com/new"{t.Fatal("reference not updated")}}
 if e:=a.apply(c);e!=errRevision{t.Fatal("stale catalog allowed",e)}
}
func TestLegacyConfigStillAccepted(t *testing.T) {
 a:=fixture(t);if e:=a.apply(Config{Routes:[]Route{{Host:"go.example.com",Path:"/a",Destination:"https://example.com/legacy"}}});e!=nil{t.Fatal(e)}
}
