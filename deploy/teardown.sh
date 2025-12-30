#!/bin/bash
# Delete all CoSense Cloud Run services
# Use this to clean up after demos or when done

set -euo pipefail

# Load environment if available
if [[ -f .env ]]; then
  set -a; source .env; set +a
fi

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?ERROR: Set GOOGLE_CLOUD_PROJECT in .env}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"

echo "=== CoSense Cloud - Teardown ==="
echo "Project: $PROJECT_ID"
echo "Region:  $REGION"
echo ""

# Delete services in reverse dependency order
echo "Deleting Cloud Run services..."
for svc in control-center-webapp backend stream-processor simulator; do
  echo "  Deleting $svc..."
  gcloud run services delete "$svc" \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --quiet 2>/dev/null || echo "    (not found or already deleted)"
done

echo ""
echo "=== Teardown Complete ==="
echo "Note: Artifact Registry images retained. Delete manually if needed:"
echo "  gcloud artifacts repositories delete cosense --location=$REGION"
