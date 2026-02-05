#!/bin/bash
# Add test accounts to Predict Account Service

set -e

API_URL="${PREDICT_ACCOUNT_URL:-http://localhost:8010}"

# Source .env if exists
if [ -f .env ]; then
    source .env
fi

echo "Adding Account 1..."
curl -s -X POST "$API_URL/accounts" \
    -H "Content-Type: application/json" \
    -d "{
        \"name\": \"${TEST_ACCOUNT_1_NAME:-TestAccount1}\",
        \"private_key\": \"${TEST_ACCOUNT_1_PRIVATE_KEY:-139f61b6c7ff48af3d46d377eac532d934ff60bdda57061bffa621cc671a3b48}\",
        \"api_key\": \"${TEST_ACCOUNT_1_API_KEY:-64f65a47-393c-44f5-bfdc-4d5218dc1ba3}\",
        \"proxy_url\": \"${TEST_ACCOUNT_1_PROXY:-}\",
        \"tags\": [\"test\", \"primary\"]
    }" | jq .

echo ""
echo "Adding Account 2..."
curl -s -X POST "$API_URL/accounts" \
    -H "Content-Type: application/json" \
    -d "{
        \"name\": \"${TEST_ACCOUNT_2_NAME:-TestAccount2}\",
        \"private_key\": \"${TEST_ACCOUNT_2_PRIVATE_KEY:-69e9520b523919945635c49dd5084c157dba056c24964d1d9897d77a04fea299}\",
        \"api_key\": \"${TEST_ACCOUNT_2_API_KEY:-d4200ab1-497f-4c17-83fd-9a4ef406dcde}\",
        \"proxy_url\": \"${TEST_ACCOUNT_2_PROXY:-}\",
        \"tags\": [\"test\", \"hedge\"]
    }" | jq .

echo ""
echo "✅ Test accounts added!"
echo ""
echo "List accounts:"
curl -s "$API_URL/accounts" | jq .
