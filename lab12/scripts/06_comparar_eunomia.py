#!/usr/bin/env python3
"""Carga las tablas necesarias de GiBleed y compara Eunomia con la base propia."""

from pathlib import Path
from urllib.request import urlretrieve
from zipfile import ZipFile

import duckdb
import pandas as pd


RAIZ = Path("lab12")
CACHE = RAIZ / "data/reference/eunomia_cache"
ZIP = CACHE / "GiBleed_5.3.zip"
CSV_DIR = RAIZ / "data/reference/eunomia_csv"
DB = RAIZ / "data/reference/eunomia_gibleed.duckdb"
SALIDA = RAIZ / "evidencias/analisis"
REPORTE = RAIZ / "reporte_calidad.md"
URL = (
    "https://raw.githubusercontent.com/OHDSI/EunomiaDatasets/"
    "main/datasets/GiBleed/GiBleed_5.3.zip"
)

TABLAS = {
    "person": "person",
    "observation_period": "observation_period",
    "condition_occurrence": "condition_occurrence",
    "visit_occurrence": "visit_occurrence",
    "concept": "concept",
}


def localizar_csv(nombres: list[str], tabla: str) -> str:
    objetivo = f"{tabla}.csv".lower()
    candidatos = [nombre for nombre in nombres if Path(nombre).name.lower() == objetivo]
    if len(candidatos) != 1:
        raise RuntimeError(
            f"Se esperaba un CSV para {tabla}; encontrados: {candidatos}"
        )
    return candidatos[0]


def tabla_markdown(datos: pd.DataFrame) -> str:
    columnas = [str(x) for x in datos.columns]
    lineas = [
        "| " + " | ".join(columnas) + " |",
        "| " + " | ".join(["---"] * len(columnas)) + " |",
    ]
    for _, fila in datos.iterrows():
        valores = []
        for valor in fila:
            if pd.isna(valor):
                texto = ""
            elif isinstance(valor, float):
                texto = f"{valor:.4f}".rstrip("0").rstrip(".")
            else:
                texto = str(valor)
            valores.append(texto.replace("|", r"\|"))
        lineas.append("| " + " | ".join(valores) + " |")
    return "\n".join(lineas)


