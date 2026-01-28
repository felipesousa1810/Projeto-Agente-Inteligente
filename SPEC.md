# 🔧 SPEC.md - Agente de Atendimento WhatsApp

**Versão:** 1.0.0  
**Data:** 2026-01-28  
**PRD Fonte:** PRD__1_.md v1.0.0  
**Status:** Implementation Ready

---

## CONSTITUTION (Princípios Imutáveis)

### Princípios Arquiteturais
1. **Determinismo First:** Mesma entrada → Mesma saída (100%)
2. **Type Safety:** Todo dado validado via Pydantic schemas
3. **Idempotency:** request_id garante processamento único
4. **Observability:** Trace ID em toda transação
5. **Fail-Safe:** Dead Letter Queue captura 100% das falhas
6. **Data-Centric:** Foco em dados de alta qualidade vs. algoritmos complexos

### Constraints
- **Budget:** $0 (open-source apenas)
- **Latência:** < 500ms P95
- **Uptime:** 99.5% target
- **Solo Dev:** Design bulletproof, automação máxima

---

## SYSTEM ARCHITECTURE

### Stack Tecnológico
```
┌─ Application Layer ────────────────────────────┐
│  FastAPI (Python 3.11+)                        │
│  └─ Pydantic AI (deterministic agent)         │
│     └─ GPT-4o-mini (LLM)                      │
└────────────────────────────────────────────────┘
           ↓
┌─ Integration Layer ────────────────────────────┐
│  Evolution API (WhatsApp Bridge)               │
│  └─ Webhooks (incoming messages)              │
└────────────────────────────────────────────────┘
           ↓
┌─ Data Layer ───────────────────────────────────┐
│  Supabase (PostgreSQL + Auth)                  │
│  └─ Row Level Security (RLS)                  │
└────────────────────────────────────────────────┘
           ↓
┌─ Observability Layer ──────────────────────────┐
│  OpenTelemetry + Jaeger (tracing)             │
│  Structured JSON Logging                       │
└────────────────────────────────────────────────┘
```

---

## DATA CONTRACTS (Schema First)

### 1. Input: WhatsApp Message
```python
# contracts/whatsapp_message.py
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

class WhatsAppMessage(BaseModel):
    """Contrato de entrada: webhook Evolution API"""
    message_id: str = Field(
        ..., 
        description="ID único para idempotência",
        min_length=16,
        max_length=64
    )
    from_number: str = Field(
        ...,
        description="Telefone com código país",
        pattern=r"^\+?[1-9]\d{1,14}$"
    )
    body: str = Field(
        ...,
        description="Texto da mensagem",
        min_length=1,
        max_length=4096
    )
    timestamp: datetime = Field(
        ...,
        description="Timestamp da mensagem"
    )
    
    @field_validator('body')
    def sanitize_body(cls, v):
        # Remove caracteres não-textuais
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "3EB0E51D3B4B1A25AA4AA001",
                "from_number": "+5511987654321",
                "body": "Quero agendar para 15 de fevereiro",
                "timestamp": "2026-01-28T10:30:45.123Z"
            }
        }
```

### 2. Output: Agent Response
```python
# contracts/agent_response.py
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

class IntentType(str, Enum):
    FAQ = "faq"
    SCHEDULE = "schedule"
    RESCHEDULE = "reschedule"
    CANCEL = "cancel"
    UNKNOWN = "unknown"

class AgentResponse(BaseModel):
    """Contrato de saída: resposta do agente"""
    trace_id: str = Field(..., description="UUID para rastreamento")
    intent: IntentType = Field(..., description="Intenção detectada")
    reply_text: str = Field(..., description="Texto da resposta")
    confidence: float = Field(..., ge=0.0, le=1.0)
    appointment_id: str | None = Field(None, description="ID do agendamento (se aplicável)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                "intent": "schedule",
                "reply_text": "Perfeito! Agendei sua consulta para 15/02/2026 às 14:00.",
                "confidence": 0.95,
                "appointment_id": "appt_123456"
            }
        }
```

