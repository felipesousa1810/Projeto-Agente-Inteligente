# 🤖 AGENTS.md - Agente de Atendimento WhatsApp

> **Para Agentes de IDE:** Este arquivo contém instruções específicas para implementar o projeto. Leia SPEC.md primeiro para contexto técnico completo.

---

## 🎯 META-INSTRUÇÃO (Leia Primeiro)

**Você é um agente de código especializado em:**
- Python 3.11+ com type hints estritos
- FastAPI para APIs REST
- Pydantic AI para agentes determinísticos
- Arquitetura orientada a contratos (Schema First)

**Filosofia de Desenvolvimento:**
1. **Determinismo > Flexibilidade:** Mesma entrada sempre produz mesma saída
2. **Type Safety > Praticidade:** Todo dado validado via Pydantic
3. **Testes > Documentação:** Código auto-explicativo com testes abrangentes
4. **Observabilidade > Debug:** Trace ID em toda transação

**Quando Estiver em Dúvida:**
- ❓ Peça clarificação antes de implementar
- 📋 Proponha um plano em bullet points
- 🚫 NUNCA faça mudanças especulativas grandes
- ✅ SEMPRE rode testes após mudanças

---

## 📁 ESTRUTURA DO PROJETO

```
whatsapp-agent/
├── src/
│   ├── main.py                    # FastAPI app entry point
│   ├── config/
│   │   ├── settings.py           # Pydantic Settings (env vars)
│   │   └── agent_config.py       # Agent configuration
│   ├── contracts/                 # Pydantic schemas (READ FIRST)
│   │   ├── whatsapp_message.py   # Input contract
│   │   ├── agent_response.py     # Output contract
│   │   └── appointment.py        # Appointment models
│   ├── core/
│   │   ├── agent.py              # Pydantic AI agent
│   │   ├── fsm.py                # Finite State Machine
│   │   └── idempotency.py        # Request deduplication
│   ├── services/
│   │   ├── evolution.py          # Evolution API client
│   │   ├── supabase.py           # Database client
│   │   └── observability.py      # OpenTelemetry setup
│   ├── handlers/
│   │   └── webhook.py            # Webhook handler
│   └── utils/
│       ├── logger.py             # Structured logging
│       └── dlq.py                # Dead Letter Queue
├── tests/
│   ├── unit/                     # Unit tests (pytest)
│   ├── integration/              # Integration tests
│   └── contract/                 # Contract tests (Pydantic)
├── supabase/
│   └── migrations/               # SQL migrations
├── docker-compose.yml            # Local dev environment
├── pyproject.toml                # Python dependencies (Poetry/uv)
├── .env.example                  # Environment variables template
└── README.md                     # Human-facing docs
```

**Key Files to Check First:**
- `contracts/*.py` - Schemas definem toda a estrutura
- `SPEC.md` - Especificação técnica completa
- `tests/` - Veja padrões de teste esperados

---

## 🛠️ COMANDOS COMUNS

### Setup Inicial
```bash
# Instalar dependências (use uv se disponível, senão Poetry)
uv pip install -r requirements.txt
# OU
poetry install

# Configurar ambiente
cp .env.example .env
# EDITE .env com suas credenciais

# Subir serviços locais (Supabase, Jaeger, Redis)
docker-compose up -d
```

### Desenvolvimento
```bash
# Rodar aplicação localmente
uvicorn src.main:app --reload --port 8000

# Verificar tipos (SEMPRE antes de commitar)
mypy src/ --strict

# Formatar código (auto-fix)
ruff format src/ tests/
ruff check --fix src/ tests/

# Linting (sem auto-fix)
ruff check src/ tests/
```

### Testes
```bash
# Rodar todos os testes
pytest

# Rodar testes específicos
pytest tests/unit/test_agent.py -v
pytest tests/contract/ -v

# Rodar teste específico por nome
pytest -k "test_agent_extracts_date"

# Testes com coverage
pytest --cov=src --cov-report=html

# Watch mode (re-run on changes)
pytest-watch
```

### Database
```bash
# Aplicar migrations
supabase db push

# Reset database (cuidado!)
supabase db reset

# Gerar migration a partir de mudanças
supabase db diff -f <migration_name>
```

