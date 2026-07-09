import structlog
import logging
from contextvars import ContextVar

# Context variable to hold the request ID for tracing
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

def add_request_id(logger, log_method, event_dict):
    req_id = request_id_var.get()
    if req_id:
        event_dict["request_id"] = req_id
    return event_dict

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        add_request_id,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logging.basicConfig(format="%(message)s", level=logging.INFO)

def get_logger(name: str):
    return structlog.get_logger(name)
