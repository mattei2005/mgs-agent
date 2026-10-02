package main

import (
 "context"
 "crypto/pbkdf2"
 "crypto/rand"
 "crypto/sha256"
 "crypto/subtle"
 "embed"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "log"
 "net"
 "net/http"
 "net/url"
 "os"
 "os/signal"
 "path/filepath"
 "regexp"
 "strings"
 "sync"
 "syscall"
 "time"
)

//go:embed web/*
var web embed.FS

type Route struct { Host string `json:"host"`; Path string `json:"path"`; Destination string `json:"destination"` }
type Config struct { Revision int `json:"revision"`; Routes []Route `json:"routes"` }
type User struct { Username string `json:"username"`; Salt string `json:"salt"`; Hash string `json:"hash"`; Iterations int `json:"iterations"` }
type Session struct { Username, CSRF string; Expires time.Time }
type Attempt struct { Count int; Until time.Time }
type App struct {
 mu sync.RWMutex
 cfg Config
 index map[string]string
 users map[string]User
 sessions map[string]Session
 attempts map[string]Attempt
 dir,origin,adminHost string
 secure bool
 authSlots chan struct{}
}
var errRevision=errors.New("configuration changed; refresh before saving")
var hostPattern=regexp.MustCompile(`^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$`)
var userPattern=regexp.MustCompile(`^[a-z][a-z0-9_-]{2,39}$`)

