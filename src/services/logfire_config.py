"""Logfire Configuration - Observability for Pydantic AI.

Configura Logfire para instrumentação automática do Pydantic AI,
permitindo visualização de traces, spans e logs no dashboard Logfire.
"""

import logfire

from src.utils.logger import get_logger

logger = get_logger(__name__)


def configure_logfire() -> None:
    """Configura Logfire para instrumentação do Pydantic AI.

    Esta função deve ser chamada uma única vez no início da aplicação,
    antes de criar qualquer agente Pydantic AI.

    Environment Variables:
        LOGFIRE_TOKEN: Token de autenticação do Logfire (opcional se .logfire existe)
        ENABLE_LOGFIRE: Se 'false', desabilita Logfire (default: true)
    """
    from src.config.settings import get_settings
    settings = get_settings()

    if not settings.enable_logfire:
        logger.info("logfire_disabled", reason="enable_logfire=false")
        return

    try:
        # Configura Logfire com token se disponível
        if settings.logfire_token:
            logfire.configure(token=settings.logfire_token)
        else:
            # Usa .logfire dir local (para desenvolvimento)
            logfire.configure()

        # Instrumenta Pydantic AI automaticamente
        logfire.instrument_pydantic_ai()

        logger.info("logfire_configured", status="success")

    except Exception as e:
        # Fail open - não quebra a aplicação se Logfire falhar
        logger.warning(
            "logfire_configuration_failed",
            error=str(e),
            error_type=type(e).__name__,
        )


def instrument_fastapi_with_logfire(app: object) -> None:
    """Instrumenta FastAPI com Logfire (opcional).

    Args:
        app: Instância FastAPI a ser instrumentada.
    """
    enable_logfire = os.getenv("ENABLE_LOGFIRE", "true").lower() != "false"

    if not enable_logfire:
        return

    try:
        logfire.instrument_fastapi(app)  # type: ignore
        logger.info("logfire_fastapi_instrumented")
    except Exception as e:
        logger.warning(
            "logfire_fastapi_instrumentation_failed",
            error=str(e),
        )
