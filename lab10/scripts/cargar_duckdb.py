"""Carga reproducible de cinco CSV de Synthea en DuckDB."""

from __future__ import annotations

import csv
from pathlib import Path

import duckdb

TABLES = (
    "patients",
    "encounters",
    "conditions",
    "medications",
    "observations",
)

EXPECTED_HEADERS: dict[str, tuple[str, ...]] = {
    "patients": (
        "Id",
        "BIRTHDATE",
        "DEATHDATE",
        "SSN",
        "DRIVERS",
        "PASSPORT",
        "PREFIX",
        "FIRST",
        "MIDDLE",
        "LAST",
        "SUFFIX",
        "MAIDEN",
        "MARITAL",
        "RACE",
        "ETHNICITY",
        "GENDER",
        "BIRTHPLACE",
        "ADDRESS",
        "CITY",
        "STATE",
        "COUNTY",
        "FIPS",
        "ZIP",
        "LAT",
        "LON",
        "HEALTHCARE_EXPENSES",
        "HEALTHCARE_COVERAGE",
        "INCOME",
    ),
    "encounters": (
        "Id",
        "START",
        "STOP",
        "PATIENT",
        "ORGANIZATION",
        "PROVIDER",
        "PAYER",
        "ENCOUNTERCLASS",
        "CODE",
        "DESCRIPTION",
        "BASE_ENCOUNTER_COST",
        "TOTAL_CLAIM_COST",
        "PAYER_COVERAGE",
        "REASONCODE",
        "REASONDESCRIPTION",
    ),
    "conditions": (
        "START",
        "STOP",
        "PATIENT",
        "ENCOUNTER",
        "SYSTEM",
        "CODE",
        "DESCRIPTION",
    ),
    "medications": (
        "START",
        "STOP",
        "PATIENT",
        "PAYER",
        "ENCOUNTER",
        "CODE",
        "DESCRIPTION",
        "BASE_COST",
        "PAYER_COVERAGE",
        "DISPENSES",
        "TOTALCOST",
        "REASONCODE",
        "REASONDESCRIPTION",
    ),
    "observations": (
        "DATE",
        "PATIENT",
        "ENCOUNTER",
        "CATEGORY",
        "CODE",
        "DESCRIPTION",
        "VALUE",
        "UNITS",
        "TYPE",
    ),
}


def repository_root() -> Path:
    """Obtiene la raíz del repositorio."""
    return Path(__file__).resolve().parents[2]


def read_header(csv_file: Path) -> tuple[str, ...]:
    """Lee únicamente el encabezado de un CSV."""
    with csv_file.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.reader(handle)
        return tuple(next(reader))


def validate_csv_files(csv_directory: Path) -> None:
    """Valida existencia y estructura de los CSV."""
    print("===== VALIDACIÓN DE CSV =====")

    for table in TABLES:
        csv_file = csv_directory / f"{table}.csv"

        if not csv_file.is_file():
            raise FileNotFoundError(
                f"No existe: {csv_file}"
            )

        if csv_file.stat().st_size == 0:
            raise ValueError(
                f"El archivo está vacío: {csv_file}"
            )

        observed = read_header(csv_file)
        expected = EXPECTED_HEADERS[table]

        if observed != expected:
            raise ValueError(
                f"Encabezado inesperado en {csv_file.name}\n"
                f"Esperado: {expected}\n"
                f"Observado: {observed}"
            )

        print(
            f"{csv_file.name}: "
            f"{len(observed)} columnas correctas"
        )


def load_database(
    database_file: Path,
    sql_file: Path,
) -> None:
    """Ejecuta la carga y presenta conteos y tipos."""
    sql = sql_file.read_text(encoding="utf-8")

    with duckdb.connect(str(database_file)) as connection:
        connection.execute(sql)
        connection.execute("CHECKPOINT")

        print("\n===== CONTEOS EN DUCKDB =====")

        for table in TABLES:
            result = connection.execute(
                f"SELECT count(*) FROM {table}"
            ).fetchone()

            if result is None:
                raise RuntimeError(
                    f"No se pudo contar {table}"
                )

            print(f"{table}: {result[0]}")

        print("\n===== COLUMNAS TEMPORALES =====")

        temporal_columns = connection.execute(
            """
            SELECT
                table_name,
                column_name,
                data_type
            FROM information_schema.columns
            WHERE table_schema = 'main'
              AND (
                    data_type = 'DATE'
                    OR data_type LIKE 'TIMESTAMP%'
              )
            ORDER BY
                table_name,
                ordinal_position
            """
        ).fetchall()

        for table, column, data_type in temporal_columns:
            print(
                f"{table}.{column}: {data_type}"
            )


def main() -> None:
    """Valida entradas y crea la base clínica."""
    root = repository_root()

    csv_directory = (
        root
        / "lab10"
        / "data"
        / "raw"
        / "synthea_5000"
        / "csv"
    )

    database_file = (
        root
        / "lab10"
        / "clinical.duckdb"
    )

    sql_file = (
        root
        / "lab10"
        / "sql"
        / "carga.sql"
    )

    validate_csv_files(csv_directory)

    print("\n===== CARGA =====")
    print(f"Base: {database_file}")
    print(f"SQL: {sql_file}")

    load_database(
        database_file=database_file,
        sql_file=sql_file,
    )

    print("\nCarga completada correctamente.")


if __name__ == "__main__":
    main()
