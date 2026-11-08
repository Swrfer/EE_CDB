-- Laboratorio 11: Analítica longitudinal
-- Consultas clínicas temporales con DuckDB.

-- ========================================
-- Fuente: ctes_comparacion.sql
-- ========================================

-- QUERY: nested_encounters
-- ¿Cuál es el promedio y la mediana de encuentros por paciente?
SELECT
    avg(encounter_count)::DOUBLE AS mean_encounters,
    median(encounter_count)::DOUBLE AS median_encounters
FROM (
    SELECT
        p.patient_id,
        count(e.encounter_id) AS encounter_count
    FROM patients AS p
    LEFT JOIN encounters AS e
        ON p.patient_id = e.patient_id
    GROUP BY p.patient_id
) AS patient_encounter_counts;

-- QUERY: cte_encounters
-- ¿Cuál es el número medio y mediano de encuentros por paciente usando CTEs?
-- Misma pregunta reescrita con una CTE descriptiva.
WITH patient_encounter_counts AS (
    SELECT
        p.patient_id,
        count(e.encounter_id) AS encounter_count
    FROM patients AS p
    LEFT JOIN encounters AS e
        ON p.patient_id = e.patient_id
    GROUP BY p.patient_id
)
SELECT
    avg(encounter_count)::DOUBLE AS mean_encounters,
    median(encounter_count)::DOUBLE AS median_encounters
FROM patient_encounter_counts;

-- QUERY: nested_diabetes
-- ¿Qué pacientes con diabetes no tienen una medición de HbA1c?
SELECT d.patient_id
FROM (
    SELECT DISTINCT patient_id
    FROM conditions
    WHERE lower(description) LIKE '%diabetes%'
) AS d
ANTI JOIN (
    SELECT DISTINCT patient_id
    FROM observations
    WHERE code = '4548-4'
) AS h
    ON d.patient_id = h.patient_id
ORDER BY d.patient_id;

-- QUERY: cte_diabetes
-- ¿Qué pacientes tienen diabetes sin ninguna medición de HbA1c usando CTEs?
-- Misma pregunta reescrita con CTEs descriptivas.
WITH diabetes_patients AS (
    SELECT DISTINCT patient_id
    FROM conditions
    WHERE lower(description) LIKE '%diabetes%'
),
hba1c_patients AS (
    SELECT DISTINCT patient_id
    FROM observations
    WHERE code = '4548-4'
)
SELECT d.patient_id
FROM diabetes_patients AS d
ANTI JOIN hba1c_patients AS h
    ON d.patient_id = h.patient_id
ORDER BY d.patient_id;

-- ========================================
-- Fuente: 03_primera_ultima_visita.sql
-- ========================================

-- QUERY: visits_group_by
-- ¿Cuál fue la primera y última visita de cada paciente
-- y cuántos encuentros tuvo?

WITH grouped_visits AS (
    SELECT
        patient_id,
        min(start_time) AS first_visit,
        max(start_time) AS last_visit,
        count(*)::BIGINT AS total_visits
    FROM encounters
    GROUP BY patient_id
)
SELECT
    patient_id,
    first_visit,
    last_visit,
    total_visits
FROM grouped_visits
ORDER BY patient_id;

-- QUERY: visits_window
-- ¿Cuál es la primera visita, la última y el total por paciente usando ventanas?
-- Misma pregunta mediante funciones de ventana.

WITH visit_windows AS (
    SELECT
        patient_id,
        first_value(start_time) OVER (
            PARTITION BY patient_id
            ORDER BY start_time, encounter_id
            ROWS BETWEEN UNBOUNDED PRECEDING
                AND UNBOUNDED FOLLOWING
        ) AS first_visit,
        last_value(start_time) OVER (
            PARTITION BY patient_id
            ORDER BY start_time, encounter_id
            ROWS BETWEEN UNBOUNDED PRECEDING
                AND UNBOUNDED FOLLOWING
        ) AS last_visit,
        count(*) OVER (
            PARTITION BY patient_id
            ROWS BETWEEN UNBOUNDED PRECEDING
                AND UNBOUNDED FOLLOWING
        )::BIGINT AS total_visits
    FROM encounters
),
one_row_per_patient AS (
    SELECT DISTINCT
        patient_id,
        first_visit,
        last_visit,
        total_visits
    FROM visit_windows
)
SELECT
    patient_id,
    first_visit,
    last_visit,
    total_visits
