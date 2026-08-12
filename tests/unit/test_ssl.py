from app.common.ssl import trusted_ssl_context


def test_trusted_ssl_context_contains_root_certificates():
    context = trusted_ssl_context()
    assert context.verify_mode.name == "CERT_REQUIRED"
    assert context.check_hostname is True
    assert len(context.get_ca_certs()) > 100