### 3. Database Schema
```sql
-- supabase/migrations/001_initial_schema.sql

-- Tabela: customers
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number TEXT UNIQUE NOT NULL,
    name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_customers_phone ON customers(phone_number);

-- Tabela: appointments
CREATE TABLE appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) NOT NULL,
    scheduled_date DATE NOT NULL,
    scheduled_time TIME NOT NULL,
    status TEXT CHECK (status IN ('scheduled', 'confirmed', 'canceled')) NOT NULL,
    confirmation_code TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_appointments_customer ON appointments(customer_id);
CREATE INDEX idx_appointments_date ON appointments(scheduled_date);

-- Tabela: messages
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id TEXT UNIQUE NOT NULL, -- Para idempotência
    customer_id UUID REFERENCES customers(id) NOT NULL,
    direction TEXT CHECK (direction IN ('incoming', 'outgoing')) NOT NULL,
    body TEXT NOT NULL,
    intent TEXT,
    trace_id UUID NOT NULL,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_messages_message_id ON messages(message_id);
CREATE INDEX idx_messages_trace ON messages(trace_id);

-- Tabela: dead_letter_queue
CREATE TABLE dead_letter_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id TEXT NOT NULL,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    payload JSONB NOT NULL,
    trace_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    retried BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_dlq_trace ON dead_letter_queue(trace_id);

-- Row Level Security (RLS)
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
```

---

## ML SYSTEM DESIGN (Baseado em Chip Huyen + Eugene Yan + Andrew Ng)

### Princípios de Design

#### 1. Data-Centric Approach (Andrew Ng)
- **Foco:** Dados limpos e consistentes > Modelos complexos
- **Baseline:** Estabelecer performance baseline cedo
- **Validação:** Schema validation em toda entrada de dados

#### 2. Iterative Process (Chip Huyen)
```
Scoping → Data → Modeling → Deployment → Monitor → (loop)
```

#### 3. Production Patterns (Eugene Yan)

**Pattern 1: Early Processing**
- Processar e agregar dados RAW uma vez
- Downstream usa dados processados

**Pattern 2: Validation Hold-out**
- Sempre avaliar antes de produção
- Split temporal (não aleatório)

**Pattern 3: Defensive UX**
- Antecipar erros gracefully
- Transparência sobre limitações

### Agent Configuration

```python
# config/agent_config.py
from pydantic import BaseModel

class AgentConfig(BaseModel):
    """Configuração do agente Pydantic AI"""
    
    # LLM Settings
    model: str = "gpt-4o-mini"
    temperature: float = 0.0  # Determinismo máximo
    max_tokens: int = 256
    timeout: int = 10  # segundos
    
    # Prompt Engineering
    system_prompt: str = """Você é um assistente de agendamentos.
Regras:
1. Sempre extraia data/hora de forma explícita
2. Confirme dados antes de agendar
3. Use linguagem clara e profissional
4. Se não entender, peça clarificação

Formato de data: DD/MM/YYYY
Formato de hora: HH:MM (24h)
"""
    
    # Tools disponíveis
    tools: list[str] = [
        "check_availability",
        "create_appointment",
        "send_confirmation"
    ]
    
    # Validação
    require_confirmation: bool = True
    min_confidence: float = 0.7
```

### Deterministic Prompt Strategy

```python
# agents/deterministic_agent.py
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

# Configuração determinística
agent = Agent(
    model=OpenAIModel(
        'gpt-4o-mini',
        temperature=0.0,  # Zero variação
        seed=42  # Seed fixo para reprodutibilidade
    ),
    system_prompt=SYSTEM_PROMPT,
    retries=0  # Sem retry automático (controlado externamente)
)

# Few-shot examples para consistência
FEW_SHOT_EXAMPLES = [
    {
        "input": "quero agendar para amanhã",
        "output": {
            "intent": "schedule",
            "extracted_date": "TOMORROW",
            "clarification_needed": True,
            "question": "Para que horário você gostaria?"
        }
    },
    {
        "input": "15 de fevereiro às 14h",
        "output": {
            "intent": "schedule",
            "extracted_date": "2026-02-15",
            "extracted_time": "14:00",
            "clarification_needed": False
        }
    }
]
```

### Monitoring & Evaluation (Eugene Yan)

