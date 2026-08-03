# Lockout-safe SSH hardening

Use when a VPS exposes public SSH and the owner wants to reduce exposure without breaking administrative or automation access.

## 1. Classify the real dependency surface

Before recommending a firewall change, inspect metadata only:

- effective `sshd -T` values and listening addresses;
- login-capable users and authorized-key entry counts, without reading or displaying key material;
- active inbound SSH sessions and retained successful-login metadata;
- provider/cloud firewall ownership and local firewall state;
- provider or emergency-console availability;
- known jobs and agents that use SSH.

Separate **inbound-to-this-host** from **outbound-from-this-host**. Blocking public inbound `22/tcp` normally does not affect local gateways, outbound APIs, Discord connections, or SSH initiated from the VPS toward another server. It can break administrators, bastions, CI, backup systems, or other automation that logs into the VPS, so reconcile those consumers first.

## 2. Never remove the only working access path

If no validated SSH key exists, do not disable password authentication, root login, or public port access. A safe sequence is:

1. verify the provider/emergency console in practice;
2. create or select a dedicated administrator and install only the public key;
3. keep the current session open and prove two fresh key-authenticated sessions;
4. arm a time-bounded rollback before changing authentication or firewall state;
5. disable SSH password authentication while public port access remains available;
6. validate private WireGuard/Tailscale or a stable bastion path;
7. restrict public `22/tcp` in runtime first, run positive and negative tests, then make the rule persistent;
8. mirror the final policy in the provider and host firewalls and cancel rollback only after both agree.

For dynamic residential IPs, prefer WireGuard/Tailscale or a stable bastion. Do not whitelist a broad ISP range. A provider-firewall `/32` is suitable only for a proven stable egress address.

## 3. Validation and rollback

Keep authentication hardening and network closure as separate gates. For each gate record:

- exact before/after state;
- active and fresh-session readback;
- provider-console test;
- rollback timer and cancellation evidence;
- provider firewall, host firewall, nftables and Fail2Ban agreement;
- authorized source success and unauthorized/public-path failure.

Firewall, `sshd_config`, production keys, and access-policy changes remain Critical Subset operations. Discovery or design approval does not authorize mutation.

## 4. Executive reporting

Answer the owner's lockout concern directly:

- say whether changing the port/firewall **now** is safe;
- name the current replacement access path, or state that none is validated;
- distinguish which MGS workloads are outbound and therefore unaffected;
- identify any unknown inbound consumer as a residual risk;
- recommend the next reversible phase rather than proposing an all-at-once lockdown.
