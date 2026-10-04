package main

import (
 "reflect"
 "testing"
)
func scopedFixture() Config {
 c:=catalogFixture(); c.GroupSchema=2; c.RouteGroups=[]string{"US-CC-ES"}; c.DestinationGroups=[]string{"US-CC-ES"}; c.Groups=nil; return c
}
func TestScopedGroupsIndependentAndPersistent(t *testing.T) {
 a:=fixture(t);c:=scopedFixture();if e:=a.apply(c);e!=nil {t.Fatal(e)}
 c.Revision=a.cfg.Revision;c.RouteGroups=[]string{"Campaign renamed"};c.Routes[0].Group="Campaign renamed"
 if e:=a.apply(c);e!=nil {t.Fatal(e)}
 if a.cfg.Catalog[0].Group!="US-CC-ES" {t.Fatal("campaign rename changed landing")}
 c.Revision=a.cfg.Revision;c.RouteGroups=[]string{};c.Routes[0].Group=""
 if e:=a.apply(c);e!=nil {t.Fatal(e)}
 b,e:=newApp(a.dir,a.origin,true);if e!=nil {t.Fatal(e)}
 if !reflect.DeepEqual(b.cfg.DestinationGroups,[]string{"US-CC-ES"})||b.cfg.RouteGroups==nil {t.Fatal("scoped empty state lost")}
 w:=send(b,"GET","/a?x=1&x=2","go.example.com","",nil)
 if w.Header().Get("Location")!="https://example.com/a?x=1&x=2" {t.Fatal("traffic changed")}
}
func TestScopedGroupsRejectCrossScopeMissingAndDowngrade(t *testing.T) {
 for _,kind:=range []string{"cross-route","cross-landing","missing","legacy","duplicate","version"} {
 t.Run(kind,func(t *testing.T){a:=fixture(t);c:=scopedFixture();if e:=a.apply(c);e!=nil{t.Fatal(e)};c=scopedFixture();c.Revision=a.cfg.Revision
 switch kind {case "cross-route":c.RouteGroups=[]string{"other"};case "cross-landing":c.DestinationGroups=[]string{"other"};case "missing":c.RouteGroups=nil;case "legacy":c.GroupSchema=0;c.Groups=[]string{"US-CC-ES"};c.RouteGroups=nil;c.DestinationGroups=nil;case "duplicate":c.RouteGroups=append(c.RouteGroups,c.RouteGroups[0]);case "version":c.GroupSchema=3}
 if a.apply(c)==nil {t.Fatal("unsafe scope accepted")};if a.cfg.Revision!=1{t.Fatal("partial write")}
 }) }
}
func TestScopedGroupsLegacyMigrationExact(t *testing.T) {
 a:=fixture(t);c:=catalogFixture();if e:=a.apply(c);e!=nil{t.Fatal(e)}
 before:=a.cfg;c=scopedFixture();c.Revision=before.Revision
 if e:=a.apply(c);e!=nil{t.Fatal(e)}
 if !reflect.DeepEqual(c.Routes,before.Routes)||!reflect.DeepEqual(c.Catalog,before.Catalog){t.Fatal("migration changed records")}
 if e:=a.apply(c);e!=errRevision{t.Fatal("stale write",e)}
}