```python
# monitoring/metrics.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class AgentMetrics:
    """Métricas de observabilidade do agente"""
    
    # Performance metrics
    latency_p50: float
    latency_p95: float
    latency_p99: float
    
    # Quality metrics
    intent_accuracy: float
    extraction_accuracy: float
    confidence_score: float
    
    # Business metrics
    successful_bookings: int
    failed_bookings: int
    clarification_rate: float
    
    # System metrics
    error_rate: float
    dlq_count: int
    retry_count: int
    
    measured_at: datetime

# Alertas
ALERT_THRESHOLDS = {
    "latency_p95": 500,  # ms
    "intent_accuracy": 0.85,
    "error_rate": 0.01,
    "dlq_count": 10
}
```

---

## FINITE STATE MACHINE (FSM)

```python
# core/fsm.py
from enum import Enum
from typing import Optional
from pydantic import BaseModel

class AppointmentState(str, Enum):
    """Estados possíveis de um agendamento"""
    INITIATED = "initiated"
    DATE_COLLECTED = "date_collected"
    TIME_COLLECTED = "time_collected"
    CONFIRMED = "confirmed"
    SCHEDULED = "scheduled"
    CANCELED = "canceled"

class StateMachine(BaseModel):
    """Máquina de estados para fluxo de agendamento"""
    current_state: AppointmentState
    customer_id: str
    collected_data: dict = {}
    
    def can_transition_to(self, next_state: AppointmentState) -> bool:
        """Valida se transição é permitida"""
        transitions = {
            AppointmentState.INITIATED: [AppointmentState.DATE_COLLECTED],
            AppointmentState.DATE_COLLECTED: [AppointmentState.TIME_COLLECTED],
            AppointmentState.TIME_COLLECTED: [AppointmentState.CONFIRMED],
            AppointmentState.CONFIRMED: [AppointmentState.SCHEDULED, AppointmentState.CANCELED],
            AppointmentState.SCHEDULED: [AppointmentState.CANCELED],
            AppointmentState.CANCELED: []
        }
        return next_state in transitions.get(self.current_state, [])
    
    def transition(self, next_state: AppointmentState):
        """Executa transição de estado"""
        if not self.can_transition_to(next_state):
            raise ValueError(
                f"Invalid transition: {self.current_state} -> {next_state}"
            )
        self.current_state = next_state
```

---

## CORE IMPLEMENTATION

### Main Application Structure

```
src/
├── main.py                 # FastAPI app
├── config/
│   ├── settings.py        # Environment config
│   └── agent_config.py    # Agent settings
├── contracts/
│   ├── whatsapp_message.py
│   ├── agent_response.py
│   └── appointment.py
├── core/
│   ├── agent.py           # Pydantic AI agent
│   ├── fsm.py            # State machine
│   └── idempotency.py    # Request deduplication
├── services/
│   ├── evolution.py      # Evolution API client
│   ├── supabase.py       # Database client
│   └── observability.py  # OpenTelemetry
├── handlers/
│   └── webhook.py        # Webhook handler
├── utils/
│   ├── logger.py         # Structured logging
│   └── dlq.py           # Dead letter queue
└── tests/
    ├── unit/
    ├── integration/
    └── contract/
```

### Critical Handlers

```python
# handlers/webhook.py
from fastapi import APIRouter, HTTPException, BackgroundTasks
from opentelemetry import trace
from core.agent import process_message
from core.idempotency import check_duplicate
from utils.dlq import send_to_dlq
from contracts.whatsapp_message import WhatsAppMessage

router = APIRouter()
tracer = trace.get_tracer(__name__)

@router.post("/webhook/whatsapp")
async def whatsapp_webhook(
    message: WhatsAppMessage,
    background_tasks: BackgroundTasks
):
    """
    Webhook handler para mensagens WhatsApp
    Garante: idempotência, observabilidade, error handling
    """
    # Criar span para tracing
    with tracer.start_as_current_span("whatsapp_webhook") as span:
        span.set_attribute("message_id", message.message_id)
        
        try:
            # 1. Verificar idempotência
            if await check_duplicate(message.message_id):
                span.set_attribute("duplicate", True)
                return {"status": "duplicate", "processed": False}
            
            # 2. Processar mensagem com agente
            response = await process_message(message)
            span.set_attribute("intent", response.intent)
            
            # 3. Enviar resposta (assíncrono)
            background_tasks.add_task(
                send_whatsapp_reply,
                message.from_number,
                response.reply_text
            )
            
            return {
                "status": "success",
                "trace_id": response.trace_id,
                "intent": response.intent
            }
            
        except Exception as e:
            # 4. Enviar para DLQ
            span.record_exception(e)
            await send_to_dlq(message, str(e))
            raise HTTPException(status_code=500, detail="Processing failed")
```

