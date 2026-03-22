# Charlie 2.0 Railway Deploy Guide

## Steps

1. Create Railway account at https://railway.app
2. Install Railway CLI on your Predator PC:
   winget install Railway.Railway

3. Login:
   railway login

4. Create project:
   cd ~/charlie2 && railway init

5. Link GitHub repo:
   railway link

6. Add RAILWAY_TOKEN secret to GitHub:
   - GitHub repo → Settings → Secrets → New secret
   - Name: RAILWAY_TOKEN
   - Value: from railway whoami --token

7. Push to deploy:
   git add . && git commit -m "deploy charlie2" && git push

8. Your API will be live at:
   https://charlie2-api.up.railway.app

9. Update Android app Charlie2Client.railwayUrl with your URL
