# 🤖 WhatsApp Agent

![CI Status](https://github.com/felipesousa1810/Projeto-Agente-Inteligente/actions/workflows/ci.yml/badge.svg)
![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Code Style](https://img.shields.io/badge/code%20style-ruff-000000.svg)

Agente de atendimento inteligente via WhatsApp, construído com **Pydantic AI**, **Supabase** e **Google Calendar**.

## ✨ Features

- **Decisões Determinísticas**: Máquina de Estados (FSM) garante fluxo lógico 100% previsível.
- **NLU & NLG**: Separação clara entre entendimento (Natural Language Understanding) e geração de resposta (Natural Language Generation).
- **Integração Real**:
  - **Supabase**: Banco de dados PostgreSQL com RLS para segurança.
  - **Google Calendar**: Agendamento real com verificação de conflitos.
- **Observabilidade**: Logs estruturados e rastreamento de execução.
- **Segurança**: Políticas RLS, timeouts em requisições e validação rigorosa de dados.

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
```

## 🤝 Contributing

Veja nosso guia de contribuição em [CONTRIBUTING.md](./CONTRIBUTING.md).

## 📄 License

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](./LICENSE) para detalhes.

## 📝 Changelog

Acompanhe as atualizações no [CHANGELOG.md](./CHANGELOG.md).
