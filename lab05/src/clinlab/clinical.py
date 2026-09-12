"""Clinical calculations with explicit units."""

import math
from typing import Literal


def egfr_ckd_epi_2021(
    creatinine_mg_dl: float,
    age_years: float,
    sex: Literal["female", "male"],
) -> float:
    """Estimate adult eGFR using the CKD-EPI creatinine equation (2021).

    Parameters

    ----------

    creatinine_mg_dl:

        Serum creatinine in mg/dL, standardized to IDMS.

        Must be finite and greater than zero.

    age_years:

        Age in years. Must be finite and at least 18.

    sex:

        Sex category used by the published equation: "female" or "male".

    Returns

    -------

    float

        Estimated GFR in mL/min/1.73 m², without rounding.

    Raises

    ------

    ValueError

        If creatinine, age, or sex does not meet the input contract.

    Notes

    -----

    Educational implementation; this result alone does not diagnose CKD.

    Reference:

    https://www.kidney.org/ckd-epi-creatinine-equation-2021

    """

    if not math.isfinite(creatinine_mg_dl) or creatinine_mg_dl <= 0:
        raise ValueError("Creatinine must be finite and greater than zero")

    if not math.isfinite(age_years) or age_years < 18:
        raise ValueError("Age must be finite and at least 18 years")

    if sex not in ("female", "male"):
        raise ValueError("Sex must be 'female' or 'male'")

    kappa = 0.7 if sex == "female" else 0.9

    alpha = -0.241 if sex == "female" else -0.302

    sex_factor = 1.012 if sex == "female" else 1.0

    ratio = creatinine_mg_dl / kappa

    return (
        142.0
        * math.pow(min(ratio, 1.0), alpha)
        * math.pow(max(ratio, 1.0), -1.200)
        * math.pow(0.9938, age_years)
        * sex_factor
    )
