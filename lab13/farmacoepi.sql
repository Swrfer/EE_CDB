-- Laboratorio 13: exposición a fármacos y laboratorios
-- Base: OMOP CDM v5.4 en DuckDB
-- Los conteos epidemiológicos usan COUNT(DISTINCT person_id).


-- ========================================================================
-- Actividad 1. Tipo de exposición
-- ========================================================================

-- Consulta: 01_tipo_exposicion
SELECT
    de.drug_type_concept_id,
    c.concept_name AS drug_type_concept_name,
    COUNT(*) AS exposiciones,
    COUNT(DISTINCT de.person_id) AS personas,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 4) AS porcentaje
FROM cdm.drug_exposure de
LEFT JOIN cdm.concept c
  ON c.concept_id = de.drug_type_concept_id
GROUP BY de.drug_type_concept_id, c.concept_name
ORDER BY exposiciones DESC;

-- ========================================================================
-- Actividad 2. Caracterización de DRUG_EXPOSURE
-- ========================================================================

-- Consulta: 02_top20_ingredientes
SELECT
    ca.ancestor_concept_id AS ingredient_concept_id,
    ingredient.concept_name AS ingredient_name,
    COUNT(*) AS exposiciones,
    COUNT(DISTINCT de.person_id) AS personas,
    COUNT(DISTINCT de.drug_concept_id) AS productos_descendientes
FROM cdm.drug_exposure de
INNER JOIN cdm.concept_ancestor ca
  ON ca.descendant_concept_id = de.drug_concept_id
INNER JOIN cdm.concept ingredient
  ON ingredient.concept_id = ca.ancestor_concept_id
WHERE ingredient.domain_id = 'Drug'
  AND ingredient.concept_class_id = 'Ingredient'
  AND ingredient.standard_concept = 'S'
GROUP BY ca.ancestor_concept_id, ingredient.concept_name
ORDER BY personas DESC, exposiciones DESC
LIMIT 20;

-- Consulta: 02_days_supply
SELECT
    COUNT(*) AS exposiciones,
    COUNT(days_supply) AS days_supply_no_nulos,
    MIN(days_supply) AS minimo,
    QUANTILE_CONT(days_supply, 0.25) AS q1,
    MEDIAN(days_supply) AS mediana,
    QUANTILE_CONT(days_supply, 0.75) AS q3,
    MAX(days_supply) AS maximo,
    COUNT(*) FILTER (WHERE days_supply <= 0) AS no_positivos,
    COUNT(*) FILTER (WHERE days_supply > 365) AS mayores_365
FROM cdm.drug_exposure;

-- Consulta: 02_calidad_fechas
SELECT
    COUNT(*) AS exposiciones,
    COUNT(DISTINCT person_id) AS personas,
    ROUND(100.0 * COUNT(*) FILTER (
        WHERE drug_exposure_end_date IS NULL
    ) / COUNT(*), 4) AS porcentaje_end_date_nulo,
    ROUND(100.0 * COUNT(*) FILTER (
        WHERE drug_exposure_end_date = drug_exposure_start_date
    ) / COUNT(*), 4) AS porcentaje_misma_fecha,
    ROUND(100.0 * COUNT(*) FILTER (
        WHERE drug_concept_id = 0
    ) / COUNT(*), 4) AS porcentaje_concept_id_cero
FROM cdm.drug_exposure;

-- ========================================================================
-- Actividad 3. Ingrediente exacto frente a jerarquía
-- ========================================================================

