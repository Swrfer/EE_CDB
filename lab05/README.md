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