FROM one_row_per_patient
ORDER BY patient_id;

-- ========================================
-- Fuente: 04_intervalos_visitas.sql
-- ========================================

-- QUERY: visit_intervals
-- ¿Cuántos días transcurrieron entre cada visita
-- y la visita anterior del mismo paciente?

WITH ordered_visits AS (
    SELECT
        patient_id,
        encounter_id,
        start_time,
        lag(start_time) OVER (
            PARTITION BY patient_id
            ORDER BY start_time, encounter_id
            ROWS BETWEEN UNBOUNDED PRECEDING
                AND CURRENT ROW
        ) AS previous_visit
    FROM encounters
),
visit_intervals AS (
    SELECT
        patient_id,
        encounter_id,
        start_time,
        previous_visit,
        date_diff(
            'day',
            previous_visit,
            start_time
        ) AS days_since_previous
    FROM ordered_visits
)
SELECT
    patient_id,
    encounter_id,
    start_time,
    previous_visit,
    days_since_previous
FROM visit_intervals
ORDER BY patient_id, start_time, encounter_id;

-- QUERY: visit_interval_summary
-- ¿Cuál es la mediana de días entre visitas consecutivas?

WITH ordered_visits AS (
    SELECT
        patient_id,
        start_time,
        lag(start_time) OVER (
            PARTITION BY patient_id
            ORDER BY start_time, encounter_id
            ROWS BETWEEN UNBOUNDED PRECEDING
                AND CURRENT ROW
        ) AS previous_visit
    FROM encounters
),
visit_intervals AS (
    SELECT
        date_diff(
            'day',
            previous_visit,
            start_time
        ) AS days_since_previous
    FROM ordered_visits
)
SELECT
    count(*) AS total_visits,
    count(*) FILTER (
        WHERE days_since_previous IS NULL
    ) AS first_visits_with_null,
    count(*) FILTER (
        WHERE days_since_previous IS NOT NULL
    ) AS comparable_intervals,
    median(days_since_previous)::DOUBLE
        AS median_days
FROM visit_intervals;

-- ========================================
-- Fuente: 05_readmisiones.sql
-- ========================================

-- QUERY: readmission_events
-- ¿Qué ingresos hospitalarios ocurrieron dentro de los
-- 30 días posteriores al alta hospitalaria previa?

WITH dataset_limits AS (
    SELECT
        max(
            coalesce(stop_time, start_time)
        ) AS dataset_end
    FROM encounters
),
ordered_admissions AS (
    SELECT
        patient_id,
        encounter_id,
        start_time AS admission_time,
        stop_time AS discharge_time,
        lead(start_time) OVER (
            PARTITION BY patient_id
            ORDER BY start_time, encounter_id
            ROWS BETWEEN CURRENT ROW
                AND UNBOUNDED FOLLOWING
        ) AS next_admission
    FROM encounters
    WHERE encounter_class = 'inpatient'
),
eligible_discharges AS (
    SELECT
        a.patient_id,
        a.encounter_id,
        a.admission_time,
        a.discharge_time,
        a.next_admission,
        date_diff(
            'day',
            a.discharge_time,
            a.next_admission
        ) AS days_to_readmission
    FROM ordered_admissions AS a
    CROSS JOIN dataset_limits AS d
    WHERE a.discharge_time IS NOT NULL
      AND a.discharge_time
          <= d.dataset_end - INTERVAL 30 DAY
),
readmissions AS (
    SELECT
        patient_id,
        encounter_id,
        admission_time,
        discharge_time,
        next_admission,
        days_to_readmission
    FROM eligible_discharges
    WHERE next_admission >= discharge_time
          AND next_admission <= discharge_time + INTERVAL 30 DAY
)
SELECT
    patient_id,
    encounter_id,
    admission_time,
    discharge_time,
    next_admission,
    days_to_readmission
FROM readmissions
ORDER BY patient_id, admission_time;

