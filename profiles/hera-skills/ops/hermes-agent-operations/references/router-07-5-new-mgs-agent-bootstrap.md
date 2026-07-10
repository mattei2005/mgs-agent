## 5. New MGS agent bootstrap

When Rodolfo asks to start a new MGS agent/profile (Ares or future agents), use `references/mgs-new-agent-bootstrap.md`. Core rule: clone profile/config as needed, but immediately blank any inherited Discord bot token; do not create/enable the systemd gateway until the agent has its own dedicated bot token and Rodolfo confirms the Critical Subset system-file write.
