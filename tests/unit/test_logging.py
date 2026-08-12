import logging

from app.common.logging import SecretRedactionFilter, redact


def test_log_redaction_hides_secrets():
    value = redact("token=secret-value authorization: Bearer abc.def")
    assert "secret-value" not in value
    assert "abc.def" not in value
    assert value.count("[REDACTED]") == 2


def test_log_redaction_preserves_numeric_format_arguments():
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "port=%d", (8080,), None)
    SecretRedactionFilter().filter(record)
    assert record.getMessage() == "port=8080"
