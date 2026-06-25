from __future__ import annotations

from io import StringIO

import pytest

import pychete
from pychete import logging as pychete_logging


def test_configure_logging_emits_progress_messages_to_configured_stream() -> None:
    stream = StringIO()
    pychete.configure_logging(stream=stream, fmt="%(levelname)s:%(name)s:%(message)s", force=True)
    try:
        with pychete_logging.progress("running unit step", logger=pychete.get_logger("unit")):
            pass
    finally:
        pychete.disable_logging()

    output = stream.getvalue()
    assert "INFO:pychete.unit:running unit step ..." in output
    assert "INFO:pychete.unit:running unit step done in" in output


def test_disable_logging_removes_pychete_configured_handler() -> None:
    stream = StringIO()
    pychete.configure_logging(stream=stream, fmt="%(message)s", force=True)
    pychete.disable_logging()

    pychete.get_logger("unit").info("hidden message")

    assert stream.getvalue() == ""


def test_configure_logging_rejects_unknown_level() -> None:
    with pytest.raises(ValueError, match="unknown logging level"):
        pychete.configure_logging("LOUD", force=True)
    pychete.disable_logging()


def test_logging_helpers_are_public_api() -> None:
    assert pychete.configure_logging is pychete.api.configure_logging
    assert pychete.disable_logging is pychete.api.disable_logging
    assert pychete.get_logger is pychete.api.get_logger
