# clinlab

[![Lab 05 CI](https://github.com/Swrfer/EE_CDB/actions/workflows/lab05-ci.yml/badge.svg)](https://github.com/Swrfer/EE_CDB/actions/workflows/lab05-ci.yml)

Paquete de Python para validar y resumir datos clínicos derivados del
laboratorio 2. Este laboratorio forma parte del repositorio central
[`EE_CDB`](https://github.com/Swrfer/EE_CDB).

## Instalación y pruebas desde un clon limpio

```bash
git clone git@github.com:Swrfer/EE_CDB.git
cd EE_CDB/lab05
python -m pip install -e ".[dev]"
python -m pytest

## Evidencias

- [01 — Pytest: prueba fallando en rojo](evidencias/lab05_01_pytest_rojo_fallo_esperado.png)
- [02 — Pytest: prueba corregida en verde](evidencias/lab05_02_pytest_verde_correccion.png)
- [03 — Pre-commit: commit rechazado por Ruff](evidencias/lab05_03_precommit_rojo_commit_rechazado.png)
- [04 — Pre-commit: corrección y commit aceptado](evidencias/lab05_04_precommit_verde_commit_aceptado.png)
- [05 — Referencia NKF: entrada del caso clínico 8](evidencias/lab05_05_referencia_nkf_caso_08_entrada.png)
- [06 — Suite completa y cobertura de 95.19 %](evidencias/lab05_06_pruebas_y_cobertura_95.png)
- [07 — Instalación y 58 pruebas desde un clon limpio](evidencias/lab05_07_clon_limpio_58_pruebas.png)
- [08 — GitHub Actions en verde](evidencias/lab05_08_ci_github_actions_verde.png)

El archivo [`precommit_demo.py`](evidencias/precommit_demo.py) conserva el
código corregido empleado en la demostración del hook.
