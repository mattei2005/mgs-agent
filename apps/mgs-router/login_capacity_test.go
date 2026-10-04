package main

import (
 "fmt"
 "net/http/httptest"
 "strings"
 "testing"
 "time"
)

func TestLoginCapacityCannotBlockPreviouslySeenHealthySource(t *testing.T) {
 a := fixture(t)
 now:=time.Now()
 for i:=0;i<10000;i++ { a.attempts[fmt.Sprintf("10.0.%d.%d",i/256,i%256)]=Attempt{Count:1,Until:now.Add(15*time.Minute)} }
 a.attempts["192.0.2.10"]=Attempt{Count:1,Until:now.Add(15*time.Minute)}
 r:=httptest.NewRequest("POST","/login",strings.NewReader("username=missing&password=synthetic"))
 r.RemoteAddr="192.0.2.10:12345"
 r.Header.Set("Origin",a.origin);r.Header.Set("Content-Type","application/x-www-form-urlencoded")
 w:=httptest.NewRecorder();a.login(w,r)
 if w.Code==429 { t.Fatal("global cardinality blocked healthy source") }
}

func TestLoginNewSourceAtCapacityDoesNotGlobalBlock(t *testing.T) {
 a:=fixture(t); now:=time.Now()
 for i:=0;i<10000;i++ { a.attempts[fmt.Sprintf("10.0.%d.%d",i/256,i%256)]=Attempt{Count:1,Until:now.Add(15*time.Minute)} }
 r:=httptest.NewRequest("POST","/login",strings.NewReader("username=missing&password=synthetic"))
 r.RemoteAddr="192.0.2.20:12345";r.Header.Set("Origin",a.origin);r.Header.Set("Content-Type","application/x-www-form-urlencoded")
 w:=httptest.NewRecorder();a.login(w,r)
 if w.Code==429 {t.Fatal("new legitimate source globally blocked")}
 if len(a.attempts)>10000 {t.Fatal("attempt memory capacity exceeded")}
}

func TestLoginPerSourceLimitRemains(t *testing.T) {
 a:=fixture(t);a.attempts["192.0.2.30"]=Attempt{Count:5,Until:time.Now().Add(15*time.Minute)}
 r:=httptest.NewRequest("POST","/login",strings.NewReader("username=missing&password=synthetic"))
 r.RemoteAddr="192.0.2.30:12345";r.Header.Set("Origin",a.origin);r.Header.Set("Content-Type","application/x-www-form-urlencoded")
 w:=httptest.NewRecorder();a.login(w,r)
 if w.Code!=429 {t.Fatal("per-source limit lost")}
}
