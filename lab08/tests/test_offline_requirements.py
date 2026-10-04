"""Pruebas explícitas de los requisitos offline."""

from __future__ import annotations

import socket

import pytest
from pydantic import ValidationError

from clientes.models import ClinicalTrialRecord


def test_real_network_is_blocked() -> None:
    """La barrera global impide abrir sockets reales."""
    with (
        socket.socket() as test_socket,
        pytest.raises(
            AssertionError,
            match="intentó acceder a la red",
        ),
    ):
        test_socket.connect(
            (
                "127.0.0.1",
                9,
            )
        )


def test_pydantic_rejects_missing_required_field() -> None:
    """Pydantic rechaza un registro con inscripción ausente."""
    incomplete_trial: dict[str, object] = {
        "nct_id": "NCT01234567",
        "title": "Controlled malformed trial",
        "overall_status": "COMPLETED",
        "start_date": "2020-01",
        "completion_date": "2021-01",
        "countries": [
            "Mexico",
        ],
    }

    with pytest.raises(
        ValidationError,
        match="enrollment_count",
    ):
        ClinicalTrialRecord.model_validate(
            incomplete_trial,
        )
