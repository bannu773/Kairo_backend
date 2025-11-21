# Google Cloud Platform (GCP) Deployment Guide

## Prerequisites

1. **Google Cloud SDK (gcloud CLI)** installed on your machine
   - Download from: https://cloud.google.com/sdk/docs/install
   - After installation, run: `gcloud init`

2. **GCP Project**: `fleet-ivy-478805-a7`

3. **App Engine API** enabled in your GCP project

## Step-by-Step Deployment

### 1. Install Google Cloud SDK

If you haven't already, install the gcloud CLI:

**Windows (PowerShell):**
```powershell
# Download and run the installer
# https://cloud.google.com/sdk/docs/install
```

After installation:
```powershell
gcloud init
```

### 2. Authenticate with GCP

```powershell
gcloud auth login
```

This will open a browser window for authentication.

### 3. Set Your GCP Project

```powershell
gcloud config set project fleet-ivy-478805-a7
```

### 4. Enable Required APIs

```powershell
# Enable App Engine API
gcloud services enable appengine.googleapis.com

# Enable Cloud Build API (for deployment)
gcloud services enable cloudbuild.googleapis.com

# Enable Cloud Speech API (for transcription)
gcloud services enable speech.googleapis.com
```

### 5. Create App Engine Application

**Note:** You can only create one App Engine application per project, and you must choose a region.

```powershell
# Create App Engine app in us-central region (recommended)
gcloud app create --region=us-central
```

If you get an error that the app already exists, that's fine - skip this step.

### 6. Update Environment Variables

**IMPORTANT:** Before deploying, update the following in `app.yaml`:

1. **Generate secure secret keys:**
```powershell
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Generate JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"
```

2. Update `app.yaml` with the generated keys:
```yaml
SECRET_KEY: 'paste-generated-secret-here'
JWT_SECRET_KEY: 'paste-generated-jwt-secret-here'
```

3. **Verify your MongoDB URI** is correct in `app.yaml`

4. **Update your frontend URL** if it's different

### 7. Update Google OAuth Redirect URI

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services > Credentials**
3. Click on your OAuth 2.0 Client ID: `50297190088-a6otf5pf0qqjl9fa4rpdb0qv6te245k6.apps.googleusercontent.com`
4. Under **Authorized redirect URIs**, add:
   ```
   https://fleet-ivy-478805-a7.uc.r.appspot.com/api/auth/callback
   ```
5. Under **Authorized JavaScript origins**, add:
   ```
   https://fleet-ivy-478805-a7.uc.r.appspot.com
   ```
6. Click **Save**

### 8. Deploy to App Engine

From the `backend` directory:

```powershell
cd backend
gcloud app deploy app.yaml --project=fleet-ivy-478805-a7
```

You'll be asked to confirm:
```
Do you want to continue (Y/n)? Y
```

The deployment will take a few minutes.

### 9. Verify Deployment

```powershell
# Open the deployed app in your browser
gcloud app browse --project=fleet-ivy-478805-a7
```

Or manually visit: `https://fleet-ivy-478805-a7.uc.r.appspot.com`

### 10. Check Health Endpoint

```powershell
curl https://fleet-ivy-478805-a7.uc.r.appspot.com/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "..."
}
```

## Viewing Logs

```powershell
# View recent logs
gcloud app logs tail --project=fleet-ivy-478805-a7

# View logs in browser
gcloud app logs read --project=fleet-ivy-478805-a7
```

Or view in the GCP Console:
https://console.cloud.google.com/logs/query?project=fleet-ivy-478805-a7

## Updating the Deployment

After making code changes:

```powershell
cd backend
gcloud app deploy --project=fleet-ivy-478805-a7
```

## Managing Versions

```powershell
# List all versions
gcloud app versions list --project=fleet-ivy-478805-a7

# Delete old versions to save resources
gcloud app versions delete <VERSION_ID> --project=fleet-ivy-478805-a7
```

## Common Issues & Solutions

### Issue 1: "ERROR: gcloud crashed (AttributeError)"
**Solution:** Update gcloud CLI:
```powershell
gcloud components update
```

