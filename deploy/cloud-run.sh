#!/bin/bash
# Deploy CoSense Cloud to Google Cloud Run
# Requires: gcloud CLI authenticated, .env configured

set -euo pipefail

# Load environment
if [[ -f .env ]]; then
  set -a; source .env; set +a
fi

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?ERROR: Set GOOGLE_CLOUD_PROJECT in .env}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/cosense"

echo "=== CoSense Cloud - Deploying to Cloud Run ==="
echo "Project:  $PROJECT_ID"
echo "Region:   $REGION"
echo "Registry: $REGISTRY"
echo ""

# Validate required Confluent Cloud settings
: "${KAFKA_BROKERS:?ERROR: Set KAFKA_BROKERS in .env}"
: "${KAFKA_API_KEY:?ERROR: Set KAFKA_API_KEY in .env}"
: "${KAFKA_API_SECRET:?ERROR: Set KAFKA_API_SECRET in .env}"

# ============================================================
# Step 1: Build backend services (simulator, stream-processor, backend)
# ============================================================
echo "[1/6] Building backend services..."

for svc in simulator stream-processor backend; do
  echo "  Building $svc..."
  gcloud builds submit "./$svc" \
    --tag "${REGISTRY}/${svc}:latest" \
    --project "$PROJECT_ID" \
    --quiet
done

# ============================================================
# Step 2: Deploy Simulator
# ============================================================
echo "[2/6] Deploying simulator..."

gcloud run deploy simulator \
  --image "${REGISTRY}/simulator:latest" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --allow-unauthenticated \
  --cpu=1 --memory=512Mi \
  --min-instances=1 --max-instances=3 \
  --set-env-vars="KAFKA_BROKERS=${KAFKA_BROKERS}" \
  --set-env-vars="KAFKA_API_KEY=${KAFKA_API_KEY}" \
  --set-env-vars="KAFKA_API_SECRET=${KAFKA_API_SECRET}" \
  --set-env-vars="KAFKA_SECURITY_PROTOCOL=${KAFKA_SECURITY_PROTOCOL:-SASL_SSL}" \
  --set-env-vars="KAFKA_SASL_MECHANISM=${KAFKA_SASL_MECHANISM:-PLAIN}" \
  --set-env-vars="ROBOT_COUNT=${ROBOT_COUNT:-2}" \
  --set-env-vars="HUMAN_COUNT=${HUMAN_COUNT:-2}" \
  --set-env-vars="TICK_RATE_HZ=${TICK_RATE_HZ:-10}" \
  --quiet

SIMULATOR_URL=$(gcloud run services describe simulator --region "$REGION" --project "$PROJECT_ID" --format='value(status.url)')
echo "  Simulator: $SIMULATOR_URL"

# ============================================================
# Step 3: Deploy Stream Processor (private, always-on)
# ============================================================
echo "[3/6] Deploying stream-processor..."

gcloud run deploy stream-processor \
  --image "${REGISTRY}/stream-processor:latest" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --no-allow-unauthenticated \
  --cpu=1 --memory=512Mi \
  --min-instances=1 --max-instances=1 \
  --concurrency=1 \
  --set-env-vars="KAFKA_BROKERS=${KAFKA_BROKERS}" \
  --set-env-vars="KAFKA_API_KEY=${KAFKA_API_KEY}" \
  --set-env-vars="KAFKA_API_SECRET=${KAFKA_API_SECRET}" \
  --set-env-vars="KAFKA_SECURITY_PROTOCOL=${KAFKA_SECURITY_PROTOCOL:-SASL_SSL}" \
  --set-env-vars="KAFKA_SASL_MECHANISM=${KAFKA_SASL_MECHANISM:-PLAIN}" \
  --set-env-vars="SIMULATOR_URL=${SIMULATOR_URL}" \
  --quiet

echo "  Stream processor deployed (private)"

# ============================================================
# Step 4: Deploy Backend API
# ============================================================
echo "[4/6] Deploying backend..."

gcloud run deploy backend \
  --image "${REGISTRY}/backend:latest" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --allow-unauthenticated \
  --cpu=1 --memory=512Mi \
  --min-instances=1 --max-instances=5 \
  --set-env-vars="KAFKA_BROKERS=${KAFKA_BROKERS}" \
  --set-env-vars="KAFKA_API_KEY=${KAFKA_API_KEY}" \
  --set-env-vars="KAFKA_API_SECRET=${KAFKA_API_SECRET}" \
  --set-env-vars="KAFKA_SECURITY_PROTOCOL=${KAFKA_SECURITY_PROTOCOL:-SASL_SSL}" \
  --set-env-vars="KAFKA_SASL_MECHANISM=${KAFKA_SASL_MECHANISM:-PLAIN}" \
  --set-env-vars="SIMULATOR_URL=${SIMULATOR_URL}" \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
  --set-env-vars="GOOGLE_CLOUD_LOCATION=${REGION}" \
  --set-env-vars="USE_VERTEX_AI=${USE_VERTEX_AI:-true}" \
  --set-env-vars="GEMINI_MODEL=${GEMINI_MODEL:-gemini-2.0-flash}" \
  --quiet

BACKEND_URL=$(gcloud run services describe backend --region "$REGION" --project "$PROJECT_ID" --format='value(status.url)')
echo "  Backend: $BACKEND_URL"

# ============================================================
# Step 5: Build Frontend (needs BACKEND_URL at build time)
# ============================================================
echo "[5/6] Building frontend with VITE_API_URL=${BACKEND_URL}..."

# Create a temporary cloudbuild.yaml for frontend with build arg
cat > /tmp/cloudbuild-frontend.yaml << EOF
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '--build-arg'
      - 'VITE_API_URL=${BACKEND_URL}'
      - '-t'
      - '${REGISTRY}/control-center-webapp:latest'
      - '.'
images:
  - '${REGISTRY}/control-center-webapp:latest'
EOF

gcloud builds submit ./control-center-webapp \
  --config=/tmp/cloudbuild-frontend.yaml \
  --project "$PROJECT_ID" \
  --quiet

rm /tmp/cloudbuild-frontend.yaml

# ============================================================
# Step 6: Deploy Frontend
# ============================================================
echo "[6/6] Deploying frontend..."

gcloud run deploy control-center-webapp \
  --image "${REGISTRY}/control-center-webapp:latest" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --allow-unauthenticated \
  --cpu=0.5 --memory=256Mi \
  --min-instances=0 --max-instances=3 \
  --quiet

FRONTEND_URL=$(gcloud run services describe control-center-webapp --region "$REGION" --project "$PROJECT_ID" --format='value(status.url)')

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "  Frontend (UI):  $FRONTEND_URL"
echo "  Backend (API):  $BACKEND_URL"
echo "  Simulator:      $SIMULATOR_URL"
echo ""
echo "Open the frontend URL in your browser to access CoSense Cloud."
