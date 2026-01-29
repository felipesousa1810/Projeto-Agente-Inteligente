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
        # Log token status for debugging
        has_token = bool(settings.logfire_token)
        logger.info(
            "logfire_init",
            has_token=has_token,
            token_prefix=settings.logfire_token[:8] + "..." if has_token else "none",
        )

        # Configura Logfire com token se disponível
        if settings.logfire_token:
            logfire.configure(token=settings.logfire_token)
            logger.info("logfire_configured_with_token")
        else:
            # Usa .logfire dir local (para desenvolvimento)
            logfire.configure()
            logger.info("logfire_configured_local")

        # Instrumenta Pydantic AI automaticamente
        logfire.instrument_pydantic_ai()

        logger.info(
            "logfire_configured", status="success", pydantic_ai_instrumented=True
        )

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
    from src.config.settings import get_settings

    settings = get_settings()

    if not settings.enable_logfire:
        return

    try:
        logfire.instrument_fastapi(app)  # type: ignore
        logger.info("logfire_fastapi_instrumented")
    except Exception as e:
        logger.warning(
            "logfire_fastapi_instrumentation_failed",
            error=str(e),
        )
