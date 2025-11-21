# 🎯 Deploy to GCP - Start Here

Your backend is now **ready to deploy to Google Cloud Platform**! 

## 🚨 Why It Wasn't Working

Your backend was configured for **Render** (using `Procfile`) but **not for GCP**. GCP App Engine requires different configuration files, which I've now created for you.

---

## 🚀 Quick Start (3 Steps)

### Step 1: Run Pre-Deployment Check
```powershell
cd backend
.\check-deployment-ready.ps1
```
This will verify you have everything needed.

### Step 2: Generate Secure Keys
```powershell
# Run this twice to get two different keys
python -c "import secrets; print(secrets.token_hex(32))"
```

Update `app.yaml` with both keys:
- Replace `SECRET_KEY: 'your-production-secret-key-change-this'`
- Replace `JWT_SECRET_KEY: 'your-production-jwt-secret-key-change-this'`

### Step 3: Deploy!
```powershell
.\deploy-gcp.ps1
```

**That's it!** The script will handle everything else.

---

## 📁 Files Created for You

| File | Purpose |
|------|---------|
| `app.yaml` | Main GCP configuration with all environment variables |
| `.gcloudignore` | Files to exclude from deployment |
| `deploy-gcp.ps1` | **Automated deployment script** |
| `check-deployment-ready.ps1` | Pre-flight checklist |
| `GCP_DEPLOYMENT.md` | Complete step-by-step guide |
| `QUICK_DEPLOY_GCP.md` | Quick reference |
| `GCP_SETUP_COMPLETE.md` | Setup summary |
| `.env.gcp.example` | Environment variables reference |

---

## 📋 Pre-Deployment Checklist

- [ ] Install Google Cloud SDK ([Download](https://cloud.google.com/sdk/docs/install))
- [ ] Run `gcloud auth login`
- [ ] Generate secure `SECRET_KEY` and `JWT_SECRET_KEY`
- [ ] Update both keys in `app.yaml`
- [ ] Update Google OAuth redirect URIs ([Console](https://console.cloud.google.com/apis/credentials))
  - Add: `https://fleet-ivy-478805-a7.uc.r.appspot.com/api/auth/callback`

---

## 🎬 Deployment Commands

### Automated (Recommended)
```powershell
cd backend
.\check-deployment-ready.ps1  # Verify setup
.\deploy-gcp.ps1              # Deploy
```

### Manual
```powershell
cd backend
gcloud auth login
gcloud config set project fleet-ivy-478805-a7
gcloud services enable appengine.googleapis.com cloudbuild.googleapis.com
gcloud app create --region=us-central
gcloud app deploy
```

---

## ✅ After Deployment

### 1. Test Your Backend
```powershell
# Health check
curl https://fleet-ivy-478805-a7.uc.r.appspot.com/api/health

# View in browser
gcloud app browse
```

### 2. Update Your Frontend
Update frontend environment variable:
```
REACT_APP_API_URL=https://fleet-ivy-478805-a7.uc.r.appspot.com/api
```

### 3. Test Authentication
1. Open your frontend
2. Click "Sign in with Google"
3. Verify you can log in successfully

### 4. View Logs
```powershell
gcloud app logs tail --project=fleet-ivy-478805-a7
```

---

## 🔧 Troubleshooting

### "gcloud: command not found"
**Fix**: Install Google Cloud SDK
- Windows: https://cloud.google.com/sdk/docs/install-sdk#windows
- After install: Close and reopen PowerShell

### "API not enabled"
**Fix**: 
```powershell
gcloud services enable appengine.googleapis.com --project=fleet-ivy-478805-a7
```

### "Application error" after deployment
**Fix**: Check logs for the real error:
```powershell
gcloud app logs tail
```
Common causes:
- Forgot to update SECRET_KEY in app.yaml
- Wrong MongoDB URI
- Missing environment variables

### "redirect_uri_mismatch" OAuth error
**Fix**: 
1. Go to https://console.cloud.google.com/apis/credentials
2. Add exact URI: `https://fleet-ivy-478805-a7.uc.r.appspot.com/api/auth/callback`
3. Wait 5 minutes for changes to propagate

### Deployment taking too long
This is normal! First deployment can take 5-10 minutes.

---

## 💰 Cost Estimate

With current configuration:
- **Minimum**: $0/month (scales to 0 when idle)
- **Light usage**: $5-10/month
- **Moderate usage**: $20-30/month

Free tier includes: 28 instance hours/day

Monitor costs: https://console.cloud.google.com/billing?project=fleet-ivy-478805-a7

---

## 📚 Documentation

- **Start Here**: This file
- **Pre-Flight Check**: Run `.\check-deployment-ready.ps1`
- **Quick Deploy**: See `QUICK_DEPLOY_GCP.md`
- **Complete Guide**: See `GCP_DEPLOYMENT.md`
- **What Changed**: See `GCP_SETUP_COMPLETE.md`

---

## 🆘 Need Help?

1. **Run the checklist**: `.\check-deployment-ready.ps1`
2. **Check logs**: `gcloud app logs tail`
3. **Read troubleshooting**: See `GCP_DEPLOYMENT.md`
4. **GCP Status**: https://status.cloud.google.com/

---

## 🎉 You're Ready!

Your backend is fully configured for GCP deployment. Just follow the Quick Start above and you'll be deployed in minutes!

**Your deployment URL will be:**
```
https://fleet-ivy-478805-a7.uc.r.appspot.com
```

Good luck! 🚀

---

## Quick Command Reference

```powershell
# Check if ready
.\check-deployment-ready.ps1

# Deploy
.\deploy-gcp.ps1

# View logs
gcloud app logs tail

# View in browser
gcloud app browse

# Check status
gcloud app describe

# Generate secret key
python -c "import secrets; print(secrets.token_hex(32))"
```
