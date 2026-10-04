"""Pruebas sin red para el cliente HTTP robusto."""


import pytest
import requests
import responses

from clientes.base import RobustAPIClient

TEST_URL = "https://example.test/api"


def make_client(
    *,
    max_attempts: int = 3,
    backoff_factor: float = 0.5,
) -> tuple[RobustAPIClient, list[float]]:
    """Crea un cliente con caché en memoria y espera simulada."""
    sleeps: list[float] = []

    client = RobustAPIClient(
        cache_name="test_cache",
        cache_backend="memory",
        timeout=(0.1, 0.1),
        max_attempts=max_attempts,
        backoff_factor=backoff_factor,
        sleep_func=sleeps.append,
    )

    return client, sleeps


@responses.activate
def test_200_returns_valid_json() -> None:
    """Una respuesta 200 se devuelve sin reintentos."""
    responses.add(
        responses.GET,
        TEST_URL,
        json={"status": "ok"},
        status=200,
    )

    client, sleeps = make_client()

    with client:
        payload = client.get_json(TEST_URL)

    assert payload == {"status": "ok"}
    assert len(responses.calls) == 1
    assert client.metrics.real_requests == 1
    assert client.metrics.cache_hits == 0
    assert client.metrics.retries == 0
    assert sleeps == []


@responses.activate
def test_429_honors_retry_after_then_succeeds() -> None:
    """Un 429 respeta Retry-After y después termina bien."""
    responses.add(
        responses.GET,
        TEST_URL,
        json={"error": "too many requests"},
        status=429,
        headers={"Retry-After": "2"},
    )
    responses.add(
        responses.GET,
        TEST_URL,
        json={"status": "ok"},
        status=200,
    )

    client, sleeps = make_client()

    with client:
        payload = client.get_json(TEST_URL)

    assert payload == {"status": "ok"}
    assert len(responses.calls) == 2
    assert client.metrics.real_requests == 2
    assert client.metrics.retries == 1
    assert sleeps == [2.0]


@responses.activate
def test_persistent_500_stops_after_three_attempts() -> None:
    """Un error 500 persistente se abandona tras N intentos."""
    for _ in range(3):
        responses.add(
            responses.GET,
            TEST_URL,
            json={"error": "server failure"},
            status=500,
        )

    client, sleeps = make_client(
        max_attempts=3,
        backoff_factor=0.5,
    )

    with client, pytest.raises(
        requests.exceptions.HTTPError
    ):
        client.get_json(TEST_URL)

    assert len(responses.calls) == 3
    assert client.metrics.real_requests == 3
    assert client.metrics.retries == 2
    assert sleeps == [0.5, 1.0]


@responses.activate
def test_503_uses_exponential_backoff() -> None:
    """Un 503 transitorio usa backoff y puede recuperarse."""
    responses.add(
        responses.GET,
        TEST_URL,
        json={"error": "service unavailable"},
        status=503,
    )
    responses.add(
        responses.GET,
        TEST_URL,
        json={"status": "recovered"},
        status=200,
    )

    client, sleeps = make_client()

    with client:
        payload = client.get_json(TEST_URL)

    assert payload == {"status": "recovered"}
    assert len(responses.calls) == 2
    assert client.metrics.retries == 1
    assert sleeps == [0.5]


@pytest.mark.parametrize(
    "status_code",
    [
        400,
        401,
        404,
    ],
)
@responses.activate
def test_client_errors_are_not_retried(
    status_code: int,
) -> None:
    """Los 4xx permanentes fallan en el primer intento."""
    responses.add(
        responses.GET,
        TEST_URL,
        json={"error": "client failure"},
        status=status_code,
    )

    client, sleeps = make_client()

    with client, pytest.raises(
        requests.exceptions.HTTPError
    ):
        client.get_json(TEST_URL)

    assert len(responses.calls) == 1
    assert client.metrics.real_requests == 1
    assert client.metrics.retries == 0
    assert sleeps == []


@responses.activate
def test_non_idempotent_method_is_not_retried() -> None:
    """POST no se repite automáticamente ante un 503."""
    responses.add(
        responses.POST,
        TEST_URL,
        json={"error": "service unavailable"},
        status=503,
    )

    client, sleeps = make_client()

    with client, pytest.raises(
        requests.exceptions.HTTPError
    ):
        client.request(
            "POST",
            TEST_URL,
        )

    assert len(responses.calls) == 1
    assert client.metrics.real_requests == 1
    assert client.metrics.retries == 0
    assert sleeps == []


@responses.activate
def test_second_identical_get_uses_cache() -> None:
    """La segunda consulta GET idéntica sale de la caché."""
    responses.add(
        responses.GET,
        TEST_URL,
        json={"status": "cached"},
        status=200,
    )

    client, sleeps = make_client()

    with client:
        first = client.get_json(TEST_URL)
        second = client.get_json(TEST_URL)

    assert first == second == {"status": "cached"}
    assert len(responses.calls) == 1
    assert client.metrics.real_requests == 1
    assert client.metrics.cache_hits == 1
    assert client.metrics.retries == 0
    assert sleeps == []
