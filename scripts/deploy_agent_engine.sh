#!/usr/bin/env bash
# ==============================================================================
# Deploy BikeFit Agent to Google Cloud Vertex AI Agent Engine
# Using Google ADK (Agent Development Kit)
# ==============================================================================

set -euo pipefail

# Ensure environment variables or defaults
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
DISPLAY_NAME="${DISPLAY_NAME:-bikefit-agent}"
AGENT_DIR="${1:-bikefit_agent}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "❌ Error: GOOGLE_CLOUD_PROJECT environment variable is not set."
  echo "Usage: GOOGLE_CLOUD_PROJECT=your-project-id ./scripts/deploy_agent_engine.sh"
  exit 1
fi

echo "🚀 Deploying BikeFit Agent to Vertex AI Agent Engine..."
echo "   Project:      ${PROJECT_ID}"
echo "   Region:       ${REGION}"
echo "   Display Name: ${DISPLAY_NAME}"
echo "   Agent Path:   ${AGENT_DIR}"

# Run ADK Agent Engine deployment with OpenTelemetry & Cloud Trace enabled
adk deploy agent_engine \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --display_name="${DISPLAY_NAME}" \
  --description="Autonomous Bike Fit Geometry & Cockpit Match Agent" \
  --otel_to_cloud \
  --trace_to_cloud \
  --adk_app_object="root_agent" \
  "${AGENT_DIR}"

echo "✅ Deployment initiated successfully!"
