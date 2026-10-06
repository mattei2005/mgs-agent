package main

import (
	"errors"
 "math"
	"math/rand/v2"
	"net"
	"net/url"
	"strings"
)

var utmTemplates = map[string]bool{"utm_source": true, "utm_medium": true, "utm_campaign": true, "utm_term": true, "utm_content": true}

// Literal Keitaro compatibility: substitute present UTM macros only; preserve
// missing macros, fixed URLs and fragments, and do not append unrelated input.
func resolveKeitaroQuery(destination, raw string) string {
	values := map[string]string{}
	for _, part := range strings.Split(raw, "&") {
		kv := strings.SplitN(part, "=", 2)
		key, e := url.QueryUnescape(kv[0])
		if e != nil || !utmTemplates[key] || len(kv) != 2 {
			continue
		}
		value, e := url.QueryUnescape(kv[1])
		if e != nil {
			continue
		}
		values[key] = strings.ReplaceAll(url.QueryEscape(value), "~", "%7E") // PHP urlencode parity.
	}
	for key, value := range values {
		destination = strings.ReplaceAll(destination, "{"+key+"}", value)
		destination = strings.ReplaceAll(destination, url.QueryEscape("{"+key+"}"), value)
	}
	return destination
}

func validateDestination(destination, admin string, hosts map[string]bool) error {
	if len(destination) > 8192 || strings.ContainsAny(destination, "\r\n\t") {
		return errors.New("invalid destination")
	}
	u, e := url.Parse(destination)
	if e != nil || u.Scheme != "https" || u.Host == "" || u.User != nil || u.Opaque != "" {
		return errors.New("destination must be an HTTPS URL without credentials")
	}
	dh := strings.ToLower(u.Hostname())
	if dh == "localhost" || !strings.Contains(dh, ".") || strings.HasSuffix(dh, ".local") || strings.HasSuffix(dh, ".internal") || strings.EqualFold(u.Host, admin) || hosts[strings.ToLower(u.Host)] || hosts[dh] {
		return errors.New("destination cannot point to the panel or a route domain")
	}
	if ip := net.ParseIP(dh); ip != nil && (ip.IsPrivate() || ip.IsLoopback() || ip.IsLinkLocalUnicast() || ip.IsUnspecified() || !ip.IsGlobalUnicast()) {
		return errors.New("nonpublic destination not allowed")
	}
	if u.Port() != "" && u.Port() != "443" {
		return errors.New("destination port must be 443")
	}
	if strings.ContainsAny(u.Host+u.Path, "{}") {
		return errors.New("templates allowed only in UTM query values")
	}
	for _, part := range strings.Split(u.RawQuery, "&") {
		kv := strings.SplitN(part, "=", 2)
		key, e := url.QueryUnescape(kv[0])
		if e != nil {
			return errors.New("invalid query encoding")
		}
		value := ""
		if len(kv) == 2 {
			value, e = url.QueryUnescape(kv[1])
			if e != nil {
				return errors.New("invalid query encoding")
			}
		}
		if strings.ContainsAny(key+value, "{}") && !(utmTemplates[key] && strings.HasPrefix(value, "{") && strings.HasSuffix(value, "}") && utmTemplates[strings.TrimSuffix(strings.TrimPrefix(value, "{"), "}")]) {
			return errors.New("unsupported query template")
		}
	}
	return nil
}
func (a *App) validate(c Config) (map[string]Route, error) {
	if c.ActionSchema != 0 && c.ActionSchema != 1 {
		return nil, errors.New("unsupported action schema")
	}
	if c.Revision < 0 || len(c.Routes) > 10000 {
		return nil, errors.New("invalid route configuration")
	}
	idx := make(map[string]Route, len(c.Routes))
	hosts := map[string]bool{}
	for _, r := range c.Routes {
		hosts[r.Host] = true
	}
	if _, e := a.validateCatalog(c, hosts); e != nil {
		return nil, e
	}
	disabledIDs := map[string]bool{}
	for _, d := range c.Catalog {
		if d.Disabled {
			if c.ActionSchema != 1 {
				return nil, errors.New("disabled state requires action schema")
			}
			disabledIDs[d.ID] = true
		}
	}
	for _, r := range c.Routes {
		if r.Disabled && c.ActionSchema != 1 {
			return nil, errors.New("disabled state requires action schema")
		}
		if !validDomain(r.Host, a.adminHost) {
			return nil, errors.New("invalid route hostname")
		}
		if r.Path == "" || r.Path[0] != '/' || strings.HasPrefix(r.Path, "//") || reserved(r.Path) || strings.ContainsAny(r.Path, "? #%\\\r\n\t") || len(r.Path) > 1024 {
			return nil, errors.New("invalid or reserved route path")
		}
		if len(r.Name) > 300 || strings.ContainsAny(r.Name, "\r\n\t") {
			return nil, errors.New("invalid route name")
		}
		if r.Destination != "" && len(r.Destinations) > 0 {
			return nil, errors.New("use one destination or weighted destinations, not both")
		}
		if r.ResponseStatus != 0 {
			if r.ResponseStatus != 500 || r.Destination != "" || r.DestinationID != "" || len(r.Destinations) != 0 || r.RelativeWeights {
				return nil, errors.New("only empty source HTTP500 is supported")
			}
		} else if len(r.Destinations) == 0 {
			if r.RelativeWeights {
				return nil, errors.New("relative weights require destinations")
			}
			if e := validateDestination(r.Destination, a.adminHost, hosts); e != nil {
				return nil, e
			}
		} else {
			if len(r.Destinations) > 100 {
				return nil, errors.New("too many destinations")
			}
			total := 0.0
			for _, target := range r.Destinations {
				if math.IsNaN(target.Weight) || math.IsInf(target.Weight,0) || target.Weight < 0.000000001 || target.Weight > 1000000 || (!r.RelativeWeights && target.Weight > 100) {
					return nil, errors.New("invalid destination weight")
				}
				total += target.Weight
				if e := validateDestination(target.URL, a.adminHost, hosts); e != nil {
					return nil, e
				}
			}
			if !r.RelativeWeights && math.Abs(total-100) > 0.00000001 {
				return nil, errors.New("destination percentages must total 100")
			}
		}
		key := r.Host + "\n" + r.Path
		if _, ok := idx[key]; ok {
			return nil, errors.New("duplicate route")
		}
		// Build only an effective runtime copy. Preserve configured weights/URLs.
		if disabledIDs[r.DestinationID] {
			r.Disabled = true
		}
		if len(r.Destinations) > 0 {
			active := make([]Target, 0, len(r.Destinations))
			for _, t := range r.Destinations {
				if !disabledIDs[t.DestinationID] {
					active = append(active, t)
				}
			}
			if len(active) == 0 {
				r.Disabled = true
			}
			r.Destinations = active
		}
		idx[key] = r
	}
	return idx, nil
}
func targetAt(route Route,n int) string { return targetAtValue(route,float64(n)) }
func targetAtValue(route Route, n float64) string {
	if len(route.Destinations) == 0 {
		return route.Destination
	}
	for _, target := range route.Destinations {
		if n < target.Weight {
			return target.URL
		}
		n -= target.Weight
	}
	return "" // Unreachable for a validated route and n in [0,100).
}
func pickTarget(route Route) string {
	if len(route.Destinations) == 0 {
		return route.Destination
	}
	total := 0.0
	for _, target := range route.Destinations {
		total += target.Weight
	}
	return targetAtValue(route, rand.Float64()*total)
}