### Docker
```bash
# Build imagem
docker build -t whatsapp-agent .

# Rodar container
docker run -p 8000:8000 --env-file .env whatsapp-agent

# Ver logs
docker logs -f <container_id>
```

---

## 📋 CONVENÇÕES DE CÓDIGO

### Python Style
- **Type Hints:** SEMPRE use type hints (`def func(x: int) -> str:`)
- **Docstrings:** Google style para funções públicas
- **Naming:** `snake_case` para funções/variáveis, `PascalCase` para classes
- **Line Length:** Max 88 caracteres (Black/Ruff default)
- **Imports:** Ordenar com `ruff check --select I --fix`

### Pydantic Models
```python
# ✅ BOM: Validação explícita, field_validator para lógica complexa
class WhatsAppMessage(BaseModel):
    message_id: str = Field(..., min_length=16)
    body: str = Field(..., min_length=1, max_length=4096)
    
    @field_validator('body')
    def sanitize_body(cls, v):
        return v.strip()
    
    class Config:
        json_schema_extra = {"example": {...}}

# ❌ RUIM: Sem validação, sem examples
class Message(BaseModel):
    id: str
    text: str
```

### Error Handling
```python
# ✅ BOM: Estruturado, observável, recuperável
try:
    result = await process_message(msg)
except ValidationError as e:
    logger.error("validation_failed", error=str(e), trace_id=trace_id)
    await send_to_dlq(msg, e)
    raise HTTPException(status_code=400, detail=e.errors())

# ❌ RUIM: Silent fail, não observável
try:
    result = await process_message(msg)
except:
    pass
```

### Async/Await
- Use `async def` para I/O-bound operations (DB, HTTP)
- Use funções síncronas para CPU-bound operations
- SEMPRE use `await` em chamadas async

### Logging
```python
# ✅ BOM: Structured logging com contexto
logger.info(
    "message_processed",
    message_id=msg.message_id,
    intent=response.intent,
    trace_id=trace_id,
    latency_ms=elapsed
)

# ❌ RUIM: String logging sem contexto
logger.info(f"Processed message {msg.message_id}")
```

---

## 🔄 WORKFLOWS

### Workflow 1: Criar Novo Endpoint
1. **Definir Contrato:** Crie Pydantic model em `contracts/`
2. **Escrever Testes:** Contract tests primeiro, depois unit tests
3. **Implementar Handler:** Em `handlers/` ou `services/`
4. **Adicionar Rota:** No `main.py` ou router dedicado
5. **Validar:** Rode `mypy`, `ruff`, `pytest`
6. **Documentar:** FastAPI auto-gera, adicione examples no schema

### Workflow 2: Adicionar Ferramenta ao Agente
1. **Definir Tool Function:** Em `core/agent.py`
2. **Registrar com Pydantic AI:** `@agent.tool` decorator
3. **Testar Isoladamente:** Unit test para a função
4. **Testar no Agente:** Integration test end-to-end
5. **Adicionar a agent_config.py:** Lista de tools disponíveis

### Workflow 3: Debugging Produção
1. **Buscar Trace ID:** Do log ou resposta de erro
2. **Consultar Jaeger:** `http://localhost:16686` (local)
3. **Verificar DLQ:** Query `dead_letter_queue` table
4. **Reproduzir Local:** Use payload da DLQ em teste
5. **Fix + Test:** Adicione regression test

### Workflow 4: Adicionar Nova Funcionalidade
**IMPORTANTE: Siga TDD (Test-Driven Development)**
1. **Escrever Teste que Falha:** Defina comportamento esperado
2. **Implementar Código Mínimo:** Para passar o teste
3. **Refatorar:** Melhorar código mantendo testes verdes
4. **Adicionar Casos de Borda:** Testes para edge cases
5. **Documentar no SPEC.md:** Se for mudança arquitetural

---

## 🔒 SEGURANÇA E PERMISSÕES

### Permitido SEM Perguntar:
- ✅ Ler arquivos do projeto
- ✅ Criar/modificar código em `src/` e `tests/`
- ✅ Rodar formatters: `ruff format`, `mypy`
- ✅ Rodar testes: `pytest`
- ✅ Instalar dependências via `pyproject.toml`

