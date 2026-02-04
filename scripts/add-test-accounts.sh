#!/bin/bash
set -euo pipefail

# Script to add test accounts to the system
# Usage: ./add-test-accounts.sh

API_URL="${API_URL:-http://localhost:8010}"

echo "Adding test accounts to Predict Account Service..."

# Account 1
echo "Adding account1..."
curl -X POST "${API_URL}/accounts" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "account1",
    "private_key": "139f61b6c7ff48af3d46d377eac532d934ff60bdda57061bffa621cc671a3b48",
    "api_key": "64f65a47-393c-44f5-bfdc-4d5218dc1ba3",
    "proxy_url": "http://wbjT8rk3:EV65rUkU@93.190.123.154:62360",
    "tags": ["delta-neutral", "test"],
    "notes": "Test account 1 - Balance: 500"
  }'

echo ""
echo ""

# Account 2  
echo "Adding account2..."
curl -X POST "${API_URL}/accounts" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "account2",
    "private_key": "69e9520b523919945635c49dd5084c157dba056c24964d1d9897d77a04fea299",
    "api_key": "d4200ab1-497f-4c17-83fd-9a4ef406dcde",
    "proxy_url": "http://wbjT8rk3:EV65rUkU@193.202.113.117:62782",
    "tags": ["delta-neutral", "test"],
    "notes": "Test account 2 - Balance: 500"
  }'

echo ""
echo ""
echo "✅ Test accounts added successfully!"
