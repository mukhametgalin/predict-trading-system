-- Predict Trading System - ClickHouse Schema

-- ===== Markets =====

CREATE TABLE IF NOT EXISTS markets (
    market_id String,
    platform LowCardinality(String),  -- predict, polymarket
    question String,
    category LowCardinality(String),
    end_date DateTime64(3),
    liquidity Float64,
    volume Float64,
    yes_price Float64,
    no_price Float64,
    updated_at DateTime64(3) DEFAULT now64(3)
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (platform, market_id);

-- ===== Price History =====

CREATE TABLE IF NOT EXISTS price_history (
    market_id String,
    platform LowCardinality(String),
    timestamp DateTime64(3),
    yes_price Float64,
    no_price Float64,
    volume Float64
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (platform, market_id, timestamp)
TTL toDateTime(timestamp) + INTERVAL 90 DAY;

-- ===== Trade History =====

CREATE TABLE IF NOT EXISTS trade_history (
    trade_id String,
    account_id String,
    platform LowCardinality(String),
    market_id String,
    side LowCardinality(String),
    price Float64,
    shares Float64,
    status LowCardinality(String),
    created_at DateTime64(3),
    filled_at Nullable(DateTime64(3))
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(created_at)
ORDER BY (platform, account_id, created_at);

-- ===== Fill Events =====

CREATE TABLE IF NOT EXISTS fill_events (
    event_id String,
    account_id String,
    platform LowCardinality(String),
    market_id String,
    outcome_id String,
    side LowCardinality(String),
    price Float64,
    shares Float64,
    timestamp DateTime64(3)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (platform, account_id, timestamp);

-- ===== Strategy Events =====

CREATE TABLE IF NOT EXISTS strategy_events (
    event_id String,
    strategy_id String,
    strategy_type LowCardinality(String),
    event_type LowCardinality(String),  -- trigger, execute, error
    data String,  -- JSON
    timestamp DateTime64(3)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (strategy_type, timestamp);

-- ===== Materialized Views =====

-- Daily PnL by account
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_pnl_mv
ENGINE = SummingMergeTree()
ORDER BY (platform, account_id, date)
AS SELECT
    platform,
    account_id,
    toDate(filled_at) AS date,
    sum(CASE WHEN side = 'yes' THEN -price * shares ELSE price * shares END) AS pnl,
    count() AS trade_count
FROM trade_history
WHERE status = 'filled'
GROUP BY platform, account_id, date;

-- Hourly volume by market
CREATE MATERIALIZED VIEW IF NOT EXISTS hourly_volume_mv
ENGINE = SummingMergeTree()
ORDER BY (platform, market_id, hour)
AS SELECT
    platform,
    market_id,
    toStartOfHour(timestamp) AS hour,
    sum(volume) AS volume
FROM price_history
GROUP BY platform, market_id, hour;
