# Deployment Guide

This guide walks through deploying the Gemini Homicide Bot to Google Cloud Run.

## Quick Start (5 minutes)

If you already have gcloud CLI installed and a Google Cloud project:

```bash
# 1. Store your Gemini API key in Secret Manager
gcloud secrets create gemini-api-key --data-file=- <<< "YOUR_API_KEY"

# 2. Deploy from source
gcloud run deploy gemini-homicide-bot \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-secrets=GOOGLE_API_KEY=gemini-api-key:latest \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300

# 3. Visit the URL shown in the output
```

## Detailed Setup

### Prerequisites

1. **Google Cloud Account**
   - Sign up at [cloud.google.com](https://cloud.google.com)
   - New accounts get $300 in free credits

2. **Install Google Cloud CLI**
   - Download from [cloud.google.com/sdk](https://cloud.google.com/sdk/docs/install)
   - Or use Cloud Shell in the browser (no install needed)

3. **Gemini API Key**
   - Get your free API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Copy it for the next step

### Step-by-Step Deployment

#### 1. Create a Google Cloud Project

```bash
# Login to Google Cloud
gcloud auth login

# Create a new project (or use existing)
gcloud projects create gemini-homicide-bot-prod --name="Gemini Homicide Bot"

# Set as active project
gcloud config set project gemini-homicide-bot-prod
```

#### 2. Enable Required APIs

```bash
# Enable Cloud Run and related services
gcloud services enable run.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

#### 3. Store Gemini API Key Securely

```bash
# Create secret in Secret Manager
echo -n "YOUR_GEMINI_API_KEY_HERE" | gcloud secrets create gemini-api-key --data-file=-

# Verify it was created
gcloud secrets describe gemini-api-key
```

#### 4. Deploy to Cloud Run

```bash
# Deploy from local source code
gcloud run deploy gemini-homicide-bot \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-secrets=GOOGLE_API_KEY=gemini-api-key:latest \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --timeout 300
```

**What this does:**
- Builds Docker image from the `Dockerfile`
- Pushes to Google Artifact Registry
- Deploys to Cloud Run in `us-central1`
- Configures auto-scaling (0-10 instances)
- Injects API key from Secret Manager
- Allocates 512MB RAM and 1 CPU per instance
- Makes the service publicly accessible

#### 5. Test Your Deployment

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe gemini-homicide-bot \
  --region us-central1 \
  --format 'value(status.url)')

echo "Service URL: $SERVICE_URL"

# Test the health endpoint
curl $SERVICE_URL/api/health

# Open in browser
open $SERVICE_URL  # macOS
start $SERVICE_URL  # Windows
xdg-open $SERVICE_URL  # Linux
```

### Updating the Deployment

When you make changes to the code:

```bash
# Simply re-run the deploy command
gcloud run deploy gemini-homicide-bot \
  --source . \
  --region us-central1
```

Cloud Run will:
1. Build a new container image
2. Deploy with zero downtime
3. Route traffic to the new version

### Cost Estimates

Cloud Run pricing (as of 2025):
- **Free tier**: 2M requests/month, 180K vCPU-seconds, 360K GiB-seconds
- **After free tier**: ~$0.10 per million requests
- **This app**: Likely stays in free tier for moderate usage

Secret Manager:
- **Free tier**: 6 active secret versions
- **This app**: Uses 1 secret (free)

Artifact Registry:
- **Free tier**: 0.5 GB storage
- **This app**: ~200MB per image (free)

**Estimated monthly cost for 10K requests/month: $0**

### Monitoring and Logs

View logs in real-time:

```bash
gcloud run services logs tail gemini-homicide-bot --region us-central1
```

View metrics in Cloud Console:
```bash
# Open Cloud Run console
gcloud run services describe gemini-homicide-bot \
  --region us-central1 \
  --format 'value(status.url)' | xargs -I {} open "https://console.cloud.google.com/run"
```

### Security Best Practices

1. **Restrict Access (Optional)**
   ```bash
   # Make the service require authentication
   gcloud run services update gemini-homicide-bot \
     --no-allow-unauthenticated \
     --region us-central1
   
   # Grant access to specific users
   gcloud run services add-iam-policy-binding gemini-homicide-bot \
     --member='user:someone@example.com' \
     --role='roles/run.invoker' \
     --region us-central1
   ```

2. **Rotate API Keys**
   ```bash
   # Update secret with new key
   echo -n "NEW_API_KEY" | gcloud secrets versions add gemini-api-key --data-file=-
   
   # Redeploy to pick up new secret
   gcloud run deploy gemini-homicide-bot --region us-central1
   ```

3. **Enable VPC Egress (Optional)**
   - For production workloads, route egress through VPC for network security

### CI/CD with GitHub Actions

For automated deployments on every push to `main`:

1. **Set up Workload Identity Federation** (one-time setup)
   - Follow: https://github.com/google-github-actions/auth#setting-up-workload-identity-federation
   - This allows GitHub to deploy without storing long-lived credentials

2. **Add GitHub Secrets**
   - Go to your repo → Settings → Secrets and variables → Actions
   - Add:
     - `GCP_PROJECT_ID`: Your project ID
     - `WIF_PROVIDER`: Workload Identity Provider resource name
     - `WIF_SERVICE_ACCOUNT`: Service account email

3. **Push to main**
   - The workflow in `.github/workflows/deploy-cloud-run.yml` will:
     - Run unit tests
     - Build Docker image
     - Deploy to Cloud Run
     - Output service URL

### Troubleshooting

**Error: "Permission denied"**
```bash
# Ensure you have the necessary IAM roles
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="user:YOUR_EMAIL@gmail.com" \
  --role="roles/run.admin"
```

**Error: "Service build failed"**
- Check your `Dockerfile` syntax
- Ensure `requirements.txt` has valid packages
- Review build logs: `gcloud builds list`

**App crashes on startup**
- Check logs: `gcloud run services logs read gemini-homicide-bot --region us-central1 --limit 50`
- Verify `GOOGLE_API_KEY` is set correctly
- Test locally with Docker first

**Cold start times**
- First request after idle may take 10-15 seconds
- Set `--min-instances 1` to keep one instance warm (costs ~$5/month)

### Rolling Back

If a deployment breaks:

```bash
# List revisions
gcloud run revisions list --service gemini-homicide-bot --region us-central1

# Roll back to previous revision
gcloud run services update-traffic gemini-homicide-bot \
  --to-revisions=PREVIOUS_REVISION_NAME=100 \
  --region us-central1
```

### Alternative: Deploy from Container Image

If you prefer to build locally and push:

```bash
# Build image
docker build -t gcr.io/PROJECT_ID/gemini-homicide-bot:latest .

# Push to Google Container Registry
docker push gcr.io/PROJECT_ID/gemini-homicide-bot:latest

# Deploy from image
gcloud run deploy gemini-homicide-bot \
  --image gcr.io/PROJECT_ID/gemini-homicide-bot:latest \
  --region us-central1 \
  --set-secrets=GOOGLE_API_KEY=gemini-api-key:latest
```

## Support

- **Cloud Run docs**: https://cloud.google.com/run/docs
- **Secret Manager docs**: https://cloud.google.com/secret-manager/docs
- **Gemini API docs**: https://ai.google.dev/docs
