-- Laboratorio 16 — Jerarquías en acción
-- Motor: DuckDB 2.0.0
-- Fecha de ejecución: 2026-11-22
-- Concepto de condición: Type 2 diabetes mellitus (concept_id=201826)
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
    WHERE c.concept_id = 201826

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
WHERE ca.descendant_concept_id = 201826
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
WHERE cr.concept_id_1 = 1308216
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
        (316139::BIGINT, 'Heart failure'),
        (4229440::BIGINT, 'Chronic congestive heart failure')
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
    WHERE ancestor_concept_id = 201826
    UNION SELECT 201826
);

CREATE SCHEMA IF NOT EXISTS results;
CREATE OR REPLACE TABLE results.lab16_t2dm_concept_set AS
SELECT DISTINCT descendant_concept_id AS concept_id
FROM cdm.concept_ancestor
WHERE ancestor_concept_id = 201826
UNION SELECT 201826;

CREATE INDEX IF NOT EXISTS idx_lab16_t2dm_concept
ON results.lab16_t2dm_concept_set(concept_id);

EXPLAIN ANALYZE
SELECT COUNT(DISTINCT co.person_id)
FROM cdm.condition_occurrence co
JOIN results.lab16_t2dm_concept_set cs
  ON cs.concept_id = co.condition_concept_id;
