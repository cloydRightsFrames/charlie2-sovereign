# ⚡ Charlie 2.0 Android App

## Build on Predator PC

1. Clone the repo:
   git clone https://github.com/cloydRightsFrames/charlie2-android

2. Open Android Studio → File → Open → select charlie2-android folder

3. Let Gradle sync (2-5 min first time)

4. Update URLs in Charlie2Client.kt if needed:
   - Same WiFi: use phone IP (e.g. 192.168.x.x:8000)
   - WireGuard mesh: 10.99.0.1:8000 (default, already set)
   - After Railway deploy: set railwayUrl

5. Build → Run on Galaxy A16 (USB debug)
   OR Build → Generate Signed APK → install manually

## Screens
- Chat      — Ollama local AI with Railway cloud fallback
- Settings  — Configure API endpoints
- Audit     — Live tri-branch governance chain viewer

## WireGuard mesh (recommended)
Phone IP:  10.99.0.1
PC IP:     10.99.0.2
Configs:   ~/charlie2/wireguard/
