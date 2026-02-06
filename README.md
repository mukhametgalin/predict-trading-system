# Predict Trading System

Микросервисная система для автоматизированной торговли на prediction markets (Predict.fun, Polymarket).

## Оглавление

- [Архитектура](#архитектура)
- [Сервисы](#сервисы)
- [Быстрый старт](#быстрый-старт)
- [Отправка ордеров (Predict.fun)](#отправка-ордеров-predictfun)
- [Типы аккаунтов](#типы-аккаунтов)
- [API Endpoints](#api-endpoints)
- [Стратегии](#стратегии)
- [Event Bus (Redis Streams)](#event-bus-redis-streams)
- [База данных](#база-данных)
- [Telegram Bot](#telegram-bot)
- [Разработка](#разработка)

---

## Архитектура

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Web UI       │     │  Telegram Bot   │     │   External      │
│   (Next.js)     │     │   (aiogram)     │     │   Clients       │
│   :3000         │     │                 │     │                 │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │      Web API Gateway    │
                    │       (FastAPI)         │
                    │         :8001           │
                    └────────────┬────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌────────▼────────┐    ┌────────▼────────┐    ┌────────▼────────┐
│ Predict Account │    │Strategy Engine  │    │Polymarket Acct  │
│   (FastAPI)     │    │    (Golang)     │    │   (FastAPI)     │
│     :8010       │    │     :8020       │    │     :8011       │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
     ┌────────▼────────┐ ┌──────▼──────┐ ┌────────▼────────┐
     │   PostgreSQL    │ │    Redis    │ │   ClickHouse    │
     │     :5432       │ │    :6379    │ │  :8123/:9000    │
     └─────────────────┘ └─────────────┘ └─────────────────┘
```

### Потоки данных

1. **Trade Flow:** UI/Bot → Web API → Predict Account → Predict.fun API
2. **Event Flow:** Predict Account → Redis Streams → Strategy Engine → Predict Account
3. **Analytics Flow:** Redis Streams → ClickHouse (async)

---

## Сервисы

| Сервис | Порт | Технология | Описание |
|--------|------|------------|----------|
| **Web UI** | 3000 | Next.js 15, React 19, shadcn/ui | Дашборд для управления |
| **Web API** | 8001 | Python FastAPI | Центральный API gateway |
| **Predict Account** | 8010 | Python FastAPI | Управление аккаунтами и трейдами Predict.fun |
| **Polymarket Account** | 8011 | Python FastAPI | Управление аккаунтами Polymarket (WIP) |
| **Strategy Engine** | 8020 | Golang | Обработка стратегий, авто-хеджирование |
| **Telegram Bot** | - | Python aiogram 3 | Управление через Telegram |
| **PostgreSQL** | 5432 | PostgreSQL 16 | Аккаунты, стратегии, трейды |
| **ClickHouse** | 8123/9000 | ClickHouse 24 | Маркеты, аналитика, история |
| **Redis** | 6379 | Redis 7 | Event bus (Streams) |

---

## Быстрый старт

```bash
# 1. Клонировать репозиторий
git clone https://github.com/mukhametgalin/predict-trading-system
cd predict-trading-system

# 2. Скопировать и настроить .env
cp .env.example .env
# Отредактировать: TELEGRAM_BOT_TOKEN, TELEGRAM_BOT_PASSWORD

# 3. Запустить
docker compose up -d

# 4. Проверить статус
docker compose ps

# 5. Открыть UI
open http://localhost:3000
```

---

## Отправка ордеров (Predict.fun)

> ⚠️ **Важно:** Это ключевая часть системы. Predict.fun требует EIP-712 подписанные ордера.

### Два типа аккаунтов

1. **EOA (Externally Owned Account)** — обычный кошелёк
2. **Predict Account (Smart Wallet)** — смарт-контракт кошелёк, создаётся через Privy

### Процесс отправки ордера (Predict Account)

```
┌──────────────────────────────────────────────────────────────────┐
│                      ORDER SUBMISSION FLOW                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. GET MARKET INFO                                              │
│     GET /v1/markets/{market_id}                                  │
│     → feeRateBps, isNegRisk, isYieldBearing, outcomes            │
│                                                                  │
│  2. AUTHENTICATE (Predict Account flow)                          │
│     a) GET /v1/auth/message                                      │
│     b) Sign message with SDK:                                    │
│        builder.sign_predict_account_message(message)             │
│     c) POST /v1/auth {signer: predict_account, signature, msg}   │
│     → JWT token                                                  │
│                                                                  │
│  3. BUILD ORDER (predict-sdk)                                    │
│     a) Calculate amounts:                                        │
│        builder.get_limit_order_amounts(LimitHelperInput)         │
│     b) Build order:                                              │
│        builder.build_order("LIMIT", BuildOrderInput)             │
│     c) Build typed data:                                         │
│        builder.build_typed_data(order, is_neg_risk, is_yield)    │
│     d) Sign order:                                               │
│        builder.sign_typed_data_order(typed_data)                 │
│                                                                  │
│  4. SUBMIT ORDER                                                 │
│     POST /v1/orders                                              │
│     Headers: Authorization: Bearer {jwt}                         │
│     Body: {data: {pricePerShare, strategy, order, ...}}          │
│     → 201 Created                                                │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Формат payload для /v1/orders

```python
payload = {
    "data": {
        "pricePerShare": "500000000000000000",  # price * 1e18
        "strategy": "LIMIT",                    # or "MARKET"
        "slippageBps": "0",
        "isFillOrKill": False,
        "order": {
            "salt": "699349179",
            "maker": "0x3E54...",               # Predict Account address
            "signer": "0x3E54...",              # Predict Account address
            "taker": "0x0000...0000",
            "tokenId": "50929...",              # outcome.onChainId
            "makerAmount": "1000000000000000000",
            "takerAmount": "2000000000000000000",
            "expiration": "4102444800",
            "nonce": "0",
            "feeRateBps": "200",
            "side": 0,                          # 0=BUY, 1=SELL (integer!)
            "signatureType": 0,                 # integer
            "signature": "0x01845A..."          # EIP-712 signature
        }
    }
}
```

### Ключевые моменты

| Аспект | Детали |
|--------|--------|
| **SDK** | `predict-sdk==0.0.12` — обязателен для подписи |
| **Amounts scale** | Все суммы в wei (× 10^18) |
| **side** | Integer: `0` = BUY, `1` = SELL |
| **signatureType** | Integer: `0` = EOA |
| **Minimum order** | $0.90 USD |
| **Token ID** | Из `outcome.onChainId` маркета |
| **Predict Account** | Передаётся в `OrderBuilderOptions(predict_account=...)` |

### Код отправки (упрощённо)

```python
from predict_sdk import OrderBuilder, ChainId
from predict_sdk.types import BuildOrderInput, LimitHelperInput, OrderBuilderOptions
from predict_sdk.constants import Side

# 1. Создать builder с Predict Account
builder = OrderBuilder.make(
    ChainId.BNB_MAINNET,
    private_key,  # Privy EOA key
    options=OrderBuilderOptions(predict_account=predict_account_address)
)

# 2. Аутентификация
message = get_auth_message()
signature = builder.sign_predict_account_message(message)
jwt = get_jwt(signer=predict_account_address, signature=signature, message=message)

# 3. Построить ордер
amounts = builder.get_limit_order_amounts(
    LimitHelperInput(side=Side.BUY, price_per_share_wei=price_wei, quantity_wei=qty_wei)
)
order = builder.build_order("LIMIT", BuildOrderInput(
    side=Side.BUY,
    token_id=token_id,
    maker_amount=amounts.maker_amount,
    taker_amount=amounts.taker_amount,
    fee_rate_bps=fee_bps,
    signer=predict_account_address,
))
typed_data = builder.build_typed_data(order, is_neg_risk=..., is_yield_bearing=...)
signed = builder.sign_typed_data_order(typed_data)

# 4. Отправить
response = post("/v1/orders", headers={"Authorization": f"Bearer {jwt}"}, json=payload)
```

---

## Типы аккаунтов

### Predict Account (Smart Wallet) — рекомендуется

- Создаётся через Privy при регистрации на Predict.fun
- Адрес начинается с любого hex (например `0x3E54...`)
- Требует особый flow подписи через SDK
- Поддерживает gasless транзакции

**В БД:**
- `address` = Predict Account address (smart wallet)
- `private_key` = Privy EOA private key (для подписи)

### EOA (Legacy)

- Обычный Ethereum кошелёк
- Адрес = address derived from private key
- Стандартная EIP-712 подпись

---

## API Endpoints

### Web API Gateway (:8001)

| Method | Endpoint | Описание |
|--------|----------|----------|
| GET | `/dashboard/stats` | Статистика системы |
| GET | `/accounts` | Список всех аккаунтов |
| POST | `/accounts/{platform}` | Создать аккаунт |
| GET | `/accounts/{platform}/{id}` | Детали аккаунта |
| PUT | `/accounts/{platform}/{id}` | Обновить аккаунт |
| POST | `/accounts/{platform}/{id}/disable` | Kill-switch аккаунта |
| POST | `/accounts/{platform}/{id}/close-all` | Закрыть все позиции |
| DELETE | `/accounts/{platform}/{id}` | Удалить аккаунт |
| POST | `/trade` | Выполнить трейд |
| GET | `/trades` | История трейдов |
| GET | `/positions/{platform}/{id}` | Позиции аккаунта |
| GET | `/orders/{platform}/{id}` | Ордера аккаунта |
| GET | `/markets` | Список маркетов |
| GET | `/strategies` | Список стратегий |
| POST | `/strategies` | Создать стратегию |
| PUT | `/strategies/{id}` | Обновить стратегию |
| GET | `/alerts` | Список алертов |
| POST | `/alerts` | Создать алерт |
| WS | `/ws` | WebSocket для real-time событий |

### Predict Account Service (:8010)

| Method | Endpoint | Описание |
|--------|----------|----------|
| GET | `/accounts` | Список аккаунтов |
| POST | `/accounts` | Создать аккаунт |
| GET | `/accounts/{id}` | Детали аккаунта |
| PUT | `/accounts/{id}` | Обновить |
| DELETE | `/accounts/{id}` | Удалить |
| POST | `/trade` | Выполнить трейд (`confirm=false` для dry-run) |
| GET | `/trades` | История трейдов |
| GET | `/positions/{id}` | Позиции |
| GET | `/orders/{id}` | Ордера |
| POST | `/accounts/{id}/close-all` | Закрыть все позиции |

---

## Стратегии

### Delta Neutral

Автоматическое хеджирование между парными аккаунтами:

```
Account A: BUY YES $10 @ 0.60
    ↓ (event via Redis)
Strategy Engine detects fill
    ↓
Account B: BUY NO $10 @ 0.40 (auto-hedge)
```

**Конфигурация:**
```json
{
  "pairs": [
    {"primary": "account1_uuid", "hedge": "account2_uuid"}
  ],
  "target_platform": "predict",
  "price_adjustment": 0.0,
  "max_position_size": 10.0
}
```

---

## Event Bus (Redis Streams)

### Streams

| Stream | Publisher | Consumer | События |
|--------|-----------|----------|---------|
| `trade_events` | Predict Account | Strategy Engine, Web API | trade_executed, trade_error, trade_dry_run |
| `fill_events` | Predict Account | Strategy Engine | order_filled |
| `account_events` | Predict Account | Web API | account_created, account_updated, account_disabled |

### Формат события

```json
{
  "type": "trade_executed",
  "timestamp": "2026-02-06T11:30:00Z",
  "data": {
    "account_id": "uuid",
    "account_name": "TestAccount1",
    "market_id": "6087",
    "side": "yes",
    "price": 0.50,
    "shares": 2.0,
    "order_hash": "0x...",
    "platform": "predict"
  }
}
```

---

## База данных

### PostgreSQL — Таблицы

| Таблица | Описание |
|---------|----------|
| `predict_accounts` | Аккаунты Predict.fun |
| `predict_trades` | История трейдов |
| `predict_positions` | Позиции (кэш) |
| `strategies` | Стратегии |
| `strategy_logs` | Логи стратегий |
| `alerts` | Алерты системы |
| `users` | Пользователи (Telegram auth) |

### predict_accounts

```sql
CREATE TABLE predict_accounts (
    id UUID PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    address VARCHAR(42) NOT NULL,      -- Predict Account address
    private_key TEXT NOT NULL,          -- Privy EOA key
    api_key TEXT,                       -- Custom API key (optional)
    proxy_url TEXT,
    active BOOLEAN DEFAULT true,
    tags TEXT[],
    notes TEXT,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);
```

### ClickHouse — Аналитика

| Таблица | Описание |
|---------|----------|
| `markets` | Маркеты (синхронизация с API) |
| `trades_history` | Детальная история для аналитики |

---

## Telegram Bot

### Команды

| Команда | Описание |
|---------|----------|
| `/start` | Главное меню |
| `/auth <password>` | Аутентификация |
| `/stats` | Статистика |
| `/accounts` | Список аккаунтов |
| `/trade` | Новый трейд |
| `/cancel` | Отмена операции |

### Inline меню

- 📊 Dashboard — статистика
- 👥 Accounts — управление аккаунтами
- 📈 Markets — топ маркетов
- 💹 Trade — новый трейд
- 🎯 Strategies — стратегии
- 🔔 Alerts — алерты

---

## Разработка

### Makefile команды

```bash
make build          # Собрать все образы
make up             # Запустить всё
make down           # Остановить
make logs           # Логи всех сервисов
make logs-predict   # Логи Predict Account
make status         # Статус контейнеров
make shell-db       # Shell в PostgreSQL
make test           # Запустить тесты
```

### Локальная разработка

```bash
# Python сервисы
cd services/predict-account
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8010

# Web UI
cd ui/web
npm install
npm run dev
```

### Тестовые скрипты

```bash
# Тест отправки ордера через SDK
python scripts/sdk_limit_order_test.py

# Тест через Predict Account flow
python scripts/test_place_order_predict_account.py \
  --api-key ... \
  --privy-key ... \
  --predict-account 0x3E54... \
  --market-id 6087 \
  --outcome Yes \
  --price 0.50 \
  --shares 2
```

---

## Лимиты и безопасность

| Параметр | Значение |
|----------|----------|
| Минимальный ордер | $0.90 USD |
| Тестовый лимит | $10 суммарно |
| Slippage (market orders) | 100 bps (1%) |

⚠️ **Приватные ключи хранятся в открытом виде в БД.** В production необходимо:
- Шифрование at-rest
- Vault/HSM для ключей
- Ограничение доступа к БД

---

## TODO

- [ ] Polymarket интеграция
- [ ] Market orders (через orderbook)
- [ ] Шифрование приватных ключей
- [ ] Больше стратегий (arbitrage, market maker)
- [ ] Бэктестинг
- [ ] Аналитика и отчёты в ClickHouse
- [ ] Rate limiting
- [ ] Алерты в Telegram при событиях
- [ ] Мониторинг (Prometheus/Grafana)

---

## Стек технологий

| Категория | Технологии |
|-----------|------------|
| **Frontend** | Next.js 15, React 19, TailwindCSS, shadcn/ui |
| **Backend** | Python 3.12 FastAPI, Golang 1.21 |
| **SDK** | predict-sdk 0.0.12, web3.py, eth-account |
| **Event Bus** | Redis 7 Streams |
| **Databases** | PostgreSQL 16, ClickHouse 24 |
| **Bot** | Python aiogram 3 |
| **Deploy** | Docker Compose |

---

## Лицензия

MIT
