package main

import (
 "net/http"
 "net/http/httptest"
 "strings"
 "testing"
)

func TestEdgeGuardBlocksDirectOriginAndSpoofedClientHeaders(t *testing.T){
 networks,e:=parseEdgeNetworks("173.245.48.0/20\n2400:cb00::/32\n");if e!=nil{t.Fatal(e)}
 handler:=edgeGuard(http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){w.WriteHeader(204)}),networks)
 r:=httptest.NewRequest("GET","https://route.mgsdigitalcorp.com/",nil);r.RemoteAddr="203.0.113.8:1000";r.Header.Set("CF-Connecting-IP","198.51.100.7");w:=httptest.NewRecorder();handler.ServeHTTP(w,r);if w.Code!=403{t.Fatal("direct origin allowed")}
}
func TestEdgeGuardAllowsOnlyCloudflareWithValidClientAddress(t *testing.T){
 networks,e:=parseEdgeNetworks("173.245.48.0/20\n2400:cb00::/32\n");if e!=nil{t.Fatal(e)}
 handler:=edgeGuard(http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){if r.RemoteAddr!="198.51.100.7:0"{t.Error("trusted client address not passed")};w.WriteHeader(204)}),networks)
 for _,remote:=range []string{"173.245.48.6:1000","[2400:cb00::1]:1000"}{r:=httptest.NewRequest("GET","https://route.mgsdigitalcorp.com/",nil);r.RemoteAddr=remote;r.Header.Set("CF-Connecting-IP","198.51.100.7");w:=httptest.NewRecorder();handler.ServeHTTP(w,r);if w.Code!=204{t.Fatal(w.Code)}}
 r:=httptest.NewRequest("GET","https://route.mgsdigitalcorp.com/",nil);r.RemoteAddr="173.245.48.6:1000";r.Header.Set("CF-Connecting-IP","invalid");w:=httptest.NewRecorder();handler.ServeHTTP(w,r);if w.Code!=403{t.Fatal("invalid client IP accepted")}
 for _,s:=range []string{"", "0.0.0.0/0","bad"}{if _,e:=parseEdgeNetworks(strings.TrimSpace(s));e==nil{t.Fatal("invalid trust accepted")}}
}
