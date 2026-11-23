#!/usr/bin/env python3
"""Genera las ocho actividades y entregables del Laboratorio 16.

No ejecuta operaciones de Git. La base OMOP permanece fuera del repositorio;
solo se materializa un concept set pequeño en el esquema local ``results``.
"""

from __future__ import annotations

import shutil
import statistics
import time
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab16"
AUDIT = LAB / "evidencias" / "auditoria"
ANALYSIS = LAB / "evidencias" / "analisis"
DB = ROOT / "lab12" / "data" / "omop" / "synthea_omop_cdm54.duckdb"
SEED = 201826
LISINOPRIL = 1308216
HF_BROAD = 316139
HF_INNER = 4229440
TODAY = date.today().isoformat()


def save(df: pd.DataFrame, name: str) -> None:
    path = ANALYSIS / name
    df.to_csv(path, index=False)
    print(f"OK: {path} ({len(df)} filas)")


def scalar(con: duckdb.DuckDBPyConnection, sql: str) -> int:
    return int(con.execute(sql).fetchone()[0])


def read_audit(name: str) -> pd.DataFrame:
    path = AUDIT / name
    if not path.exists():
        raise SystemExit(f"ERROR: falta la auditoría requerida: {path}")
    return pd.read_csv(path)


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_Sin filas._"
    clean = df.copy().fillna("")
    headers = [str(column).replace("|", "\\|") for column in clean.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in clean.itertuples(index=False, name=None):
        values = [str(value).replace("|", "\\|").replace("\n", " ") for value in row]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def explain(con: duckdb.DuckDBPyConnection, query: str) -> str:
    rows = con.execute("EXPLAIN ANALYZE " + query).fetchall()
    return "\n".join(str(row[-1]) for row in rows)


def timed(con: duckdb.DuckDBPyConnection, query: str) -> tuple[list[float], int]:
    times: list[float] = []
    answer = -1
    for _ in range(3):
        started = time.perf_counter_ns()
        answer = int(con.execute(query).fetchone()[0])
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        times.append(elapsed_ms)
    return times, answer


def sql_document() -> str:
    return f"""-- Laboratorio 16 — Jerarquías en acción
-- Motor: DuckDB 2.0.0
-- Fecha de ejecución: {TODAY}
-- Concepto de condición: Type 2 diabetes mellitus (concept_id={SEED})
-- Todas las relaciones se filtran por vigencia y las recursivas tienen freno.

-- ============================================================================
-- ACTIVIDAD 1. Subir desde T2DM hasta la raíz con WITH RECURSIVE.
-- Hallazgo: se alcanzan dos ramas clínicas y una profundidad máxima de 7.
-- IMPORTANTE: solo se recorre 'Is a'; incluir 'Subsumes' crearía ciclos.
-- ============================================================================
WITH RECURSIVE camino AS (
    SELECT c.concept_id,
           c.concept_name,
           0 AS nivel,
           [c.concept_id]::BIGINT[] AS visitados,
           c.concept_name::VARCHAR AS camino_nombres
    FROM cdm.concept c
    WHERE c.concept_id = {SEED}

    UNION ALL

    SELECT padre.concept_id,
           padre.concept_name,
           camino.nivel + 1,
           list_append(camino.visitados, padre.concept_id),
           camino.camino_nombres || ' -> ' || padre.concept_name
    FROM camino
    JOIN cdm.concept_relationship cr
      ON cr.concept_id_1 = camino.concept_id
     AND cr.relationship_id = 'Is a'
     AND cr.invalid_reason IS NULL
    JOIN cdm.concept padre
      ON padre.concept_id = cr.concept_id_2
    WHERE camino.nivel < 20
      AND NOT list_contains(camino.visitados, padre.concept_id)
)
SELECT concept_id, concept_name, nivel, camino_nombres
FROM camino
ORDER BY nivel, concept_id;

-- ============================================================================
-- ACTIVIDAD 2. Ancestros del mismo concepto con CONCEPT_ANCESTOR.
-- Hallazgo: devuelve ocho ancestros clínicos; la recursiva añade la raíz técnica
-- no estándar 'SNOMED CT Concept' (4008453). Por ello los conjuntos no son
-- idénticos, aunque coinciden en todos los ancestros clínicos utilizables.
-- ============================================================================
SELECT a.concept_id,
       a.concept_name,
       ca.min_levels_of_separation,
       ca.max_levels_of_separation
FROM cdm.concept_ancestor ca
JOIN cdm.concept a
  ON a.concept_id = ca.ancestor_concept_id
WHERE ca.descendant_concept_id = {SEED}
  AND ca.min_levels_of_separation > 0
ORDER BY ca.min_levels_of_separation, a.concept_id;

-- ============================================================================
-- ACTIVIDAD 3. Metadatos de relaciones y relaciones salientes de lisinopril.
-- Hallazgo: is_hierarchical y defines_ancestry no representan el mismo conjunto.
-- ============================================================================
SELECT COUNT(*) AS tipos_relacion,
       COUNT(*) FILTER (WHERE is_hierarchical = '1') AS jerarquicas,
       COUNT(*) FILTER (WHERE defines_ancestry = '1') AS definen_ancestria,
       COUNT(*) FILTER (
           WHERE is_hierarchical = '1' AND defines_ancestry = '1'
       ) AS ambas
FROM cdm.relationship;

SELECT cr.relationship_id,
       r.relationship_name,
       r.is_hierarchical,
       r.defines_ancestry,
       destino.concept_id AS target_concept_id,
       destino.concept_name AS target_concept_name,
       destino.vocabulary_id,
       destino.concept_class_id
FROM cdm.concept_relationship cr
JOIN cdm.relationship r USING (relationship_id)
JOIN cdm.concept destino ON destino.concept_id = cr.concept_id_2
WHERE cr.concept_id_1 = {LISINOPRIL}
  AND cr.invalid_reason IS NULL
ORDER BY cr.relationship_id, destino.concept_name;

-- ============================================================================
-- ACTIVIDAD 4. Detectar poli-jerarquía y reconstruir caminos.
-- Caso real: Gingivitis (4281516) tiene 13 caminos válidos hasta Disease
-- (4274025), con longitudes de 4 a 8 aristas.
-- ============================================================================
WITH RECURSIVE rutas AS (
    SELECT c.concept_id,
           [c.concept_id]::BIGINT[] AS visitados,
           c.concept_name::VARCHAR AS camino_nombres,
           0 AS nivel
    FROM cdm.concept c
    WHERE c.concept_id = 4281516

    UNION ALL

    SELECT padre.concept_id,
           list_append(rutas.visitados, padre.concept_id),
           rutas.camino_nombres || ' -> ' || padre.concept_name,
           rutas.nivel + 1
    FROM rutas
    JOIN cdm.concept_relationship cr
      ON cr.concept_id_1 = rutas.concept_id
     AND cr.relationship_id = 'Is a'
     AND cr.invalid_reason IS NULL
    JOIN cdm.concept padre ON padre.concept_id = cr.concept_id_2
    WHERE rutas.nivel < 20
      AND NOT list_contains(rutas.visitados, padre.concept_id)
)
SELECT nivel AS longitud, camino_nombres
FROM rutas
WHERE concept_id = 4274025
ORDER BY longitud, camino_nombres;

-- ============================================================================
-- ACTIVIDAD 5. Daño de contar un JOIN con dos ramas que se traslapan.
-- A cuenta filas multiplicadas; B cuenta conceptos; C cuenta pacientes.
-- Solo C responde cuántos pacientes tienen la condición.
-- ============================================================================
WITH raices AS (
    SELECT * FROM (VALUES
        ({HF_BROAD}::BIGINT, 'Heart failure'),
        ({HF_INNER}::BIGINT, 'Chronic congestive heart failure')
    ) AS t(root_concept_id, rama)
), miembros AS (
    SELECT r.rama,
           r.root_concept_id,
           ca.descendant_concept_id AS concept_id
    FROM raices r
    JOIN cdm.concept_ancestor ca
      ON ca.ancestor_concept_id = r.root_concept_id
    UNION ALL
    SELECT rama, root_concept_id, root_concept_id FROM raices
), unidos AS (
    SELECT m.rama, co.condition_concept_id, co.person_id,
           co.condition_occurrence_id
    FROM cdm.condition_occurrence co
    JOIN miembros m ON m.concept_id = co.condition_concept_id
)
SELECT COUNT(*) AS A_filas_del_join,
       COUNT(DISTINCT condition_concept_id) AS B_conceptos,
       COUNT(DISTINCT person_id) AS C_pacientes
FROM unidos;

-- ============================================================================
-- ACTIVIDAD 6. ¿Por qué entró este paciente?
-- Consulta parametrizable: sustituya 1456 por cualquier person_id.
-- Traza evento, código fuente, estándar y rama del concept set de T2DM.
-- ============================================================================
WITH parametros AS (
    SELECT 1456::BIGINT AS person_id
), miembros AS (
    SELECT DISTINCT concept_id, concept_name
    FROM results.lab14_concept_set_membership
    WHERE version = 'C_razonada'
)
SELECT co.person_id,
       co.condition_occurrence_id AS evento_id,
       co.condition_start_date AS fecha_evento,
       co.condition_source_value,
       co.condition_source_concept_id,
       fuente.concept_name AS source_concept_name,
       co.condition_concept_id AS standard_concept_id,
       estandar.concept_name AS standard_concept_name,
       m.concept_id AS concept_set_ancestor_id,
       m.concept_name AS concept_set_ancestor_name,
       CASE
           WHEN co.condition_concept_id = m.concept_id THEN 'inclusión directa'
           ELSE 'descendiente de la rama T2DM'
       END AS por_que_rama
FROM parametros p
JOIN cdm.condition_occurrence co ON co.person_id = p.person_id
LEFT JOIN cdm.concept fuente
  ON fuente.concept_id = co.condition_source_concept_id
JOIN cdm.concept estandar
  ON estandar.concept_id = co.condition_concept_id
JOIN miembros m
  ON m.concept_id = co.condition_concept_id
  OR EXISTS (
      SELECT 1
      FROM cdm.concept_ancestor ca
      WHERE ca.ancestor_concept_id = m.concept_id
        AND ca.descendant_concept_id = co.condition_concept_id
  )
ORDER BY fecha_evento, evento_id, concept_set_ancestor_id;

-- ============================================================================
-- ACTIVIDAD 7. Cazar conceptos muertos y buscar reemplazos.
-- Hallazgo: la versión C del laboratorio 14 tiene 0 conceptos D/U; actualizarla
-- no gana ni pierde pacientes (457 antes y 457 después).
-- ============================================================================
SELECT m.concept_id,
       m.concept_name,
       c.invalid_reason,
       reemplazo.concept_id AS replacement_concept_id,
       reemplazo.concept_name AS replacement_concept_name
FROM results.lab14_concept_set_membership m
JOIN cdm.concept c ON c.concept_id = m.concept_id
LEFT JOIN cdm.concept_relationship cr
  ON cr.concept_id_1 = c.concept_id
 AND cr.relationship_id = 'Concept replaced by'
 AND cr.invalid_reason IS NULL
LEFT JOIN cdm.concept reemplazo ON reemplazo.concept_id = cr.concept_id_2
WHERE m.version = 'C_razonada'
  AND c.invalid_reason IN ('D', 'U')
ORDER BY m.concept_id;

-- ============================================================================
-- ACTIVIDAD 8. Dos formas de contar la misma cohorte.
-- Ejecutar EXPLAIN ANALYZE en cada SELECT; tiempos.md reporta tres corridas.
-- ============================================================================
EXPLAIN ANALYZE
SELECT COUNT(DISTINCT person_id)
FROM cdm.condition_occurrence
WHERE condition_concept_id IN (
    SELECT descendant_concept_id
    FROM cdm.concept_ancestor
    WHERE ancestor_concept_id = {SEED}
    UNION SELECT {SEED}
);

CREATE SCHEMA IF NOT EXISTS results;
CREATE OR REPLACE TABLE results.lab16_t2dm_concept_set AS
SELECT DISTINCT descendant_concept_id AS concept_id
FROM cdm.concept_ancestor
WHERE ancestor_concept_id = {SEED}
UNION SELECT {SEED};

CREATE INDEX IF NOT EXISTS idx_lab16_t2dm_concept
ON results.lab16_t2dm_concept_set(concept_id);

EXPLAIN ANALYZE
SELECT COUNT(DISTINCT co.person_id)
FROM cdm.condition_occurrence co
JOIN results.lab16_t2dm_concept_set cs
  ON cs.concept_id = co.condition_concept_id;
"""


def patient_trace(con: duckdb.DuckDBPyConnection, person_id: int) -> pd.DataFrame:
    return con.execute(
        """
        WITH members AS (
            SELECT DISTINCT concept_id, concept_name
            FROM results.lab14_concept_set_membership
            WHERE version='C_razonada'
        )
        SELECT co.person_id,
               co.condition_occurrence_id event_id,
               co.condition_start_date event_date,
               co.condition_source_value,
               co.condition_source_concept_id,
               source.concept_name source_concept_name,
               co.condition_concept_id standard_concept_id,
               standard.concept_name standard_concept_name,
               m.concept_id concept_set_ancestor_id,
               m.concept_name concept_set_ancestor_name,
               CASE WHEN co.condition_concept_id=m.concept_id
                    THEN 'inclusión directa'
                    ELSE 'descendiente de la rama T2DM' END why_branch
        FROM cdm.condition_occurrence co
        LEFT JOIN cdm.concept source
          ON source.concept_id=co.condition_source_concept_id
        JOIN cdm.concept standard
          ON standard.concept_id=co.condition_concept_id
        JOIN members m
          ON m.concept_id=co.condition_concept_id
          OR EXISTS (
              SELECT 1 FROM cdm.concept_ancestor ca
              WHERE ca.ancestor_concept_id=m.concept_id
                AND ca.descendant_concept_id=co.condition_concept_id
          )
        WHERE co.person_id=?
        ORDER BY event_date,event_id,concept_set_ancestor_id
        """,
        [person_id],
    ).df()


def main() -> None:
    if not DB.exists():
        raise SystemExit(f"ERROR: no existe la base OMOP: {DB}")
    ANALYSIS.mkdir(parents=True, exist_ok=True)

    recursive = read_audit("01_t2dm_recursiva.csv")
    ancestors = read_audit("02_t2dm_concept_ancestor.csv")
    comparison = read_audit("03_comparacion_ancestros.csv")
    rel_summary = read_audit("04_relationship_resumen.csv")
    lisinopril_types = read_audit("07_lisinopril_tipos_relacion.csv")
    poly_candidates = read_audit("08_polijerarquia_candidatos.csv")
    poly_paths = read_audit("09_polijerarquia_caminos.csv")
    hf_counts = read_audit("12_heart_failure_conteos.csv")
    dead = read_audit("14_conceptos_retirados.csv")
    dead_effect = read_audit("15_conceptos_retirados_efecto.csv")

    shutil.copy2(AUDIT / "01_t2dm_recursiva.csv", ANALYSIS / "01_camino_recursivo.csv")
    shutil.copy2(AUDIT / "02_t2dm_concept_ancestor.csv", ANALYSIS / "02_ancestros_precomputados.csv")
    shutil.copy2(AUDIT / "03_comparacion_ancestros.csv", ANALYSIS / "03_comparacion_ancestros.csv")
    shutil.copy2(AUDIT / "04_relationship_resumen.csv", ANALYSIS / "04_relationship_resumen.csv")
    shutil.copy2(AUDIT / "07_lisinopril_tipos_relacion.csv", ANALYSIS / "05_lisinopril_tipos_relacion.csv")
    shutil.copy2(AUDIT / "08_polijerarquia_candidatos.csv", ANALYSIS / "06_polijerarquia_candidatos.csv")
    shutil.copy2(AUDIT / "09_polijerarquia_caminos.csv", ANALYSIS / "07_polijerarquia_caminos.csv")
    shutil.copy2(AUDIT / "12_heart_failure_conteos.csv", ANALYSIS / "08_conteos_solapamiento.csv")
    shutil.copy2(AUDIT / "14_conceptos_retirados.csv", ANALYSIS / "11_conceptos_retirados.csv")
    shutil.copy2(AUDIT / "15_conceptos_retirados_efecto.csv", ANALYSIS / "12_conceptos_retirados_efecto.csv")

    con = duckdb.connect(str(DB))
    try:
        con.execute("CREATE SCHEMA IF NOT EXISTS results")
        con.execute("DROP TABLE IF EXISTS results.lab16_t2dm_concept_set")
        con.execute(
            f"""
            CREATE TABLE results.lab16_t2dm_concept_set AS
            SELECT DISTINCT descendant_concept_id concept_id
            FROM cdm.concept_ancestor
            WHERE ancestor_concept_id={SEED}
            UNION SELECT {SEED}
            """
        )
        con.execute(
            "CREATE INDEX idx_lab16_t2dm_concept "
            "ON results.lab16_t2dm_concept_set(concept_id)"
        )

        root_meta = con.execute(
            """
            SELECT concept_id,concept_name,domain_id,vocabulary_id,
                   concept_class_id,standard_concept,invalid_reason
            FROM cdm.concept WHERE concept_id=4008453
            """
        ).df()
        save(root_meta, "03b_raiz_tecnica_snomed.csv")

        explanations = pd.DataFrame(
            [
                ["RxNorm ing of", "Conecta el ingrediente con productos y formas que lo contienen; sí define ancestría."],
                ["Has brand name", "Relaciona el ingrediente con nombres comerciales; es jerárquica en metadatos, pero no define CONCEPT_ANCESTOR."],
                ["Mapped from", "Muestra conceptos no estándar que se normalizan hacia lisinopril en sentido inverso a Maps to."],
                ["RxNorm - ATC pr lat", "Enlace lateral primario entre RxNorm y una clase o combinación ATC; no es una relación de descendencia."],
                ["Has form", "Vincula el ingrediente general con una forma precisa, como lisinopril anhidro."],
            ],
            columns=["relationship_id", "explicacion"],
        )
        save(explanations, "05b_cinco_relaciones_explicadas.csv")

        chosen_paths = pd.concat(
            [
                poly_paths.iloc[[0]],
                poly_paths[poly_paths.camino_nombres.str.contains("digestive", case=False)].iloc[[0]],
            ],
            ignore_index=True,
        )
        chosen_paths.insert(0, "ruta_representativa", ["cabeza_mandíbula", "sistema_digestivo"])
        save(chosen_paths, "07b_dos_caminos_representativos.csv")

        patient_ids = [1456, 1112, 635]
        traces = []
        for pid in patient_ids:
            current = patient_trace(con, pid)
            current.insert(
                0,
                "criterio_seleccion",
                "selección independiente de apoyo" if pid == 635 else "muestra reproducible con semilla fija",
            )
            traces.append(current)
        trace = pd.concat(traces, ignore_index=True)
        save(trace, "09_trazabilidad_tres_pacientes.csv")

        q_subquery = f"""
            SELECT COUNT(DISTINCT person_id)
            FROM cdm.condition_occurrence
            WHERE condition_concept_id IN (
                SELECT descendant_concept_id FROM cdm.concept_ancestor
                WHERE ancestor_concept_id={SEED}
                UNION SELECT {SEED}
            )
        """
        q_materialized = """
            SELECT COUNT(DISTINCT co.person_id)
            FROM cdm.condition_occurrence co
            JOIN results.lab16_t2dm_concept_set cs
              ON cs.concept_id=co.condition_concept_id
        """

        times_sub, answer_sub = timed(con, q_subquery)
        times_mat, answer_mat = timed(con, q_materialized)
        if answer_sub != answer_mat:
            raise RuntimeError("Las consultas de rendimiento no devuelven la misma cohorte")

        performance = pd.DataFrame(
            [
                ["IN + CONCEPT_ANCESTOR", *times_sub, statistics.median(times_sub), answer_sub],
                ["JOIN + concept set materializado", *times_mat, statistics.median(times_mat), answer_mat],
            ],
            columns=["version", "corrida_1_ms", "corrida_2_ms", "corrida_3_ms", "mediana_ms", "pacientes"],
        )
        save(performance, "13_rendimiento_tres_corridas.csv")
        plan_sub = explain(con, q_subquery)
        plan_mat = explain(con, q_materialized)
        (ANALYSIS / "14_plan_subconsulta.txt").write_text(plan_sub + "\n", encoding="utf-8")
        (ANALYSIS / "15_plan_materializado.txt").write_text(plan_mat + "\n", encoding="utf-8")

        vocab = con.execute(
            """
            SELECT vocabulary_id,vocabulary_version,vocabulary_reference
            FROM cdm.vocabulary
            WHERE vocabulary_id IN ('SNOMED','RxNorm')
            ORDER BY vocabulary_id
            """
        ).df()
        save(vocab, "00_version_vocabularios.csv")
    finally:
        con.close()

    (LAB / "jerarquias.sql").write_text(sql_document(), encoding="utf-8")

    med_sub = float(performance.loc[0, "mediana_ms"])
    med_mat = float(performance.loc[1, "mediana_ms"])
    delta = med_mat - med_sub
    verdict = (
        "No se observó una mejora material a esta escala; la diferencia está en el ruido de ejecución."
        if abs(delta) < max(0.25, med_sub * 0.20)
        else (
            "La versión materializada fue más rápida en esta base."
            if delta < 0
            else "La subconsulta fue más rápida en esta base pequeña."
        )
    )

    times_md = f"""# Rendimiento de consultas jerárquicas

Motor: **DuckDB 2.0.0**. Fecha: **{TODAY}**. Cada consulta se ejecutó tres veces
en la misma conexión y se reportó la mediana. Ambas devolvieron **{answer_sub} pacientes**.

{md_table(performance.round(4))}

## Interpretación

{verdict} La consulta con `IN` expande `CONCEPT_ANCESTOR` durante la ejecución;
la segunda lee una tabla pequeña ya materializada y realiza un `HASH_JOIN` con
`CONDITION_OCCURRENCE`. DuckDB puede optimizar ambas como operaciones vectorizadas,
por lo que una base sintética de este tamaño no garantiza una diferencia relevante.

## Plan 1 — subconsulta sobre CONCEPT_ANCESTOR

```text
{plan_sub}
```

## Plan 2 — concept set materializado e índice

```text
{plan_mat}
```
"""
    (LAB / "tiempos.md").write_text(times_md, encoding="utf-8")

    first_path = chosen_paths.iloc[0].camino_nombres
    second_path = chosen_paths.iloc[1].camino_nombres
    hallazgos = f"""# Hallazgos de jerarquías OMOP

## 1. Recursiva frente a CONCEPT_ANCESTOR

La recursiva de `Type 2 diabetes mellitus` encontró **9 ancestros distintos** y
`CONCEPT_ANCESTOR` encontró **8**. Coinciden en los ocho ancestros clínicos. La
diferencia es `SNOMED CT Concept` (`4008453`), raíz técnica no estándar alcanzada
por las aristas `Is a`, pero omitida de la clausura clínica precomputada.

## 2. RELATIONSHIP

{md_table(rel_summary)}

Los conjuntos no coinciden: una relación puede describirse como jerárquica para
navegación sin participar en la construcción de `CONCEPT_ANCESTOR`, y algunas
relaciones de ancestría se usan para normalización entre vocabularios aunque no
se marquen como jerárquicas.

### Cinco relaciones de lisinopril

{md_table(explanations)}

## 3. Caso real de poli-jerarquía

El par seleccionado fue `Disease` (`4274025`) ← `Gingivitis` (`4281516`).
`CONCEPT_ANCESTOR` reporta una distancia mínima de 4 y máxima de 8; la recursiva
reconstruyó **13 caminos**. Dos rutas representativas son:

1. {first_path}
2. {second_path}

Clínicamente tiene sentido: la gingivitis es simultáneamente una inflamación de
tejidos de la cabeza/mandíbula y una enfermedad de la cavidad oral, que SNOMED
también organiza dentro del tracto digestivo. No son duplicados erróneos, sino
clasificaciones válidas desde perspectivas anatómicas y patológicas diferentes.

## 4. Daño del solapamiento

{md_table(hf_counts)}

Las ramas `Heart failure` y `Chronic congestive heart failure` se solapan. El
`COUNT(*)` cuenta nuevamente los eventos que pertenecen a ambas ramas; el conteo
de conceptos responde cuántos diagnósticos estándar distintos aparecen, y solo
`COUNT(DISTINCT person_id)` responde cuántos pacientes tienen la condición.

## 5. Conceptos retirados

{md_table(dead_effect)}

El concept set razonado de diabetes tipo 2 no contiene conceptos `D` ni `U`.
Por ello no hay reemplazos que aplicar y el número permanece en 457 pacientes.
La consulta queda generalizada en `jerarquias.sql` para detectar cambios en una
futura versión del vocabulario.

## 6. Trazabilidad de pacientes

Se documentaron los pacientes `1456`, `1112` y `635`. El tercero fue escogido
mediante una selección independiente del flujo principal. En esta base los tres
entran directamente por `Type 2 diabetes mellitus`; la consulta parametrizable
también funciona si un evento entra por un descendiente del concept set.
"""
    (LAB / "hallazgos.md").write_text(hallazgos, encoding="utf-8")

    readme = f"""# Laboratorio 16 — Jerarquías en acción

## Propósito

Explicar cómo se construyen y recorren las jerarquías OMOP, demostrar un caso
real de poli-jerarquía, trazar por qué un paciente entra a una cohorte y comparar
el rendimiento de una expansión dinámica frente a un concept set materializado.

## Entregables

- `jerarquias.sql`: las ocho actividades, comentadas y reproducibles.
- `hallazgos.md`: comparación de representaciones, poli-jerarquía, solapamiento,
  trazabilidad y auditoría de conceptos retirados.
- `tiempos.md`: tres corridas por versión, medianas y planes `EXPLAIN ANALYZE`.
- `evidencias/analisis/`: resultados tabulares y planes completos.
- `scripts/`: auditoría y generación reproducible.

## Decisiones principales

- Condición principal: diabetes mellitus tipo 2 (`{SEED}`).
- Poli-jerarquía: gingivitis hacia `Disease` mediante 13 caminos.
- Solapamiento deliberado: `Heart failure` y `Chronic congestive heart failure`.
- Motor de rendimiento: DuckDB 2.0.0.
- Los conceptos clínicos locales permanecen en la base ignorada por Git.

## Reproducibilidad

```bash
python lab16/scripts/00_auditar_lab16.py
python lab16/scripts/01_generar_lab16.py
```

Los scripts no ejecutan `git commit` ni `git push`.
"""
    (LAB / "README.md").write_text(readme, encoding="utf-8")

    print("\n===== LABORATORIO 16 GENERADO =====")
    print("Recursiva y CONCEPT_ANCESTOR idénticos:", bool(comparison.iloc[0].conjuntos_identicos))
    print("Caminos de poli-jerarquía:", len(poly_paths))
    print("Pacientes por ramas solapadas:", int(hf_counts.iloc[0].conteo_C_pacientes))
    print("Conceptos retirados:", len(dead))
    print("Mediana subconsulta (ms):", round(med_sub, 4))
    print("Mediana materializada (ms):", round(med_mat, 4))
    print("Commit y push: NO ejecutados")


if __name__ == "__main__":
    main()
