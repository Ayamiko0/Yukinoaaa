"""Tests for structured logger."""

from yukinoaaa.infrastructure.logging.logger import StructlogLogger


def test_logger_instantiation_and_bind() -> None:
    """Verify logger creation and context binding."""
    logger = StructlogLogger(log_level="INFO", is_production=False)
    bound_logger = logger.bind(user_id="12345", module="TestModule")
    assert bound_logger is not logger
    # Log statements should not raise exceptions
    bound_logger.info("Test message", action="test")
    bound_logger.error("Test error", code=500)
