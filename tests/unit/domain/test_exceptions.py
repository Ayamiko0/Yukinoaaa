"""Domain unit tests for exceptions."""

from yukinoaaa.domain.exceptions import (
    DomainException,
    InfrastructureException,
    ResourceNotFoundException,
    RiskViolationException,
    ValidationException,
    YukinoaaaException,
)


def test_domain_exceptions() -> None:
    """Verify exception hierarchy and details initialization."""
    exc = YukinoaaaException("Base error", details={"code": 500})
    assert exc.message == "Base error"
    assert exc.details == {"code": 500}

    domain_exc = DomainException("Domain error")
    assert isinstance(domain_exc, YukinoaaaException)
    assert domain_exc.details == {}

    assert issubclass(ValidationException, DomainException)
    assert issubclass(RiskViolationException, DomainException)
    assert issubclass(ResourceNotFoundException, DomainException)
    assert issubclass(InfrastructureException, YukinoaaaException)