-- Consulta: 03_ingrediente_directo_jerarquia
WITH directo AS (
    SELECT COUNT(*) AS exposiciones,
           COUNT(DISTINCT person_id) AS personas
    FROM cdm.drug_exposure
    WHERE drug_concept_id = 1308216
), descendientes AS (
    SELECT COUNT(*) AS exposiciones,
           COUNT(DISTINCT de.person_id) AS personas,
           COUNT(DISTINCT de.drug_concept_id) AS productos
    FROM cdm.drug_exposure de
    INNER JOIN cdm.concept_ancestor ca
      ON ca.descendant_concept_id = de.drug_concept_id
    WHERE ca.ancestor_concept_id = 1308216
)
SELECT 1308216 AS ingredient_concept_id,
       'lisinopril' AS ingredient_name,
       d.exposiciones AS exposiciones_directas,
       d.personas AS personas_directas,
       h.exposiciones AS exposiciones_jerarquia,
       h.personas AS personas_jerarquia,
       h.productos AS productos_descendientes,
       h.personas - d.personas AS diferencia_personas
FROM directo d CROSS JOIN descendientes h;

-- ========================================================================
-- Actividad 4. Construcción manual de DRUG_ERA
-- ========================================================================

-- Consulta: 04_crear_drug_era
CREATE SCHEMA IF NOT EXISTS results;
CREATE OR REPLACE TABLE results.drug_era_lisinopril AS
WITH exposiciones AS (
    SELECT
        de.person_id,
        de.drug_exposure_id,
        de.drug_exposure_start_date AS start_date,
        CASE
            WHEN de.days_supply BETWEEN 1 AND 365
              THEN de.drug_exposure_start_date + (de.days_supply - 1)
            WHEN de.drug_exposure_end_date >= de.drug_exposure_start_date
             AND DATE_DIFF('day', de.drug_exposure_start_date,
                                 de.drug_exposure_end_date) <= 364
              THEN de.drug_exposure_end_date
            ELSE de.drug_exposure_start_date
        END AS end_date
    FROM cdm.drug_exposure de
    INNER JOIN cdm.concept_ancestor ca
      ON ca.descendant_concept_id = de.drug_concept_id
    WHERE ca.ancestor_concept_id = 1308216
), maximo_previo AS (
    SELECT *,
        MAX(end_date) OVER (
            PARTITION BY person_id
            ORDER BY start_date, end_date, drug_exposure_id
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        ) AS previous_max_end
    FROM exposiciones
), comienzos AS (
    SELECT *,
        CASE
            WHEN previous_max_end IS NULL
              OR start_date > previous_max_end + 30
            THEN 1 ELSE 0
        END AS new_era
    FROM maximo_previo
), grupos AS (
    SELECT *,
        SUM(new_era) OVER (
            PARTITION BY person_id
            ORDER BY start_date, end_date, drug_exposure_id
            ROWS UNBOUNDED PRECEDING
        ) AS era_group
    FROM comienzos
)
SELECT
    ROW_NUMBER() OVER (
        ORDER BY person_id, MIN(start_date)
    ) AS drug_era_id,
    person_id,
    1308216 AS ingredient_concept_id,
    'lisinopril' AS ingredient_name,
    MIN(start_date) AS drug_era_start_date,
    MAX(end_date) AS drug_era_end_date,
    COUNT(*) AS exposure_count,
    DATE_DIFF('day', MIN(start_date), MAX(end_date)) + 1 AS era_days,
    30 AS permissible_gap_days
FROM grupos
GROUP BY person_id, era_group;

-- Consulta: 04_resumen_drug_era
SELECT
    COUNT(*) AS eras_manuales,
    COUNT(DISTINCT person_id) AS personas,
    MIN(drug_era_start_date) AS fecha_minima,
    MAX(drug_era_end_date) AS fecha_maxima,
    MEDIAN(era_days) AS mediana_dias,
    MAX(era_days) AS maximo_dias,
    (SELECT COUNT(*) FROM cdm.drug_era) AS eras_cdm
FROM results.drug_era_lisinopril;

-- ========================================================================
-- Actividad 5. PDC a un año
-- ========================================================================

