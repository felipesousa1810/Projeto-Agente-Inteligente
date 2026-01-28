# 🤖 WhatsApp Agent - Agente de Atendimento

Agente de atendimento via WhatsApp com Pydantic AI para agendamentos.

## 🚀 Quick Start

### Pré-requisitos

- Python 3.11+
- Docker e Docker Compose
- Conta OpenAI com API Key

### Setup

1. **Clone e configure ambiente:**

```bash
# Copiar variáveis de ambiente
cp .env.example .env

# Editar .env com suas credenciais
# OPENAI_API_KEY=sua-chave
```

2. **Instalar dependências:**

```bash
# Usando uv (recomendado)
uv pip install -e ".[dev]"

# OU usando pip
pip install -e ".[dev]"
```

3. **Subir serviços locais:**

```bash
docker-compose up -d
```

4. **Rodar aplicação:**

```bash
uvicorn src.main:app --reload --port 8000
```

5. **Acessar:**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Jaeger UI: http://localhost:16686

## 🧪 Testes

```bash
# Rodar todos os testes
pytest

# Com coverage
pytest --cov=src --cov-report=html

# Testes específicos
pytest tests/contract/ -v
pytest tests/unit/ -v
```

## 📁 Estrutura

```
src/
├── main.py              # FastAPI app
├── config/              # Configurações
├── contracts/           # Schemas Pydantic
├── core/               # Lógica de negócio
├── services/           # Integrações externas
├── handlers/           # Endpoints
└── utils/              # Utilitários
```

## 📋 Documentação

- [SPEC.md](./SPEC.md) - Especificação técnica completa
- [AGENTS.md](./AGENTS.md) - Guia para agentes de código

## 📄 Licença

MIT
