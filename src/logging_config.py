"""Central logging configuration for the ingestion pipeline."""

import logging

from pythonjsonlogger.json import JsonFormatter


def configure_logger(level: int = logging.INFO) -> None:
    """Attach a JSON-formatting handler to the root logger.

    Called once by the pipeline entrypoint (the ingestion DAG, #25);
    library modules should only call getLogger(__name__) and log.

    Args:
        level: The minimum log level to emit.
    """
    handler = logging.StreamHandler()
    formatter = JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    root_logger = logging.getLogger()

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(level)
