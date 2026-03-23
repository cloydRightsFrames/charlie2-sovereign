# ⚡ Charlie 2.0 — Sovereign AI VS Code Extension

**RightsFrames Intelligence / cloydRightsFrames**

Sovereign AI Copilot powered by Charlie 2.0 running on Samsung Galaxy A16.
No external cloud dependency. Your phone is the AI server.

## Features

| Command | Shortcut | Description |
|---|---|---|
| Ask Charlie 2.0 | Ctrl+Shift+A | Ask about selected code or anything |
| Explain Code | — | Explain selected code |
| Fix Code | Ctrl+Shift+F | Fix bugs, apply directly to editor |
| Generate Code | — | Describe → insert at cursor |
| Constitutional Review | — | Security + privacy audit |
| Debate This Code | — | 3-agent council debates quality |
| View Governance Chain | — | Live tri-branch audit viewer |
| Open Chat | Ctrl+Shift+C | Sidebar streaming chat |
| Generate ZK Proof | — | Cryptographic chain proof |

## Install on Predator PC

```bash
# Clone sovereign repo
git clone https://github.com/cloydRightsFrames/charlie2-sovereign
cd charlie2-sovereign/vscode-extension

# Build VSIX
npm install
npx vsce package --no-dependencies

# Install
code --install-extension charlie2-sovereign-2.0.0.vsix
Configure
Set charlie2.apiUrl in VS Code settings:
WireGuard mesh (recommended): http://10.99.0.1:8000
Same WiFi: http://PHONE_IP:8000
Railway cloud: https://your-app.up.railway.app
Architecture
Every AI response passes through:
RAG — memory-enhanced context
Constitutional enforcement — 6 articles
Debate council — 3-agent review (optional)
Governance audit — hash-chained ledger
Sovereign Stack
Running on Samsung Galaxy A16 ARM64:
Tor .onion hidden service
Local Ollama inference
Tri-branch governance (488+ records)
Zero-knowledge proofs
