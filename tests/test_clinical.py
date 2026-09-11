"""External reference tests for clinical calculations."""

from typing import Literal

import pytest

from clinlab import egfr_ckd_epi_2021


@pytest.mark.parametrize(
    ("creatinine_mg_dl", "age_years", "sex", "expected"),
    [
        pytest.param(0.4, 18, "female", 147, id="female-low-creatinine"),
        pytest.param(0.5, 25, "male", 145, id="male-low-creatinine"),
        pytest.param(0.7, 40, "female", 112, id="female-equation-threshold"),
        pytest.param(0.9, 40, "male", 111, id="male-equation-threshold"),
        pytest.param(1.5, 60, "female", 40, id="female-elevated-creatinine"),
        pytest.param(2.0, 65, "male", 36, id="male-elevated-creatinine"),
        pytest.param(5.0, 75, "female", 9, id="female-high-creatinine"),
        pytest.param(8.0, 80, "male", 6, id="male-high-creatinine"),
    ],
)
def test_egfr_coincide_con_referencia_externa(
    creatinine_mg_dl: float,
    age_years: float,
    sex: Literal["female", "male"],
    expected: float,
) -> None:
    """Compare eight cases against the NKF calculator.

    Source: https://www.kidney.org/professionals/gfr_calculator
    Equation: CKD-EPI creatinine equation (2021).
    Consultation date: 2026-09-10.
    All eight expected values were manually obtained by Alejandro
    Garcia Colorado from the external calculator.

    Inputs: creatinine in mg/dL, age in years, standardized assays,
    no cystatin C, and no adjustment for individual body surface area.
    Expected output: eGFR in mL/min/1.73 m².

    The calculator results were recorded as whole numbers.
    Absolute tolerance is 0.5 to accommodate rounding to the nearest
    integer; relative tolerance is disabled.
    """
    result = egfr_ckd_epi_2021(
        creatinine_mg_dl=creatinine_mg_dl,
        age_years=age_years,
        sex=sex,
    )

    assert result == pytest.approx(expected, abs=0.5, rel=0)
