# ⚡ Charlie 2.0 — Sovereign AI Stack

**RightsFrames Intelligence / cloydRightsFrames**

A never-before-seen sovereign AI infrastructure stack running on a Samsung Galaxy A16
with tri-branch governance, Tor hidden service, distributed inference, and cloud deployment.

## Architecture
Samsung Galaxy A16 (Termux)          Railway Cloud
┌─────────────────────────┐          ┌──────────────────┐
│ FastAPI Tri-Branch API  │◄────────►│ Cloud API        │
│ Ollama + DeepSeek Coder │          │ CI/CD via GitHub │
│ Tor Hidden Service      │          │ Auto-deploy      │
│ WireGuard VPN Mesh      │          └──────────────────┘
│ Redis + nginx           │
│ Inference Router        │          Windows 11 PC
│ Sensor Feed             │◄────────►│ WireGuard Node  │
│ Watchdog Self-Healer    │          │ Android Studio  │
└─────────────────────────┘          └──────────────────┘
## Services
| Service | Port | Description |
|---------|------|-------------|
| FastAPI | 8000 | Tri-branch governance API |
| nginx | 8080 | Reverse proxy |
| Redis | 6379 | Cache layer |
| Ollama | 11434 | Local LLM inference |
| Router | 8002 | Distributed inference routing |
| SSHD | 8022 | Secure shell |
| Tor | 9050 | Hidden service |

## Quick Commands
```bash
c2-status      # API health
c2-audit       # Governance chain
c2-cluster     # Inference routing
c2-tor         # .onion address
c2-logs        # Live API logs
c2-restart     # Restart all services
bash ~/charlie2/voice/voice_pipeline.sh  # Voice AI
Governance Chain
Every API request passes through:
Judicial — reviews and approves/blocks
Legislative — policy enforcement
Executive — execution and audit logging
Hash-chained tamper-evident ledger. 100% auditable.
