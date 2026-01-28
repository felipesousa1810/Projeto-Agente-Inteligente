-- Supabase Initial Schema
-- Migration: 001_initial_schema.sql
-- Description: Create initial tables for WhatsApp Agent

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabela: customers
-- Armazena informações dos clientes
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number TEXT UNIQUE NOT NULL,
    name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index para busca por telefone
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone_number);

-- Tabela: appointments
-- Armazena agendamentos
CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) NOT NULL,
    scheduled_date DATE NOT NULL,
    scheduled_time TIME NOT NULL,
    status TEXT CHECK (status IN ('scheduled', 'confirmed', 'canceled')) NOT NULL DEFAULT 'scheduled',
    confirmation_code TEXT UNIQUE NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes para appointments
CREATE INDEX IF NOT EXISTS idx_appointments_customer ON appointments(customer_id);
CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);
CREATE INDEX IF NOT EXISTS idx_appointments_confirmation_code ON appointments(confirmation_code);

-- Tabela: messages
-- Armazena histórico de mensagens para observabilidade
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id TEXT UNIQUE NOT NULL,  -- ID original do WhatsApp para idempotência
    customer_id UUID REFERENCES customers(id) NOT NULL,
    direction TEXT CHECK (direction IN ('incoming', 'outgoing')) NOT NULL,
    body TEXT NOT NULL,
    intent TEXT,
    trace_id UUID NOT NULL,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes para messages
CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_message_id ON messages(message_id);
CREATE INDEX IF NOT EXISTS idx_messages_trace ON messages(trace_id);
CREATE INDEX IF NOT EXISTS idx_messages_customer ON messages(customer_id);
CREATE INDEX IF NOT EXISTS idx_messages_direction ON messages(direction);

-- Tabela: dead_letter_queue
-- Armazena mensagens que falharam no processamento
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

-- Indexes para DLQ
CREATE INDEX IF NOT EXISTS idx_dlq_trace ON dead_letter_queue(trace_id);
CREATE INDEX IF NOT EXISTS idx_dlq_retried ON dead_letter_queue(retried);
CREATE INDEX IF NOT EXISTS idx_dlq_created_at ON dead_letter_queue(created_at);

-- Tabela: conversation_state
-- Armazena estado da conversa (FSM) por cliente
CREATE TABLE IF NOT EXISTS conversation_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) UNIQUE NOT NULL,
    current_state TEXT NOT NULL DEFAULT 'initiated',
    collected_data JSONB DEFAULT '{}',
    history JSONB DEFAULT '[]',
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '24 hours'),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index para busca por customer
CREATE INDEX IF NOT EXISTS idx_conversation_state_customer ON conversation_state(customer_id);
CREATE INDEX IF NOT EXISTS idx_conversation_state_expires ON conversation_state(expires_at);

-- Row Level Security (RLS)
-- Habilita RLS em todas as tabelas
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE dead_letter_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_state ENABLE ROW LEVEL SECURITY;

-- Políticas RLS (permitem tudo para service_role, que é usado pelo backend)
-- Em produção, você deve criar políticas mais restritivas

-- Customers: service_role pode tudo
CREATE POLICY "Service role full access to customers"
ON customers
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Appointments: service_role pode tudo
CREATE POLICY "Service role full access to appointments"
ON appointments
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Messages: service_role pode tudo
CREATE POLICY "Service role full access to messages"
ON messages
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- DLQ: service_role pode tudo
CREATE POLICY "Service role full access to dlq"
ON dead_letter_queue
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Conversation State: service_role pode tudo
CREATE POLICY "Service role full access to conversation_state"
ON conversation_state
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Função para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para updated_at
CREATE TRIGGER update_customers_updated_at
    BEFORE UPDATE ON customers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_appointments_updated_at
    BEFORE UPDATE ON appointments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversation_state_updated_at
    BEFORE UPDATE ON conversation_state
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Função para limpar estados de conversa expirados
CREATE OR REPLACE FUNCTION cleanup_expired_conversation_states()
RETURNS void AS $$
BEGIN
    DELETE FROM conversation_state WHERE expires_at < NOW();
END;
$$ language 'plpgsql';

-- Comentários para documentação
COMMENT ON TABLE customers IS 'Clientes do sistema de agendamento';
COMMENT ON TABLE appointments IS 'Agendamentos realizados';
COMMENT ON TABLE messages IS 'Histórico de mensagens WhatsApp';
COMMENT ON TABLE dead_letter_queue IS 'Mensagens que falharam no processamento';
COMMENT ON TABLE conversation_state IS 'Estado da conversa por cliente (FSM)';

COMMENT ON COLUMN messages.message_id IS 'ID original do WhatsApp para garantir idempotência';
COMMENT ON COLUMN messages.trace_id IS 'ID de rastreamento para observabilidade';
COMMENT ON COLUMN appointments.confirmation_code IS 'Código único de confirmação no formato APPT-XXXXXX';
