# Handoff Note - Session 2 (2026-01-29)

**Data:** 29/01/2026, ~01:30 - 04:30 (3 horas)
**Engenheiro:** Antigravity AI

---

## 1. TRABALHO CONCLUÍDO

### Correções de Bugs

| Bug | Causa | Solução |
|-----|-------|---------|
| Hora congelada no agente | Singleton criava prompt uma vez | Injeção dinâmica de data/hora por request |
| Contexto não limpava | Formato de telefone diferente | Normalização E.164 nos endpoints debug |
| Loop infinito de tool calls | LLM chamava tools em loop | `UsageLimits(request_limit=10)` |

### Arquivos Modificados

```
src/config/agent_config.py     # Prompt com placeholders dinâmicos
src/core/agent.py              # Injeção de data/hora + UsageLimits
src/handlers/webhook.py        # Endpoints debug + normalização telefone
src/services/logfire_config.py # Logs melhorados para diagnóstico
src/static/admin.html          # Interface admin para gerenciar contexto
src/main.py                    # Rota /admin
```

### Features Novas

1. **Página Admin** (`/admin`) - Interface para:
   - Ver contexto de conversa por telefone
   - Limpar contexto
   - Lista de contextos ativos (clicável)

2. **Endpoint list-contexts** - Lista todos os números com conversas ativas no Redis

3. **UsageLimits** - Guardrail via código (não prompt) para evitar loops

---

## 2. ESTADO ATUAL

### ✅ Funcionando

- Agendamento básico via WhatsApp
- FSM persistida no Redis
- Injeção dinâmica de data/hora
- Página admin para debug
- CI/CD com GitHub Actions

### ⚠️ Parcialmente Implementado

- **Logfire**: Configurado mas não confirmado se está enviando ao cloud
- **Reagendamento**: Funcionou em teste, mas deu erro de loop em um caso

### ❌ Bugs/Problemas Conhecidos

1. **Agente NÃO é determinístico** - LLM decide tudo (fluxo, tools, resposta)
2. **Logfire cloud** - Token configurado, mas logs não aparecem no dashboard
3. **Loop de tools** - Mitigado com UsageLimits, mas causa raiz não resolvida

---

## 3. PRÓXIMOS PASSOS

### Tarefa Imediata: Refatoração para Arquitetura Determinística

O plano está em: `implementation_plan.md` (artefato)

**Criar:**
```
src/core/nlu.py             # NLU - só extrai intent/entidades
src/core/decision_engine.py # Decisões 100% em código
src/core/templates.py       # Templates de resposta
src/core/nlg.py             # Humaniza templates via LLM
```

**Fluxo alvo:**
```
Mensagem → [NLU/LLM] → Intent + Entidades
                ↓
          [Código/FSM] → Decisão + Template
                ↓
          [NLG/LLM] → Humaniza resposta
```

### Bloqueadores

- Nenhum técnico, apenas decisão de arquitetura aprovada

### Tempo Estimado

- Fase 1 (NLU isolado): ~2 horas
- Fase 2 (Decision Engine): ~2 horas
- Fase 3 (Templates + NLG): ~2 horas
- Fase 4 (Integração): ~2 horas
- Fase 5 (Testes): ~1 hora

**Total: ~9 horas de desenvolvimento**

---

## 4. CONTEXTO IMPORTANTE

### Decisões Tomadas

| Decisão | Motivo |
|---------|--------|
| **Guardrails via código, não prompt** | Usuário citou Eugene Yan - prompts são probabilísticos |
| **UsageLimits do Pydantic AI** | Forma correta de limitar tool calls |
| **Arquitetura NLU → Código → NLG** | LLM só extrai e humaniza, nunca decide |
| **Templates + NLG** | Respostas previsíveis mas naturais |

### Padrões Estabelecidos

- **Logs estruturados**: `logger.info("event_name", key=value)`
- **Validação Pydantic**: Todos os outputs estruturados
- **FSM para estado**: `ConversationFSM` no Redis
- **Phone E.164**: Sempre normalizar com `+` antes de usar

### Pegadinhas Descobertas

1. **Número de telefone**: Evolution API envia sem `+`, Redis armazena com `+`
2. **Data/hora singleton**: Não usar singleton para dados dinâmicos
3. **Tool call loops**: LLM pode entrar em loop se não limitado via código

### Referências

- **Eugene Yan**: [Patterns for Building LLM-based Systems](https://eugeneyan.com)
- **Pydantic AI**: [UsageLimits](https://docs.pydantic.dev/ai/latest/)

---

## 5. TRECHOS DE CÓDIGO CRÍTICOS

### Normalização de Telefone (webhook.py)

```python
def _normalize_phone(phone: str) -> str:
    """Normalize phone to E.164 format."""
    cleaned = "".join(c for c in phone if c.isdigit() or c == "+")
    if not cleaned.startswith("+"):
        cleaned = f"+{cleaned}"
    return cleaned
```

### UsageLimits - Guardrail via Código (agent.py)

```python
from pydantic_ai import UsageLimits

result = await agent.run(
    prompt_with_context,
    deps=deps,
    usage_limits=UsageLimits(
        request_limit=10,  # Max 10 requests por mensagem
        token_limit=4096,
    ),
)
```

### Injeção Dinâmica de Data/Hora (agent_config.py)

```python
def get_dynamic_system_prompt() -> str:
    """Returns system prompt with current date/time."""
    now = datetime.now()
    weekday = WEEKDAYS_PT[now.weekday()]

    return SYSTEM_PROMPT.replace(
        "{{CURRENT_DATE}}", now.strftime("%Y-%m-%d")
    ).replace(
        "{{CURRENT_TIME}}", now.strftime("%H:%M")
    ).replace(
        "{{CURRENT_WEEKDAY}}", weekday
    )
```

### Arquitetura Alvo (próxima sessão)

```python
async def process_message(message: WhatsAppMessage) -> AgentResponse:
    # 1. NLU - extrair intent/entidades (LLM)
    nlu_output = await nlu.extract(message.body)

    # 2. Atualizar FSM (CÓDIGO)
    fsm.update_from_nlu(nlu_output)

    # 3. Decisão DETERMINÍSTICA (CÓDIGO)
    action = decision_engine.decide(fsm, nlu_output)

    # 4. Executar ação (CÓDIGO)
    result = await action.execute()

    # 5. Template base (CÓDIGO)
    template = templates.get(action.template_key)

    # 6. NLG - humanizar (LLM - não decide nada)
    response = await nlg.humanize(template, result.context)

    return AgentResponse(reply_text=response, intent=nlu_output.intent)
```

---

## Commits desta Sessão

```
183d9f2 fix(admin): normalize phone number in debug endpoints
157b41d feat(admin): add list-contexts endpoint and active contexts section
1c37db5 fix(agent): prevent tool call loops with guardrails and model settings
2713cd4 refactor(agent): replace prompt guardrails with code-based UsageLimits
```

---

**Boa sorte, próximo engenheiro! 🚀**
