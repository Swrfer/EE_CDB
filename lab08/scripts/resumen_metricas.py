"""Resume las métricas de cortesía del Laboratorio 08."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ActivityMetrics:
    """Métricas observadas en una actividad."""

    activity: str
    real_requests: int
    cache_hits: int


METRICS = (
    ActivityMetrics(
        activity=(
            "Exploración y fallos controlados "
            "(actividades 1–2)"
        ),
        real_requests=6,
        cache_hits=0,
    ),
    ActivityMetrics(
        activity=(
            "Paginación de ClinicalTrials.gov "
            "(actividad 3)"
        ),
        real_requests=3,
        cache_hits=6,
    ),
    ActivityMetrics(
        activity=(
            "Descarga cruda de las tres APIs "
            "(actividad 5)"
        ),
        real_requests=3,
        cache_hits=0,
    ),
    ActivityMetrics(
        activity=(
            "Resumen ESummary de PubMed "
            "(actividad 6)"
        ),
        real_requests=1,
        cache_hits=0,
    ),
    ActivityMetrics(
        activity=(
            "Validación, consolidación y pruebas "
            "(actividades 6–8)"
        ),
        real_requests=0,
        cache_hits=0,
    ),
)


def main() -> None:
    """Calcula y conserva el resumen de métricas."""
    project_root = Path(__file__).resolve().parents[1]
    evidence_dir = (
        project_root
        / "evidencias"
    )

    real_requests = sum(
        metric.real_requests
        for metric in METRICS
    )
    cache_hits = sum(
        metric.cache_hits
        for metric in METRICS
    )
    resolved_requests = (
        real_requests
        + cache_hits
    )

    if (
        real_requests != 13
        or cache_hits != 6
    ):
        raise RuntimeError(
            "El conteo no coincide con la "
            "bitácora del laboratorio."
        )

    cache_percentage = (
        100.0
        * cache_hits
        / resolved_requests
    )

    report = {
        "activities": [
            asdict(metric)
            for metric in METRICS
        ],
        "totals": {
            "real_requests": real_requests,
            "cache_hits": cache_hits,
            "resolved_requests": (
                resolved_requests
            ),
            "cache_percentage": round(
                cache_percentage,
                2,
            ),
        },
        "interpretation": {
            "simultaneous_users": 1000,
            "estimated_first_run_requests": (
                real_requests
                * 1000
            ),
        },
    }

    evidence_dir.mkdir(
        parents=True,
        exist_ok=True,
    )
    json_path = (
        evidence_dir
        / "lab08_09_metrics.json"
    )
    json_path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print("===== MÉTRICAS POR ACTIVIDAD =====")

    for metric in METRICS:
        print(
            f"{metric.activity}: "
            f"reales={metric.real_requests}, "
            f"caché={metric.cache_hits}"
        )

    print("\n===== TOTALES =====")
    print(
        "Peticiones reales:",
        real_requests,
    )
    print(
        "Respuestas desde caché:",
        cache_hits,
    )
    print(
        "Solicitudes resueltas:",
        resolved_requests,
    )
    print(
        "Porcentaje resuelto desde caché:",
        f"{cache_percentage:.2f}%",
    )

    print("\n===== REFLEXIÓN =====")
    print(
        "Mil primeras ejecuciones simultáneas "
        "podrían generar 13,000 solicitudes "
        "reales y ejercer presión innecesaria."
    )
    print(
        "La caché reduce las repeticiones, pero "
        "también se requieren límites de tasa, "
        "pausas y ejecuciones escalonadas."
    )

    print(
        "\nInforme JSON:",
        json_path.relative_to(
            project_root,
        ),
    )


if __name__ == "__main__":
    main()
