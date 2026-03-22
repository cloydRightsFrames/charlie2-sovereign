# Charlie 2.0 Android App

## Open in Android Studio (Predator PC)

1. Copy ~/charlie2/android-app/ to your Windows PC
   - Via rsync: bash ~/charlie2/sync_to_pc.sh
   - Or via USB

2. Open Android Studio → Open → select android-app folder

3. Let Gradle sync (2-5 min first time)

4. Update Charlie2Client URLs in MainActivity.kt:
   - baseUrl   = your phone IP on same WiFi (e.g. 192.168.x.x:8000)
   - ollamaUrl = same phone IP :11434
   - railwayUrl = https://charlie2-api.up.railway.app (after deploy)

5. Build → Run on your Galaxy A16 or Build APK

## WireGuard mesh (best option)
Once WireGuard is active:
   baseUrl   = "http://10.99.0.1:8000"
   ollamaUrl = "http://10.99.0.1:11434"