### Issue 2: "API [appengine.googleapis.com] not enabled"
**Solution:** Enable the API:
```powershell
gcloud services enable appengine.googleapis.com --project=fleet-ivy-478805-a7
```

### Issue 3: "BUILD FAILED: requirements.txt not found"
**Solution:** Ensure you're in the `backend` directory when deploying:
```powershell
cd backend
gcloud app deploy
```

### Issue 4: "Application error" after deployment
**Solution:** Check logs for errors:
```powershell
gcloud app logs tail --project=fleet-ivy-478805-a7
```

Common causes:
- Missing or incorrect environment variables in `app.yaml`
- Database connection issues (check MongoDB URI)
- Missing Python dependencies in `requirements.txt`

### Issue 5: "redirect_uri_mismatch" OAuth error
**Solution:** 
1. Verify the redirect URI in Google Cloud Console exactly matches: `https://fleet-ivy-478805-a7.uc.r.appspot.com/api/auth/callback`
2. Wait 5-10 minutes after updating OAuth settings

### Issue 6: CORS errors from frontend
**Solution:** Ensure `CORS_ORIGINS` in `app.yaml` includes your frontend URL

## Cost Management

App Engine charges based on:
- Instance hours
- Outbound bandwidth
- API calls

With the current configuration:
- `min_instances: 0` - scales to zero when not in use (saves cost)
- `max_instances: 5` - prevents runaway costs
- `instance_class: F2` - suitable for most workloads

To monitor costs:
```
https://console.cloud.google.com/billing?project=fleet-ivy-478805-a7
```

## Production Checklist

- [ ] Google Cloud SDK installed and authenticated
- [ ] Project set to `fleet-ivy-478805-a7`
- [ ] App Engine APIs enabled
- [ ] App Engine application created in us-central region
- [ ] Secure SECRET_KEY and JWT_SECRET_KEY generated and set in `app.yaml`
- [ ] MongoDB URI verified
- [ ] Google OAuth redirect URIs updated in Google Cloud Console
- [ ] Frontend URL configured in `app.yaml`
- [ ] Deployed successfully with `gcloud app deploy`
- [ ] Health endpoint returns 200 OK
- [ ] Authentication flow tested
- [ ] Logs reviewed for errors

## Useful Commands

```powershell
# View app info
gcloud app describe --project=fleet-ivy-478805-a7

# View current deployment
gcloud app versions list --project=fleet-ivy-478805-a7

# Stop all instances (stop billing)
gcloud app versions stop <VERSION_ID> --project=fleet-ivy-478805-a7

# View deployed URL
gcloud app browse --project=fleet-ivy-478805-a7

# SSH into instance (for debugging)
gcloud app instances ssh --service=default --version=<VERSION_ID> --project=fleet-ivy-478805-a7
```

## Support Resources

- [App Engine Python 3 Documentation](https://cloud.google.com/appengine/docs/standard/python3)
- [Troubleshooting Deployments](https://cloud.google.com/appengine/docs/standard/python3/testing-and-deploying-your-app#troubleshooting)
- [GCP Status Dashboard](https://status.cloud.google.com/)
- [GCP Support](https://cloud.google.com/support)

## Security Best Practices

1. **Never commit `app.yaml` with secrets to Git** - Consider using Secret Manager
2. **Rotate secrets regularly**
3. **Use Cloud Secret Manager** for production secrets (advanced):
   ```powershell
   gcloud secrets create SECRET_KEY --data-file=- --project=fleet-ivy-478805-a7
   ```
4. **Enable Cloud Armor** for DDoS protection
5. **Set up Cloud Monitoring** for alerts
6. **Review IAM permissions** regularly

## Next Steps

After successful deployment:

1. **Update frontend** to use the new GCP backend URL
2. **Test all features** (auth, tasks, meetings, email sync)
3. **Set up monitoring** in GCP Console
4. **Configure custom domain** (optional)
5. **Set up CI/CD** with Cloud Build (optional)
