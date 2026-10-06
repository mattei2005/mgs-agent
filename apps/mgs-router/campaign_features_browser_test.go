package main
import("bytes";"crypto/sha256";"encoding/hex";"encoding/json";"fmt";"net/http/httptest";"net/url";"os/exec";"testing")
func TestCampaignFeaturesBrowser(t *testing.T){
 a:=fixture(t);c:=Config{GroupSchema:2,ActionSchema:1,Routes:[]Route{},RouteGroups:[]string{},DestinationGroups:[]string{}}
 for _,n:=range []int{20,23}{r:=Route{Host:"go.example.com",Path:fmt.Sprintf("/equal%d",n),Name:fmt.Sprintf("Equal %d",n),RelativeWeights:true};for i:=0;i<n;i++{r.Destinations=append(r.Destinations,Target{URL:fmt.Sprintf("https://example.com/page%d",i),Weight:5})};c.Routes=append(c.Routes,r)}
 c.Routes=append(c.Routes,Route{Host:"go.example.com",Path:"/click",Name:"Clicks",Destination:"https://example.com/a"});if e:=a.apply(c);e!=nil{t.Fatal(e)}
 srv:=httptest.NewServer(a);defer srv.Close();u,_:=url.Parse(srv.URL);a.origin=srv.URL;a.adminHost=u.Host;a.secure=false
 token:=randomHex(32);kh:=sha256.Sum256([]byte(token));key:=hex.EncodeToString(kh[:]);a.sessions[key]=Session{Username:"browser-qa",CSRF:randomHex(32)}
 input,_:=json.Marshal(map[string]string{"url":srv.URL,"session":token});cmd:=exec.Command("/root/.local/share/mgs-router-toolchain/qa-venv/bin/python","tests/campaign_features_smoke.py");cmd.Stdin=bytes.NewReader(input);out,e:=cmd.CombinedOutput();if e!=nil{t.Fatalf("browser: %v %s",e,out)};t.Log(string(out))
}
