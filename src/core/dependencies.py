"""Dependências do Aplicativo.

Este módulo define as dependências que são injetadas no agente durante a execução.
Isso permite um melhor isolamento para testes e desacomplamento da infraestrutura.
"""

from dataclasses import dataclass

from src.services.supabase import SupabaseService


@dataclass
class AppDependencies:
    """Dependências injetadas nos tools do agente.

    Attributes:
        supabase: Serviço do Supabase para banco de dados.
        customer_id: ID (telefone) do cliente atual.
        trace_id: ID de rastreamento para observabilidade.
    """

    supabase: SupabaseService
    customer_id: str | None = None
    trace_id: str | None = None
    # Futuro: calendar_service, etc.
