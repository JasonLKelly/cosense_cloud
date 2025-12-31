#!/bin/bash
# Deploy frontend to Firebase Hosting
# Requires: firebase CLI authenticated, backend deployed to Cloud Run

set -euo pipefail

# Load environment
if [[ -f .env ]]; then
  set -a; source .env; set +a
fi

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?ERROR: Set GOOGLE_CLOUD_PROJECT in .env}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"

echo "=== CoSense Cloud - Firebase Hosting Deploy ==="

# Get backend URL from Cloud Run
echo "Getting backend URL..."
BACKEND_URL=$(gcloud run services describe backend --region "$REGION" --project "$PROJECT_ID" --format='value(status.url)' 2>/dev/null) || {
  echo "ERROR: Backend not deployed. Run ./deploy/cloud-run.sh first"
  exit 1
}
echo "  Backend: $BACKEND_URL"

# Confluent Cloud URL (default for production)
CONFLUENT_URL="${VITE_CONFLUENT_URL:-https://confluent.cloud/environments/env-x5ddpg/clusters/lkc-1pyorj/overview}"

# Poll interval (default 1000ms for Cloud Run latency)
POLL_INTERVAL="${VITE_POLL_INTERVAL:-1000}"

# Build frontend
echo "Building frontend..."
cd control-center-webapp
npm install --silent
VITE_API_URL="$BACKEND_URL" \
  VITE_CONFLUENT_URL="$CONFLUENT_URL" \
  VITE_POLL_INTERVAL="$POLL_INTERVAL" \
  npm run build
cd ..

# Deploy to Firebase (from project root where firebase.json is)
echo "Deploying to Firebase Hosting..."
~/.local/bin/firebase deploy --only hosting:cosense-cloud

echo ""
echo "=== Deploy Complete ==="
echo "  Frontend: https://cosense-cloud.web.app"
echo "  Backend:  $BACKEND_URL"
