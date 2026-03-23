#!/bin/bash
# Smoke test for admin API endpoints
# Run: ./scripts/test-admin-api.sh [base_url] [admin_key]
# Example: ./scripts/test-admin-api.sh http://localhost:8000 mentorlab2026
#
# Validates that all admin endpoints return expected HTTP codes.
# Use after deployments to catch broken endpoints before users do.

set -e
BASE="${1:-http://localhost:8000}"
KEY="${2:-mentorlab2026}"
ERRORS=0

echo "=== Admin API Smoke Test ==="
echo "Base: $BASE"

check() {
  local method="$1" path="$2" expect="$3" desc="$4"
  local code
  if [ "$method" = "GET" ]; then
    code=$(curl -s -o /dev/null -w "%{http_code}" -H "X-Admin-Key: $KEY" "$BASE$path")
  else
    code=$(curl -s -o /dev/null -w "%{http_code}" -H "X-Admin-Key: $KEY" -H "Content-Type: application/json" -X "$method" "$BASE$path")
  fi
  if [ "$code" = "$expect" ]; then
    echo "  OK  $method $path → $code"
  else
    echo "  FAIL $method $path → $code (expected $expect)"
    echo "    FIX: Check backend logs for this endpoint."
    ERRORS=$((ERRORS + 1))
  fi
}

echo ""
echo "--- Dashboard ---"
check GET /api/v1/admin/dashboard 200 "Dashboard stats"

echo ""
echo "--- Participants ---"
check GET /api/v1/admin/participants 200 "Participant list"

echo ""
echo "--- Export ---"
check GET "/api/v1/admin/export/transcripts?admin_key=$KEY" 200 "Transcripts CSV (query param auth)"
check GET "/api/v1/admin/export/surveys?admin_key=$KEY" 200 "Surveys CSV (query param auth)"
check GET /api/v1/admin/export/history 200 "Export history"

echo ""
echo "--- Auth ---"
# Test that endpoints reject without key
NO_KEY_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/v1/admin/dashboard")
if [ "$NO_KEY_CODE" = "401" ]; then
  echo "  OK  No-key request correctly rejected (401)"
else
  echo "  FAIL No-key request returned $NO_KEY_CODE (expected 401)"
  ERRORS=$((ERRORS + 1))
fi

echo ""
if [ "$ERRORS" -gt 0 ]; then
  echo "FAILED: $ERRORS endpoint(s) broken."
  exit 1
else
  echo "PASSED: All admin endpoints healthy."
  exit 0
fi
