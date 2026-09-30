CREATE TABLE IF NOT EXISTS cdm.patient_demo (
    patient_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    patient_code TEXT NOT NULL UNIQUE,
    sex TEXT,
    birth_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS results.analysis_run (
    run_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    analysis_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'created',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO cdm.patient_demo (
    patient_code,
    sex,
    birth_date
)
VALUES (
    'LAB07-P001',
    'male',
    DATE '1986-01-15'
)
ON CONFLICT (patient_code) DO NOTHING;

CREATE TABLE IF NOT EXISTS results.quality_check (
    check_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    check_name TEXT NOT NULL,
    passed BOOLEAN NOT NULL,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
