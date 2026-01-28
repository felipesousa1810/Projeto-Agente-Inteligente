"""Observability - OpenTelemetry setup for tracing."""

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from src.config.settings import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def setup_tracing(service_name: str = "whatsapp-agent") -> None:
    """Setup OpenTelemetry tracing with Jaeger exporter.

    Args:
        service_name: Name of the service for tracing.
    """
    settings = get_settings()

    if not settings.enable_tracing:
        logger.info("tracing_disabled")
        return

    # Create resource
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": "1.0.0",
            "deployment.environment": settings.app_env,
        }
    )

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Configure Jaeger exporter
    try:
        jaeger_exporter = JaegerExporter(
            collector_endpoint=settings.jaeger_endpoint,
        )

        # Add span processor
        processor = BatchSpanProcessor(jaeger_exporter)
        provider.add_span_processor(processor)

        # Set as global provider
        trace.set_tracer_provider(provider)

        logger.info(
            "tracing_configured",
            service_name=service_name,
            jaeger_endpoint=settings.jaeger_endpoint,
        )

    except Exception as e:
        logger.warning(
            "tracing_setup_failed",
            error=str(e),
            message="Tracing will be disabled",
        )


def instrument_fastapi(app) -> None:  # type: ignore[no-untyped-def]
    """Instrument FastAPI app with OpenTelemetry.

    Args:
        app: FastAPI application instance.
    """
    settings = get_settings()

    if not settings.enable_tracing:
        return

    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("fastapi_instrumented")
    except Exception as e:
        logger.warning(
            "fastapi_instrumentation_failed",
            error=str(e),
        )


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance.

    Args:
        name: Name of the tracer (usually __name__).

    Returns:
        Tracer instance.
    """
    return trace.get_tracer(name)


def get_current_trace_id() -> str | None:
    """Get the current trace ID if available.

    Returns:
        Trace ID as hex string or None.
    """
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        return format(span.get_span_context().trace_id, "032x")
    return None
