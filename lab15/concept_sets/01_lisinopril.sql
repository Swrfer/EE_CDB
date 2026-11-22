-- Concept set: exposición a lisinopril
-- Vocabulario: RxNorm 20260601; consulta: 2026-11-22
-- Define tres versiones por jerarquía RxNorm, no por listas de productos.
-- A: monoterapia (un ingrediente); B: todos los descendientes;
-- C: B menos combinaciones con hidroclorotiazida, que puede modificar
--    independientemente volumen, creatinina y función renal.
-- Conteos validados tras filtrar conceptos estándar y vigentes:
-- A=53, B=77, C=53 conceptos de vocabulario.

CREATE SCHEMA IF NOT EXISTS results;

CREATE OR REPLACE TABLE results.lab15_lisinopril_sets AS
WITH ingredient AS (
    SELECT concept_id
    FROM cdm.concept
    WHERE vocabulary_id = 'RxNorm'
      AND concept_code = '29046'
      AND concept_class_id = 'Ingredient'
      AND standard_concept = 'S'
      AND invalid_reason IS NULL
),
descendants AS (
    SELECT DISTINCT ca.descendant_concept_id AS drug_concept_id
    FROM ingredient i
    JOIN cdm.concept_ancestor ca ON ca.ancestor_concept_id = i.concept_id
    JOIN cdm.concept d ON d.concept_id = ca.descendant_concept_id
    WHERE d.domain_id = 'Drug'
      AND d.standard_concept = 'S'
      AND d.invalid_reason IS NULL
),
ingredient_counts AS (
    SELECT d.drug_concept_id,
           COUNT(DISTINCT i.concept_id) AS numero_ingredientes,
           MAX(CASE WHEN lower(i.concept_name) = 'hydrochlorothiazide'
                    THEN 1 ELSE 0 END) AS tiene_hctz
    FROM descendants d
    JOIN cdm.concept_ancestor ca
      ON ca.descendant_concept_id = d.drug_concept_id
    JOIN cdm.concept i ON i.concept_id = ca.ancestor_concept_id
    WHERE i.domain_id = 'Drug'
      AND i.concept_class_id = 'Ingredient'
      AND i.standard_concept = 'S'
      AND i.invalid_reason IS NULL
    GROUP BY d.drug_concept_id
)
SELECT 'A_monoterapia' AS version, ic.drug_concept_id,
       c.concept_name, ic.numero_ingredientes,
       'Solo productos con un ingrediente' AS criterio
FROM ingredient_counts ic
JOIN cdm.concept c ON c.concept_id = ic.drug_concept_id
WHERE ic.numero_ingredientes = 1
UNION ALL
SELECT 'B_todo_lisinopril', ic.drug_concept_id,
       c.concept_name, ic.numero_ingredientes,
       'Todos los descendientes, combinaciones incluidas'
FROM ingredient_counts ic
JOIN cdm.concept c ON c.concept_id = ic.drug_concept_id
UNION ALL
SELECT 'C_sin_hctz', ic.drug_concept_id,
       c.concept_name, ic.numero_ingredientes,
       'Todos los descendientes excepto combinaciones con HCTZ'
FROM ingredient_counts ic
JOIN cdm.concept c ON c.concept_id = ic.drug_concept_id
WHERE ic.tiene_hctz = 0;

SELECT * FROM results.lab15_lisinopril_sets
ORDER BY version, concept_name;
