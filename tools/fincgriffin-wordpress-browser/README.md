# Fincgriffin WordPress Persistent Browser

Persistent Chromium profile for manual WordPress authentication and recurring Zeus operations on `fincgriffin.com`.

- Runtime code is versioned here.
- Sensitive session state lives only at `/root/.hermes/profiles/zeus/browser-profiles/fincgriffin-wordpress-chromium` with mode `0700`.
- Safe status files live under `/root/.hermes/profiles/zeus/artifacts/`; they never contain cookie values.
- The visual login wrapper binds VNC/noVNC only to `127.0.0.1` and requires an SSH tunnel.
- Visual login and headless probe share one exclusive lock and must never run concurrently.
- Close the visual wrapper gracefully before running the probe so Chromium flushes cookies and releases `SingletonLock`.

Commands:

```text
/root/mgs-agent/scripts/zeus-fincgriffin-wordpress-login-browser.sh
/root/mgs-agent/scripts/zeus-fincgriffin-wordpress-session-probe.sh
```