### Idempotency Implementation

```python
# core/idempotency.py
from typing import Optional
import redis.asyncio as redis
from datetime import timedelta

class IdempotencyManager:
    """Gerencia idempotência via Redis"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.ttl = timedelta(hours=24)  # Cache por 24h
    
    async def check_duplicate(self, request_id: str) -> bool:
        """Verifica se request já foi processado"""
        key = f"idempotency:{request_id}"
        exists = await self.redis.exists(key)
        return bool(exists)
    
    async def mark_processed(self, request_id: str):
        """Marca request como processado"""
        key = f"idempotency:{request_id}"
        await self.redis.setex(key, self.ttl, "1")
```

---

## EVALUATION STRATEGY (Eugene Yan)

### Evals Framework

```python
# evals/eval_suite.py
from dataclasses import dataclass
from typing import List

@dataclass
class EvalCase:
    """Caso de teste para avaliação"""
    input: str
    expected_intent: str
    expected_extraction: dict
    description: str

EVAL_CASES: List[EvalCase] = [
    EvalCase(
        input="Quero agendar para 15 de fevereiro às 14h",
        expected_intent="schedule",
        expected_extraction={
            "date": "2026-02-15",
            "time": "14:00"
        },
        description="Agendamento com data e hora explícitas"
    ),
    EvalCase(
        input="Preciso remarcar",
        expected_intent="reschedule",
        expected_extraction={},
        description="Remarcação sem contexto"
    ),
    # ... adicionar 50+ casos cobrindo edge cases
]

async def run_eval_suite() -> EvalResults:
    """Executa suite de avaliação"""
    results = []
    for case in EVAL_CASES:
        response = await agent.process(case.input)
        results.append({
            "case": case.description,
            "passed": (
                response.intent == case.expected_intent and
                response.extracted_data == case.expected_extraction
            ),
            "actual": response,
            "expected": case
        })
    
    return EvalResults(
        total=len(EVAL_CASES),
        passed=sum(1 for r in results if r["passed"]),
        failed=[r for r in results if not r["passed"]]
    )
```

---

## DEPLOYMENT PIPELINE

### CI/CD Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy Agent

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Contract Tests
        run: pytest tests/contract/ -v
      
      - name: Run Eval Suite
        run: python -m evals.eval_suite
        env:
          MIN_ACCURACY: 0.90
      
      - name: Type Check
        run: mypy src/
      
      - name: Lint
        run: ruff check src/
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Production
        run: |
          # Deploy FastAPI to cloud
          # Update Evolution API webhook URL
          # Run smoke tests
```

---

## ERROR HANDLING & DLQ

```python
# utils/dlq.py
from contracts.whatsapp_message import WhatsAppMessage
from services.supabase import get_supabase_client
import structlog

logger = structlog.get_logger()

async def send_to_dlq(
    message: WhatsAppMessage,
    error: str,
    error_type: str = "processing_error"
):
    """Envia mensagem falha para Dead Letter Queue"""
    supabase = get_supabase_client()
    
    await supabase.table("dead_letter_queue").insert({
        "message_id": message.message_id,
        "error_type": error_type,
        "error_message": error,
        "payload": message.model_dump_json(),
        "trace_id": get_current_trace_id()
    }).execute()
    
    logger.error(
        "message_sent_to_dlq",
        message_id=message.message_id,
        error_type=error_type,
        error=error
    )
