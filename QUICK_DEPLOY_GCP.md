# Quick GCP Deployment Guide

## TL;DR - Deploy in 5 Minutes

### 1. Install Google Cloud SDK
Download and install: https://cloud.google.com/sdk/docs/install

### 2. Authenticate and Set Project
```powershell
gcloud auth login
gcloud config set project fleet-ivy-478805-a7
```

### 3. Enable APIs
```powershell
gcloud services enable appengine.googleapis.com cloudbuild.googleapis.com speech.googleapis.com
```

### 4. Create App Engine App (One-time only)
```powershell
gcloud app create --region=us-central
```

### 5. Update Secrets in app.yaml
Generate secure keys:
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Update `app.yaml`:
- Replace `SECRET_KEY` with generated value
- Replace `JWT_SECRET_KEY` with generated value

### 6. Update Google OAuth Settings
Go to: https://console.cloud.google.com/apis/credentials?project=fleet-ivy-478805-a7

Add to **Authorized redirect URIs**:
```
https://fleet-ivy-478805-a7.uc.r.appspot.com/api/auth/callback
```

### 7. Deploy
```powershell
cd backend
gcloud app deploy
```

### 8. Test
```powershell
curl https://fleet-ivy-478805-a7.uc.r.appspot.com/api/health
```

## OR Use the Automated Script

```powershell
cd backend
.\deploy-gcp.ps1
```

---

## What Was Created

I've added the following files to enable GCP deployment:

1. **`app.yaml`** - App Engine configuration with all your environment variables
2. **`.gcloudignore`** - Specifies files to exclude from deployment
3. **`GCP_DEPLOYMENT.md`** - Complete deployment guide with troubleshooting
4. **`deploy-gcp.ps1`** - Automated PowerShell deployment script
5. **`QUICK_DEPLOY_GCP.md`** - This quick reference guide

## Why It Wasn't Working Before

Your backend was configured only for Render (with `Procfile`). GCP App Engine requires:
- `app.yaml` configuration file
- Environment variables defined in the YAML file
- Proper entrypoint configuration

These files are now created and ready to use!

## Next Steps After Deployment

1. **Update Frontend**:
   Update your frontend `.env` or environment variables to:
   ```
   REACT_APP_API_URL=https://fleet-ivy-478805-a7.uc.r.appspot.com/api
   ```

2. **Test Everything**:
   - Health endpoint: `https://fleet-ivy-478805-a7.uc.r.appspot.com/api/health`
   - Google OAuth login
   - Task creation from emails
   - Meeting transcription

3. **Monitor Costs**:
   - View billing: https://console.cloud.google.com/billing?project=fleet-ivy-478805-a7
   - Current config scales to 0 instances when idle (saves money)

## Common Errors

### "gcloud: command not found"
**Fix**: Install Google Cloud SDK from https://cloud.google.com/sdk/docs/install

### "API not enabled"
**Fix**: Run:
```powershell
gcloud services enable appengine.googleapis.com --project=fleet-ivy-478805-a7
```

### "redirect_uri_mismatch"
**Fix**: Add the exact redirect URI to Google Cloud Console OAuth settings

### "Application error" after deployment
**Fix**: Check logs:
```powershell
gcloud app logs tail --project=fleet-ivy-478805-a7
```

## Support

- Full documentation: See `GCP_DEPLOYMENT.md`
- View logs: `gcloud app logs tail`
- GCP Console: https://console.cloud.google.com/?project=fleet-ivy-478805-a7
