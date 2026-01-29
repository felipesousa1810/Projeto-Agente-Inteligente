"""Decision Engine - 100% deterministic action selection.

This module contains ALL decision logic for the agent.
The LLM NEVER decides what to do - this code does.

Architecture principle: LLM extracts, Code decides.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.core.fsm import AppointmentState, StateMachine
from src.core.nlu import NLUOutput
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ActionType(str, Enum):
    """Types of actions the agent can take."""

    # Conversation actions (no tool needed)
    GREET = "greet"
    ASK_PROCEDURE = "ask_procedure"
    ASK_DATE = "ask_date"
    ASK_TIME = "ask_time"
    CONFIRM_APPOINTMENT = "confirm_appointment"
    APPOINTMENT_CONFIRMED = "appointment_confirmed"
    ASK_CONFIRMATION_CODE = "ask_confirmation_code"
    APPOINTMENT_CANCELED = "appointment_canceled"
    ANSWER_FAQ = "answer_faq"
    CLARIFY = "clarify"
    ERROR = "error"

    # Tool actions
    CHECK_AVAILABILITY = "check_availability"
    CREATE_APPOINTMENT = "create_appointment"
    CANCEL_APPOINTMENT = "cancel_appointment"


class Action(BaseModel):
    """Base class for all actions.

    An action represents what the agent should do next.
    It includes the template to use and any context needed.
    """

    action_type: ActionType = Field(
        ...,
        description="Type of action to take",
    )
    template_key: str = Field(
        ...,
        description="Key for the response template",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Context data for template formatting",
    )
    requires_tool: bool = Field(
        default=False,
        description="Whether this action requires a tool call",
    )
    tool_name: str | None = Field(
        default=None,
        description="Name of the tool to call, if requires_tool is True",
    )
    next_state: AppointmentState | None = Field(
        default=None,
        description="State to transition to after this action",
    )


class DecisionEngine:
    """Deterministic engine that decides next action based on FSM state and NLU output.

    This is the ONLY place where decisions are made.
    All logic is explicit and deterministic - same input always produces same output.
    """

    def decide(self, fsm: StateMachine, nlu_output: NLUOutput) -> Action:
        """Decide the next action based on current state and extracted intent.

        Args:
            fsm: Current conversation state machine.
            nlu_output: Extracted intent and entities from NLU.

        Returns:
            Action to take, including template and context.
        """
        logger.info(
            "decision_engine_decide",
            current_state=fsm.current_state.value,
            intent=nlu_output.intent,
            has_procedure=nlu_output.extracted_procedure is not None,
            has_date=nlu_output.extracted_date is not None,
            has_time=nlu_output.extracted_time is not None,
        )

        # Update FSM with extracted data
        self._update_fsm_from_nlu(fsm, nlu_output)

        # Route to intent-specific handler
        intent = nlu_output.intent

        if intent == "greeting":
            return self._handle_greeting(fsm)

        if intent == "schedule":
            return self._handle_schedule(fsm, nlu_output)

        if intent == "reschedule":
            return self._handle_reschedule(fsm, nlu_output)

        if intent == "cancel":
            return self._handle_cancel(fsm, nlu_output)

        if intent == "confirm":
            return self._handle_confirm(fsm, nlu_output)

        if intent == "deny":
            return self._handle_deny(fsm)

        if intent == "faq":
            return self._handle_faq(fsm, nlu_output)

        # Unknown intent - ask for clarification
        return Action(
            action_type=ActionType.CLARIFY,
            template_key="clarify",
            context={},
        )

    def _update_fsm_from_nlu(self, fsm: StateMachine, nlu: NLUOutput) -> None:
        """Update FSM with extracted entities from NLU.

        Args:
            fsm: State machine to update.
            nlu: Extracted entities.
        """
        if nlu.extracted_procedure and not fsm.get_data("procedure"):
            fsm.set_data("procedure", nlu.extracted_procedure)
            logger.info(
                "fsm_data_updated", key="procedure", value=nlu.extracted_procedure
            )

        if nlu.extracted_date and not fsm.get_data("date"):
            fsm.set_data("date", nlu.extracted_date)
            logger.info("fsm_data_updated", key="date", value=nlu.extracted_date)

        if nlu.extracted_time and not fsm.get_data("time"):
            fsm.set_data("time", nlu.extracted_time)
            logger.info("fsm_data_updated", key="time", value=nlu.extracted_time)

    def _handle_greeting(self, fsm: StateMachine) -> Action:
        """Handle greeting intent.

        Always respond with greeting + ask what they need.
        """
        return Action(
            action_type=ActionType.GREET,
            template_key="greeting",
            context={},
        )

    def _handle_schedule(self, fsm: StateMachine, nlu: NLUOutput) -> Action:
        """Handle scheduling intent - deterministic flow.

        Flow:
        1. Need procedure? -> Ask procedure
        2. Need date? -> Ask date
        3. Need time? -> Ask time (with availability check)
        4. Have all? -> Confirm
        """
        # Check what we still need to collect
        procedure = fsm.get_data("procedure")
        date = fsm.get_data("date")
        time = fsm.get_data("time")

        # Step 1: Need procedure
        if not procedure:
            return Action(
                action_type=ActionType.ASK_PROCEDURE,
                template_key="ask_procedure",
                context={},
            )

        # Step 2: Need date
        if not date:
            return Action(
                action_type=ActionType.ASK_DATE,
                template_key="ask_date",
                context={"procedure": procedure},
            )

        # Transition FSM if we collected date
        if fsm.current_state == AppointmentState.INITIATED and fsm.can_transition_to(
            AppointmentState.DATE_COLLECTED
        ):
            fsm.transition(AppointmentState.DATE_COLLECTED)

        # Step 3: Need time
        if not time:
            return Action(
                action_type=ActionType.ASK_TIME,
                template_key="ask_time",
                context={
                    "procedure": procedure,
                    "date": date,
                },
                requires_tool=True,
                tool_name="check_availability",
            )

        # Transition FSM if we collected time
        if (
            fsm.current_state == AppointmentState.DATE_COLLECTED
            and fsm.can_transition_to(AppointmentState.TIME_COLLECTED)
        ):
            fsm.transition(AppointmentState.TIME_COLLECTED)

        # Step 4: Confirm appointment
        return Action(
            action_type=ActionType.CONFIRM_APPOINTMENT,
            template_key="confirm_appointment",
            context={
                "procedure": procedure,
                "date": date,
                "time": time,
            },
            next_state=AppointmentState.CONFIRMED,
        )

    def _handle_reschedule(self, fsm: StateMachine, nlu: NLUOutput) -> Action:
        """Handle reschedule intent.

        For now, treat as new schedule (simplified).
        TODO: Implement full reschedule flow with existing appointment lookup.
        """
        # Reset FSM for new scheduling
        fsm.reset()
        return self._handle_schedule(fsm, nlu)

    def _handle_cancel(self, fsm: StateMachine, nlu: NLUOutput) -> Action:
        """Handle cancellation intent.

        Ask for confirmation code if not provided.
        """
        confirmation_code = fsm.get_data("confirmation_code")

        if not confirmation_code:
            return Action(
                action_type=ActionType.ASK_CONFIRMATION_CODE,
                template_key="ask_confirmation_code",
                context={},
            )

        return Action(
            action_type=ActionType.CANCEL_APPOINTMENT,
            template_key="cancel_appointment",
            context={"confirmation_code": confirmation_code},
            requires_tool=True,
            tool_name="cancel_appointment",
            next_state=AppointmentState.CANCELED,
        )

    def _handle_confirm(self, fsm: StateMachine, nlu: NLUOutput) -> Action:
        """Handle confirm intent (user saying yes/ok).

        What we do depends on current state.
        """
        current_state = fsm.current_state

        # If we're in TIME_COLLECTED and waiting for confirmation
        if current_state == AppointmentState.TIME_COLLECTED:
            procedure = fsm.get_data("procedure")
            date = fsm.get_data("date")
            time = fsm.get_data("time")

            return Action(
                action_type=ActionType.CREATE_APPOINTMENT,
                template_key="appointment_confirmed",
                context={
                    "procedure": procedure,
                    "date": date,
                    "time": time,
                },
                requires_tool=True,
                tool_name="create_appointment",
                next_state=AppointmentState.SCHEDULED,
            )

        # If we're in CONFIRMED state, just acknowledge
        if current_state == AppointmentState.CONFIRMED:
            return Action(
                action_type=ActionType.APPOINTMENT_CONFIRMED,
                template_key="appointment_already_confirmed",
                context={},
            )

        # Otherwise, we don't know what they're confirming
        return Action(
            action_type=ActionType.CLARIFY,
            template_key="clarify_confirm",
            context={},
        )

    def _handle_deny(self, fsm: StateMachine) -> Action:
        """Handle deny intent (user saying no).

        Reset the conversation.
        """
        fsm.reset()
        return Action(
            action_type=ActionType.GREET,
            template_key="denied_restart",
            context={},
        )

    def _handle_faq(self, fsm: StateMachine, nlu: NLUOutput) -> Action:
        """Handle FAQ intent.

        This will use NLG to generate a response based on the question.
        """
        return Action(
            action_type=ActionType.ANSWER_FAQ,
            template_key="faq_response",
            context={"procedure": nlu.extracted_procedure},
        )


# Singleton instance
_decision_engine: DecisionEngine | None = None


def get_decision_engine() -> DecisionEngine:
    """Get or create the decision engine singleton."""
    global _decision_engine
    if _decision_engine is None:
        _decision_engine = DecisionEngine()
    return _decision_engine