```

---

## MONITORING DASHBOARDS

### Key Metrics to Track

1. **Latency:** P50, P95, P99 de response time
2. **Intent Accuracy:** % de intents corretamente identificados
3. **Extraction Accuracy:** % de data/hora corretamente extraídos
4. **Error Rate:** % de requests que falharam
5. **DLQ Size:** Número de mensagens em DLQ
6. **Idempotency Hits:** % de requests duplicados bloqueados

### Jaeger Traces
- Cada request tem trace_id único
- Spans para: webhook, agent, database, external API
- Atributos: message_id, intent, confidence, latency

---

## TESTING STRATEGY

### 1. Contract Tests (Pact-style)
```python
# tests/contract/test_whatsapp_contract.py
def test_whatsapp_message_schema():
    """Valida que input segue contrato"""
    valid_message = {
        "message_id": "ABC123",
        "from_number": "+5511987654321",
        "body": "Olá",
        "timestamp": "2026-01-28T10:00:00Z"
    }
    msg = WhatsAppMessage(**valid_message)
    assert msg.message_id == "ABC123"
```

### 2. Unit Tests (Behavioral)
```python
# tests/unit/test_agent.py
async def test_agent_extracts_date_correctly():
    """Testa extração determinística de data"""
    input_text = "Quero agendar para 15 de fevereiro"
    response = await agent.process(input_text)
    assert response.intent == "schedule"
    assert response.extracted_data["date"] == "2026-02-15"
```

### 3. Integration Tests
```python
# tests/integration/test_full_flow.py
async def test_end_to_end_booking():
    """Testa fluxo completo de agendamento"""
    # 1. Simular webhook
    # 2. Verificar resposta do agente
    # 3. Confirmar registro no DB
    # 4. Validar envio de confirmação
```

---

## CONFIGURATION

### Environment Variables

```bash
# .env.example

# LLM
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.0

# Database
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...

# Evolution API
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=xxx

# Observability
JAEGER_ENDPOINT=http://localhost:14268/api/traces
LOG_LEVEL=INFO

# Redis (Idempotency)
REDIS_URL=redis://localhost:6379

# Application
APP_ENV=production
API_PORT=8000
```

---

## ACCEPTANCE CRITERIA

### MVP Definition of Done

✅ **Functional:**
- [ ] Recebe webhook de Evolution API
- [ ] Extrai intent (FAQ, Schedule, Cancel)
- [ ] Persiste em Supabase com schema validado
- [ ] Envia resposta via WhatsApp
- [ ] Idempotência garantida (100%)

✅ **Quality:**
- [ ] Intent accuracy > 90% (eval suite)
- [ ] Latency P95 < 500ms
- [ ] Zero erros não capturados (DLQ = 100%)
- [ ] Coverage > 80%
- [ ] Type safety (mypy strict)

✅ **Observability:**
- [ ] Trace ID em todos os logs
- [ ] Jaeger dashboard operacional
- [ ] Alertas configurados

---

## RISKS & MITIGATION

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Evolution API downtime | High | Medium | Retry com exponential backoff, queue em Redis |
| LLM latency > 5s | High | Low | Timeout de 10s, fallback para regras hard-coded |
| Supabase quota exceeded | High | Low | Monitorar storage mensal, exportar dados históricos |
| Non-deterministic LLM output | Medium | Medium | Temperature=0.0, seed fixo, eval suite contínua |

---

## NEXT STEPS (Post-MVP)

1. **V1.1:** Dashboard web para visualizar agendamentos
2. **V1.2:** Integração com Google Calendar
3. **V1.3:** Suporte a múltiplos idiomas
4. **V2.0:** Fine-tuning do modelo para domínio específico

---

## REFERENCES

### Academic & Industry
- Chip Huyen: "Designing Machine Learning Systems" (O'Reilly, 2022)
- Eugene Yan: "Patterns for LLM Systems" (eugeneyan.com)
- Andrew Ng: "MLOps Specialization" (Coursera)

### Spec-Driven Development
- GitHub Spec Kit: https://github.com/github/spec-kit
- Addy Osmani: "Good Spec for AI Agents"
- Tessl: "Spec-Driven Development"

### Tools Documentation
- Pydantic AI: https://ai.pydantic.dev/
- FastAPI: https://fastapi.tiangolo.com/
- OpenTelemetry: https://opentelemetry.io/
- Evolution API: https://github.com/EvolutionAPI/evolution-api

---

**Document Status:** ✅ Ready for Implementation  
**Next Action:** Generate implementation code following this spec  
**Validation:** Run eval suite to confirm > 90% accuracy before production
