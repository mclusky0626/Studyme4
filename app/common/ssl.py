from __future__ import annotations

import ssl

import certifi


def trusted_ssl_context() -> ssl.SSLContext:
    """Build a verified TLS context from Mozilla's maintained CA bundle.

    Python.org macOS installations do not always inherit Keychain root certificates.
    This keeps certificate verification enabled while making HTTPS reliable.
    """
    return ssl.create_default_context(cafile=certifi.where())