-- Consulta: 05_crear_pdc
CREATE OR REPLACE TABLE results.pdc_lisinopril AS
WITH exposiciones AS (
    SELECT
        de.person_id,
        de.drug_exposure_id,
        de.drug_exposure_start_date AS start_date,
        CASE
            WHEN de.days_supply BETWEEN 1 AND 365
              THEN de.drug_exposure_start_date + (de.days_supply - 1)
            WHEN de.drug_exposure_end_date >= de.drug_exposure_start_date
             AND DATE_DIFF('day', de.drug_exposure_start_date,
                                 de.drug_exposure_end_date) <= 364
              THEN de.drug_exposure_end_date
            ELSE de.drug_exposure_start_date
        END AS end_date
    FROM cdm.drug_exposure de
    INNER JOIN cdm.concept_ancestor ca
      ON ca.descendant_concept_id = de.drug_concept_id
    WHERE ca.ancestor_concept_id = 1308216
), indice AS (
    SELECT person_id, MIN(start_date) AS index_date
    FROM exposiciones
    GROUP BY person_id
), elegibles AS (
    SELECT i.person_id, i.index_date, i.index_date + 364 AS followup_end
    FROM indice i
    WHERE EXISTS (
        SELECT 1
        FROM cdm.observation_period op
        WHERE op.person_id = i.person_id
          AND op.observation_period_start_date <= i.index_date
          AND op.observation_period_end_date >= i.index_date + 364
    )
), recortadas AS (
    SELECT
        e.person_id,
        e.index_date,
        e.followup_end,
        x.drug_exposure_id,
        GREATEST(x.start_date, e.index_date) AS covered_start,
        LEAST(x.end_date, e.followup_end) AS covered_end
    FROM elegibles e
    INNER JOIN exposiciones x ON x.person_id = e.person_id
    WHERE x.start_date <= e.followup_end
      AND x.end_date >= e.index_date
), previas AS (
    SELECT *,
        MAX(covered_end) OVER (
            PARTITION BY person_id
            ORDER BY covered_start, covered_end, drug_exposure_id
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        ) AS previous_max_end
    FROM recortadas
), comienzos AS (
    SELECT *,
        CASE
            WHEN previous_max_end IS NULL
              OR covered_start > previous_max_end + 1
            THEN 1 ELSE 0
        END AS new_segment
    FROM previas
), grupos AS (
    SELECT *,
        SUM(new_segment) OVER (
            PARTITION BY person_id
            ORDER BY covered_start, covered_end, drug_exposure_id
            ROWS UNBOUNDED PRECEDING
        ) AS segment_group
    FROM comienzos
), segmentos AS (
    SELECT person_id, index_date, followup_end, segment_group,
           MIN(covered_start) AS segment_start,
           MAX(covered_end) AS segment_end
    FROM grupos
    GROUP BY person_id, index_date, followup_end, segment_group
), cubiertos AS (
    SELECT person_id, index_date, followup_end,
           LEAST(365, SUM(DATE_DIFF('day', segment_start, segment_end) + 1))
               AS covered_days
    FROM segmentos
    GROUP BY person_id, index_date, followup_end
)
SELECT
    person_id,
    index_date,
    followup_end,
    covered_days,
    365 AS denominator_days,
    ROUND(covered_days / 365.0, 6) AS pdc,
    covered_days / 365.0 >= 0.8 AS adherent_pdc_080
FROM cubiertos;

-- Consulta: 05_resumen_pdc
SELECT
    COUNT(*) AS pacientes_elegibles,
    MIN(pdc) AS minimo,
    QUANTILE_CONT(pdc, 0.25) AS q1,
    MEDIAN(pdc) AS mediana,
    QUANTILE_CONT(pdc, 0.75) AS q3,
    MAX(pdc) AS maximo,
    COUNT(*) FILTER (WHERE adherent_pdc_080) AS pacientes_pdc_080,
    ROUND(100.0 * COUNT(*) FILTER (WHERE adherent_pdc_080) / COUNT(*), 4)
        AS porcentaje_pdc_080
