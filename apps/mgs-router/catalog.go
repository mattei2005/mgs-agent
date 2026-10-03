package main

import (
 "errors"
 "regexp"
 "strings"
)
var catalogIDPattern = regexp.MustCompile(`^[a-zA-Z0-9_-]{1,80}$`)
func validLabel(s string) bool {return len(s)>0 && len(s)<=300 && strings.TrimSpace(s)==s && !strings.ContainsAny(s,"\r\n\t")}
func (a *App) validateCatalog(c Config, hosts map[string]bool) (map[string]Destination,error) {
 if len(c.Catalog)>10000 || len(c.Groups)>1000 {return nil,errors.New("catalog too large")}
 groups:=map[string]bool{}
 for _,g:=range c.Groups {if !validLabel(g)||groups[g]{return nil,errors.New("invalid or duplicate group")};groups[g]=true}
 validGroup:=func(g string)bool{return g==""||groups[g]}
 catalog:=map[string]Destination{}
 for _,d:=range c.Catalog {
  if !catalogIDPattern.MatchString(d.ID)||!validLabel(d.Name)||!validGroup(d.Group){return nil,errors.New("invalid destination metadata")}
  if _,ok:=catalog[d.ID];ok{return nil,errors.New("duplicate destination ID")}
  if e:=validateDestination(d.URL,a.adminHost,hosts);e!=nil{return nil,e}
  catalog[d.ID]=d
 }
 ref:=func(id,url string)bool{if id==""{return true};d,ok:=catalog[id];return ok&&d.URL==url}
 for _,r:=range c.Routes {
  if !validGroup(r.Group)||!ref(r.DestinationID,r.Destination){return nil,errors.New("invalid route group or destination reference")}
  if len(r.Destinations)>0&&r.DestinationID!=""{return nil,errors.New("single reference on weighted route")}
  for _,t:=range r.Destinations {if !ref(t.DestinationID,t.URL){return nil,errors.New("invalid weighted destination reference")}}
 }
 return catalog,nil
}
