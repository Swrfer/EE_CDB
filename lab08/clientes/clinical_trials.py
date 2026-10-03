"""Funciones para consultar la API v2 de ClinicalTrials.gov."""

from typing import Any, cast

import requests
from requests import Session

STUDIES_URL = "https://clinicaltrials.gov/api/v2/studies"
DEFAULT_TIMEOUT = (3.05, 20.0)


def buscar_estudios_simple(
    condicion: str,
    page_size: int = 10,
    *,
    session: Session | None = None,
) -> dict[str, Any]:
    """Realiza una búsqueda sencilla de estudios por condición clínica.

    Esta función conserva explícitamente las tres prácticas mínimas de una
    petición HTTP: parámetros separados, tiempo límite y comprobación del
    código de estado.
    """
    if not condicion.strip():
        raise ValueError("La condición no puede estar vacía.")

    if page_size < 1:
        raise ValueError("page_size debe ser mayor que cero.")

    params: dict[str, str | int] = {
        "query.cond": condicion,
        "pageSize": page_size,
        "countTotal": "true",
        "format": "json",
    }

    owns_session = session is None
    http = session if session is not None else requests.Session()

    try:
        response = http.get(
            STUDIES_URL,
            params=params,
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        payload: object = response.json()
    finally:
        if owns_session:
            http.close()

    if not isinstance(payload, dict):
        raise TypeError("ClinicalTrials.gov no devolvió un objeto JSON.")

    return cast(dict[str, Any], payload)
