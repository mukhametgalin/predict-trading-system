# Quick Start Guide

## Prerequisites

- Docker & Docker Compose
- Predict.fun API key
- 2+ accounts with private keys

## Step 1: Setup Environment

```bash
cd predict-trading-system

# Copy env example
cp .env.example .env

# Edit .env
nano .env
```

Add your Predict API key to `.env`:
```
PREDICT_API_KEY=your_key_here
```

## Step 2: Start Services

```bash
# Build and start everything
make quickstart
```

This will:
- Build all Docker images
- Start all services
- Add test accounts
- Initialize delta neutral strategy

## Step 3: Verify

```bash
# Check service status
make ps

# Watch logs
make logs

# Check accounts
curl http://localhost:8010/accounts
```

## Step 4: Test Delta Neutral Strategy

The delta neutral strategy is now active and listening for fill events.

When a fill occurs on `account1`, it will automatically place an opposite order on `account2`.

### Manual Test

Place a test order on account1:

```bash
curl -X POST http://localhost:8010/trade \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "account1",
    "market_id": "YOUR_MARKET_ID",
    "side": "yes",
    "price": 0.55,
    "shares": 10,
    "confirm": false
  }'
```

Set `confirm: true` to execute for real.

When this order fills, the strategy engine will automatically:
1. Detect the fill event from Redis
2. Execute Delta Neutral handler
3. Place opposite order on account2 (NO @ 0.55)

## Step 5: Monitor

```bash
# Watch strategy engine logs
make strategy-logs

# Watch predict account logs  
make predict-logs

# Connect to database
make db-shell
SELECT * FROM strategies;
```

## Troubleshooting

### Services not starting

```bash
make down
make build
make up
make logs
```

### Database issues

```bash
make db-shell
\dt  -- List tables
```

### Redis issues

```bash
make redis-cli
XINFO STREAM fill_events
```

## Next Steps

- Customize strategy config in database
- Add more account pairs
- Monitor positions via Web UI (coming soon)
- Set up Telegram alerts (coming soon)
