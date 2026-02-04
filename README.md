# Predict Trading System 🎯

Event-driven multi-platform prediction market trading system with automated strategies.

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────┐
│                    UI Layer                         │
│  ┌──────────────┐         ┌──────────────────────┐ │
│  │ Web Frontend │         │  Telegram Bot       │ │
│  │ (React)      │         │  (Alerts, Control)  │ │
│  └──────────────┘         └──────────────────────┘ │
└─────────────────────────────────────────────────────┘
              │                        │
              └────────────┬───────────┘
                           │ (REST/WebSocket)
┌─────────────────────────────────────────────────────┐
│           Strategy Engine (Golang)                  │
│  ┌──────────────────────────────────────────────┐  │
│  │  Event Bus (Redis Streams)                   │  │
│  │  - Trade fills                               │  │
│  │  - Order cancels                             │  │
│  │  - Market updates                            │  │
│  └──────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │  Strategy Executor                           │  │
│  │  - Delta Neutral                             │  │
│  │  - Custom strategies                         │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
       │                │                │
       ▼                ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Predict.fun  │ │ Polymarket   │ │  ClickHouse  │
│ Account Svc  │ │ Account Svc  │ │  Data Store  │
│ (Python)     │ │ (Python)     │ │              │
└──────────────┘ └──────────────┘ └──────────────┘
```

## 🚀 Features

- ✅ **Multi-account management** - Predict.fun & Polymarket
- ✅ **Event-driven strategies** - React to fills, cancels, market changes
- ✅ **Delta neutral trading** - Automated hedging across platforms
- ✅ **Real-time monitoring** - Web dashboard + Telegram alerts
- ✅ **Account isolation** - Proxy support per account
- ✅ **Strategy versioning** - Code + config in database

## 📦 Services

### Core Services
- **predict-account** - Predict.fun account & trading service (Python/FastAPI)
- **polymarket-account** - Polymarket account & trading service (Python/FastAPI)
- **strategy-engine** - Event processing & strategy execution (Golang)
- **web-api** - Web API & WebSocket gateway (Python/FastAPI)

### UI
- **web** - React dashboard for monitoring & management
- **telegram** - Telegram bot for alerts & critical controls

### Infrastructure
- **ClickHouse** - Market data & trade logs
- **PostgreSQL** - Accounts, strategies, configs
- **Redis** - Event bus (Redis Streams)

## 🔧 Quick Start

### Prerequisites
- Docker & Docker Compose
- Predict.fun API key ([request here](https://discord.gg/predictdotfun))
- Telegram bot token (optional, for alerts)

### Setup

```bash
# Clone repository
git clone https://github.com/mukhametgalin/predict-trading-system.git
cd predict-trading-system

# Copy example env
cp .env.example .env

# Edit .env with your API keys
nano .env

# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### Add accounts

```bash
# Using CLI
./scripts/add-account.sh predict account1 0xYOUR_PRIVATE_KEY http://proxy:8080

# Or via Web UI
# Navigate to http://localhost:3000/accounts
```

### Run first strategy

```bash
# Initialize delta neutral strategy
./scripts/init-strategy.sh delta-neutral \
  --accounts acc1,acc2,acc3,acc4 \
  --markets market_id_1,market_id_2

# Start strategy
curl -X POST http://localhost:8001/strategies/delta-neutral/start
```

## 📊 Monitoring

- **Web Dashboard**: http://localhost:3000
- **API Docs**: http://localhost:8001/docs
- **ClickHouse UI**: http://localhost:8123/play
- **Redis Commander**: http://localhost:8081

## 🎯 Strategies

### Delta Neutral (Built-in)

Automated hedging strategy:
1. Place limit orders on Platform A (e.g., Predict.fun YES @ -2% from mid)
2. When filled, immediately place opposite order on Platform B (e.g., Predict.fun NO @ same price)
3. Monitor positions and alert on imbalances

**Configuration:**
```yaml
strategy: delta_neutral_v1
active_accounts:
  - predict_acc1
  - predict_acc2
  - predict_acc3
  - predict_acc4
pairs:
  - primary: predict_acc1
    hedge: predict_acc2
  - primary: predict_acc3
    hedge: predict_acc4
markets:
  - market_id_1
  - market_id_2
initial_orders:
  side: yes
  price_offset: -0.02  # -2% from best bid
  shares: 100
target_platform: predict  # Start with predict-only, later: polymarket
```

### Custom Strategies

Create your own strategies by implementing the strategy interface:

```go
type Strategy interface {
    OnEvent(event Event) ([]Command, error)
    OnInit(config Config) error
    OnShutdown() error
}
```

## 🔐 Security

- All private keys encrypted at rest
- Per-account proxy support
- No keys in logs or UI
- Telegram 2FA for critical operations

## 📚 Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [Strategy Development](docs/STRATEGIES.md)
- [Deployment](docs/DEPLOYMENT.md)

## 🐛 Troubleshooting

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

## 🤝 Contributing

Pull requests welcome!

## 📄 License

MIT
