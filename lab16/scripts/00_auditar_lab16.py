#!/usr/bin/env python3
"""Auditoría previa para el Laboratorio 16 de jerarquías OMOP."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


ROOT = Path.cwd()
DB = ROOT / "lab12/data/omop/synthea_omop_cdm54.duckdb"
OUT = ROOT / "lab16/evidencias/auditoria"
T2DM = 201826
LISINOPRIL = 1308216


def section(title: str) -> None:
    print(f"\n===== {title} =====")


def save_show(df: pd.DataFrame, filename: str, limit: int = 100) -> None:
    path = OUT / filename
    df.to_csv(path, index=False)
    if df.empty:
        print("SIN FILAS")
    else:
        print(df.head(limit).to_string(index=False))
    if len(df) > limit:
        print(f"... {len(df)-limit} filas adicionales en {path}")
    print(f"Guardado: {path} ({len(df)} filas)")


def main() -> None:
    if not DB.exists():
        raise SystemExit(f"ERROR: no existe {DB}")
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB), read_only=True)
    try:
        section("TABLAS REQUERIDAS")
        tables = con.execute("""
            SELECT lower(table_name) table_name,
                   estimated_size AS filas_estimadas
            FROM duckdb_tables()
            WHERE schema_name = 'cdm'
              AND lower(table_name) IN ('concept','concept_relationship','concept_ancestor','relationship')
            ORDER BY table_name
        """).df()
        save_show(tables, "00_tablas_requeridas.csv")
        if set(tables.table_name) != {"concept", "concept_relationship", "concept_ancestor", "relationship"}:
            raise RuntimeError("Falta alguna tabla requerida.")

        section("RECORRIDO RECURSIVO HACIA ARRIBA: T2DM")
        recursive = con.execute(f"""
            WITH RECURSIVE walk AS (
                SELECT c.concept_id, c.concept_name,
                       0 AS nivel,
                       [c.concept_id]::BIGINT[] AS path_ids,
                       [c.concept_name]::VARCHAR[] AS path_names
                FROM cdm.concept c
                WHERE c.concept_id = {T2DM}
                UNION ALL
                SELECT parent.concept_id, parent.concept_name,
                       w.nivel + 1,
                       list_append(w.path_ids, parent.concept_id),
                       list_append(w.path_names, parent.concept_name)
                FROM walk w
                JOIN cdm.concept_relationship cr
                  ON cr.concept_id_1 = w.concept_id
                 AND cr.relationship_id = 'Is a'
                 AND cr.invalid_reason IS NULL
                JOIN cdm.concept parent ON parent.concept_id = cr.concept_id_2
                WHERE w.nivel < 20
                  AND parent.invalid_reason IS NULL
                  AND NOT list_contains(w.path_ids, parent.concept_id)
            )
            SELECT concept_id, concept_name, nivel,
                   array_to_string(path_ids, ' -> ') AS camino_ids,
                   array_to_string(path_names, ' -> ') AS camino_nombres
            FROM walk
            ORDER BY nivel, concept_name, camino_ids
        """).df()
        save_show(recursive, "01_t2dm_recursiva.csv", limit=200)
        print("Profundidad máxima:", int(recursive.nivel.max()))

        section("ANCESTROS T2DM MEDIANTE CONCEPT_ANCESTOR")
        ancestors = con.execute(f"""
            SELECT a.concept_id, a.concept_name,
                   ca.min_levels_of_separation,
                   ca.max_levels_of_separation
            FROM cdm.concept_ancestor ca
            JOIN cdm.concept a ON a.concept_id = ca.ancestor_concept_id
            WHERE ca.descendant_concept_id = {T2DM}
              AND ca.ancestor_concept_id <> {T2DM}
            ORDER BY ca.min_levels_of_separation, a.concept_name
        """).df()
        save_show(ancestors, "02_t2dm_concept_ancestor.csv", limit=200)
        recursive_set = set(recursive.loc[recursive.nivel > 0, "concept_id"].astype(int))
        ancestor_set = set(ancestors.concept_id.astype(int))
        comparison = pd.DataFrame([{
            "ancestros_recursiva": len(recursive_set),
            "ancestros_concept_ancestor": len(ancestor_set),
            "interseccion": len(recursive_set & ancestor_set),
            "solo_recursiva": len(recursive_set - ancestor_set),
            "solo_concept_ancestor": len(ancestor_set - recursive_set),
            "conjuntos_identicos": recursive_set == ancestor_set,
            "ids_solo_recursiva": "|".join(map(str, sorted(recursive_set - ancestor_set))),
            "ids_solo_concept_ancestor": "|".join(map(str, sorted(ancestor_set - recursive_set))),
        }])
        save_show(comparison, "03_comparacion_ancestros.csv")

        section("METADATOS DE RELATIONSHIP")
        relationship_summary = con.execute("""
            SELECT COUNT(*) tipos_relacion,
                   COUNT(*) FILTER (WHERE is_hierarchical = '1') jerarquicas,
                   COUNT(*) FILTER (WHERE defines_ancestry = '1') definen_ancestria,
                   COUNT(*) FILTER (WHERE is_hierarchical = '1' AND defines_ancestry = '1') ambas,
                   COUNT(*) FILTER (WHERE is_hierarchical = '1' AND defines_ancestry <> '1') solo_jerarquicas,
                   COUNT(*) FILTER (WHERE is_hierarchical <> '1' AND defines_ancestry = '1') solo_ancestria
            FROM cdm.relationship
        """).df()
        save_show(relationship_summary, "04_relationship_resumen.csv")
        relationship_diff = con.execute("""
            SELECT relationship_id, relationship_name,
                   is_hierarchical, defines_ancestry,
                   reverse_relationship_id
            FROM cdm.relationship
            WHERE is_hierarchical <> defines_ancestry
            ORDER BY defines_ancestry DESC, is_hierarchical DESC, relationship_id
        """).df()
        save_show(relationship_diff, "05_relationship_diferencias.csv", limit=200)

        section("RELACIONES QUE SALEN DE LISINOPRIL")
        drug_relations = con.execute(f"""
            SELECT cr.relationship_id, r.relationship_name,
                   r.is_hierarchical, r.defines_ancestry,
                   target.concept_id AS target_concept_id,
                   target.concept_name AS target_concept_name,
                   target.vocabulary_id AS target_vocabulary_id,
                   target.concept_class_id AS target_concept_class,
                   cr.invalid_reason
            FROM cdm.concept_relationship cr
            JOIN cdm.relationship r USING (relationship_id)
            JOIN cdm.concept target ON target.concept_id = cr.concept_id_2
            WHERE cr.concept_id_1 = {LISINOPRIL}
            ORDER BY cr.relationship_id, target.concept_name
        """).df()
        save_show(drug_relations, "06_lisinopril_relaciones_salientes.csv", limit=300)
        distinct_rel = (
            drug_relations.groupby(["relationship_id", "relationship_name", "is_hierarchical", "defines_ancestry"], dropna=False)
            .agg(destinos=("target_concept_id", "nunique"), ejemplo=("target_concept_name", "first"))
            .reset_index()
            .sort_values(["destinos", "relationship_id"], ascending=[False, True])
        )
        save_show(distinct_rel, "07_lisinopril_tipos_relacion.csv", limit=200)

        section("CANDIDATOS REALES DE POLI-JERARQUÍA")
        poly = con.execute("""
            SELECT ca.ancestor_concept_id, anc.concept_name ancestor_name,
                   ca.descendant_concept_id, des.concept_name descendant_name,
                   ca.min_levels_of_separation, ca.max_levels_of_separation,
                   COUNT(co.condition_occurrence_id) eventos,
                   COUNT(DISTINCT co.person_id) pacientes
            FROM cdm.concept_ancestor ca
            JOIN cdm.concept anc ON anc.concept_id = ca.ancestor_concept_id
            JOIN cdm.concept des ON des.concept_id = ca.descendant_concept_id
            LEFT JOIN cdm.condition_occurrence co
              ON co.condition_concept_id = ca.descendant_concept_id
            WHERE ca.min_levels_of_separation <> ca.max_levels_of_separation
              AND ca.min_levels_of_separation > 0
              AND ca.max_levels_of_separation <= 8
              AND anc.domain_id = 'Condition'
              AND des.domain_id = 'Condition'
              AND anc.standard_concept = 'S'
              AND des.standard_concept = 'S'
              AND anc.invalid_reason IS NULL
              AND des.invalid_reason IS NULL
            GROUP BY ca.ancestor_concept_id, anc.concept_name,
                     ca.descendant_concept_id, des.concept_name,
                     ca.min_levels_of_separation, ca.max_levels_of_separation
            HAVING COUNT(co.condition_occurrence_id) > 0
            ORDER BY pacientes DESC,
                     (ca.max_levels_of_separation-ca.min_levels_of_separation) DESC,
                     ca.max_levels_of_separation,
                     ca.ancestor_concept_id, ca.descendant_concept_id
            LIMIT 30
        """).df()
        save_show(poly, "08_polijerarquia_candidatos.csv", limit=100)
        if poly.empty:
            raise RuntimeError("No se encontró un caso de poli-jerarquía con eventos.")
        selected = poly.iloc[0]
        ancestor_id = int(selected.ancestor_concept_id)
        descendant_id = int(selected.descendant_concept_id)

        section("CAMINOS DEL CASO SELECCIONADO")
        paths = con.execute("""
            WITH RECURSIVE paths AS (
                SELECT c.concept_id AS current_id,
                       [c.concept_id]::BIGINT[] AS path_ids,
                       [c.concept_name]::VARCHAR[] AS path_names,
                       0 AS nivel
                FROM cdm.concept c
                WHERE c.concept_id = ?
                UNION ALL
                SELECT parent.concept_id,
                       list_append(p.path_ids, parent.concept_id),
                       list_append(p.path_names, parent.concept_name),
                       p.nivel + 1
                FROM paths p
                JOIN cdm.concept_relationship cr
                  ON cr.concept_id_1 = p.current_id
                 AND cr.relationship_id = 'Is a'
                 AND cr.invalid_reason IS NULL
                JOIN cdm.concept parent ON parent.concept_id = cr.concept_id_2
                WHERE p.nivel < 20
                  AND parent.invalid_reason IS NULL
                  AND NOT list_contains(p.path_ids, parent.concept_id)
            )
            SELECT row_number() OVER (ORDER BY nivel, array_to_string(path_ids,' -> ')) camino,
                   nivel AS longitud,
                   array_to_string(path_ids, ' -> ') camino_ids,
                   array_to_string(path_names, ' -> ') camino_nombres
            FROM paths
            WHERE current_id = ?
            ORDER BY longitud, camino_ids
        """, [descendant_id, ancestor_id]).df()
        save_show(paths, "09_polijerarquia_caminos.csv", limit=100)
        print("Par seleccionado:", ancestor_id, "<-", descendant_id)
        print("Caminos reconstruidos:", len(paths))

        section("CANDIDATOS DE INSUFICIENCIA CARDIACA")
        heart = con.execute("""
            SELECT c.concept_id, c.concept_name, c.concept_code,
                   COUNT(co.condition_occurrence_id) eventos,
                   COUNT(DISTINCT co.person_id) pacientes
            FROM cdm.concept c
            LEFT JOIN cdm.condition_occurrence co ON co.condition_concept_id=c.concept_id
            WHERE c.domain_id='Condition' AND c.vocabulary_id='SNOMED'
              AND c.standard_concept='S' AND c.invalid_reason IS NULL
              AND lower(c.concept_name) LIKE '%heart failure%'
            GROUP BY c.concept_id,c.concept_name,c.concept_code
            ORDER BY pacientes DESC,eventos DESC,c.concept_name
            LIMIT 50
        """).df()
        save_show(heart, "10_heart_failure_candidatos.csv", limit=100)

        hf_roots = con.execute("""
            WITH broad AS (
              SELECT concept_id,concept_name FROM cdm.concept
              WHERE domain_id='Condition' AND vocabulary_id='SNOMED'
                AND standard_concept='S' AND invalid_reason IS NULL
                AND lower(concept_name)='heart failure'
              LIMIT 1
            ), branch AS (
              SELECT d.concept_id,d.concept_name,
                     COUNT(DISTINCT co.person_id) pacientes,
                     COUNT(co.condition_occurrence_id) eventos
              FROM broad b
              JOIN cdm.concept_ancestor ca ON ca.ancestor_concept_id=b.concept_id
              JOIN cdm.concept d ON d.concept_id=ca.descendant_concept_id
              LEFT JOIN cdm.condition_occurrence co ON co.condition_concept_id=d.concept_id
              WHERE ca.descendant_concept_id<>b.concept_id
                AND d.standard_concept='S' AND d.invalid_reason IS NULL
              GROUP BY d.concept_id,d.concept_name
              HAVING COUNT(DISTINCT co.person_id)>0
              ORDER BY pacientes DESC,eventos DESC,d.concept_name
              LIMIT 1
            )
            SELECT 'rama_amplia' rama, concept_id,concept_name,NULL::BIGINT pacientes,NULL::BIGINT eventos FROM broad
            UNION ALL
            SELECT 'rama_interna',concept_id,concept_name,pacientes,eventos FROM branch
        """).df()
        save_show(hf_roots, "11_heart_failure_ramas.csv")
        if len(hf_roots) != 2:
            raise RuntimeError("No se pudieron elegir dos ramas traslapadas de insuficiencia cardiaca.")
        root1, root2 = hf_roots.concept_id.astype(int).tolist()
        damage = con.execute("""
            WITH roots(concept_id) AS (VALUES (?),(?)),
            expanded AS (
              SELECT r.concept_id root_id,ca.descendant_concept_id concept_id
              FROM roots r JOIN cdm.concept_ancestor ca ON ca.ancestor_concept_id=r.concept_id
            ), joined AS (
              SELECT e.root_id,e.concept_id,co.condition_occurrence_id,co.person_id
              FROM expanded e JOIN cdm.condition_occurrence co ON co.condition_concept_id=e.concept_id
            )
            SELECT COUNT(*) conteo_A_filas_join,
                   COUNT(DISTINCT concept_id) conteo_B_conceptos,
                   COUNT(DISTINCT person_id) conteo_C_pacientes,
                   COUNT(DISTINCT condition_occurrence_id) eventos_unicos,
                   COUNT(*)-COUNT(DISTINCT condition_occurrence_id) filas_duplicadas_por_solapamiento
            FROM joined
        """, [root1, root2]).df()
        save_show(damage, "12_heart_failure_conteos.csv")

        section("PACIENTES CANDIDATOS PARA DEPURACIÓN")
        patients = con.execute("""
            WITH set_c AS (
              SELECT DISTINCT concept_id FROM results.lab14_concept_set_membership
              WHERE version='C_razonada'
            )
            SELECT co.person_id,co.condition_occurrence_id,
                   co.condition_start_date,co.condition_source_value,
                   co.condition_source_concept_id,
                   src.concept_name source_concept_name,
                   co.condition_concept_id,std.concept_name standard_concept_name
            FROM cdm.condition_occurrence co
            JOIN set_c s ON s.concept_id=co.condition_concept_id
            LEFT JOIN cdm.concept src ON src.concept_id=co.condition_source_concept_id
            JOIN cdm.concept std ON std.concept_id=co.condition_concept_id
            QUALIFY row_number() OVER (PARTITION BY co.person_id ORDER BY co.condition_start_date,co.condition_occurrence_id)=1
            ORDER BY hash(CAST(co.person_id AS VARCHAR)||'lab16-externo')
            LIMIT 10
        """).df()
        save_show(patients, "13_pacientes_candidatos.csv")

        section("CONCEPTOS RETIRADOS EN EL CONCEPT SET FINAL")
        dead = con.execute("""
            SELECT DISTINCT m.concept_id,m.concept_name,c.invalid_reason,
                   replacement.concept_id replacement_concept_id,
                   replacement.concept_name replacement_concept_name
            FROM results.lab14_concept_set_membership m
            JOIN cdm.concept c ON c.concept_id=m.concept_id
            LEFT JOIN cdm.concept_relationship cr
              ON cr.concept_id_1=c.concept_id
             AND cr.relationship_id='Concept replaced by'
             AND cr.invalid_reason IS NULL
            LEFT JOIN cdm.concept replacement ON replacement.concept_id=cr.concept_id_2
            WHERE m.version='C_razonada' AND c.invalid_reason IN ('D','U')
            ORDER BY m.concept_id
        """).df()
        save_show(dead, "14_conceptos_retirados.csv")
        dead_effect = pd.DataFrame([{
            "conceptos_retirados": len(dead),
            "conceptos_D": int((dead.invalid_reason == "D").sum()) if not dead.empty else 0,
            "conceptos_U": int((dead.invalid_reason == "U").sum()) if not dead.empty else 0,
            "pacientes_antes": int(con.execute("SELECT COUNT(DISTINCT co.person_id) FROM cdm.condition_occurrence co JOIN results.lab14_concept_set_membership m ON m.concept_id=co.condition_concept_id AND m.version='C_razonada'").fetchone()[0]),
        }])
        dead_effect["pacientes_despues"] = dead_effect.pacientes_antes
        dead_effect["diferencia_pacientes"] = 0
        save_show(dead_effect, "15_conceptos_retirados_efecto.csv")

        section("RESUMEN")
        print("Recursiva y CONCEPT_ANCESTOR idénticos:", bool(comparison.iloc[0].conjuntos_identicos))
        print("Tipos de relación salientes de lisinopril:", len(distinct_rel))
        print("Caso poli-jerárquico:", selected.ancestor_name, "<-", selected.descendant_name)
        print("Caminos reconstruidos:", len(paths))
        print("Ramas de insuficiencia cardiaca:")
        print(hf_roots.to_string(index=False))
        print("Conceptos retirados:", len(dead))
        print("AUDITORÍA COMPLETADA")
    finally:
        con.close()


if __name__ == "__main__":
    main()
