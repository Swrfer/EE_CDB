-- ============================================================
-- calidad_mapeo
-- ============================================================
WITH calidad AS (
            SELECT 'Condition' dominio, COUNT(*) eventos,
                   COUNT(DISTINCT person_id) personas,
                   COUNT_IF(COALESCE(condition_concept_id, 0) = 0) concept_id_cero
            FROM cdm.condition_occurrence
            UNION ALL
            SELECT 'Drug', COUNT(*), COUNT(DISTINCT person_id),
                   COUNT_IF(COALESCE(drug_concept_id, 0) = 0)
            FROM cdm.drug_exposure
            UNION ALL
            SELECT 'Measurement', COUNT(*), COUNT(DISTINCT person_id),
                   COUNT_IF(COALESCE(measurement_concept_id, 0) = 0)
            FROM cdm.measurement
            UNION ALL
            SELECT 'Observation', COUNT(*), COUNT(DISTINCT person_id),
                   COUNT_IF(COALESCE(observation_concept_id, 0) = 0)
            FROM cdm.observation
            UNION ALL
            SELECT 'Procedure', COUNT(*), COUNT(DISTINCT person_id),
                   COUNT_IF(COALESCE(procedure_concept_id, 0) = 0)
            FROM cdm.procedure_occurrence
            UNION ALL
            SELECT 'Visit', COUNT(*), COUNT(DISTINCT person_id),
                   COUNT_IF(COALESCE(visit_concept_id, 0) = 0)
            FROM cdm.visit_occurrence
        )
        SELECT dominio, eventos, personas, concept_id_cero,
               ROUND(100.0 * concept_id_cero / NULLIF(eventos, 0), 4)
                   porcentaje_concept_id_cero
        FROM calidad
        ORDER BY porcentaje_concept_id_cero DESC, dominio;


-- ============================================================
-- personas_sexo
-- ============================================================
SELECT COALESCE(c.concept_name, 'Sin concepto legible') sexo,
               COUNT(DISTINCT p.person_id) personas,
               ROUND(100.0 * COUNT(DISTINCT p.person_id)
                     / SUM(COUNT(DISTINCT p.person_id)) OVER (), 2) porcentaje
        FROM cdm.person p
        LEFT JOIN cdm.concept c ON c.concept_id = p.gender_concept_id
        GROUP BY 1
        ORDER BY personas DESC;


-- ============================================================
-- personas_nacimiento
-- ============================================================
SELECT year_of_birth anio_nacimiento, COUNT(DISTINCT person_id) personas
        FROM cdm.person
        GROUP BY year_of_birth
        ORDER BY year_of_birth;


-- ============================================================
-- observacion_mediana
-- ============================================================
WITH por_persona AS (
            SELECT person_id,
                   SUM(DATE_DIFF('day', observation_period_start_date,
                                 observation_period_end_date) + 1) dias_observacion
            FROM cdm.observation_period
            GROUP BY person_id
        )
        SELECT COUNT(DISTINCT person_id) personas,
               MEDIAN(dias_observacion) mediana_dias_observacion,
               ROUND(AVG(dias_observacion), 2) media_dias_observacion,
               MIN(dias_observacion) minimo_dias,
               MAX(dias_observacion) maximo_dias
        FROM por_persona;


-- ============================================================
-- top20_diagnosticos
-- ============================================================
SELECT co.condition_concept_id concept_id, c.concept_name,
               COUNT(*) eventos, COUNT(DISTINCT co.person_id) personas
        FROM cdm.condition_occurrence co
        LEFT JOIN cdm.concept c ON c.concept_id = co.condition_concept_id
        WHERE co.condition_concept_id <> 0
        GROUP BY co.condition_concept_id, c.concept_name
        ORDER BY eventos DESC, personas DESC
        LIMIT 20;