func newApp(dir,origin string,secure bool)(*App,error){
 u,e:=url.Parse(origin);if e!=nil||u.Host==""||u.Path!=""||(u.Scheme!="https"&&u.Scheme!="http"){return nil,errors.New("invalid admin origin")}
 if e=os.MkdirAll(dir,0700);e!=nil{return nil,e}
 a:=&App{dir:dir,origin:origin,adminHost:strings.ToLower(u.Host),secure:secure,cfg:Config{Routes:[]Route{}},index:map[string]string{},users:map[string]User{},sessions:map[string]Session{},attempts:map[string]Attempt{},authSlots:make(chan struct{},2)}
 b,e:=os.ReadFile(filepath.Join(dir,"routes.json"));if e==nil{if e=json.Unmarshal(b,&a.cfg);e!=nil{return nil,errors.New("invalid routes store")};idx,e:=a.validate(a.cfg);if e!=nil{return nil,e};a.index=idx}else if !os.IsNotExist(e){return nil,e}
 b,e=os.ReadFile(filepath.Join(dir,"users.json"));if e==nil{if e=json.Unmarshal(b,&a.users);e!=nil{return nil,errors.New("invalid user store")};for k,u:=range a.users{if k!=u.Username||!userPattern.MatchString(k)||u.Iterations<600000||u.Iterations>1000000||len(u.Salt)!=48||len(u.Hash)!=64{return nil,errors.New("invalid user record")}}}else if !os.IsNotExist(e){return nil,e}
 return a,nil
}
func reserved(p string)bool{return p=="/"||p=="/login"||p=="/logout"||p=="/admin"||strings.HasPrefix(p,"/admin/")||strings.HasPrefix(p,"/api/")||strings.HasPrefix(p,"/assets/")||p=="/healthz"}
func(a *App)validate(c Config)(map[string]string,error){
 if len(c.Routes)>10000{return nil,errors.New("too many routes")}
 idx:=make(map[string]string,len(c.Routes));hosts:=map[string]bool{}
 for _,r:=range c.Routes{hosts[r.Host]=true}
 for _,r:=range c.Routes{
  if len(r.Host)>253||r.Host!=strings.ToLower(r.Host)||!hostPattern.MatchString(r.Host)||!strings.Contains(r.Host,".")||strings.Contains(r.Host,"..")||r.Host=="localhost"{return nil,errors.New("invalid route hostname")}
  if r.Path==""||r.Path[0]!='/'||strings.HasPrefix(r.Path,"//")||reserved(r.Path)||strings.ContainsAny(r.Path,"? #%\\\r\n\t")||len(r.Path)>1024{return nil,errors.New("invalid or reserved route path")}
  if strings.ContainsAny(r.Destination,"\r\n\t")||len(r.Destination)>8192{return nil,errors.New("invalid destination")}
  u,e:=url.Parse(r.Destination);if e!=nil||u.Scheme!="https"||u.Host==""||u.User!=nil||u.Fragment!=""||u.Opaque!=""{return nil,errors.New("destination must be an HTTPS URL without credentials or fragment")}
  dh:=strings.ToLower(u.Hostname());if dh=="localhost"||!strings.Contains(dh,".")||strings.HasSuffix(dh,".local")||strings.HasSuffix(dh,".internal")||strings.EqualFold(u.Host,a.adminHost)||hosts[u.Host]{return nil,errors.New("destination cannot point to the panel or a route domain")}
  if ip:=net.ParseIP(dh);ip!=nil&&(ip.IsPrivate()||ip.IsLoopback()||ip.IsLinkLocalUnicast()||ip.IsUnspecified()||!ip.IsGlobalUnicast()){return nil,errors.New("nonpublic destination not allowed")}
  if u.Port()!=""&&u.Port()!="443"{return nil,errors.New("destination port must be 443")}
  key:=r.Host+"\n"+r.Path;if _,ok:=idx[key];ok{return nil,errors.New("duplicate route")};idx[key]=r.Destination
 }
 return idx,nil
}
func atomicJSON(path string,v any)error{
 b,e:=json.MarshalIndent(v,"","  ");if e!=nil{return e};b=append(b,'\n')
 f,e:=os.CreateTemp(filepath.Dir(path),".router-state-");if e!=nil{return e};name:=f.Name();ok:=false
 defer func(){f.Close();if !ok{os.Remove(name)}}()
 if e=f.Chmod(0600);e!=nil{return e};if _,e=f.Write(b);e!=nil{return e};if e=f.Sync();e!=nil{return e};if e=f.Close();e!=nil{return e};if e=os.Rename(name,path);e!=nil{return e};ok=true
 d,e:=os.Open(filepath.Dir(path));if e==nil{e=d.Sync();d.Close()};return e
}
func(a *App)apply(c Config)error{
 idx,e:=a.validate(c);if e!=nil{return e}
 a.mu.Lock();defer a.mu.Unlock();if c.Revision!=a.cfg.Revision{return errRevision}
 c.Revision++;if c.Routes==nil{c.Routes=[]Route{}};if e=atomicJSON(filepath.Join(a.dir,"routes.json"),c);e!=nil{return e};a.cfg=c;a.index=idx;return nil
}
func randomHex(n int)string{b:=make([]byte,n);if _,e:=rand.Read(b);e!=nil{panic("entropy unavailable")};return hex.EncodeToString(b)}
func digest(password,salt string,iterations int)string{b,_:=hex.DecodeString(salt);key,e:=pbkdf2.Key(sha256.New,password,b,iterations,32);if e!=nil{return ""};return hex.EncodeToString(key)}
func(a *App)addUser(username,password string)error{
 if !userPattern.MatchString(username)||len(password)<20||len(password)>256{return errors.New("username invalid or generated password too short")}
 u:=User{Username:username,Salt:randomHex(24),Iterations:600000};u.Hash=digest(password,u.Salt,u.Iterations)
 a.mu.Lock();defer a.mu.Unlock();if _,ok:=a.users[username];ok{return errors.New("user already exists; no credential overwrite")}
 next:=map[string]User{};for k,v:=range a.users{next[k]=v};next[username]=u;if e:=atomicJSON(filepath.Join(a.dir,"users.json"),next);e!=nil{return e};a.users=next;return nil
}
func safeEqual(a,b string)bool{return len(a)==len(b)&&subtle.ConstantTimeCompare([]byte(a),[]byte(b))==1}
func jsonReply(w http.ResponseWriter,status int,v any){w.Header().Set("Content-Type","application/json; charset=utf-8");w.WriteHeader(status);json.NewEncoder(w).Encode(v)}
func(a *App)session(r *http.Request)(Session,bool){
 c,e:=r.Cookie("mgs_session");if e!=nil||len(c.Value)!=64{return Session{},false};key:=sha256.Sum256([]byte(c.Value));a.mu.RLock();s,ok:=a.sessions[hex.EncodeToString(key[:])];a.mu.RUnlock();return s,ok&&s.Expires.After(time.Now())
}
func(a *App)csrf(r *http.Request,s Session)bool{return r.Header.Get("Origin")==a.origin&&safeEqual(r.Header.Get("X-CSRF-Token"),s.CSRF)}
func(a *App)asset(w http.ResponseWriter,name,contentType string){b,e:=web.ReadFile("web/"+name);if e!=nil{http.Error(w,"asset unavailable",500);return};w.Header().Set("Content-Type",contentType);w.Write(b)}
func(a *App)login(w http.ResponseWriter,r *http.Request){
 if r.Method=="GET"{a.asset(w,"login.html","text/html; charset=utf-8");return}
 if r.Method!="POST"{w.WriteHeader(405);return}
 if r.Header.Get("Origin")!=a.origin{http.Error(w,"invalid origin",403);return}
 r.Body=http.MaxBytesReader(w,r.Body,4096);if e:=r.ParseForm();e!=nil{http.Error(w,"invalid request",400);return}
 username:=r.Form.Get("username");password:=r.Form.Get("password");if len(username)>40||len(password)>256{http.Error(w,"invalid request",400);return}
 host,_,_:=net.SplitHostPort(r.RemoteAddr);key:=host
 now:=time.Now();a.mu.Lock();for k,v:=range a.attempts{if v.Until.Before(now){delete(a.attempts,k)}};at:=a.attempts[key];if at.Until.Before(now){at=Attempt{Until:now.Add(15*time.Minute)}};if at.Count>=5||len(a.attempts)>=10000{a.mu.Unlock();w.Header().Set("Retry-After","900");http.Error(w,"too many attempts",429);return};at.Count++;a.attempts[key]=at;u,exists:=a.users[username];a.mu.Unlock()
 select{case a.authSlots<-struct{}{}:defer func(){<-a.authSlots}();default:w.Header().Set("Retry-After","5");http.Error(w,"try again",429);return}
 if !exists{u=User{Salt:strings.Repeat("0",48),Hash:strings.Repeat("0",64),Iterations:600000}}
 actual:=digest(password,u.Salt,u.Iterations);if !safeEqual(actual,u.Hash)||!exists{http.Redirect(w,r,"/login?error=1",303);return}
 token:=randomHex(32);kh:=sha256.Sum256([]byte(token));s:=Session{Username:username,CSRF:randomHex(32),Expires:now.Add(8*time.Hour)}
 a.mu.Lock();for k,v:=range a.sessions{if v.Expires.Before(now){delete(a.sessions,k)}};if len(a.sessions)>=1000{a.mu.Unlock();http.Error(w,"session limit",503);return};a.sessions[hex.EncodeToString(kh[:])]=s;delete(a.attempts,key);a.mu.Unlock()
 http.SetCookie(w,&http.Cookie{Name:"mgs_session",Value:token,Path:"/",Secure:a.secure,HttpOnly:true,SameSite:http.SameSiteStrictMode,MaxAge:28800});http.Redirect(w,r,"/admin",303)
}
func(a *App)ServeHTTP(w http.ResponseWriter,r *http.Request){
 w.Header().Set("Cache-Control","no-store");w.Header().Set("X-Content-Type-Options","nosniff");w.Header().Set("Referrer-Policy","no-referrer");w.Header().Set("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'");w.Header().Set("Permissions-Policy","camera=(), microphone=(), geolocation=()")
 if a.secure{w.Header().Set("Strict-Transport-Security","max-age=31536000")}
 if strings.EqualFold(r.Host,a.adminHost){
  if r.URL.Path=="/healthz"&&r.Method=="GET"{jsonReply(w,200,map[string]string{"status":"ok","version":"0.1.0"});return}
  if r.URL.Path=="/login"{a.login(w,r);return}
  if r.URL.Path=="/assets/app.js"&&r.Method=="GET"{a.asset(w,"app.js","text/javascript; charset=utf-8");return}
  if r.URL.Path=="/assets/style.css"&&r.Method=="GET"{a.asset(w,"style.css","text/css; charset=utf-8");return}
  if r.URL.Path=="/"{http.Redirect(w,r,"/admin",302);return}
  if r.URL.Path=="/admin"{if _,ok:=a.session(r);!ok{http.Redirect(w,r,"/login",303);return};a.asset(w,"admin.html","text/html; charset=utf-8");return}
  if strings.HasPrefix(r.URL.Path,"/api/")||r.URL.Path=="/logout"{
   s,ok:=a.session(r);if !ok{jsonReply(w,401,map[string]string{"error":"authentication required"});return}
   if r.URL.Path=="/api/me"&&r.Method=="GET"{jsonReply(w,200,map[string]string{"username":s.Username,"csrf":s.CSRF});return}
   if r.URL.Path=="/api/routes"&&r.Method=="GET"{a.mu.RLock();c:=a.cfg;a.mu.RUnlock();jsonReply(w,200,c);return}
   if r.URL.Path=="/api/routes"&&r.Method=="POST"{
    if !a.csrf(r,s){jsonReply(w,403,map[string]string{"error":"invalid request origin or csrf"});return}
    if !strings.HasPrefix(r.Header.Get("Content-Type"),"application/json"){jsonReply(w,415,map[string]string{"error":"JSON required"});return}
    r.Body=http.MaxBytesReader(w,r.Body,2<<20);dec:=json.NewDecoder(r.Body);dec.DisallowUnknownFields();var c Config;if e:=dec.Decode(&c);e!=nil{jsonReply(w,400,map[string]string{"error":"invalid JSON"});return};if dec.Decode(&struct{}{})!=io.EOF{jsonReply(w,400,map[string]string{"error":"unexpected extra data"});return}
    if e:=a.apply(c);e!=nil{code:=400;if errors.Is(e,errRevision){code=409};jsonReply(w,code,map[string]string{"error":e.Error()});return};a.mu.RLock();cfg:=a.cfg;a.mu.RUnlock();jsonReply(w,200,cfg);return
   }
   if r.URL.Path=="/logout"&&r.Method=="POST"{if !a.csrf(r,s){w.WriteHeader(403);return};c,_:=r.Cookie("mgs_session");kh:=sha256.Sum256([]byte(c.Value));a.mu.Lock();delete(a.sessions,hex.EncodeToString(kh[:]));a.mu.Unlock();http.SetCookie(w,&http.Cookie{Name:"mgs_session",Value:"",Path:"/",Secure:a.secure,HttpOnly:true,SameSite:http.SameSiteStrictMode,MaxAge:-1});jsonReply(w,200,map[string]bool{"ok":true});return}
   http.NotFound(w,r);return
  }
 }
 if reserved(r.URL.Path){http.NotFound(w,r);return}
 if r.Method!="GET"&&r.Method!="HEAD"{w.WriteHeader(405);return}
 if len(r.URL.RawQuery)>16384{http.Error(w,"query too long",414);return}
 a.mu.RLock();destination,ok:=a.index[strings.ToLower(r.Host)+"\n"+r.URL.EscapedPath()];a.mu.RUnlock();if !ok{http.NotFound(w,r);return}
 if r.URL.RawQuery!=""{if strings.Contains(destination,"?"){if !strings.HasSuffix(destination,"?")&&!strings.HasSuffix(destination,"&"){destination+="&"}}else{destination+="?"};destination+=r.URL.RawQuery}
 w.Header().Set("Location",destination);w.WriteHeader(http.StatusFound)
}
func main(){
 listen:=flag.String("listen","127.0.0.1:18787","listen address");dir:=flag.String("state","","private state directory");origin:=flag.String("origin","https://route.mgsdigitalcorp.com","exact panel origin");local:=flag.Bool("local-test",false,"permit insecure localhost-only tests");initUsers:=flag.Bool("init-users",false,"read new users JSON from stdin; requires owner credential confirmation");check:=flag.Bool("check",false,"validate state only");cert:=flag.String("tls-cert","","TLS certificate path");key:=flag.String("tls-key","","TLS key path");flag.Parse()
 if *dir==""{log.Fatal("private state directory required")};if *local&&!strings.HasPrefix(*listen,"127.0.0.1:"){log.Fatal("local test must bind loopback")}
 a,e:=newApp(*dir,*origin,!*local);if e!=nil{log.Fatal("state validation failed")}
 if *initUsers{var users []struct{Username string `json:"username"`;Password string `json:"password"`};dec:=json.NewDecoder(io.LimitReader(os.Stdin,8192));dec.DisallowUnknownFields();if e:=dec.Decode(&users);e!=nil||len(users)==0{log.Fatal("invalid user provisioning input")};for _,u:=range users{if e:=a.addUser(u.Username,u.Password);e!=nil{log.Fatal("user provisioning failed; reconcile state before retry")}};fmt.Printf("users_provisioned=%d\n",len(users));return}
 if *check{fmt.Printf("state_valid=true routes=%d users=%d\n",len(a.cfg.Routes),len(a.users));return}
 server:=&http.Server{Addr:*listen,Handler:a,ReadHeaderTimeout:5*time.Second,ReadTimeout:10*time.Second,WriteTimeout:10*time.Second,IdleTimeout:30*time.Second,MaxHeaderBytes:32<<10,ErrorLog:log.New(io.Discard,"",0)}
 if !*local&&(*cert==""||*key==""){log.Fatal("TLS certificate and key required outside localhost test mode")}
 stop:=make(chan os.Signal,1);signal.Notify(stop,syscall.SIGTERM,syscall.SIGINT);go func(){<-stop;ctx,cancel:=context.WithTimeout(context.Background(),10*time.Second);defer cancel();server.Shutdown(ctx)}()
 log.Printf("mgs-router starting; mode_local=%t",*local)
 if *local{e=server.ListenAndServe()}else{e=server.ListenAndServeTLS(*cert,*key)};if e!=nil&&!errors.Is(e,http.ErrServerClosed){log.Fatal("server stopped unexpectedly")}
}
