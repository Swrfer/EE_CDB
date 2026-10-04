"""Configuración global de la suite offline."""

from __future__ import annotations

import socket

import pytest


@pytest.fixture(autouse=True)
def prevent_real_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Impide conexiones reales durante cualquier prueba."""

    def blocked_connect(
        _socket: socket.socket,
        address: object,
    ) -> None:
        raise AssertionError(
            "La suite intentó acceder a la red: "
            f"{address!r}"
        )

    monkeypatch.setattr(
        socket.socket,
        "connect",
        blocked_connect,
    )
