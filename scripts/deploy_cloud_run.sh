#!/usr/bin/env bash
# ==============================================================================
# Deploy BikeFit Agent to Google Cloud Run
# ==============================================================================

set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-bikefit-agent}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "❌ Error: GOOGLE_CLOUD_PROJECT environment variable is not set."
  echo "Usage: GOOGLE_CLOUD_PROJECT=your-project-id ./scripts/deploy_cloud_run.sh"
  exit 1
fi

echo "🚀 Building and deploying ${SERVICE_NAME} to Google Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --allow-unauthenticated \
  --port=8080 \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=5

echo "✅ Cloud Run deployment complete!"
