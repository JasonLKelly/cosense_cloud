#!/bin/bash
# One-time GCP project setup for CoSense Cloud
# Run this once before first deployment

set -euo pipefail

# Load environment if available
if [[ -f .env ]]; then
  set -a; source .env; set +a
fi

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?ERROR: Set GOOGLE_CLOUD_PROJECT in .env}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"

echo "=== CoSense Cloud - GCP Setup ==="
echo "Project: $PROJECT_ID"
echo "Region:  $REGION"
echo ""

# Set project
echo "Setting active project..."
gcloud config set project "$PROJECT_ID"

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com

# Create Artifact Registry repository
echo "Creating Artifact Registry repository..."
gcloud artifacts repositories create cosense \
  --repository-format=docker \
  --location="$REGION" \
  --description="CoSense Cloud container images" \
  2>/dev/null || echo "  Repository 'cosense' already exists"

echo ""
echo "=== Setup Complete ==="
echo "Next step: ./deploy/cloud-run.sh"
