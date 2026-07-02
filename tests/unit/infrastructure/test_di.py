"""Tests for Dependency Injection container."""

import pytest
from yukinoaaa.infrastructure.di.container import Container


class ServiceA:
    """Dummy service A."""


class ServiceB:
    """Dummy service B requiring ServiceA."""

    def __init__(self, a: ServiceA) -> None:
        self.a = a


def test_di_container_singleton() -> None:
    """Verify registering and resolving singletons."""
    container = Container()
    inst_a = ServiceA()
    container.register_singleton(ServiceA, inst_a)

    resolved = container.resolve(ServiceA)
    assert resolved is inst_a


def test_di_container_factory() -> None:
    """Verify resolving transient instances via factory."""
    container = Container()
    container.register_singleton(ServiceA, ServiceA())
    container.register_factory(ServiceB, lambda c: ServiceB(c.resolve(ServiceA)))

    inst_b1 = container.resolve(ServiceB)
    inst_b2 = container.resolve(ServiceB)
    assert isinstance(inst_b1, ServiceB)
    assert inst_b1 is not inst_b2
    assert inst_b1.a is inst_b2.a


def test_di_container_unregistered_raises() -> None:
    """Verify resolving unregistered key raises KeyError."""
    container = Container()
    with pytest.raises(KeyError):
        container.resolve(ServiceA)