FROM results.pdc_lisinopril;

-- ========================================================================
-- Actividad 6. Caracterización de MEASUREMENT
-- ========================================================================

-- Consulta: 06_top15_analitos
SELECT
    m.measurement_concept_id,
    c.concept_name AS measurement_concept_name,
    COUNT(*) AS mediciones,
    COUNT(DISTINCT m.person_id) AS personas,
    COUNT(DISTINCT m.unit_concept_id) AS unidades
FROM cdm.measurement m
LEFT JOIN cdm.concept c
  ON c.concept_id = m.measurement_concept_id
GROUP BY m.measurement_concept_id, c.concept_name
ORDER BY mediciones DESC, personas DESC
LIMIT 15;

-- Consulta: 06_unidades_egfr
SELECT
    m.measurement_concept_id,
    mc.concept_name AS measurement_concept_name,
    m.unit_concept_id,
    COALESCE(uc.concept_name, 'No matching concept') AS unit_concept_name,
    m.unit_source_value,
    COUNT(*) AS mediciones,
    COUNT(DISTINCT m.person_id) AS personas,
    MIN(m.value_as_number) AS minimo,
    MEDIAN(m.value_as_number) AS mediana,
    MAX(m.value_as_number) AS maximo
FROM cdm.measurement m
LEFT JOIN cdm.concept mc
  ON mc.concept_id = m.measurement_concept_id
LEFT JOIN cdm.concept uc
  ON uc.concept_id = m.unit_concept_id
WHERE m.measurement_concept_id = 46236952
GROUP BY m.measurement_concept_id, mc.concept_name,
         m.unit_concept_id, uc.concept_name, m.unit_source_value
ORDER BY mediciones DESC;

-- Consulta: 06_calidad_measurement
SELECT
    COUNT(*) AS mediciones,
    COUNT(DISTINCT person_id) AS personas,
    ROUND(100.0 * COUNT(*) FILTER (
        WHERE value_as_number IS NULL
    ) / COUNT(*), 4) AS porcentaje_value_number_nulo,
    ROUND(100.0 * COUNT(*) FILTER (
        WHERE operator_concept_id IS NOT NULL
          AND operator_concept_id <> 0
    ) / COUNT(*), 4) AS porcentaje_operador_no_cero,
    ROUND(100.0 * COUNT(*) FILTER (
        WHERE measurement_concept_id = 0
    ) / COUNT(*), 4) AS porcentaje_concept_id_cero
FROM cdm.measurement;

-- ========================================================================
-- Actividad 7. Normalización de unidades
-- ========================================================================

-- Consulta: 07_normalizar_peso
CREATE OR REPLACE TABLE results.weight_unit_normalized AS
SELECT
    measurement_id,
    person_id,
    measurement_date,
    value_as_number AS original_value_kg,
    'kg' AS original_unit,
    CASE WHEN measurement_id % 5 = 0
         THEN value_as_number / 0.45359237
         ELSE value_as_number END AS simulated_value,
    CASE WHEN measurement_id % 5 = 0 THEN 'lb' ELSE 'kg' END
        AS simulated_unit,
    CASE WHEN measurement_id % 5 = 0
         THEN (value_as_number / 0.45359237) * 0.45359237
         ELSE value_as_number END AS normalized_value_kg,
    'kg' AS canonical_unit,
    measurement_id % 5 = 0 AS converted_from_lb,
    0.45359237 AS lb_to_kg_factor
FROM cdm.measurement
WHERE measurement_concept_id = 3025315
  AND value_as_number IS NOT NULL;

-- Consulta: 07_resumen_normalizacion
SELECT
    simulated_unit AS unidad_antes,
    COUNT(*) AS filas,
    MIN(simulated_value) AS minimo_antes,
    MEDIAN(simulated_value) AS mediana_antes,
    MAX(simulated_value) AS maximo_antes,
    'kg' AS unidad_despues,
    MIN(normalized_value_kg) AS minimo_despues,
    MEDIAN(normalized_value_kg) AS mediana_despues,
    MAX(normalized_value_kg) AS maximo_despues
