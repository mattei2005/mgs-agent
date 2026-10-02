package main

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"crypto/tls"
	"encoding/hex"
	"encoding/json"
	"io"
	"net"
	"net/http"
	"strings"
	"time"
)

const probePath = "/__mgs-router-check"

type probeResponse struct {
	Host      string `json:"host"`
	Challenge string `json:"challenge"`
	Signature string `json:"signature"`
}

func (a *App) registered(host string) bool {
	if host == a.adminHost {
		return true
	} // Panel control provides a positive probe without traffic DNS cutover.
	a.mu.RLock()
	defer a.mu.RUnlock()
	for _, d := range a.domains.Domains {
		if d == host {
			return true
		}
	}
	for _, r := range a.cfg.Routes {
		if r.Host == host {
			return true
		}
	}
	return false
}
func (a *App) probeSignature(host, challenge string) string {
	m := hmac.New(sha256.New, a.probeKey[:])
	m.Write([]byte(host + "\n" + challenge))
	return hex.EncodeToString(m.Sum(nil))
}
func (a *App) validProbe(p probeResponse, host, challenge string) bool {
	return p.Host == host && p.Challenge == challenge && safeEqual(p.Signature, a.probeSignature(host, challenge))
}
func (a *App) publicProbe(w http.ResponseWriter, r *http.Request) {
	host := strings.ToLower(r.Host)
	nonce := r.URL.Query().Get("challenge")
	b, e := hex.DecodeString(nonce)
	if r.Method != "GET" || !a.registered(host) || e != nil || len(b) != 16 {
		http.NotFound(w, r)
		return
	}
	jsonReply(w, 200, probeResponse{Host: host, Challenge: nonce, Signature: a.probeSignature(host, nonce)})
}
func publicIP(s string) bool {
	ip := net.ParseIP(s)
	if ip == nil || !ip.IsGlobalUnicast() || ip.IsPrivate() || ip.IsLoopback() || ip.IsLinkLocalUnicast() || ip.IsUnspecified() {
		return false
	}
	for _, prefix := range []string{"0.0.0.0/8", "100.64.0.0/10", "192.0.0.0/24", "192.0.2.0/24", "198.18.0.0/15", "198.51.100.0/24", "203.0.113.0/24", "2001:db8::/32"} {
		_, n, _ := net.ParseCIDR(prefix)
		if n.Contains(ip) {
			return false
		}
	}
	return true
}
func (a *App) checkDomain(ctx context.Context, host string) (bool, string) {
	ips, e := net.DefaultResolver.LookupHost(ctx, host)
	if e != nil || len(ips) == 0 {
		return false, "DNS não encontrado ou ainda em propagação."
	}
	for _, ip := range ips {
		if !publicIP(ip) {
			return false, "DNS aponta para endereço não público; verificação recusada."
		}
	}
	nonce := randomHex(16)
	transport := &http.Transport{TLSClientConfig: &tls.Config{MinVersion: tls.VersionTLS12, ServerName: host}, DialContext: func(ctx context.Context, network, address string) (net.Conn, error) {
		return (&net.Dialer{Timeout: 4 * time.Second}).DialContext(ctx, "tcp", net.JoinHostPort(ips[0], "443"))
	}}
	defer transport.CloseIdleConnections()
	client := &http.Client{Transport: transport, Timeout: 6 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}
	req, e := http.NewRequestWithContext(ctx, "GET", "https://"+host+probePath+"?challenge="+nonce, nil)
	if e != nil {
		return false, "Domínio inválido."
	}
	req.Header.Set("User-Agent", "MGS-Router-Domain-Check/1.0")
	response, e := client.Do(req)
	if e != nil {
		return false, "HTTPS indisponível ou certificado inválido. Confira DNS e proxy Cloudflare."
	}
	defer response.Body.Close()
	if response.StatusCode != 200 {
		return false, "O domínio ainda não está chegando ao MGS Router. Confira o destino DNS e o proxy Cloudflare."
	}
	var p probeResponse
	if json.NewDecoder(io.LimitReader(response.Body, 1024)).Decode(&p) != nil || !a.validProbe(p, host, nonce) {
		return false, "DNS/HTTPS respondem, mas o destino não é este MGS Router."
	}
	return true, "DNS e HTTPS confirmados neste MGS Router."
}
func (a *App) domainCheckAPI(w http.ResponseWriter, r *http.Request, s Session) {
	if r.Method != "POST" {
		w.WriteHeader(405)
		return
	}
	if !a.csrf(r, s) {
		jsonReply(w, 403, map[string]string{"error": "invalid request origin or csrf"})
		return
	}
	if !strings.HasPrefix(r.Header.Get("Content-Type"), "application/json") {
		jsonReply(w, 415, map[string]string{"error": "JSON required"})
		return
	}
	r.Body = http.MaxBytesReader(w, r.Body, 1024)
	var p struct {
		Host string `json:"host"`
	}
	d := json.NewDecoder(r.Body)
	d.DisallowUnknownFields()
	if d.Decode(&p) != nil || d.Decode(&struct{}{}) != io.EOF || (!validDomain(p.Host, a.adminHost) && p.Host != a.adminHost) || !a.registered(p.Host) {
		jsonReply(w, 400, map[string]string{"error": "Informe um domínio cadastrado."})
		return
	}
	select {
	case a.checkSlots <- struct{}{}:
		defer func() { <-a.checkSlots }()
	default:
		jsonReply(w, 429, map[string]string{"error": "Há uma verificação em andamento. Tente novamente em alguns segundos."})
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 6*time.Second)
	defer cancel()
	ok, message := a.checkDomain(ctx, p.Host)
	jsonReply(w, 200, map[string]any{"host": p.Host, "verified": ok, "message": message, "checked_at": time.Now().UTC().Format(time.RFC3339)})
}
