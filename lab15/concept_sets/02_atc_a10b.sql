-- Concept set: hipoglucemiantes A10B, excluyendo insulinas
-- Vocabulario: ATC 2026-02-01; consulta: 2026-11-22
-- Construido desde la clase ATC A10B mediante CONCEPT_ANCESTOR.
-- Devuelve 42 ingredientes estándar vigentes.
-- La cobertura de ATC se audita porque no incluye todos los productos de la base.

CREATE SCHEMA IF NOT EXISTS results;

CREATE OR REPLACE TABLE results.lab15_atc_a10b_ingredients AS
WITH root AS (
    SELECT concept_id
    FROM cdm.concept
    WHERE vocabulary_id = 'ATC'
      AND concept_code = 'A10B'
      AND invalid_reason IS NULL
)
SELECT DISTINCT i.concept_id AS ingredient_concept_id,
       i.concept_name AS ingredient_name,
       i.vocabulary_id, i.concept_code
FROM root r
JOIN cdm.concept_ancestor ca ON ca.ancestor_concept_id = r.concept_id
JOIN cdm.concept i ON i.concept_id = ca.descendant_concept_id
WHERE i.domain_id = 'Drug'
  AND i.concept_class_id = 'Ingredient'
  AND i.standard_concept = 'S'
  AND i.invalid_reason IS NULL;

CREATE OR REPLACE TABLE results.lab15_atc_a10b_products_observed AS
SELECT DISTINCT de.drug_concept_id, c.concept_name
FROM cdm.drug_exposure de
JOIN cdm.concept c ON c.concept_id = de.drug_concept_id
JOIN cdm.concept_ancestor ca ON ca.descendant_concept_id = de.drug_concept_id
JOIN results.lab15_atc_a10b_ingredients i
  ON i.ingredient_concept_id = ca.ancestor_concept_id;

SELECT * FROM results.lab15_atc_a10b_ingredients ORDER BY ingredient_name;
SELECT * FROM results.lab15_atc_a10b_products_observed ORDER BY concept_name;