FROM results.weight_unit_normalized
GROUP BY simulated_unit
ORDER BY simulated_unit;

-- ========================================================================
-- Actividad 8. Valores implausibles
-- ========================================================================

-- Consulta: 08_valores_implausibles
WITH limites AS (
    SELECT 3004249 AS concept_id, 'Systolic blood pressure' AS concept_name,
           40.0 AS lower_limit, 250.0 AS upper_limit, 'mmHg' AS unit
    UNION ALL
    SELECT 3000483, 'Glucose [Mass/volume] in Blood',
           10.0, 500.0, 'mg/dL'
    UNION ALL
    SELECT 3025315, 'Body weight',
           60.0 * 0.45359237, 700.0 * 0.45359237, 'kg'
), adultos AS (
    SELECT
        m.measurement_id,
        m.person_id,
        m.measurement_concept_id AS concept_id,
        m.measurement_date,
        m.value_as_number,
        DATE_DIFF(
            'year',
            MAKE_DATE(
                p.year_of_birth,
                COALESCE(p.month_of_birth, 7),
                COALESCE(p.day_of_birth, 1)
            ),
            m.measurement_date
        ) AS age_years
    FROM cdm.measurement m
    INNER JOIN cdm.person p ON p.person_id = m.person_id
    WHERE m.measurement_concept_id IN (3004249, 3000483, 3025315)
      AND m.value_as_number IS NOT NULL
), evaluados AS (
    SELECT a.*, l.concept_name, l.lower_limit, l.upper_limit, l.unit,
           a.value_as_number < l.lower_limit
            OR a.value_as_number > l.upper_limit AS implausible
    FROM adultos a
    INNER JOIN limites l ON l.concept_id = a.concept_id
    WHERE a.age_years >= 18
), frecuencias AS (
    SELECT concept_id, value_as_number, COUNT(*) AS repetitions
    FROM evaluados
    GROUP BY concept_id, value_as_number
)
SELECT
    e.concept_id,
    e.concept_name,
    e.unit,
    e.lower_limit,
    e.upper_limit,
    COUNT(*) AS adult_measurements,
    COUNT(*) FILTER (WHERE e.implausible) AS outside_range,
    ROUND(100.0 * COUNT(*) FILTER (WHERE e.implausible) / COUNT(*), 4)
        AS outside_percentage,
    COUNT(*) FILTER (
        WHERE e.implausible AND f.repetitions >= 2
    ) AS repeated_implausible_rows,
    COUNT(DISTINCT e.value_as_number) FILTER (
        WHERE e.implausible AND f.repetitions >= 2
    ) AS repeated_implausible_values
FROM evaluados e
INNER JOIN frecuencias f
  ON f.concept_id = e.concept_id
 AND f.value_as_number = e.value_as_number
GROUP BY e.concept_id, e.concept_name, e.unit,
         e.lower_limit, e.upper_limit
ORDER BY e.concept_id;

-- Consulta: 08_detalle_implausibles
WITH limites AS (
    SELECT 3004249 AS concept_id, 40.0 AS lower_limit, 250.0 AS upper_limit
    UNION ALL SELECT 3000483, 10.0, 500.0
    UNION ALL SELECT 3025315, 60.0 * 0.45359237, 700.0 * 0.45359237
), evaluados AS (
    SELECT m.measurement_id, m.person_id, m.measurement_concept_id AS concept_id,
           m.measurement_date, m.value_as_number, l.lower_limit, l.upper_limit
    FROM cdm.measurement m
    INNER JOIN cdm.person p ON p.person_id = m.person_id
    INNER JOIN limites l ON l.concept_id = m.measurement_concept_id
    WHERE m.value_as_number IS NOT NULL
      AND DATE_DIFF(
            'year',
            MAKE_DATE(p.year_of_birth, COALESCE(p.month_of_birth, 7),
                      COALESCE(p.day_of_birth, 1)),
            m.measurement_date
          ) >= 18
)
SELECT *,
       CASE WHEN value_as_number < lower_limit THEN 'below_range'
            WHEN value_as_number > upper_limit THEN 'above_range' END AS reason
