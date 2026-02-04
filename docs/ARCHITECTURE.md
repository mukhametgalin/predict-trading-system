# Architecture

## Overview

Event-driven microservices architecture with clear separation of concerns.

```
┌─────────────────────────────────────────────────────┐
│                    UI Layer                         │
│  ┌──────────────┐         ┌──────────────────────┐ │
│  │ Web Frontend │         │  Telegram Bot       │ │
│  │ (Next.js)    │         │  (Alerts, Control)  │ │
│  └──────────────┘         └──────────────────────┘ │
└─────────────────────────────────────────────────────┘
              │                        │
              └────────────┬───────────┘
                           │ HTTP/WS
┌─────────────────────────────────────────────────────┐
│              Web API Gateway                        │
│  - REST API for UI                                  │
│  - WebSocket for real-time updates                  │
│  - Aggregates data from all services                │
└─────────────────────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼────┐  ┌───▼────┐  ┌───▼───────┐
        │ Predict  │  │ Poly-  │  │ Strategy  │
        │ Account  │  │ market │  │ Engine    │
        │          │  │ Account│  │           │
        └─────┬────┘  └───┬────┘  └───┬───────┘
              │           │           │
              └───────┬───┴───────────┘
                      │
              ┌───────▼────────┐
              │  Event Bus     │
              │  (Redis        │
              │  Streams)      │
              └────────────────┘
                      │
        ┌─────────────┼──────────────┐
        │             │              │
   ┌────▼────┐   ┌───▼────┐    ┌───▼──────┐
   │Postgres │   │ Click  │    │  Redis   │
   │         │   │ House  │    │          │
   └─────────┘   └────────┘    └──────────┘
```

## Services

### Predict Account Service (Python/FastAPI)

**Responsibility:** Manage Predict.fun accounts and execute trades

**API Endpoints:**
- `POST /accounts` - Create account
- `GET /accounts` - List accounts
- `PUT /accounts/{id}` - Update account
- `POST /trade` - Execute trade
- `GET /positions/{id}` - Get positions

**Events Published:**
- `account_created` → `account_events`
- `trade_executed` → `trade_events`
- `fill` → `fill_events` (most important)

**Database:**
- Tables: `predict_accounts`, `predict_trades`, `predict_positions`

### Strategy Engine (Golang)

**Responsibility:** Process events and execute strategies

**Flow:**
1. Subscribe to Redis Streams (`fill_events`, `trade_events`, `account_events`)
2. Load active strategies from Postgres
3. For each event, execute all active strategy handlers
4. Send resulting commands to Account Services

**Strategies:**
- Delta Neutral (built-in)
- Extensible for custom strategies

**Database:**
- Tables: `strategies`

### Web API Gateway (Python/FastAPI)

**Responsibility:** Aggregate data and provide unified API for UI

**Endpoints:**
- `/markets` - Market data from ClickHouse
- `/accounts` - Accounts from all platforms
- `/positions` - Aggregated positions
- `/strategies` - Strategy management
- `/ws` - WebSocket for real-time updates

### Web UI (Next.js)

**Responsibility:** Dashboard and management interface

**Pages:**
- Dashboard - Overview, PnL, active positions
- Accounts - Manage accounts across platforms
- Strategies - Configure and monitor strategies
- Markets - Browse and search markets
- Logs - Event and trade logs

### Telegram Bot (Python/aiogram)

**Responsibility:** Critical alerts and remote control

**Features:**
- Fill alerts
- Error alerts
- Position imbalance alerts
- Emergency stop commands
- Strategy start/stop

## Data Flow

### Trade Execution Flow

```
1. User → Web UI → Web API → Predict Account Service
2. Predict Account → Predict.fun API
3. Predict.fun → Fill occurs
4. Predict Account → Publishes "fill" event to Redis
5. Strategy Engine → Consumes fill event
6. Strategy Engine → Executes Delta Neutral handler
7. Delta Neutral → Returns hedge command
8. Strategy Engine → Sends hedge command to Predict Account
9. Predict Account → Places hedge order on Predict.fun
10. Cycle repeats
```

### Event Types

**`fill_events`:**
```json
{
  "type": "fill",
  "platform": "predict",
  "timestamp": "2026-02-05T01:00:00Z",
  "data": {
    "account_id": "uuid",
    "account_name": "account1",
    "market_id": "123",
    "side": "yes",
    "price": 0.55,
    "shares": 100,
    "order_hash": "0x..."
  }
}
```

**Commands:**
```json
{
  "type": "place_order",
  "platform": "predict",
  "account_id": "account2",
  "market_id": "123",
  "side": "no",
  "price": 0.55,
  "shares": 100
}
```

## Databases

### PostgreSQL
- Accounts (all platforms)
- Strategies
- Trades
- Positions

### ClickHouse
- Market data (historical)
- Trade logs (analytical)
- Event logs

### Redis
- Event bus (Streams)
- Real-time state
- Rate limiting

## Deployment

Docker Compose orchestrates all services with:
- Health checks
- Restart policies
- Volume persistence
- Network isolation

## Security

- Private keys encrypted at rest (TODO: implement encryption)
- Per-account proxy support
- No keys in logs
- Separate networks for services
- Postgres/ClickHouse password-protected

## Scalability

Current setup supports:
- ~100 accounts
- ~10 active strategies
- ~1000 events/minute

For larger scale:
- Use Kubernetes for orchestration
- Separate Redis instances per stream
- PostgreSQL replication
- ClickHouse clustering
