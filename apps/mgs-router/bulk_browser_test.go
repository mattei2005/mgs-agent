package main
import("bytes";"encoding/json";"net/http/httptest";"net/url";"os/exec";"testing")
func TestBulkBrowserWorkflow(t *testing.T){
 a:=fixture(t);c:=Config{ActionSchema:1,GroupSchema:2,RouteGroups:[]string{"Common","Empty"},DestinationGroups:[]string{"Common","Empty"},Catalog:[]Destination{{ID:"lp-1",Name:"LP1",URL:"https://example.com/a",Group:"Common"},{ID:"lp-2",Name:"LP2",URL:"https://example.com/b",Group:"Common"},{ID:"lp-unused",Name:"Unused",URL:"https://example.com/unused"}},Routes:[]Route{{Host:"go.example.com",Path:"/a",Name:"A",Group:"Common",Destinations:[]Target{{URL:"https://example.com/a",Weight:30,DestinationID:"lp-1"},{URL:"https://example.com/b",Weight:70,DestinationID:"lp-2"}}},{Host:"go.example.com",Path:"/b",Name:"B",Group:"Common",Destination:"https://example.com/a",DestinationID:"lp-1"}}}
 if e:=a.apply(c);e!=nil{t.Fatal(e)}
 srv:=httptest.NewServer(a);defer srv.Close();u,_:=url.Parse(srv.URL);a.origin=srv.URL;a.adminHost=u.Host;a.secure=false
 password:=randomHex(24);if e:=a.addTestUser("bulk-test",password);e!=nil{t.Fatal(e)}
 form:=url.Values{"username":{"bulk-test"},"password":{password}};w:=send(a,"POST","/login",a.adminHost,form.Encode(),map[string]string{"Origin":a.origin,"Content-Type":"application/x-www-form-urlencoded"});if w.Code!=303{t.Fatal("login failed")}
 input,_:=json.Marshal(map[string]string{"url":srv.URL,"session":w.Result().Cookies()[0].Value});cmd:=exec.Command("/root/.local/share/mgs-router-toolchain/qa-venv/bin/python","tests/bulk_browser_smoke.py");cmd.Stdin=bytes.NewReader(input);output,e:=cmd.CombinedOutput();if e!=nil{t.Fatalf("bulk browser failed: %v\n%s",e,output)};t.Log(string(output))
 if len(a.cfg.Routes)!=2||len(a.cfg.Catalog)!=3{t.Fatal("local cleanup original inventory mismatch")}
 for _,r:=range a.cfg.Routes{if r.Disabled{t.Fatal("original route disabled after cleanup")}}
}
func TestDisabledSchemaRejectAndLegacyHTTP500(t *testing.T){
 a:=fixture(t);c:=catalogFixture();c.Routes[0].Disabled=true;if a.apply(c)==nil{t.Fatal("disabled flag accepted without schema")};c.Routes[0].Disabled=false;c.Catalog[0].Disabled=true;if a.apply(c)==nil{t.Fatal("disabled LP accepted without schema")}
 c=Config{ActionSchema:1,Routes:[]Route{{Host:"go.example.com",Path:"/source",ResponseStatus:500}}};if e:=a.apply(c);e!=nil{t.Fatal(e)}
 if send(a,"GET","/source","go.example.com","",nil).Code!=500{t.Fatal("source500 changed")};c.Revision=a.cfg.Revision;c.Routes[0].Disabled=true;if e:=a.apply(c);e!=nil{t.Fatal(e)};if send(a,"HEAD","/source","go.example.com","",nil).Code!=404{t.Fatal("disabled source500 still responds500")}
}
