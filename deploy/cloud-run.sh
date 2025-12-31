#!/bin/bash
# Deploy CoSense Cloud backend services to Cloud Run
# Frontend is deployed separately via ./deploy/firebase-hosting.sh
#
# Usage:
#   ./deploy/cloud-run.sh              # Build and deploy all
#   ./deploy/cloud-run.sh --skip-build # Deploy only (use existing images)

set -euo pipefail

SKIP_BUILD=false
if [[ "${1:-}" == "--skip-build" ]]; then
  SKIP_BUILD=true
fi

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
# Step 1: Build services (parallel)
# ============================================================
if [[ "$SKIP_BUILD" == "false" ]]; then
  echo "[1/4] Building services in parallel..."

  # Copy maps into backend/ for Docker build context
  cp -r maps backend/

  # Build all services in parallel
  pids=()
  for svc in simulator stream-processor backend; do
    echo "  Starting build: $svc"
    gcloud builds submit "./$svc" \
      --tag "${REGISTRY}/${svc}:latest" \
      --project "$PROJECT_ID" \
      --quiet &
    pids+=($!)
  done

  # Wait for all builds to complete
  echo "  Waiting for builds to complete..."
  failed=0
  for pid in "${pids[@]}"; do
    if ! wait "$pid"; then
      failed=1
    fi
  done

  # Clean up
  rm -rf backend/maps

  if [[ $failed -ne 0 ]]; then
    echo "ERROR: One or more builds failed"
    exit 1
  fi
  echo "  All builds completed"
else
  echo "[1/4] Skipping build (--skip-build)"
fi

# ============================================================
# Step 2: Deploy Simulator
# ============================================================
echo "[2/4] Deploying simulator..."

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
  --set-env-vars="KAFKA_TOPIC_PREFIX=${KAFKA_TOPIC_PREFIX:-prod}" \
  --set-env-vars="ROBOT_COUNT=${ROBOT_COUNT:-2}" \
  --set-env-vars="HUMAN_COUNT=${HUMAN_COUNT:-2}" \
  --set-env-vars="TICK_RATE_HZ=${TICK_RATE_HZ:-10}" \
  --quiet

SIMULATOR_URL=$(gcloud run services describe simulator --region "$REGION" --project "$PROJECT_ID" --format='value(status.url)')
echo "  Simulator: $SIMULATOR_URL"

# ============================================================
# Step 3: Deploy Stream Processor
# ============================================================
echo "[3/4] Deploying stream-processor..."

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
  --set-env-vars="KAFKA_TOPIC_PREFIX=${KAFKA_TOPIC_PREFIX:-prod}" \
  --set-env-vars="SIMULATOR_URL=${SIMULATOR_URL}" \
  --quiet

echo "  Stream processor deployed (private)"

# ============================================================
# Step 4: Deploy Backend API
# ============================================================
echo "[4/4] Deploying backend..."

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
  --set-env-vars="KAFKA_TOPIC_PREFIX=${KAFKA_TOPIC_PREFIX:-prod}" \
  --set-env-vars="SIMULATOR_URL=${SIMULATOR_URL}" \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
  --set-env-vars="GOOGLE_CLOUD_LOCATION=${REGION}" \
  --set-env-vars="USE_VERTEX_AI=${USE_VERTEX_AI:-true}" \
  --set-env-vars="GEMINI_MODEL=${GEMINI_MODEL:-gemini-2.0-flash}" \
  --quiet

BACKEND_URL=$(gcloud run services describe backend --region "$REGION" --project "$PROJECT_ID" --format='value(status.url)')
echo "  Backend: $BACKEND_URL"

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "  Simulator: $SIMULATOR_URL"
echo "  Backend:   $BACKEND_URL"
echo ""
echo "Next: Deploy frontend with ./deploy/firebase-hosting.sh"
