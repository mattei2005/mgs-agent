package main
import("net";"net/http")
func parseEdgeNetworks(text string)([]*net.IPNet,error){return nil,nil}
func edgeGuard(next http.Handler,nets []*net.IPNet)http.Handler{return next}