-- ============================================================
-- visitas_resumen
-- ============================================================
WITH por_persona AS (
            SELECT p.person_id, COUNT(v.visit_occurrence_id) visitas
            FROM cdm.person p
            LEFT JOIN cdm.visit_occurrence v ON v.person_id = p.person_id
            GROUP BY p.person_id
        )
        SELECT COUNT(DISTINCT person_id) personas, SUM(visitas) visitas,
               ROUND(AVG(visitas), 4) media_visitas_por_persona,
               MEDIAN(visitas) mediana_visitas_por_persona
        FROM por_persona;


-- ============================================================
-- visitas_tipo
-- ============================================================
SELECT v.visit_concept_id concept_id,
               COALESCE(c.concept_name, 'Sin concepto legible') tipo_visita,
               COUNT(*) visitas, COUNT(DISTINCT v.person_id) personas,
               ROUND(COUNT(*) * 1.0 / NULLIF(COUNT(DISTINCT v.person_id), 0), 4)
                   media_visitas_por_persona
        FROM cdm.visit_occurrence v
        LEFT JOIN cdm.concept c ON c.concept_id = v.visit_concept_id
        GROUP BY v.visit_concept_id, c.concept_name
        ORDER BY visitas DESC;


-- ============================================================
-- estandar_vs_origen
-- ============================================================
WITH frecuente AS (
            SELECT condition_concept_id,
                   COUNT(*) eventos_estandar,
                   COUNT(DISTINCT person_id) personas_estandar
            FROM cdm.condition_occurrence
            WHERE condition_concept_id <> 0
            GROUP BY condition_concept_id
            ORDER BY eventos_estandar DESC
            LIMIT 1
        ), origen AS (
            SELECT co.condition_concept_id, co.condition_source_value,
                   COUNT(*) eventos_origen,
                   COUNT(DISTINCT co.person_id) personas_origen,
                   ROW_NUMBER() OVER (
                       PARTITION BY co.condition_concept_id
                       ORDER BY COUNT(*) DESC, co.condition_source_value
                   ) posicion
            FROM cdm.condition_occurrence co
            JOIN frecuente f ON f.condition_concept_id = co.condition_concept_id
            GROUP BY co.condition_concept_id, co.condition_source_value
        )
        SELECT f.condition_concept_id concept_id, c.concept_name,
               f.eventos_estandar, f.personas_estandar,
               o.condition_source_value codigo_origen_mas_frecuente,
               o.eventos_origen, o.personas_origen,
               f.eventos_estandar - o.eventos_origen diferencia_eventos,
               ROUND(100.0 * (f.eventos_estandar - o.eventos_origen)
                     / NULLIF(f.eventos_estandar, 0), 4) diferencia_porcentaje
        FROM frecuente f
        LEFT JOIN cdm.concept c ON c.concept_id = f.condition_concept_id
        LEFT JOIN origen o ON o.condition_concept_id = f.condition_concept_id
                           AND o.posicion = 1;


-- ============================================================
-- codigos_origen_condicion
-- ============================================================
WITH frecuente AS (
            SELECT condition_concept_id
            FROM cdm.condition_occurrence
            WHERE condition_concept_id <> 0
            GROUP BY condition_concept_id
            ORDER BY COUNT(*) DESC
            LIMIT 1
        )
        SELECT co.condition_concept_id concept_id, c.concept_name,
               co.condition_source_value codigo_origen,
               COUNT(*) eventos, COUNT(DISTINCT co.person_id) personas
        FROM cdm.condition_occurrence co
        JOIN frecuente f ON f.condition_concept_id = co.condition_concept_id
        LEFT JOIN cdm.concept c ON c.concept_id = co.condition_concept_id
        GROUP BY co.condition_concept_id, c.concept_name,
                 co.condition_source_value
        ORDER BY eventos DESC;


