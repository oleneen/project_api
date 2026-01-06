DROP TYPE IF EXISTS order_direction_enum CASCADE;
DROP TYPE IF EXISTS order_type_enum CASCADE;
DROP TYPE IF EXISTS order_status_enum CASCADE;

CREATE TYPE order_direction_enum AS ENUM ('BUY', 'SELL');
CREATE TYPE order_type_enum AS ENUM ('MARKET', 'LIMIT');
CREATE TYPE order_status_enum AS ENUM ('NEW', 'EXECUTED', 'PARTIALLY_EXECUTED', 'CANCELLED');

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    api_key VARCHAR(100) UNIQUE NOT NULL,
    role VARCHAR(10) NOT NULL DEFAULT 'USER',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS instruments (
    ticker VARCHAR(10) PRIMARY KEY,
    name VARCHAR(255),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS balances (
    user_id UUID,
    instrument_ticker VARCHAR(10),
    amount INTEGER DEFAULT 0,
    locked INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, instrument_ticker),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (instrument_ticker) REFERENCES instruments(ticker) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    direction order_direction_enum NOT NULL,
    instrument_ticker VARCHAR(10) REFERENCES instruments(ticker) ON DELETE CASCADE,
    qty INTEGER NOT NULL,
    price INTEGER,
    type order_type_enum NOT NULL,
    status order_status_enum NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    filled INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(10) NOT NULL,
    qty INTEGER NOT NULL,
    price INTEGER NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    buy_order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
    sell_order_id UUID REFERENCES orders(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_ticker ON orders(instrument_ticker);
CREATE INDEX IF NOT EXISTS idx_orders_price ON orders(price);
CREATE INDEX IF NOT EXISTS idx_transactions_ticker ON transactions(ticker);
CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp);

INSERT INTO instruments (ticker, name) VALUES
    ('USD', 'US Dollar'),
    ('AAPL', 'Apple Inc.'),
    ('GOOGL', 'Alphabet Inc.'),
    ('MSFT', 'Microsoft Corporation'),
    ('TSLA', 'Tesla Inc.')
ON CONFLICT (ticker) DO NOTHING;

INSERT INTO users (id, name, api_key, role) VALUES
    ('11111111-1111-1111-1111-111111111111', 'Test User', 'test-api-key-123', 'USER')
ON CONFLICT (id) DO NOTHING;

INSERT INTO balances (user_id, instrument_ticker, amount) VALUES
    ('11111111-1111-1111-1111-111111111111', 'USD', 100000),
    ('11111111-1111-1111-1111-111111111111', 'AAPL', 100)
ON CONFLICT (user_id, instrument_ticker) DO NOTHING;