-- QUERY: readmission_summary
-- ¿Cuántas readmisiones hay y cuál es la tasa
-- entre las altas elegibles?

WITH dataset_limits AS (
    SELECT
        max(
            coalesce(stop_time, start_time)
        ) AS dataset_end
    FROM encounters
),
ordered_admissions AS (
    SELECT
        patient_id,
        stop_time AS discharge_time,
        lead(start_time) OVER (
            PARTITION BY patient_id
            ORDER BY start_time, encounter_id
            ROWS BETWEEN CURRENT ROW
                AND UNBOUNDED FOLLOWING
        ) AS next_admission
    FROM encounters
    WHERE encounter_class = 'inpatient'
),
eligible_discharges AS (
    SELECT
        patient_id,
        discharge_time,
        next_admission,
        date_diff(
            'day',
            discharge_time,
            next_admission
        ) AS days_to_readmission
    FROM ordered_admissions
    CROSS JOIN dataset_limits
    WHERE discharge_time IS NOT NULL
      AND discharge_time
          <= dataset_end - INTERVAL 30 DAY
)
SELECT
    count(*) AS eligible_discharges,
    count(*) FILTER (
        WHERE next_admission >= discharge_time
          AND next_admission <= discharge_time + INTERVAL 30 DAY
    ) AS readmissions,
    round(
        100.0
        * count(*) FILTER (
            WHERE next_admission >= discharge_time
          AND next_admission <= discharge_time + INTERVAL 30 DAY
        )
        / nullif(count(*), 0),
        4
    )::DOUBLE AS readmission_rate_percent
FROM eligible_discharges;

-- ========================================
-- Fuente: 06_episodios_lisinopril.sql
-- ========================================

-- QUERY: lisinopril_episodes
-- ¿Cuáles son los episodios continuos de tratamiento
-- con lisinopril usando gaps de 30, 60 y 90 días?

WITH persistence_gaps AS (
    SELECT gap_days
    FROM (
        VALUES (30), (60), (90)
    ) AS configured_gaps(gap_days)
),
medication_records AS (
    SELECT DISTINCT
        patient_id,
        cast(start_time AS DATE) AS start_date,
        greatest(
            coalesce(
                cast(stop_time AS DATE),
                cast(start_time AS DATE)
            ),
            cast(start_time AS DATE)
        ) AS end_date
    FROM medications
    WHERE code = '314076'
      AND start_time IS NOT NULL
),
expanded_records AS (
    SELECT
        g.gap_days,
        m.patient_id,
        m.start_date,
        m.end_date
    FROM medication_records AS m
    CROSS JOIN persistence_gaps AS g
),
previous_boundaries AS (
    SELECT
        gap_days,
        patient_id,
        start_date,
        end_date,
        max(end_date) OVER (
            PARTITION BY gap_days, patient_id
            ORDER BY start_date, end_date
            ROWS BETWEEN UNBOUNDED PRECEDING
                AND 1 PRECEDING
        ) AS previous_max_end
    FROM expanded_records
),
episode_flags AS (
    SELECT
        gap_days,
        patient_id,
        start_date,
        end_date,
        CASE
            WHEN previous_max_end IS NULL THEN 1
            WHEN start_date
                > previous_max_end
                    + gap_days * INTERVAL 1 DAY
                THEN 1
            ELSE 0
        END AS starts_new_episode
    FROM previous_boundaries
),
episode_numbers AS (
    SELECT
        gap_days,
        patient_id,
        start_date,
        end_date,
        sum(starts_new_episode) OVER (
            PARTITION BY gap_days, patient_id
            ORDER BY start_date, end_date
            ROWS BETWEEN UNBOUNDED PRECEDING
                AND CURRENT ROW
        )::BIGINT AS episode_number
    FROM episode_flags
),
episodes AS (
    SELECT
        gap_days,
        patient_id,
        episode_number,
        min(start_date) AS episode_start,
        max(end_date) AS episode_end,
        date_diff(
            'day',
            min(start_date),
            max(end_date)
        ) + 1 AS duration_days
    FROM episode_numbers
    GROUP BY
        gap_days,
        patient_id,
        episode_number
)
SELECT
    gap_days,
    patient_id,
    episode_number,
    episode_start,
    episode_end,
    duration_days,
    count(*) OVER (
        PARTITION BY gap_days
        ROWS BETWEEN UNBOUNDED PRECEDING
            AND UNBOUNDED FOLLOWING
    )::BIGINT AS episodes_for_gap