### Perguntar ANTES:
- ⚠️ Modificar schemas de database (migrations)
- ⚠️ Adicionar novas dependências externas (PyPI packages)
- ⚠️ Mudar configurações de Docker/docker-compose
- ⚠️ Fazer commits ou pushes para Git
- ⚠️ Deletar arquivos
- ⚠️ Rodar comandos que afetam produção

### NUNCA Fazer:
- 🚫 Commitar secrets ou API keys
- 🚫 Modificar `.env` files (use `.env.example`)
- 🚫 Fazer push direto para `main` branch
- 🚫 Rodar comandos destrutivos sem confirmação
- 🚫 Adicionar código não testado

---

## 🧪 ESTRATÉGIA DE TESTES

### Contract Tests (Alta Prioridade)
```python
# tests/contract/test_contracts.py
def test_whatsapp_message_schema():
    """Valida que input segue contrato"""
    valid_msg = {
        "message_id": "ABC123",
        "from_number": "+5511987654321",
        "body": "Olá",
        "timestamp": "2026-01-28T10:00:00Z"
    }
    msg = WhatsAppMessage(**valid_msg)
    assert msg.message_id == "ABC123"
    
def test_whatsapp_message_invalid():
    """Testa que validação funciona"""
    with pytest.raises(ValidationError):
        WhatsAppMessage(
            message_id="",  # Inválido: empty
            from_number="invalid",
            body="X",
            timestamp="invalid"
        )
```

### Unit Tests (Comportamento)
```python
# tests/unit/test_agent.py
@pytest.mark.asyncio
async def test_agent_extracts_date():
    """Testa extração determinística de data"""
    agent = create_test_agent()
    input_text = "Quero agendar para 15 de fevereiro"
    
    response = await agent.process(input_text)
    
    assert response.intent == "schedule"
    assert response.extracted_data["date"] == "2026-02-15"
```

### Integration Tests (End-to-End)
```python
# tests/integration/test_webhook.py
@pytest.mark.asyncio
async def test_full_booking_flow():
    """Testa fluxo completo de agendamento"""
    # 1. Simular webhook
    response = await client.post("/webhook/whatsapp", json={...})
    assert response.status_code == 200
    
    # 2. Verificar DB
    appt = await supabase.table("appointments").select("*").eq("id", appt_id).single()
    assert appt["status"] == "scheduled"
    
    # 3. Verificar que resposta foi enviada
    assert mock_evolution_api.send_message.called
```

### Mocking
```python
# Use pytest-mock ou unittest.mock
@pytest.fixture
def mock_llm(mocker):
    """Mock LLM para testes determinísticos"""
    mock = mocker.patch("pydantic_ai.models.openai.OpenAIModel")
    mock.return_value.complete.return_value = {
        "intent": "schedule",
        "confidence": 0.95
    }
    return mock
```

---

## 🏗️ ARQUITETURA

### Princípios
1. **Schema First:** Contratos Pydantic definem toda a interface
2. **Separation of Concerns:** Handler → Service → Repository
3. **Dependency Injection:** FastAPI `Depends()` para injeção
4. **Observability:** OpenTelemetry spans em toda transação

### Fluxo de Dados
```
┌─ Webhook (Evolution API) ────────────────────┐
│ POST /webhook/whatsapp                        │
│ Body: WhatsAppMessage (Pydantic)             │
└────────────────┬──────────────────────────────┘
                 │
                 ▼
┌─ Handler (handlers/webhook.py) ──────────────┐
│ 1. Validar schema (automático via Pydantic)  │
│ 2. Verificar idempotência (Redis)            │
│ 3. Criar span de tracing (OpenTelemetry)     │
└────────────────┬──────────────────────────────┘
                 │
                 ▼
┌─ Core Agent (core/agent.py) ─────────────────┐
│ 1. Extract intent via Pydantic AI            │
│ 2. Execute FSM transition (core/fsm.py)      │
│ 3. Call tools (check_availability, etc)      │
└────────────────┬──────────────────────────────┘
                 │
                 ▼
┌─ Services (services/) ───────────────────────┐
│ - supabase.py: Database operations           │
│ - evolution.py: Send WhatsApp reply          │
│ - observability.py: Log structured events    │
└────────────────┬──────────────────────────────┘
                 │
                 ▼
┌─ Response ───────────────────────────────────┐
│ AgentResponse (Pydantic)                      │
│ - trace_id, intent, reply_text, etc          │
└───────────────────────────────────────────────┘
```