FROM evaluados
WHERE value_as_number < lower_limit OR value_as_number > upper_limit
ORDER BY concept_id, value_as_number;

-- ========================================================================
-- Actividad 9. MEASUREMENT frente a OBSERVATION
-- ========================================================================

-- Consulta: 09_measurement_observation
SELECT 'Body weight' AS clinical_fact,
       'MEASUREMENT' AS omop_table,
       3025315 AS concept_id,
       c.concept_name,
       COUNT(*) AS events,
       COUNT(DISTINCT m.person_id) AS persons,
       'Concordant: quantitative standardized measurement' AS themis_assessment
FROM cdm.measurement m
INNER JOIN cdm.concept c ON c.concept_id = m.measurement_concept_id
WHERE m.measurement_concept_id = 3025315
GROUP BY c.concept_name
UNION ALL
SELECT 'Tobacco smoking status', 'OBSERVATION', 43054909,
       c.concept_name, COUNT(*), COUNT(DISTINCT o.person_id),
       'Concordant: social and lifestyle fact'
FROM cdm.observation o
INNER JOIN cdm.concept c ON c.concept_id = o.observation_concept_id
WHERE o.observation_concept_id = 43054909
GROUP BY c.concept_name
UNION ALL
SELECT 'Systolic blood pressure', 'MEASUREMENT', 3004249,
       c.concept_name, COUNT(*), COUNT(DISTINCT m.person_id),
       'Concordant: quantitative standardized measurement'
FROM cdm.measurement m
INNER JOIN cdm.concept c ON c.concept_id = m.measurement_concept_id
WHERE m.measurement_concept_id = 3004249
GROUP BY c.concept_name;

-- ========================================================================
-- Actividad 10. Último valor alrededor del índice
-- ========================================================================

-- Consulta: 10_glucosa_indice
WITH indice AS (
    SELECT person_id, MIN(condition_start_date) AS index_date
    FROM cdm.condition_occurrence
    GROUP BY person_id
), candidatos AS (
    SELECT
        i.person_id,
        i.index_date,
        m.measurement_id,
        m.measurement_date,
        m.value_as_number,
        m.unit_concept_id,
        uc.concept_name AS unit_concept_name,
        ABS(DATE_DIFF('day', i.index_date, m.measurement_date)) AS distance_days,
        ROW_NUMBER() OVER (
            PARTITION BY i.person_id
            ORDER BY
                ABS(DATE_DIFF('day', i.index_date, m.measurement_date)),
                CASE WHEN m.measurement_date <= i.index_date THEN 0 ELSE 1 END,
                m.measurement_date DESC,
                m.measurement_id
        ) AS rn
    FROM indice i
    INNER JOIN cdm.measurement m
      ON m.person_id = i.person_id
     AND m.measurement_concept_id = 3000483
     AND m.value_as_number IS NOT NULL
     AND m.measurement_date BETWEEN i.index_date - 90 AND i.index_date + 90
    LEFT JOIN cdm.concept uc ON uc.concept_id = m.unit_concept_id
)
SELECT
    i.person_id,
    i.index_date,
    c.measurement_id,
    c.measurement_date,
    c.value_as_number,
    c.unit_concept_id,
    c.unit_concept_name,
    c.distance_days,
    c.measurement_id IS NOT NULL AS has_baseline_glucose
FROM indice i
LEFT JOIN candidatos c
  ON c.person_id = i.person_id AND c.rn = 1
ORDER BY i.person_id;
