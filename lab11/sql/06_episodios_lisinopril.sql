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