### Dependency Injection Pattern
```python
# main.py
from fastapi import Depends
from services.supabase import get_supabase_client

@app.post("/webhook/whatsapp")
async def webhook(
    message: WhatsAppMessage,
    db = Depends(get_supabase_client)
):
    # db é injetado automaticamente
    result = await process_with_db(message, db)
    return result
```

---

## 🔍 OBSERVABILITY

### Structured Logging
```python
# Usar structlog configurado em utils/logger.py
import structlog

logger = structlog.get_logger()

# Em toda operação importante:
logger.info(
    "operation_name",
    trace_id=trace_id,
    user_id=user_id,
    duration_ms=elapsed,
    status="success"
)
```

### OpenTelemetry Tracing
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

# Em handlers e services:
with tracer.start_as_current_span("operation_name") as span:
    span.set_attribute("message_id", msg.message_id)
    # ... código ...
    span.set_attribute("intent", response.intent)
```

### Métricas para Monitorar
- Latência (P50, P95, P99)
- Taxa de erro (por intent type)
- DLQ size (dead letter queue)
- Intent accuracy (via eval suite)

---

## 🧠 PYDANTIC AI GUIDELINES

### Agent Configuration
```python
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

# SEMPRE use temperature=0.0 para determinismo
agent = Agent(
    model=OpenAIModel('gpt-4o-mini', temperature=0.0, seed=42),
    system_prompt=SYSTEM_PROMPT,
    retries=0  # Controle externo de retry
)
```

### Tools Definition
```python
@agent.tool
async def check_availability(date: str, time: str) -> dict:
    """
    Verifica disponibilidade de horário.
    
    Args:
        date: Data no formato YYYY-MM-DD
        time: Hora no formato HH:MM
        
    Returns:
        {"available": bool, "alternatives": list[str]}
    """
    # Implementação...
    return {"available": True, "alternatives": []}
```

### Prompt Engineering
- Use few-shot examples no system prompt
- Seja explícito sobre formato de output esperado
- Peça confirmação antes de ações críticas

---

## 🚨 COMMON PITFALLS (Evite!)

### ❌ Não Fazer
```python
# RUIM: Sem type hints
def process(msg):
    return do_something(msg)

# RUIM: Try-except genérico
try:
    result = dangerous_operation()
except:
    pass

# RUIM: Hardcoded values
api_key = "sk-123456"

# RUIM: Sem validação
def create_appointment(data):
    db.insert(data)  # E se data for None ou mal-formado?
```

### ✅ Fazer
```python
# BOM: Type hints + docstring
def process(msg: WhatsAppMessage) -> AgentResponse:
    """Process incoming message and return response."""
    return do_something(msg)

# BOM: Error handling específico
try:
    result = dangerous_operation()
except ValueError as e:
    logger.error("invalid_value", error=str(e))
    raise
except DatabaseError as e:
    logger.error("db_error", error=str(e))
    await send_to_dlq(payload, e)
    raise

# BOM: Environment variables
from config.settings import settings
api_key = settings.OPENAI_API_KEY

# BOM: Schema validation
def create_appointment(data: dict) -> Appointment:
    # Pydantic valida automaticamente
    appt = Appointment(**data)
    db.insert(appt.model_dump())
    return appt
```

---

## 📚 RECURSOS E REFERÊNCIAS

### Documentação Oficial
- Pydantic AI: https://ai.pydantic.dev/
- FastAPI: https://fastapi.tiangolo.com/
- Pydantic: https://docs.pydantic.dev/
- pytest: https://docs.pytest.org/
- OpenTelemetry: https://opentelemetry.io/docs/languages/python/

### Comandos de Ajuda
```bash
# Ver ajuda de qualquer comando
python -m pytest --help
mypy --help
ruff --help

# Ver versões instaladas
pip list
uv pip list

