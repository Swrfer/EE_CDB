-- Laboratorio 14: construir y defender un concept set de diabetes tipo 2
-- OMOP CDM 5.4 / DuckDB. Ejecutable de principio a fin.

CREATE SCHEMA IF NOT EXISTS results;

-- 1-2. Concepto semilla estándar, vigente y del dominio Condition.
SELECT concept_id, concept_name, domain_id, vocabulary_id,
       concept_class_id, standard_concept, concept_code,
       valid_start_date, valid_end_date, invalid_reason
FROM cdm.concept
WHERE concept_id = 201826;

-- Padre inmediato.
SELECT parent.concept_id, parent.concept_name, parent.domain_id,
       parent.vocabulary_id, parent.standard_concept
FROM cdm.concept_ancestor ca
JOIN cdm.concept parent ON parent.concept_id = ca.ancestor_concept_id
WHERE ca.descendant_concept_id = 201826
  AND ca.min_levels_of_separation = 1
  AND parent.invalid_reason IS NULL;

-- 3. Traducción ICD-10-CM -> conceptos estándar mediante Maps to.
-- Filtros: dirección correcta, destino estándar, vigencia de conceptos y
-- vigencia de la relación. No se presupone una relación 1:1.
CREATE OR REPLACE TABLE results.lab14_icd10_mapping AS
WITH requested(code) AS (
    VALUES
    ('E11.9'),
    ('E11.65'),
    ('E11.22'),
    ('E11.21'),
    ('E11.40'),
    ('E11.42'),
    ('E11.319'),
    ('E11.3299'),
    ('E11.51'),
    ('E11.621'),
    ('E11.649'),
    ('E11.10')
)
SELECT r.code AS codigo_icd10,
       src.concept_id AS concept_id_origen,
       src.concept_name AS nombre_origen,
       tgt.concept_id AS concept_id_estandar,
       tgt.concept_name AS nombre_estandar,
       tgt.domain_id AS dominio_estandar,
       tgt.vocabulary_id AS vocabulario_estandar,
       tgt.standard_concept,
       cr.relationship_id
FROM requested r
LEFT JOIN cdm.concept src
  ON src.concept_code = r.code
 AND src.vocabulary_id = 'ICD10CM'
 AND src.invalid_reason IS NULL
 AND CURRENT_DATE BETWEEN src.valid_start_date AND src.valid_end_date
LEFT JOIN cdm.concept_relationship cr
  ON cr.concept_id_1 = src.concept_id
 AND cr.relationship_id = 'Maps to'
 AND cr.invalid_reason IS NULL
 AND CURRENT_DATE BETWEEN cr.valid_start_date AND cr.valid_end_date
LEFT JOIN cdm.concept tgt
  ON tgt.concept_id = cr.concept_id_2
 AND tgt.standard_concept = 'S'
 AND tgt.invalid_reason IS NULL
 AND CURRENT_DATE BETWEEN tgt.valid_start_date AND tgt.valid_end_date
ORDER BY r.code, tgt.concept_id;

-- 4. Tres versiones reproducibles. La versión C excluye ramas clínicas,
-- no una lista arbitraria de todos los conceptos finales.
CREATE OR REPLACE TABLE results.lab14_concept_set_membership AS
WITH
broad AS (
    SELECT DISTINCT c.concept_id, c.concept_name
    FROM cdm.concept_ancestor ca
    JOIN cdm.concept c ON c.concept_id = ca.descendant_concept_id
    WHERE ca.ancestor_concept_id = 201826
      AND c.domain_id = 'Condition'
      AND c.standard_concept = 'S'
      AND c.invalid_reason IS NULL
      AND CURRENT_DATE BETWEEN c.valid_start_date AND c.valid_end_date
),
exclusion_roots(concept_id, motivo) AS (
    VALUES
      (4129519, 'Contexto obstétrico: embarazo y diabetes tipo 2'),
      (45766052, 'Diabetes tipo 2 en remisión, no enfermedad activa')
),
excluded AS (
    SELECT DISTINCT ca.descendant_concept_id AS concept_id
    FROM exclusion_roots er
    JOIN cdm.concept_ancestor ca ON ca.ancestor_concept_id = er.concept_id
)
SELECT 'A_estricta' AS version, c.concept_id, c.concept_name,
       'Concepto semilla' AS criterio
FROM cdm.concept c
WHERE c.concept_id = 201826
UNION ALL
SELECT 'B_amplia', b.concept_id, b.concept_name,
       'Semilla o descendiente estándar vigente'
FROM broad b
UNION ALL
SELECT 'C_razonada', b.concept_id, b.concept_name,
       'Versión amplia menos embarazo y remisión'
FROM broad b
WHERE NOT EXISTS (
    SELECT 1 FROM excluded e WHERE e.concept_id = b.concept_id
);

-- 5. Impacto en pacientes distintos; no se cuentan consultas repetidas.
CREATE OR REPLACE TABLE results.lab14_impact AS
SELECT m.version,
       COUNT(DISTINCT m.concept_id) AS conceptos,
       COUNT(DISTINCT co.person_id) AS pacientes_distintos,
       COUNT(co.condition_occurrence_id) AS eventos
FROM results.lab14_concept_set_membership m
LEFT JOIN cdm.condition_occurrence co
  ON co.condition_concept_id = m.concept_id
GROUP BY m.version
ORDER BY m.version;

SELECT * FROM results.lab14_icd10_mapping;
SELECT * FROM results.lab14_concept_set_membership ORDER BY version, concept_name;
SELECT * FROM results.lab14_impact ORDER BY version;
