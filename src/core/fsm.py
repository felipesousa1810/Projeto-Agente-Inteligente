"""Finite State Machine - State management for appointment flow."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AppointmentState(str, Enum):
    """Estados possíveis de um agendamento.

    Define o ciclo de vida de um agendamento,
    desde a iniciação até cancelamento.
    """

    INITIATED = "initiated"
    DATE_COLLECTED = "date_collected"
    TIME_COLLECTED = "time_collected"
    CONFIRMED = "confirmed"
    SCHEDULED = "scheduled"
    CANCELED = "canceled"


# Valid state transitions
VALID_TRANSITIONS: dict[AppointmentState, list[AppointmentState]] = {
    AppointmentState.INITIATED: [AppointmentState.DATE_COLLECTED],
    AppointmentState.DATE_COLLECTED: [
        AppointmentState.TIME_COLLECTED,
        AppointmentState.INITIATED,  # Allow going back
    ],
    AppointmentState.TIME_COLLECTED: [
        AppointmentState.CONFIRMED,
        AppointmentState.DATE_COLLECTED,  # Allow going back
    ],
    AppointmentState.CONFIRMED: [
        AppointmentState.SCHEDULED,
        AppointmentState.CANCELED,
    ],
    AppointmentState.SCHEDULED: [AppointmentState.CANCELED],
    AppointmentState.CANCELED: [],  # Terminal state
}


class StateMachine(BaseModel):
    """Máquina de estados para fluxo de agendamento.

    Gerencia transições de estado e armazena dados coletados
    durante o processo de agendamento.
    """

    current_state: AppointmentState = Field(
        default=AppointmentState.INITIATED,
        description="Estado atual do fluxo",
    )
    customer_id: str = Field(
        ...,
        description="ID do cliente",
    )
    collected_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Dados coletados durante o fluxo",
    )
    history: list[AppointmentState] = Field(
        default_factory=list,
        description="Histórico de estados",
    )

    def can_transition_to(self, next_state: AppointmentState) -> bool:
        """Valida se transição é permitida.

        Args:
            next_state: Estado de destino desejado.

        Returns:
            True se a transição é válida, False caso contrário.
        """
        allowed = VALID_TRANSITIONS.get(self.current_state, [])
        return next_state in allowed

    def transition(self, next_state: AppointmentState) -> None:
        """Executa transição de estado.

        Args:
            next_state: Estado de destino.

        Raises:
            ValueError: Se a transição não for permitida.
        """
        if not self.can_transition_to(next_state):
            raise ValueError(
                f"Transição inválida: {self.current_state.value} -> {next_state.value}"
            )
        self.history.append(self.current_state)
        self.current_state = next_state

    def set_data(self, key: str, value: Any) -> None:
        """Armazena dado coletado.

        Args:
            key: Chave do dado (ex: 'date', 'time').
            value: Valor a armazenar.
        """
        self.collected_data[key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        """Recupera dado coletado.

        Args:
            key: Chave do dado.
            default: Valor padrão se não existir.

        Returns:
            Valor armazenado ou default.
        """
        return self.collected_data.get(key, default)

    def reset(self) -> None:
        """Reseta a máquina de estados para o estado inicial."""
        self.history.append(self.current_state)
        self.current_state = AppointmentState.INITIATED
        self.collected_data = {}

    @property
    def is_complete(self) -> bool:
        """Verifica se o fluxo está completo (scheduled ou canceled)."""
        return self.current_state in [
            AppointmentState.SCHEDULED,
            AppointmentState.CANCELED,
        ]

    @property
    def needs_date(self) -> bool:
        """Verifica se precisa coletar data."""
        return (
            self.current_state == AppointmentState.INITIATED
            and "date" not in self.collected_data
        )

    @property
    def needs_time(self) -> bool:
        """Verifica se precisa coletar horário."""
        return (
            self.current_state == AppointmentState.DATE_COLLECTED
            and "time" not in self.collected_data
        )

    @property
    def needs_confirmation(self) -> bool:
        """Verifica se precisa de confirmação do usuário."""
        return self.current_state == AppointmentState.TIME_COLLECTED