def guardar(nombre: str, datos: pd.DataFrame) -> None:
    ruta = SALIDA / nombre
    datos.to_csv(ruta, index=False)
    print(f"OK: {ruta} ({len(datos)} filas)")


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    SALIDA.mkdir(parents=True, exist_ok=True)

    if not ZIP.exists():
        print("Descargando GiBleed 5.3...")
        urlretrieve(URL, ZIP)

    print(f"ZIP de referencia: {ZIP}")

    rutas_csv: dict[str, Path] = {}
    with ZipFile(ZIP) as archivo:
        nombres = archivo.namelist()
        for tabla in TABLAS:
            miembro = localizar_csv(nombres, tabla)
            destino = CSV_DIR / f"{tabla}.csv"
            with archivo.open(miembro) as origen, destino.open("wb") as salida:
                salida.write(origen.read())
            rutas_csv[tabla] = destino
            print(f"Extraída: {tabla}")

    conexion = duckdb.connect(str(DB))
    try:
        for tabla, ruta in rutas_csv.items():
            ruta_sql = str(ruta.resolve()).replace("'", "''")
            conexion.execute(
                f"""
                CREATE OR REPLACE TABLE {tabla} AS
                SELECT *
                FROM read_csv_auto(
                    '{ruta_sql}',
                    header = TRUE,
                    sample_size = -1,
                    all_varchar = FALSE
                )
                """
            )

        personas_sexo = conexion.execute(
            """
            SELECT COALESCE(c.concept_name, 'Sin concepto legible') sexo,
                   COUNT(DISTINCT p.person_id) personas
            FROM person p
            LEFT JOIN concept c ON c.concept_id = p.gender_concept_id
            GROUP BY 1
            ORDER BY personas DESC
            """
        ).df()

        personas_nacimiento = conexion.execute(
            """
            SELECT year_of_birth anio_nacimiento,
                   COUNT(DISTINCT person_id) personas
            FROM person
            GROUP BY year_of_birth
            ORDER BY year_of_birth
            """
        ).df()

        observacion_resumen = conexion.execute(
            """
            WITH por_persona AS (
                SELECT person_id,
                       SUM(
                           DATE_DIFF(
                               'day',
                               CAST(observation_period_start_date AS DATE),
                               CAST(observation_period_end_date AS DATE)
                           ) + 1
                       ) dias_observacion
                FROM observation_period
                GROUP BY person_id
            )
            SELECT COUNT(DISTINCT person_id) personas,
                   MEDIAN(dias_observacion) mediana_dias_observacion,
                   ROUND(AVG(dias_observacion), 2) media_dias_observacion,
                   MIN(dias_observacion) minimo_dias,
                   MAX(dias_observacion) maximo_dias
            FROM por_persona
            """
        ).df()

        top20 = conexion.execute(
            """
            SELECT co.condition_concept_id concept_id,
                   c.concept_name AS concept_name,
                   COUNT(*) eventos,
                   COUNT(DISTINCT co.person_id) personas
            FROM condition_occurrence co
            LEFT JOIN concept c ON c.concept_id = co.condition_concept_id
            WHERE co.condition_concept_id <> 0
            GROUP BY co.condition_concept_id, c.concept_name
            ORDER BY eventos DESC, personas DESC
            LIMIT 20
            """
        ).df()

        visitas_resumen = conexion.execute(
            """
            WITH por_persona AS (
                SELECT p.person_id, COUNT(v.visit_occurrence_id) visitas
                FROM person p
                LEFT JOIN visit_occurrence v ON v.person_id = p.person_id
                GROUP BY p.person_id
            )
            SELECT COUNT(*) personas, SUM(visitas) visitas,
                   ROUND(AVG(visitas), 4) media_visitas_por_persona,
                   MEDIAN(visitas) mediana_visitas_por_persona
            FROM por_persona
            """
        ).df()

        visitas_tipo = conexion.execute(
            """
            SELECT v.visit_concept_id concept_id,
                   COALESCE(c.concept_name, 'Sin concepto legible') tipo_visita,
                   COUNT(*) visitas,
                   COUNT(DISTINCT v.person_id) personas,
                   ROUND(COUNT(*) * 1.0 /
                         NULLIF(COUNT(DISTINCT v.person_id), 0), 4)
                       media_visitas_por_persona
            FROM visit_occurrence v
            LEFT JOIN concept c ON c.concept_id = v.visit_concept_id
            GROUP BY v.visit_concept_id, c.concept_name
            ORDER BY visitas DESC
            """
        ).df()
    finally:
        conexion.close()

    guardar("eunomia_personas_sexo.csv", personas_sexo)
    guardar("eunomia_personas_nacimiento.csv", personas_nacimiento)
    guardar("eunomia_observacion_resumen.csv", observacion_resumen)
    guardar("eunomia_top20_diagnosticos.csv", top20)
    guardar("eunomia_visitas_resumen.csv", visitas_resumen)
    guardar("eunomia_visitas_tipo.csv", visitas_tipo)

    propio_sexo = pd.read_csv(SALIDA / "personas_sexo.csv")
    propio_obs = pd.read_csv(SALIDA / "observacion_mediana.csv")
    propio_top = pd.read_csv(SALIDA / "top20_diagnosticos.csv")
    propio_visitas = pd.read_csv(SALIDA / "visitas_resumen.csv")

    comparacion = pd.DataFrame(
        {
            "metrica": [
                "Personas",
                "Categorías de sexo",
                "Mediana de días de observación",
                "Visitas",
                "Media de visitas por persona",
                "Diagnóstico más frecuente",
                "Eventos del diagnóstico más frecuente",
            ],
            "synthea_propio": [
                propio_sexo["personas"].sum(),
                len(propio_sexo),
                propio_obs.loc[0, "mediana_dias_observacion"],
                propio_visitas.loc[0, "visitas"],
                propio_visitas.loc[0, "media_visitas_por_persona"],
                propio_top.loc[0, "concept_name"],
                propio_top.loc[0, "eventos"],
            ],
            "eunomia": [
                personas_sexo["personas"].sum(),
                len(personas_sexo),
                observacion_resumen.loc[0, "mediana_dias_observacion"],
                visitas_resumen.loc[0, "visitas"],
                visitas_resumen.loc[0, "media_visitas_por_persona"],
                top20.loc[0, "concept_name"],
                top20.loc[0, "eventos"],
            ],
        }
    )
    guardar("comparacion_synthea_eunomia.csv", comparacion)

    reporte = REPORTE.read_text(encoding="utf-8")
    origen = pd.read_csv(SALIDA / "estandar_vs_origen.csv")
    if int(origen.loc[0, "diferencia_eventos"]) == 0:
        inicio = "La diferencia se debe a que varios"
        fin = "quedan en `concept_id = 0`."
        i = reporte.find(inicio)
        j = reporte.find(fin, i)
        if i >= 0 and j >= 0:
            j += len(fin)
            explicacion = (
                "En esta base ambos conteos coinciden porque la condición "
                "seleccionada apareció con un solo código de origen. Esto no "
                "contradice OMOP: en otras fuentes varios códigos pueden "
                "converger en el mismo concepto estándar, mientras que los "
                "códigos sin mapeo se representan con `concept_id = 0`."
            )
            reporte = reporte[:i] + explicacion + reporte[j:]

    encabezado = "## 10. Base de referencia"
    i = reporte.find(encabezado)
    if i < 0:
        raise RuntimeError("No se encontró la sección de referencia del reporte")

    seccion = (
        "## 10. Comparación con Eunomia\n\n"
        + tabla_markdown(comparacion)
        + "\n\n"
        + "Eunomia se utilizó como base OMOP de demostración. La base propia "
        + "contiene una población mayor y una densidad de visitas distinta. "
        + "También cambia el diagnóstico dominante, porque ambas bases fueron "
        + "generadas para escenarios clínicos diferentes. La semejanza "
        + "estructural con OMOP no implica igualdad en distribución de "
        + "enfermedades, seguimiento o utilización de servicios.\n"
    )
    REPORTE.write_text(reporte[:i] + seccion, encoding="utf-8")

    print("\n===== COMPARACIÓN CON EUNOMIA COMPLETADA =====")
    print(comparacion.to_string(index=False))
    print(f"Base de referencia: {DB}")


if __name__ == "__main__":
    main()