FROM episodes
ORDER BY
    gap_days,
    patient_id,
    episode_number;

-- ========================================
-- Fuente: 07_deduplicar_observaciones.sql
-- ========================================

-- QUERY: latest_observations
-- ¿Cuál es la observación más reciente de cada
-- combinación paciente-analito?

WITH ranked_observations AS (
    SELECT
        patient_id,
        code,
        description,
        observation_time,
        value,
        units,
        row_number() OVER (
            PARTITION BY patient_id, code
            ORDER BY
                observation_time DESC,
                encounter_id DESC
            ROWS BETWEEN UNBOUNDED PRECEDING
                AND CURRENT ROW
        ) AS rn
    FROM observations
)
SELECT
    patient_id,
    code,
    description,
    observation_time,
    value,
    units
FROM ranked_observations
WHERE rn = 1
ORDER BY patient_id, code;

-- QUERY: deduplication_summary
-- ¿Cuántas observaciones quedan antes y después
-- de conservar únicamente la más reciente?

WITH ranked_observations AS (
    SELECT
        patient_id,
        code,
        row_number() OVER (
            PARTITION BY patient_id, code
            ORDER BY
                observation_time DESC,
                encounter_id DESC
            ROWS BETWEEN UNBOUNDED PRECEDING
                AND CURRENT ROW
        ) AS rn
    FROM observations
),
deduplicated_observations AS (
    SELECT
        patient_id,
        code
    FROM ranked_observations
    WHERE rn = 1
)
SELECT
    (
        SELECT count(*)
        FROM observations
    ) AS rows_before,
    (
        SELECT count(*)
        FROM deduplicated_observations
    ) AS rows_after;

-- ========================================
-- Fuente: 08_medias_hba1c.sql
-- ========================================

-- QUERY: hba1c_moving_average
-- ¿Cómo cambian la media acumulada y la media móvil
-- de tres mediciones de HbA1c en un mismo paciente?

WITH hba1c_counts AS (
    SELECT
        patient_id,
        count(*) AS measurements,
        count(
            DISTINCT try_cast(value AS DOUBLE)
        ) AS distinct_values
    FROM observations
    WHERE code = '4548-4'
      AND try_cast(value AS DOUBLE) IS NOT NULL
    GROUP BY patient_id
    HAVING count(*) >= 5
       AND count(
           DISTINCT try_cast(value AS DOUBLE)
       ) >= 2
),
selected_patient AS (
    SELECT patient_id
    FROM hba1c_counts
    ORDER BY
        distinct_values DESC,
        measurements DESC,
        patient_id
    LIMIT 1
),
numeric_hba1c AS (
    SELECT
        o.patient_id,
        o.encounter_id,
        o.observation_time,
        try_cast(o.value AS DOUBLE)
            AS hba1c_value,
        o.units
    FROM observations AS o
    INNER JOIN selected_patient AS s
        ON o.patient_id = s.patient_id
    WHERE o.code = '4548-4'
      AND try_cast(o.value AS DOUBLE) IS NOT NULL
),
longitudinal_hba1c AS (
    SELECT
        patient_id,
        observation_time,
        hba1c_value,
        units,
        avg(hba1c_value) OVER (
            PARTITION BY patient_id
            ORDER BY observation_time, encounter_id
            ROWS BETWEEN UNBOUNDED PRECEDING
                AND CURRENT ROW
        ) AS cumulative_mean,
        avg(hba1c_value) OVER (
            PARTITION BY patient_id
            ORDER BY observation_time, encounter_id
            ROWS BETWEEN 2 PRECEDING
                AND CURRENT ROW
        ) AS moving_mean_3
    FROM numeric_hba1c
)
SELECT
    patient_id,
    observation_time,
    hba1c_value,
    units,
    cumulative_mean,
    moving_mean_3
FROM longitudinal_hba1c
ORDER BY observation_time;

-- ========================================
-- Fuente: 09_hba1c_baseline.sql
-- ========================================

