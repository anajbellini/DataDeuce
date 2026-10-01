"""Tests for src.logging_config."""

import logging
import sys

from src.logging_config import configure_logger


def test_configure_logger_writes_json_logs_to_stdout():
    root_logger = logging.getLogger()
    handlers_before = list(root_logger.handlers)
    level_before = root_logger.level

    try:
        configure_logger()
        added = [h for h in root_logger.handlers if h not in handlers_before]

        assert len(added) == 1
        assert added[0].stream is sys.stdout  # stderr is shown as an error by Airflow
    finally:
        for handler in root_logger.handlers[len(handlers_before) :]:
            root_logger.removeHandler(handler)
        root_logger.setLevel(level_before)
