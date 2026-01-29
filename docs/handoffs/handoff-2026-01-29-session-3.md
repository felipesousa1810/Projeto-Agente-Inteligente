# Handoff - 2026-01-29 - Session 3: Arquitetura Determinística

**Objetivo da Sessão:** Eliminar a imprevisibilidade do agente substituindo o controle de fluxo via LLM por uma arquitetura determinística baseada em código e Máquina de Estados.

---

## 1. TRABALHO CONCLUÍDO

### Refatoração Arquitetural (NLU → Código → NLG)
Implementamos uma arquitetura onde o LLM é restrito a tarefas de percepção (NLU) e geração de texto (NLG), enquanto a lógica de decisão é 100% código Python.

### Arquivos Criados/Modificados
*   `src/core/nlu.py` (Novo): Extrai intent e entidades usando PydanticAI com `NLUOutput` estruturado.
*   `src/core/decision_engine.py` (Novo): Motor determinístico que recebe (FSM + NLU) e retorna `Action`. Contém toda a regra de negócio.
*   `src/core/templates.py` (Novo): Dicionário de templates de resposta e base de conhecimento FAQ simples.
*   `src/core/nlg.py` (Novo): Agente que recebe template preenchido e humaniza o texto sem permissão para alterar dados.
*   `src/core/agent.py` (Modificado): `process_message` reescrito para orquestrar os novos módulos.
*   `src/contracts/agent_response.py` (Modificado): Adicionados `IntentType.GREETING` e `IntentType.DENY`.

### Testes
*   **Total Aprovado:** 46 testes (100% passing).
*   **Novos Testes:**
    *   `tests/unit/test_decision_engine.py`: Verifica determinismo (mesmo input = mesmo output).
    *   `tests/unit/test_templates.py`: Valida consistência dos templates e FAQ.
*   **CI Fixes:** Corrigidos tipos mypy (`UsageLimits`) e formatação ruff.

---

## 2. ESTADO ATUAL

### Funcionando ✅
*   **Fluxo de Agendamento:** NLU identifica → Engine pede dados faltantes → Templates geram resposta.
*   **Determinismo:** O agente não alucina transições de estado. Se falta a data, ele SEMPRE pedirá a data.
*   **CI Pipeline:** Github Actions passando (mypy, ruff, pytest).

### Parcialmente Implementado ⚠️
*   **Tools Reais:** `_execute_tool` em `agent.py` atualmente retorna mocks para `check_availability` e `create_appointment`. Precisa ser conectado ao banco/API real.
*   **Persistência Real:** `src/core/agent.py` usa `get_conversation_state_manager` com Redis, o que está correto, mas a integração end-to-end precisa ser validada em um ambiente de deploy.

---

## 3. PRÓXIMOS PASSOS

### Imediato
1.  **Deploy em Staging/Prod:** Fazer deploy da branch `main` e testar com telefone real.
2.  **Conectar Tools:** Implementar lógica real em `_execute_tool` (conectar com Google Calendar ou banco SQL).
3.  **Observabilidade:** Monitorar logs no Logfire para ajustar prompts de NLU/NLG se necessário.

### Bloqueadores
*   Nenhum. Código está estável e testado.

### Pontos de Atenção
*   `src/core/agent.py`: A função `_execute_tool` (linhas 385+) precisa de implementação real.

---

## 4. CONTEXTO IMPORTANTE

### Decisões Arquiteturais
1.  **Inverse Control:** O LLM não chama tools. O código chama tools. Isso elimina ataques de injeção de prompt que tentam manipular chamadas de função.
2.  **Schema First:** Tudo entra e sai como Pydantic Model (`NLUOutput`, `Action`, `AgentResponse`).
3.  **Humanização Controlada:** O NLG recebe o texto *já com os dados preenchidos* (ex: "Dia 15/02"). Sua única função é reescrever com estilo. Isso impede que o LLM invente datas.

### Padrões
*   **Determinismo:** Testes devem provar que $f(state, input) \rightarrow action$ é constante.
*   **Type Safety:** `mypy --strict` é mandatório.

---

## 5. TRECHOS DE CÓDIGO CRÍTICOS

### Orquestrador (`src/core/agent.py`)
```python
# O coração determinístico
nlu_output = await nlu.extract(message.body)
action = decision_engine.decide(fsm, nlu_output)

if action.requires_tool:
    # Código executa a tool, não o LLM
    tool_result = await _execute_tool(action.tool_name, action.context...)

template_text = format_template(action.template_key, **action.context)
response_text = await nlg.humanize(template_text)
```

### Motor de Decisão (`src/core/decision_engine.py`)
```python
def decide(self, fsm, nlu):
    # Regra explícita: Se quer agendar e falta data, peça data.
    if nlu.intent == "schedule" and not fsm.get_data("date"):
        return Action(action_type=ActionType.ASK_DATE...)
```
