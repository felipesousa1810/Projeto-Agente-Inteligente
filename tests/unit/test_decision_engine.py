"""Unit Tests - Decision Engine (100% Deterministic Decisions)."""

from src.core.decision_engine import (
    ActionType,
    DecisionEngine,
    get_decision_engine,
)
from src.core.fsm import AppointmentState, StateMachine
from src.core.nlu import NLUOutput


class TestDecisionEngine:
    """Tests for the deterministic decision engine."""

    def setup_method(self) -> None:
        """Setup test fixtures."""
        self.engine = DecisionEngine()
        self.fsm = StateMachine(customer_id="test-customer")

    def test_greeting_intent_returns_greet_action(self) -> None:
        """Test that greeting intent always returns greet action."""
        nlu_output = NLUOutput(intent="greeting", confidence=1.0)

        action = self.engine.decide(self.fsm, nlu_output)

        assert action.action_type == ActionType.GREET
        assert action.template_key == "greeting"
        assert action.requires_tool is False

    def test_schedule_without_procedure_asks_procedure(self) -> None:
        """Test that schedule without procedure asks for procedure."""
        nlu_output = NLUOutput(intent="schedule", confidence=1.0)

        action = self.engine.decide(self.fsm, nlu_output)

        assert action.action_type == ActionType.ASK_PROCEDURE
        assert action.template_key == "ask_procedure"

    def test_schedule_with_procedure_asks_date(self) -> None:
        """Test that schedule with procedure but no date asks for date."""
        nlu_output = NLUOutput(
            intent="schedule",
            extracted_procedure="Limpeza",
            confidence=1.0,
        )

        action = self.engine.decide(self.fsm, nlu_output)

        assert action.action_type == ActionType.ASK_DATE
        assert action.template_key == "ask_date"
        assert "procedure" in action.context

    def test_schedule_with_procedure_and_date_asks_time(self) -> None:
        """Test that schedule with procedure and date asks for time."""
        # Pre-populate procedure in FSM
        self.fsm.set_data("procedure", "Limpeza")

        nlu_output = NLUOutput(
            intent="schedule",
            extracted_date="2026-02-15",
            confidence=1.0,
        )

        action = self.engine.decide(self.fsm, nlu_output)

        assert action.action_type == ActionType.ASK_TIME
        assert action.template_key == "ask_time"
        assert action.requires_tool is True
        assert action.tool_name == "check_availability"

    def test_schedule_complete_confirms_appointment(self) -> None:
        """Test that complete data triggers confirmation."""
        # Pre-populate all required data
        self.fsm.set_data("procedure", "Limpeza")
        self.fsm.set_data("date", "2026-02-15")

        nlu_output = NLUOutput(
            intent="schedule",
            extracted_time="14:00",
            confidence=1.0,
        )

        action = self.engine.decide(self.fsm, nlu_output)

        assert action.action_type == ActionType.CONFIRM_APPOINTMENT
        assert action.template_key == "confirm_appointment"
        assert "procedure" in action.context
        assert "date" in action.context
        assert "time" in action.context

    def test_confirm_in_time_collected_creates_appointment(self) -> None:
        """Test that confirm in TIME_COLLECTED state creates appointment."""
        # Setup FSM state
        self.fsm.set_data("procedure", "Limpeza")
        self.fsm.set_data("date", "2026-02-15")
        self.fsm.set_data("time", "14:00")
        self.fsm.transition(AppointmentState.DATE_COLLECTED)
        self.fsm.transition(AppointmentState.TIME_COLLECTED)

        nlu_output = NLUOutput(intent="confirm", confidence=1.0)

        action = self.engine.decide(self.fsm, nlu_output)

        assert action.action_type == ActionType.CREATE_APPOINTMENT
        assert action.requires_tool is True
        assert action.tool_name == "create_appointment"
        assert action.next_state == AppointmentState.SCHEDULED

    def test_unknown_intent_asks_clarification(self) -> None:
        """Test that unknown intent asks for clarification."""
        nlu_output = NLUOutput(intent="unknown", confidence=0.3)

        action = self.engine.decide(self.fsm, nlu_output)

        assert action.action_type == ActionType.CLARIFY
        assert action.template_key == "clarify"

    def test_deny_resets_fsm(self) -> None:
        """Test that deny intent resets the FSM."""
        # Pre-populate data
        self.fsm.set_data("procedure", "Limpeza")
        self.fsm.transition(AppointmentState.DATE_COLLECTED)

        nlu_output = NLUOutput(intent="deny", confidence=1.0)

        action = self.engine.decide(self.fsm, nlu_output)

        assert action.action_type == ActionType.GREET
        assert action.template_key == "denied_restart"
        assert self.fsm.current_state == AppointmentState.INITIATED

    def test_decision_is_deterministic(self) -> None:
        """Test that same input ALWAYS produces same output."""
        nlu_output = NLUOutput(
            intent="schedule",
            extracted_procedure="Limpeza",
            confidence=1.0,
        )

        # Run 10 times and verify same result
        results = []
        for _ in range(10):
            fsm = StateMachine(customer_id="test")
            action = self.engine.decide(fsm, nlu_output)
            results.append((action.action_type, action.template_key))

        # All results should be identical
        assert len(set(results)) == 1

    def test_faq_intent_returns_faq_action(self) -> None:
        """Test that FAQ intent returns FAQ action."""
        nlu_output = NLUOutput(
            intent="faq",
            extracted_procedure="clareamento",
            confidence=1.0,
        )

        action = self.engine.decide(self.fsm, nlu_output)

        assert action.action_type == ActionType.ANSWER_FAQ
        assert action.template_key == "faq_response"


class TestGetDecisionEngine:
    """Tests for the decision engine singleton."""

    def test_get_decision_engine_returns_same_instance(self) -> None:
        """Test that get_decision_engine returns singleton."""
        engine1 = get_decision_engine()
        engine2 = get_decision_engine()

        assert engine1 is engine2
