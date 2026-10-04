"""Cliente HTTP robusto compartido por las APIs biomédicas."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import requests
from requests import Response
from requests_cache import CachedSession

TimeoutValue = float | tuple[float, float]
SleepFunction = Callable[[float], None]

IDEMPOTENT_METHODS = frozenset(
    {
        "GET",
        "HEAD",
        "OPTIONS",
    }
)


@dataclass(slots=True)
class RequestMetrics:
    """Contadores acumulados de actividad HTTP."""

    real_requests: int = 0
    cache_hits: int = 0
    retries: int = 0

    @property
    def total_attempts(self) -> int:
        """Devuelve intentos de red más respuestas desde caché."""
        return self.real_requests + self.cache_hits


class RobustAPIClient:
    """Cliente con sesión, caché y reintentos controlados."""

    def __init__(
        self,
        *,
        cache_name: str | Path = ".cache/biomedical_api",
        cache_backend: str = "sqlite",
        cache_expire_seconds: int = 7 * 24 * 60 * 60,
        timeout: TimeoutValue = (3.05, 20.0),
        max_attempts: int = 3,
        backoff_factor: float = 0.5,
        sleep_func: SleepFunction = time.sleep,
        user_agent: str = "biomedical-api-client/0.1",
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts debe ser al menos 1.")

        if backoff_factor < 0:
            raise ValueError("backoff_factor no puede ser negativo.")

        if cache_expire_seconds < 0:
            raise ValueError(
                "cache_expire_seconds no puede ser negativo."
            )

        cache_path = Path(cache_name)

        if cache_backend == "sqlite":
            cache_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

        self.timeout = timeout
        self.max_attempts = max_attempts
        self.backoff_factor = backoff_factor
        self.sleep_func = sleep_func
        self.metrics = RequestMetrics()

        self.session = CachedSession(
            cache_name=str(cache_path),
            backend=cache_backend,
            expire_after=cache_expire_seconds,
            allowable_methods=tuple(IDEMPOTENT_METHODS),
            allowable_codes=(200,),
        )

        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": user_agent,
            }
        )

    def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str | int | float | None] | None = None,
    ) -> Response:
        """Realiza una petición con reintentos seguros."""
        normalized_method = method.upper()
        is_idempotent = normalized_method in IDEMPOTENT_METHODS

        attempts_allowed = (
            self.max_attempts
            if is_idempotent
            else 1
        )

        for attempt in range(1, attempts_allowed + 1):
            try:
                response = self.session.request(
                    normalized_method,
                    url,
                    params=params,
                    timeout=self.timeout,
                )
            except (
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
            ):
                self.metrics.real_requests += 1

                if attempt >= attempts_allowed:
                    raise

                self.metrics.retries += 1
                self.sleep_func(
                    self._backoff_seconds(attempt)
                )
                continue

            from_cache = bool(
                getattr(response, "from_cache", False)
            )

            if from_cache:
                self.metrics.cache_hits += 1
            else:
                self.metrics.real_requests += 1

            retryable_status = (
                response.status_code == 429
                or 500 <= response.status_code <= 599
            )

            should_retry = (
                is_idempotent
                and not from_cache
                and retryable_status
                and attempt < attempts_allowed
            )

            if should_retry:
                self.metrics.retries += 1
                delay = self._retry_delay(
                    response=response,
                    attempt=attempt,
                )
                self.sleep_func(delay)
                continue

            response.raise_for_status()
            return response

        raise RuntimeError(
            "La petición terminó sin respuesta ni excepción."
        )

    def get_json(
        self,
        url: str,
        *,
        params: dict[str, str | int | float | None] | None = None,
    ) -> dict[str, Any]:
        """Realiza GET y exige un objeto JSON como respuesta."""
        response = self.request(
            "GET",
            url,
            params=params,
        )
        payload: object = response.json()

        if not isinstance(payload, dict):
            raise TypeError(
                "La API no devolvió un objeto JSON."
            )

        return payload

    def _retry_delay(
        self,
        *,
        response: Response,
        attempt: int,
    ) -> float:
        """Prioriza Retry-After sobre el backoff exponencial."""
        retry_after = response.headers.get("Retry-After")

        if retry_after is not None:
            parsed_delay = self._parse_retry_after(
                retry_after
            )

            if parsed_delay is not None:
                return parsed_delay

        return self._backoff_seconds(attempt)

    def _backoff_seconds(self, attempt: int) -> float:
        """Calcula 0.5, 1, 2... según el intento fallido."""
        return self.backoff_factor * float(2 ** (attempt - 1))

    @staticmethod
    def _parse_retry_after(value: str) -> float | None:
        """Interpreta Retry-After como segundos o fecha HTTP."""
        stripped = value.strip()

        try:
            seconds = float(stripped)
        except ValueError:
            seconds = -1.0

        if seconds >= 0:
            return seconds

        try:
            retry_at = parsedate_to_datetime(stripped)
        except (TypeError, ValueError, OverflowError):
            return None

        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)

        now = datetime.now(UTC)
        return max(
            0.0,
            (retry_at - now).total_seconds(),
        )

    def close(self) -> None:
        """Cierra la sesión y su backend de caché."""
        self.session.close()

    def __enter__(self) -> RobustAPIClient:
        """Permite utilizar el cliente mediante with."""
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        """Cierra la sesión al abandonar el contexto."""
        self.close()
