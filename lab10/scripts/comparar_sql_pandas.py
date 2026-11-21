"""Compara tres consultas clínicas en DuckDB y pandas."""

from __future__ import annotations

import csv
import gc
import statistics
import time
from pathlib import Path

import duckdb
import pandas as pd
from pandas.testing import assert_frame_equal

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "clinical.duckdb"
EVIDENCE_DIR = ROOT / "evidencias"
RESULTS_DIR = EVIDENCE_DIR / "comparacion_sql_pandas"
METRICS_PATH = EVIDENCE_DIR / "11_sql_vs_pandas.csv"
TEXT_PATH = EVIDENCE_DIR / "11_sql_vs_pandas.txt"
DOCUMENT_PATH = ROOT / "docs" / "sql_vs_pandas.md"

SQL_QUERIES = {
    "query_01": """
        SELECT
            count(*)::BIGINT AS total_patients,
            count(*) FILTER (
                WHERE death_date IS NULL
            )::BIGINT AS living_patients,
            count(*) FILTER (
                WHERE death_date IS NOT NULL
            )::BIGINT AS deceased_patients
        FROM patients
    """,
    "query_02": """
        SELECT
            coalesce(gender, 'UNKNOWN') AS gender,
            count(*)::BIGINT AS patients,
            round(
                100.0 * count(*) / sum(count(*)) OVER (),
                2
            )::DOUBLE AS percentage
        FROM patients
        GROUP BY coalesce(gender, 'UNKNOWN')
        ORDER BY patients DESC, gender
    """,
    "query_05": """
        SELECT
            year(start_time)::INTEGER AS encounter_year,
            count(*)::BIGINT AS encounters
        FROM encounters
        GROUP BY year(start_time)
        ORDER BY encounter_year
    """,
}

PANDAS_SNIPPETS = {
    "query_01": """
patients = connection.execute(
    "SELECT patient_id, death_date FROM patients"
).fetchdf()
total_patients = len(patients)
living_patients = patients["death_date"].isna().sum()
deceased_patients = patients["death_date"].notna().sum()
""",
    "query_02": """
patients = connection.execute(
    "SELECT gender FROM patients"
).fetchdf()
gender = patients["gender"].fillna("UNKNOWN")
result = gender.value_counts().rename_axis(
    "gender"
).reset_index(name="patients")
result["percentage"] = (
    100.0 * result["patients"] / len(patients)
).round(2)
""",
    "query_05": """
timezone = connection.execute(
    "SELECT current_setting('TimeZone')"
).fetchone()[0]
encounters = connection.execute(
    "SELECT start_time FROM encounters"
).fetchdf()
timestamps = pd.to_datetime(
    encounters["start_time"],
    utc=True,
).dt.tz_convert(timezone)
years = timestamps.dt.year
result = years.value_counts().sort_index()
""",
}


def count_lines(code: str) -> int:
    """Cuenta líneas de código no vacías."""
    return sum(
        1
        for line in code.strip().splitlines()
        if line.strip()
    )


def sql_result(
    connection: duckdb.DuckDBPyConnection,
    query_id: str,
) -> pd.DataFrame:
    """Ejecuta una pregunta mediante SQL."""
    return connection.execute(
        SQL_QUERIES[query_id]
    ).fetchdf()


def pandas_result(
    connection: duckdb.DuckDBPyConnection,
    query_id: str,
) -> pd.DataFrame:
    """Reproduce una pregunta mediante pandas."""
    if query_id == "query_01":
        patients = connection.execute(
            """
            SELECT patient_id, death_date
            FROM patients
            """
        ).fetchdf()

        return pd.DataFrame(
            {
                "total_patients": [len(patients)],
                "living_patients": [
                    int(
                        patients[
                            "death_date"
                        ].isna().sum()
                    )
                ],
                "deceased_patients": [
                    int(
                        patients[
                            "death_date"
                        ].notna().sum()
                    )
                ],
            }
        )

    if query_id == "query_02":
        patients = connection.execute(
            "SELECT gender FROM patients"
        ).fetchdf()

        gender = patients["gender"].fillna(
            "UNKNOWN"
        )

        result = (
            gender.value_counts()
            .rename_axis("gender")
            .reset_index(name="patients")
        )

        result["percentage"] = (
            100.0
            * result["patients"]
            / len(patients)
        ).round(2)

        return result.sort_values(
            ["patients", "gender"],
            ascending=[False, True],
        ).reset_index(drop=True)

    if query_id == "query_05":
        timezone_record = connection.execute(
            """
            SELECT current_setting('TimeZone')
            """
        ).fetchone()

        if timezone_record is None:
            raise RuntimeError(
                "No se pudo obtener la zona horaria."
            )

        timezone = str(timezone_record[0])

        encounters = connection.execute(
            """
            SELECT start_time
            FROM encounters
            """
        ).fetchdf()

        timestamps = pd.to_datetime(
            encounters["start_time"],
            utc=True,
        ).dt.tz_convert(timezone)

        years = timestamps.dt.year

        return (
            years.value_counts()
            .sort_index()
            .rename("encounters")
            .rename_axis("encounter_year")
            .reset_index()
        )

    raise ValueError(
        f"Consulta desconocida: {query_id}"
    )


def timed_execution(
    connection: duckdb.DuckDBPyConnection,
    query_id: str,
    engine: str,
) -> tuple[pd.DataFrame, float]:
    """Ejecuta y mide una implementación."""
    start = time.perf_counter()

    if engine == "sql":
        result = sql_result(
            connection,
            query_id,
        )
    elif engine == "pandas":
        result = pandas_result(
            connection,
            query_id,
        )
    else:
        raise ValueError(
            f"Motor desconocido: {engine}"
        )

    elapsed_ms = (
        time.perf_counter() - start
    ) * 1000.0

    return result, elapsed_ms


