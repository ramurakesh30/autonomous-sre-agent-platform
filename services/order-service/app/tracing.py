
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


_provider = None
_httpx_instrumentor = None


def setup_tracing(app, service_name: str) -> TracerProvider:
    """
    Configure OpenTelemetry tracing for one service process.

    FastAPI instrumentation captures incoming requests.
    HTTPX instrumentation captures outgoing HTTP requests.
    OTLP exports spans to Grafana Tempo.
    """

    global _provider, _httpx_instrumentor

    if _provider is not None:
        return _provider

    resource = Resource.create(
        {
            "service.name": service_name,
            "deployment.environment": "development",
        }
    )

    provider = TracerProvider(resource=resource)

    exporter = OTLPSpanExporter(
        endpoint="http://localhost:4317",
        insecure=True,
    )

    provider.add_span_processor(
        BatchSpanProcessor(exporter)
    )

    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=provider,
    )

    _httpx_instrumentor = HTTPXClientInstrumentor()
    _httpx_instrumentor.instrument(
        tracer_provider=provider,
    )

    _provider = provider

    return provider


def get_tracer(name: str):
    """Return a tracer for creating custom application spans."""
    return trace.get_tracer(name)


def shutdown_tracing() -> None:
    """Flush pending spans and shut down the tracer provider."""
    global _provider, _httpx_instrumentor

    if _httpx_instrumentor is not None:
        _httpx_instrumentor.uninstrument()
        _httpx_instrumentor = None

    if _provider is not None:
        _provider.force_flush(timeout_millis=5000)
        _provider.shutdown()
        _provider = None
