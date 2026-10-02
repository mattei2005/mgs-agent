package main

import (
	"errors"
	"net"
	"net/http"
	"strings"
)

func parseEdgeNetworks(text string) ([]*net.IPNet, error) {
	var nets []*net.IPNet
	for _, line := range strings.Split(text, "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		_, network, e := net.ParseCIDR(line)
		if e != nil {
			return nil, errors.New("invalid edge network")
		}
		ones, _ := network.Mask.Size()
		if ones < 12 {
			return nil, errors.New("edge network too broad")
		}
		nets = append(nets, network)
	}
	if len(nets) == 0 || len(nets) > 100 {
		return nil, errors.New("edge networks required")
	}
	return nets, nil
}
func edgeGuard(next http.Handler, nets []*net.IPNet) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		host, _, e := net.SplitHostPort(r.RemoteAddr)
		ip := net.ParseIP(host)
		allowed := false
		if e == nil && ip != nil {
			for _, n := range nets {
				if n.Contains(ip) {
					allowed = true
					break
				}
			}
		}
		client := net.ParseIP(r.Header.Get("CF-Connecting-IP"))
		if !allowed || client == nil {
			http.Error(w, "origin access forbidden", 403)
			return
		}
		clone := r.Clone(r.Context())
		clone.RemoteAddr = net.JoinHostPort(client.String(), "0")
		next.ServeHTTP(w, clone)
	})
}
