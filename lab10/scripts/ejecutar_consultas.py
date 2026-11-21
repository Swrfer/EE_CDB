"""Ejecuta las consultas SQL y guarda cada resultado."""

from __future__ import annotations

import csv
from pathlib import Path

import duckdb
import sqlparse

ROOT = Path(__file__).resolve().parents[2]
DATABASE = ROOT / "lab10" / "clinical.duckdb"
SQL_FILE = ROOT / "lab10" / "sql" / "consultas.sql"
OUTPUT = ROOT / "lab10" / "evidencias" / "consultas"


def main() -> None:
    """Ejecuta todos los enunciados de consultas.sql."""
    sql_text = SQL_FILE.read_text(encoding="utf-8")

    statements = [
        statement.strip()
        for statement in sqlparse.split(sql_text)
        if statement.strip()
    ]

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    with duckdb.connect(
        str(DATABASE),
        read_only=True,
    ) as connection:
        for number, statement in enumerate(
            statements,
            start=1,
        ):
            cursor = connection.execute(statement)

            headers = [
                str(column[0])
                for column in cursor.description
            ]

            rows = cursor.fetchall()

            output_file = (
                OUTPUT
                / f"consulta_{number:02d}.csv"
            )

            with output_file.open(
                "w",
                encoding="utf-8",
                newline="",
            ) as handle:
                writer = csv.writer(handle)
                writer.writerow(headers)
                writer.writerows(rows)

            print(
                f"===== CONSULTA {number} ====="
            )
            print(" | ".join(headers))

            displayed_rows = rows[:20]

            for row in displayed_rows:
                print(
                    " | ".join(
                        "NULL"
                        if value is None
                        else str(value)
                        for value in row
                    )
                )

            if len(rows) > len(displayed_rows):
                hidden_rows = (
                    len(rows)
                    - len(displayed_rows)
                )

                print(
                    f"... {hidden_rows} filas adicionales "
                    "guardadas en CSV ..."
                )

            print(
                f"Filas: {len(rows)}"
            )
            print(
                f"Guardado: {output_file}"
            )
            print()


if __name__ == "__main__":
    main()
