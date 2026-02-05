-- Predict Trading System - PostgreSQL Schema

-- ===== Accounts =====

CREATE TABLE IF NOT EXISTS accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(50) NOT NULL DEFAULT 'predict',  -- predict, polymarket
    name VARCHAR(255) NOT NULL,
    address VARCHAR(42) NOT NULL,
    private_key_encrypted TEXT NOT NULL,
    api_key TEXT,
    proxy_url TEXT,
    active BOOLEAN DEFAULT true,
    tags TEXT[] DEFAULT '{}',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_accounts_platform ON accounts(platform);
CREATE INDEX idx_accounts_active ON accounts(active);
CREATE INDEX idx_accounts_tags ON accounts USING GIN(tags);

-- ===== Trades =====

CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    market_id VARCHAR(255) NOT NULL,
    outcome_id VARCHAR(255),
    side VARCHAR(10) NOT NULL,  -- yes, no
    price DECIMAL(10, 6) NOT NULL,
    shares DECIMAL(20, 8) NOT NULL,
    order_hash VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',  -- pending, filled, cancelled, error
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    filled_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_trades_account ON trades(account_id);
CREATE INDEX idx_trades_market ON trades(market_id);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_created ON trades(created_at DESC);

-- ===== Positions =====

CREATE TABLE IF NOT EXISTS positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    market_id VARCHAR(255) NOT NULL,
    outcome_id VARCHAR(255) NOT NULL,
    side VARCHAR(10) NOT NULL,
    shares DECIMAL(20, 8) DEFAULT 0,
    avg_price DECIMAL(10, 6) DEFAULT 0,
    realized_pnl DECIMAL(20, 8) DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_id, market_id, outcome_id)
);

CREATE INDEX idx_positions_account ON positions(account_id);
CREATE INDEX idx_positions_market ON positions(market_id);

-- ===== Strategies =====

CREATE TABLE IF NOT EXISTS strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,  -- delta_neutral, arbitrage, market_maker
    config JSONB NOT NULL DEFAULT '{}',
    enabled BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_strategies_type ON strategies(type);
CREATE INDEX idx_strategies_enabled ON strategies(enabled);

-- ===== Strategy Logs =====

CREATE TABLE IF NOT EXISTS strategy_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID REFERENCES strategies(id) ON DELETE CASCADE,
    level VARCHAR(20) NOT NULL,  -- info, warn, error
    message TEXT NOT NULL,
    data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_strategy_logs_strategy ON strategy_logs(strategy_id);
CREATE INDEX idx_strategy_logs_level ON strategy_logs(level);
CREATE INDEX idx_strategy_logs_created ON strategy_logs(created_at DESC);

-- ===== Users (for web UI auth) =====

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE,
    username VARCHAR(255),
    role VARCHAR(50) DEFAULT 'viewer',  -- admin, trader, viewer
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_telegram ON users(telegram_id);

-- ===== Alerts =====

CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(100) NOT NULL,  -- trade, fill, error, strategy
    title VARCHAR(255) NOT NULL,
    message TEXT,
    data JSONB,
    read BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_alerts_type ON alerts(type);
CREATE INDEX idx_alerts_read ON alerts(read);
CREATE INDEX idx_alerts_created ON alerts(created_at DESC);

-- ===== Functions =====

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER accounts_updated_at
    BEFORE UPDATE ON accounts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER strategies_updated_at
    BEFORE UPDATE ON strategies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER positions_updated_at
    BEFORE UPDATE ON positions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