-- QUERY: closest_preindex_hba1c
-- ¿Cuál es la HbA1c más cercana al primer diagnóstico
-- de diabetes dentro de los 90 días anteriores?
--
-- Política temporal:
-- No se permiten mediciones posteriores a la fecha índice,
-- porque podrían incorporar información futura.

WITH diabetes_index_dates AS (
    SELECT
        patient_id,
        min(start_date) AS index_date
    FROM conditions
    WHERE contains(
        lower(description),
        'diabetes'
    )
    GROUP BY patient_id
),
candidate_hba1c AS (
    SELECT
        d.patient_id,
        d.index_date,
        o.observation_time,
        try_cast(o.value AS DOUBLE)
            AS hba1c_value,
        o.units,
        date_diff(
            'day',
            CAST(o.observation_time AS DATE),
            d.index_date
        ) AS days_before_index
    FROM diabetes_index_dates AS d
    INNER JOIN observations AS o
        ON d.patient_id = o.patient_id
    WHERE o.code = '4548-4'
      AND try_cast(o.value AS DOUBLE) IS NOT NULL
      AND CAST(o.observation_time AS DATE)
          BETWEEN d.index_date - INTERVAL 90 DAY
              AND d.index_date
),
ranked_hba1c AS (
    SELECT
        patient_id,
        index_date,
        observation_time,
        hba1c_value,
        units,
        days_before_index,
        row_number() OVER (
            PARTITION BY patient_id
            ORDER BY
                days_before_index,
                observation_time DESC
            ROWS BETWEEN UNBOUNDED PRECEDING
                AND CURRENT ROW
        ) AS rn
    FROM candidate_hba1c
)
SELECT
    patient_id,
    index_date,
    observation_time,
    hba1c_value,
    units,
    days_before_index
FROM ranked_hba1c
WHERE rn = 1
ORDER BY patient_id;

-- ========================================
-- Fuente: 10_intervalos_window.sql
-- ========================================

-- QUERY: interval_summary_window
-- ¿Cuál es la mediana de días entre visitas consecutivas
-- utilizando una función de ventana?

WITH ordered_encounters AS (
    SELECT
        patient_id,
        encounter_id,
        start_time,
        lag(start_time) OVER (
            PARTITION BY patient_id
            ORDER BY
                start_time,
                encounter_id
            ROWS BETWEEN UNBOUNDED PRECEDING
                AND CURRENT ROW
        ) AS previous_visit
    FROM encounters
),
visit_intervals AS (
    SELECT
        patient_id,
        encounter_id,
        date_diff(
            'day',
            previous_visit,
            start_time
        ) AS days_since_previous
    FROM ordered_encounters
    WHERE previous_visit IS NOT NULL
)
SELECT
    count(*) AS comparable_intervals,
    median(days_since_previous)::DOUBLE
        AS median_days
FROM visit_intervals;

-- ========================================
-- Fuente: 10_intervalos_self_join.sql
-- ========================================

-- QUERY: interval_summary_self_join
-- ¿Cuál es la mediana de días entre visitas consecutivas
-- utilizando un self-join?

WITH previous_encounters AS (
    SELECT
        current_visit.patient_id,
        current_visit.encounter_id,
        current_visit.start_time,
        max(previous_visit.start_time)
            AS previous_visit
    FROM encounters AS current_visit
    LEFT JOIN encounters AS previous_visit
        ON current_visit.patient_id
            = previous_visit.patient_id
       AND (
           previous_visit.start_time
               < current_visit.start_time
           OR (
               previous_visit.start_time
                   = current_visit.start_time
               AND previous_visit.encounter_id
                   < current_visit.encounter_id
           )
       )
    GROUP BY
        current_visit.patient_id,
        current_visit.encounter_id,
        current_visit.start_time
),
visit_intervals AS (
    SELECT
        patient_id,
        encounter_id,
        date_diff(
            'day',
            previous_visit,
            start_time
        ) AS days_since_previous
    FROM previous_encounters
    WHERE previous_visit IS NOT NULL
)
SELECT
    count(*) AS comparable_intervals,
    median(days_since_previous)::DOUBLE
        AS median_days
FROM visit_intervals;
