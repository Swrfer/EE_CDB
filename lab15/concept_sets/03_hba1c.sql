-- Concept set: pruebas de hemoglobina A1c
-- Vocabulario: LOINC 2.82; consulta: 2026-11-22
-- Construcción por relación LOINC Has component con LP286151-8.
-- Incluye variantes por método, propiedad y sistema que sean pruebas de
-- laboratorio estándar y vigentes; excluye paneles, dispositivos, metas
-- clínicas y glucosa media estimada.
-- Devuelve 7 conceptos.

CREATE SCHEMA IF NOT EXISTS results;

CREATE OR REPLACE TABLE results.lab15_hba1c_set AS
WITH component AS (
    SELECT concept_id
    FROM cdm.concept
    WHERE vocabulary_id = 'LOINC'
      AND concept_code = 'LP286151-8'
      AND invalid_reason IS NULL
)
SELECT DISTINCT test.concept_id AS measurement_concept_id,
       test.concept_code AS loinc_code,
       test.concept_name,
       test.concept_class_id
FROM component comp
JOIN cdm.concept_relationship cr
  ON cr.concept_id_2 = comp.concept_id
 AND cr.relationship_id = 'Has component'
 AND cr.invalid_reason IS NULL
JOIN cdm.concept test ON test.concept_id = cr.concept_id_1
WHERE test.vocabulary_id = 'LOINC'
  AND test.domain_id = 'Measurement'
  AND test.concept_class_id = 'Lab Test'
  AND test.standard_concept = 'S'
  AND test.invalid_reason IS NULL
  AND CURRENT_DATE BETWEEN test.valid_start_date AND test.valid_end_date;

SELECT * FROM results.lab15_hba1c_set ORDER BY loinc_code;
