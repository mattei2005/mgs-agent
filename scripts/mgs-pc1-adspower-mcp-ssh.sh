#!/usr/bin/env bash
# Private stdio bridge for the official AdsPower MCP on PC1.
# The Python proxy keeps both gateways connected while serializing active
# Zeus/Ares tool sequences through the shared PC1 lease.
set -euo pipefail
exec /usr/bin/python3 /root/mgs-agent/scripts/mgs-pc1-adspower-mcp-proxy.py
