package main

import (
 "net/http"
 "sync"
)

type Route struct { Host string `json:"host"`; Path string `json:"path"`; Destination string `json:"destination"` }
type Config struct { Revision int `json:"revision"`; Routes []Route `json:"routes"` }
type App struct { mu sync.RWMutex; cfg Config; dir string; origin string; secure bool }
func newApp(dir,origin string,secure bool)(*App,error){return &App{dir:dir,origin:origin,secure:secure},nil}
func(a *App)apply(c Config)error{return nil}
func(a *App)addTestUser(username,password string)error{return nil}
func(a *App)ServeHTTP(w http.ResponseWriter,r *http.Request){http.NotFound(w,r)}
func main(){}