// Preserve the incoming raw query exactly. UTM template pairs are omitted when
// supplied by the input, so escaped bytes, duplicate keys and order survive once.
func resolveQuery(destination, raw string) string {
	q := strings.IndexByte(destination, '?')
	if q >= 0 {
		present := map[string]bool{}
		for _, part := range strings.Split(raw, "&") {
			key := strings.SplitN(part, "=", 2)[0]
			if decoded, e := url.QueryUnescape(key); e == nil {
				present[decoded] = true
			}
		}
		parts := []string{}
		for _, part := range strings.Split(destination[q+1:], "&") {
			kv := strings.SplitN(part, "=", 2)
			key, _ := url.QueryUnescape(kv[0])
			value := ""
			if len(kv) == 2 {
				value, _ = url.QueryUnescape(kv[1])
			}
			if len(kv) == 2 && value == "{"+key+"}" && utmTemplates[key] {
				if !present[key] {
					parts = append(parts, kv[0]+"=")
				}
			} else {
				parts = append(parts, part)
			}
		}
		destination = destination[:q]
		if len(parts) > 0 {
			destination += "?" + strings.Join(parts, "&")
		}
	}
	if raw != "" {
		if strings.Contains(destination, "?") {
			if !strings.HasSuffix(destination, "?") && !strings.HasSuffix(destination, "&") {
				destination += "&"
			}
		} else {
			destination += "?"
		}
		destination += raw
	}
	return destination
}