def normalize_frame(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    """Normaliza índices para comparar resultados."""
    normalized = frame.reset_index(drop=True)

    if "percentage" in normalized.columns:
        normalized["percentage"] = (
            normalized["percentage"]
            .astype(float)
            .round(2)
        )

    return normalized


def main() -> None:
    """Ejecuta la comparación completa."""
    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    DOCUMENT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    questions = {
        "query_01": (
            "Pacientes totales, vivos y fallecidos"
        ),
        "query_02": "Distribución por sexo",
        "query_05": "Encuentros por año",
    }

    metrics: list[dict[str, object]] = []

    with duckdb.connect(
        str(DATABASE),
        read_only=True,
    ) as connection:
        for query_id, question in questions.items():
            sql_reference = normalize_frame(
                sql_result(
                    connection,
                    query_id,
                )
            )
            pandas_reference = normalize_frame(
                pandas_result(
                    connection,
                    query_id,
                )
            )

            assert_frame_equal(
                sql_reference,
                pandas_reference,
                check_dtype=False,
                atol=0.01,
                rtol=0.0,
            )

            sql_times: list[float] = []
            pandas_times: list[float] = []

            for repetition in range(5):
                if repetition % 2 == 0:
                    _, sql_time = timed_execution(
                        connection,
                        query_id,
                        "sql",
                    )
                    _, pandas_time = timed_execution(
                        connection,
                        query_id,
                        "pandas",
                    )
                else:
                    _, pandas_time = timed_execution(
                        connection,
                        query_id,
                        "pandas",
                    )
                    _, sql_time = timed_execution(
                        connection,
                        query_id,
                        "sql",
                    )

                sql_times.append(sql_time)
                pandas_times.append(pandas_time)
                gc.collect()

            result_path = (
                RESULTS_DIR
                / f"{query_id}_resultado.csv"
            )
            sql_reference.to_csv(
                result_path,
                index=False,
            )

            sql_median = statistics.median(
                sql_times
            )
            pandas_median = statistics.median(
                pandas_times
            )

            metrics.append(
                {
                    "query_id": query_id,
                    "question": question,
                    "sql_lines": count_lines(
                        SQL_QUERIES[query_id]
                    ),
                    "pandas_lines": count_lines(
                        PANDAS_SNIPPETS[query_id]
                    ),
                    "sql_median_ms": sql_median,
                    "pandas_median_ms": pandas_median,
                    "pandas_sql_ratio": (
                        pandas_median / sql_median
                    ),
                    "same_result": True,
                }
            )

    with METRICS_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "query_id",
                "question",
                "sql_lines",
                "pandas_lines",
                "sql_median_ms",
                "pandas_median_ms",
                "pandas_sql_ratio",
                "same_result",
            ],
        )
        writer.writeheader()
        writer.writerows(metrics)

    output_lines = [
        "===== SQL CONTRA PANDAS =====",
        "",
        (
            "query_id | sql_lines | pandas_lines | "
            "sql_ms | pandas_ms | same_result"
        ),
    ]

    for row in metrics:
        output_lines.append(
            f"{row['query_id']} | "
            f"{row['sql_lines']} | "
            f"{row['pandas_lines']} | "
            f"{float(row['sql_median_ms']):.3f} | "
            f"{float(row['pandas_median_ms']):.3f} | "
            f"{row['same_result']}"
        )

    output_lines.extend(
        [
            "",
            "Las tres comparaciones produjeron",
            "resultados equivalentes.",
        ]
    )

    TEXT_PATH.write_text(
        "\n".join(output_lines) + "\n",
        encoding="utf-8",
    )

    table_rows = "\n".join(
        (
            f"| {row['query_id']} "
            f"| {row['sql_lines']} "
            f"| {row['pandas_lines']} "
            f"| {float(row['sql_median_ms']):.3f} ms "
            f"| {float(row['pandas_median_ms']):.3f} ms "
            f"| Sí |"
        )
        for row in metrics
    )

    document = f"""# Comparación entre SQL y pandas

Se reprodujeron tres de las quince preguntas clínicas mediante ambos
métodos. Cada implementación se ejecutó cinco veces y se reportó la
mediana.

| Consulta | Líneas SQL | Líneas pandas | Tiempo SQL | Tiempo pandas | Coinciden |
|---|---:|---:|---:|---:|---:|
{table_rows}

La lectura de columnas desde DuckDB se incluyó en el tiempo de pandas,
porque representa el costo real de trasladar los datos a memoria antes de
procesarlos.

## Decisión

Para este volumen y para preguntas basadas en filtros, agrupaciones y joins,
usaría **DuckDB**, porque expresa las operaciones de manera declarativa y
evita trasladar tablas grandes a la memoria de pandas.

Usaría **pandas** para trabajar con resultados ya resumidos, preparar
visualizaciones o alimentar modelos estadísticos. Cambiaría de opinión si
los datos derivados fueran pequeños y el análisis requiriera muchas
transformaciones propias del ecosistema científico de Python.
"""

    DOCUMENT_PATH.write_text(
        document,
        encoding="utf-8",
    )

    print("\n".join(output_lines))
    print()
    print(f"Métricas: {METRICS_PATH}")
    print(f"Evidencia: {TEXT_PATH}")
    print(f"Documento: {DOCUMENT_PATH}")
    print()
    print("Validación SQL contra pandas: correcta")


if __name__ == "__main__":
    main()
