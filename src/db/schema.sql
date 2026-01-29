-- supabase/migrations/001_initial_schema.sql

-- Tabela: customers
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number TEXT UNIQUE NOT NULL,
    name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone_number);

-- Tabela: appointments
CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) NOT NULL,
    scheduled_date DATE NOT NULL,
    scheduled_time TIME NOT NULL,
    status TEXT CHECK (status IN ('scheduled', 'confirmed', 'canceled')) NOT NULL,
    confirmation_code TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_appointments_customer ON appointments(customer_id);
CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(scheduled_date);

-- Tabela: messages
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id TEXT UNIQUE NOT NULL, -- Para idempotência
    customer_id UUID REFERENCES customers(id) NOT NULL,
    direction TEXT CHECK (direction IN ('incoming', 'outgoing')) NOT NULL,
    body TEXT NOT NULL,
    intent TEXT,
    trace_id UUID NOT NULL,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_message_id ON messages(message_id);
CREATE INDEX IF NOT EXISTS idx_messages_trace ON messages(trace_id);

-- Tabela: dead_letter_queue
CREATE TABLE IF NOT EXISTS dead_letter_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id TEXT NOT NULL,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    payload JSONB NOT NULL,
    trace_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    retried BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_dlq_trace ON dead_letter_queue(trace_id);

-- Row Level Security (RLS)
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