-- ============================================================
-- ventana_observacion
-- ============================================================
WITH evaluados AS (
            SELECT co.*,
                   EXISTS (
                       SELECT 1
                       FROM cdm.observation_period op
                       WHERE op.person_id = co.person_id
                         AND co.condition_start_date BETWEEN
                             op.observation_period_start_date
                             AND op.observation_period_end_date
                   ) dentro
            FROM cdm.condition_occurrence co
        )
        SELECT COUNT(*) eventos_sin_filtrar,
               COUNT(*) FILTER (WHERE dentro) eventos_dentro_observacion,
               COUNT(*) FILTER (WHERE NOT dentro) eventos_fuera_observacion,
               ROUND(100.0 * COUNT(*) FILTER (WHERE NOT dentro)
                     / NULLIF(COUNT(*), 0), 4) diferencia_porcentaje,
               COUNT(DISTINCT person_id) personas_sin_filtrar,
               COUNT(DISTINCT person_id) FILTER (WHERE dentro)
                   personas_dentro_observacion
        FROM evaluados;


-- ============================================================
-- athena_top3
-- ============================================================
WITH top3 AS (
            SELECT condition_concept_id,
                   COUNT(*) eventos,
                   COUNT(DISTINCT person_id) personas
            FROM cdm.condition_occurrence
            WHERE condition_concept_id <> 0
            GROUP BY condition_concept_id
            ORDER BY eventos DESC
            LIMIT 3
        ), hijos AS (
            SELECT ca.ancestor_concept_id,
                   COUNT(DISTINCT ca.descendant_concept_id) conceptos_hijos
            FROM cdm.concept_ancestor ca
            JOIN top3 t ON t.condition_concept_id = ca.ancestor_concept_id
            WHERE ca.descendant_concept_id <> ca.ancestor_concept_id
            GROUP BY ca.ancestor_concept_id
        ), origen AS (
            SELECT co.condition_concept_id, co.condition_source_value,
                   ROW_NUMBER() OVER (
                       PARTITION BY co.condition_concept_id
                       ORDER BY COUNT(*) DESC, co.condition_source_value
                   ) posicion
            FROM cdm.condition_occurrence co
            JOIN top3 t ON t.condition_concept_id = co.condition_concept_id
            GROUP BY co.condition_concept_id, co.condition_source_value
        )
        SELECT t.condition_concept_id concept_id, c.concept_name,
               c.vocabulary_id, c.domain_id, c.standard_concept,
               t.eventos, t.personas,
               COALESCE(h.conceptos_hijos, 0) conceptos_hijos,
               o.condition_source_value codigo_origen_ejemplo
        FROM top3 t
        LEFT JOIN cdm.concept c ON c.concept_id = t.condition_concept_id
        LEFT JOIN hijos h ON h.ancestor_concept_id = t.condition_concept_id
        LEFT JOIN origen o ON o.condition_concept_id = t.condition_concept_id
                          AND o.posicion = 1
        ORDER BY t.eventos DESC;


-- ============================================================
-- conteos_tablas
-- ============================================================
SELECT 'person' tabla, COUNT(*) filas FROM cdm.person
        UNION ALL SELECT 'observation_period', COUNT(*) FROM cdm.observation_period
        UNION ALL SELECT 'visit_occurrence', COUNT(*) FROM cdm.visit_occurrence
        UNION ALL SELECT 'condition_occurrence', COUNT(*) FROM cdm.condition_occurrence
        UNION ALL SELECT 'drug_exposure', COUNT(*) FROM cdm.drug_exposure
        UNION ALL SELECT 'measurement', COUNT(*) FROM cdm.measurement
        UNION ALL SELECT 'observation', COUNT(*) FROM cdm.observation
        UNION ALL SELECT 'procedure_occurrence', COUNT(*) FROM cdm.procedure_occurrence
        UNION ALL SELECT 'concept', COUNT(*) FROM cdm.concept
        UNION ALL SELECT 'concept_relationship', COUNT(*) FROM cdm.concept_relationship
        UNION ALL SELECT 'concept_ancestor', COUNT(*) FROM cdm.concept_ancestor
        ORDER BY tabla;
