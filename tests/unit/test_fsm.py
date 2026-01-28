"""Unit Tests - FSM (Finite State Machine)."""

import pytest

from src.core.fsm import AppointmentState, StateMachine


class TestStateMachine:
    """Tests for the appointment state machine."""

    def test_initial_state(self) -> None:
        """Test that FSM starts in INITIATED state."""
        fsm = StateMachine(customer_id="test-customer")

        assert fsm.current_state == AppointmentState.INITIATED
        assert fsm.collected_data == {}
        assert fsm.history == []

    def test_valid_transition_initiated_to_date_collected(self) -> None:
        """Test valid transition from INITIATED to DATE_COLLECTED."""
        fsm = StateMachine(customer_id="test-customer")

        assert fsm.can_transition_to(AppointmentState.DATE_COLLECTED)

        fsm.transition(AppointmentState.DATE_COLLECTED)

        assert fsm.current_state == AppointmentState.DATE_COLLECTED
        assert AppointmentState.INITIATED in fsm.history

    def test_valid_transition_full_flow(self) -> None:
        """Test complete valid transition flow."""
        fsm = StateMachine(customer_id="test-customer")

        # INITIATED -> DATE_COLLECTED
        fsm.transition(AppointmentState.DATE_COLLECTED)
        fsm.set_data("date", "2026-02-15")

        # DATE_COLLECTED -> TIME_COLLECTED
        fsm.transition(AppointmentState.TIME_COLLECTED)
        fsm.set_data("time", "14:00")

        # TIME_COLLECTED -> CONFIRMED
        fsm.transition(AppointmentState.CONFIRMED)

        # CONFIRMED -> SCHEDULED
        fsm.transition(AppointmentState.SCHEDULED)

        assert fsm.current_state == AppointmentState.SCHEDULED
        assert fsm.is_complete
        assert fsm.get_data("date") == "2026-02-15"
        assert fsm.get_data("time") == "14:00"

    def test_invalid_transition_raises_error(self) -> None:
        """Test that invalid transitions raise ValueError."""
        fsm = StateMachine(customer_id="test-customer")

        # Cannot go directly from INITIATED to SCHEDULED
        assert not fsm.can_transition_to(AppointmentState.SCHEDULED)

        with pytest.raises(ValueError) as exc_info:
            fsm.transition(AppointmentState.SCHEDULED)

        assert "Transição inválida" in str(exc_info.value)

    def test_canceled_is_terminal_state(self) -> None:
        """Test that CANCELED is a terminal state."""
        fsm = StateMachine(customer_id="test-customer")

        # Go to CONFIRMED
        fsm.transition(AppointmentState.DATE_COLLECTED)
        fsm.transition(AppointmentState.TIME_COLLECTED)
        fsm.transition(AppointmentState.CONFIRMED)

        # Cancel
        fsm.transition(AppointmentState.CANCELED)

        assert fsm.current_state == AppointmentState.CANCELED
        assert fsm.is_complete

        # Cannot transition from CANCELED
        assert not fsm.can_transition_to(AppointmentState.SCHEDULED)
        assert not fsm.can_transition_to(AppointmentState.INITIATED)

    def test_set_and_get_data(self) -> None:
        """Test data storage in FSM."""
        fsm = StateMachine(customer_id="test-customer")

        fsm.set_data("date", "2026-02-15")
        fsm.set_data("time", "14:00")
        fsm.set_data("notes", "Primeira consulta")

        assert fsm.get_data("date") == "2026-02-15"
        assert fsm.get_data("time") == "14:00"
        assert fsm.get_data("notes") == "Primeira consulta"
        assert fsm.get_data("nonexistent") is None
        assert fsm.get_data("nonexistent", "default") == "default"

    def test_reset_fsm(self) -> None:
        """Test FSM reset functionality."""
        fsm = StateMachine(customer_id="test-customer")

        fsm.transition(AppointmentState.DATE_COLLECTED)
        fsm.set_data("date", "2026-02-15")

        fsm.reset()

        assert fsm.current_state == AppointmentState.INITIATED
        assert fsm.collected_data == {}
        assert len(fsm.history) > 0  # History is preserved

    def test_needs_date_property(self) -> None:
        """Test needs_date property."""
        fsm = StateMachine(customer_id="test-customer")

        assert fsm.needs_date

        fsm.set_data("date", "2026-02-15")
        assert not fsm.needs_date

    def test_needs_time_property(self) -> None:
        """Test needs_time property."""
        fsm = StateMachine(customer_id="test-customer")

        assert not fsm.needs_time  # Not in DATE_COLLECTED state

        fsm.transition(AppointmentState.DATE_COLLECTED)
        assert fsm.needs_time

        fsm.set_data("time", "14:00")
        assert not fsm.needs_time

    def test_needs_confirmation_property(self) -> None:
        """Test needs_confirmation property."""
        fsm = StateMachine(customer_id="test-customer")

        assert not fsm.needs_confirmation

        fsm.transition(AppointmentState.DATE_COLLECTED)
        fsm.transition(AppointmentState.TIME_COLLECTED)

        assert fsm.needs_confirmation

    def test_history_tracking(self) -> None:
        """Test that state history is properly tracked."""
        fsm = StateMachine(customer_id="test-customer")

        fsm.transition(AppointmentState.DATE_COLLECTED)
        fsm.transition(AppointmentState.TIME_COLLECTED)
        fsm.transition(AppointmentState.CONFIRMED)

        expected_history = [
            AppointmentState.INITIATED,
            AppointmentState.DATE_COLLECTED,
            AppointmentState.TIME_COLLECTED,
        ]

        assert fsm.history == expected_history
