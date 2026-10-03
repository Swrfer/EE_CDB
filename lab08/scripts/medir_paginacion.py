"""Compara la memoria de un generador contra una lista."""

import gc
import tracemalloc
from pathlib import Path
from typing import Any

from requests import PreparedRequest
from requests_cache import CachedSession

from clientes.paginacion import iterar_estudios

CONDITION = "gastric cancer"
PAGE_SIZE = 100
MAX_RECORDS = 300
MIB = 1024**2


class CountingCachedSession(CachedSession):
    """Sesión con contadores de red y caché."""

    def __init__(self, cache_name: Path) -> None:
        super().__init__(
            cache_name=str(cache_name),
            backend="sqlite",
            expire_after=7 * 24 * 60 * 60,
            allowable_methods=("GET",),
        )
        self.real_requests = 0
        self.cache_hits = 0

    def send(
        self,
        request: PreparedRequest,
        expire_after: Any = None,
        only_if_cached: bool = False,
        refresh: bool = False,
        force_refresh: bool = False,
        **kwargs: Any,
    ) -> Any:
        """Envía una petición y clasifica su procedencia."""
        response = super().send(
            request,
            expire_after=expire_after,
            only_if_cached=only_if_cached,
            refresh=refresh,
            force_refresh=force_refresh,
            **kwargs,
        )

        if bool(getattr(response, "from_cache", False)):
            self.cache_hits += 1
        else:
            self.real_requests += 1

        return response


def nct_id(study: dict[str, Any]) -> str:
    """Extrae el identificador NCT de un estudio."""
    return str(
        study["protocolSection"]
        ["identificationModule"]["nctId"]
    )


def warm_cache(session: CountingCachedSession) -> int:
    """Descarga una vez las páginas necesarias."""
    count = 0

    for _ in iterar_estudios(
        CONDITION,
        page_size=PAGE_SIZE,
        max_records=MAX_RECORDS,
        session=session,
    ):
        count += 1

    return count


def measure_generator(
    session: CountingCachedSession,
) -> tuple[int, str, str, int]:
    """Procesa uno a uno y devuelve el pico de memoria."""
    gc.collect()
    tracemalloc.start()

    count = 0
    first_id = ""
    last_id = ""

    for study in iterar_estudios(
        CONDITION,
        page_size=PAGE_SIZE,
        max_records=MAX_RECORDS,
        session=session,
    ):
        current_id = nct_id(study)

        if count == 0:
            first_id = current_id

        count += 1
        last_id = current_id

        if count in {1, 100, 200, 300}:
            current, peak = tracemalloc.get_traced_memory()
            print(
                f"Generador, registro {count:>3}: "
                f"actual={current / MIB:.2f} MiB, "
                f"pico={peak / MIB:.2f} MiB"
            )

    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return count, first_id, last_id, peak


def measure_list(
    session: CountingCachedSession,
) -> tuple[int, str, str, int]:
    """Acumula todos los estudios y devuelve el pico de memoria."""
    gc.collect()
    tracemalloc.start()

    studies = list(
        iterar_estudios(
            CONDITION,
            page_size=PAGE_SIZE,
            max_records=MAX_RECORDS,
            session=session,
        )
    )

    _, peak = tracemalloc.get_traced_memory()

    count = len(studies)
    first_id = nct_id(studies[0])
    last_id = nct_id(studies[-1])

    tracemalloc.stop()

    return count, first_id, last_id, peak


def main() -> None:
    """Ejecuta la comparación completa."""
    project_root = Path(__file__).resolve().parents[1]
    cache_name = project_root / ".cache" / "activity03"

    session = CountingCachedSession(cache_name)

    try:
        session.cache.clear()

        print("===== CALENTAMIENTO DE CACHÉ =====")
        warmed = warm_cache(session)

        print("Registros recorridos:", warmed)
        print("Peticiones reales:", session.real_requests)
        print("Respuestas desde caché:", session.cache_hits)

        print("\n===== GENERADOR =====")
        generator_result = measure_generator(session)

        print("\n===== LISTA =====")
        list_result = measure_list(session)

        gen_count, gen_first, gen_last, gen_peak = generator_result
        list_count, list_first, list_last, list_peak = list_result

        print("\n===== COMPARACIÓN =====")
        print(f"Generador: {gen_count} registros")
        print(f"Lista: {list_count} registros")
        print(f"Primer NCT idéntico: {gen_first == list_first}")
        print(f"Último NCT idéntico: {gen_last == list_last}")
        print(f"Pico generador: {gen_peak / MIB:.2f} MiB")
        print(f"Pico lista: {list_peak / MIB:.2f} MiB")

        difference = list_peak - gen_peak
        print(f"Diferencia: {difference / MIB:.2f} MiB")

        if list_peak > 0:
            reduction = 100 * difference / list_peak
            print(
                "Reducción respecto a la lista: "
                f"{reduction:.2f}%"
            )

        print("\n===== PETICIONES =====")
        print("Peticiones reales:", session.real_requests)
        print("Respuestas desde caché:", session.cache_hits)
    finally:
        session.close()


if __name__ == "__main__":
    main()