# Ver configuração do projeto
cat pyproject.toml
```

### Code Quality Tools
- **mypy:** Type checking estrito
- **ruff:** Linting + formatting (substitui Black, isort, flake8)
- **pytest:** Test runner
- **coverage.py:** Code coverage

---

## 🎓 LEARNING RESOURCES

### Se Estiver Aprendendo Sobre:

**Pydantic AI:**
- Leia: `src/core/agent.py` (exemplo completo)
- Docs: https://ai.pydantic.dev/examples/

**FastAPI:**
- Leia: `src/main.py` e `src/handlers/`
- Docs: https://fastapi.tiangolo.com/tutorial/

**Testing:**
- Leia: `tests/` directory
- Docs: https://docs.pytest.org/en/stable/getting-started.html

**OpenTelemetry:**
- Leia: `src/services/observability.py`
- Docs: https://opentelemetry.io/docs/languages/python/getting-started/

---

## 🔄 GIT WORKFLOW

### Branch Strategy
```bash
# Criar feature branch
git checkout -b feature/add-cancellation-flow

# Commit messages (Conventional Commits)
git commit -m "feat: add cancellation intent to agent"
git commit -m "fix: handle duplicate message_id correctly"
git commit -m "test: add contract tests for cancellation"
```

### Commit Message Format
```
<type>: <description>

<optional body>

<optional footer>
```

**Types:**
- `feat`: Nova funcionalidade
- `fix`: Bug fix
- `test`: Adicionar/modificar testes
- `refactor`: Refatoração sem mudar comportamento
- `docs`: Documentação
- `chore`: Tarefas de manutenção

### Pre-commit Checklist
- [ ] `mypy src/` passa sem erros
- [ ] `ruff check src/ tests/` passa sem erros
- [ ] `pytest` passa 100%
- [ ] Coverage mantido ou aumentado
- [ ] Commit message segue convenção

---

## 🎯 TASK TEMPLATES

### Template 1: Nova Feature
```
✅ Checklist:
1. Ler SPEC.md para entender contexto
2. Criar branch: feature/<nome>
3. Escrever testes que falham (TDD)
4. Implementar código mínimo
5. Rodar mypy + ruff + pytest
6. Atualizar SPEC.md se necessário
7. Commit com mensagem descritiva
```

### Template 2: Bug Fix
```
✅ Checklist:
1. Reproduzir bug com teste
2. Buscar Trace ID nos logs
3. Criar branch: fix/<nome>
4. Adicionar regression test
5. Implementar fix
6. Verificar que teste passa
7. Rodar suite completa
8. Commit com "fix:" prefix
```

### Template 3: Refactoring
```
✅ Checklist:
1. Garantir coverage alto (>80%)
2. Criar branch: refactor/<nome>
3. Fazer mudanças incrementais
4. Rodar testes após cada mudança
5. Verificar que comportamento não mudou
6. Atualizar docs se necessário
7. Commit com "refactor:" prefix
```

---

## 📝 QUANDO ATUALIZAR ESTE ARQUIVO

**Adicione Regras Quando:**
- Você cometer o mesmo erro 2+ vezes
- Descobrir padrão útil que deve ser padrão
- Integrar nova ferramenta ou workflow
- Resolver bug difícil que merece documentação

**Como Atualizar:**
```bash
# 1. Edite AGENTS.md
# 2. Peça para agente validar mudanças
# 3. Commit com tipo "docs:"
git commit -m "docs: add pattern for handling timeouts"
```

---

## 🚀 QUICK START (Para Novos Agentes)

Se você acabou de ser inicializado, siga esta ordem:

1. **Leia:** SPEC.md (contexto técnico completo)
2. **Explore:** `src/contracts/` (schemas definem tudo)
3. **Entenda:** `src/core/agent.py` (lógica central)
4. **Valide:** Rode `pytest` para ver se ambiente está OK
5. **Pergunte:** Se algo não está claro, pergunte antes de codar

**Comandos de Smoke Test:**
```bash
# Verificar que tudo funciona
python -c "from src.core.agent import agent; print('OK')"
pytest tests/contract/ -v
mypy src/core/agent.py
```

---

**Última Atualização:** 2026-01-28  
**Mantenha Este Arquivo Atualizado:** Adicione novas regras conforme o projeto evolui  
**Dúvidas:** Consulte SPEC.md para detalhes técnicos completos
