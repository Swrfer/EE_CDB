import argparse
import csv
import json
import math
import threading
import time
from collections import defaultdict
from pathlib import Path

import psutil


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archivo", required=True)
    parser.add_argument("--presupuesto-mib", type=float, default=200.0)
    parser.add_argument(
        "--salida-resultados",
        default="results/actividad7_resultados_streaming.csv",
    )
    parser.add_argument(
        "--salida-metricas",
        default="results/actividad7_metricas_streaming.json",
    )
    args = parser.parse_args()

    archivo = Path(args.archivo)
    salida_resultados = Path(args.salida_resultados)
    salida_metricas = Path(args.salida_metricas)

    salida_resultados.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    salida_metricas.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    proceso = psutil.Process()
    memoria_inicial = proceso.memory_info().rss
    memoria_pico = memoria_inicial
    detener_monitor = threading.Event()

    def monitor_memoria():
        nonlocal memoria_pico

        while not detener_monitor.is_set():
            memoria_actual = proceso.memory_info().rss
            memoria_pico = max(
                memoria_pico,
                memoria_actual,
            )
            detener_monitor.wait(0.01)

    monitor = threading.Thread(
        target=monitor_memoria,
        daemon=True,
    )
    monitor.start()

    n_total = defaultdict(int)
    n_numeric = defaultdict(int)
    suma_numeric = defaultdict(float)

    filas_procesadas = 0
    inicio = time.perf_counter()

    try:
        with archivo.open(
            mode="r",
            encoding="utf-8",
            newline="",
        ) as archivo_csv:

            lector = csv.reader(archivo_csv)
            encabezado = next(lector)

            indice_code = encabezado.index("CODE")
            indice_value = encabezado.index("VALUE")

            for fila in lector:
                codigo = fila[indice_code]
                valor = fila[indice_value]

                n_total[codigo] += 1
                filas_procesadas += 1

                if valor != "":
                    try:
                        valor_numerico = float(valor)

                        if math.isfinite(valor_numerico):
                            n_numeric[codigo] += 1
                            suma_numeric[codigo] += valor_numerico

                    except ValueError:
                        pass

                if filas_procesadas % 2_000_000 == 0:
                    print(
                        "Filas procesadas:",
                        f"{filas_procesadas:,}",
                        flush=True,
                    )

    finally:
        detener_monitor.set()
        monitor.join()

    tiempo_total = time.perf_counter() - inicio

    memoria_inicial_mib = memoria_inicial / (1024 ** 2)
    memoria_pico_mib = memoria_pico / (1024 ** 2)
    incremento_pico_mib = (
        memoria_pico - memoria_inicial
    ) / (1024 ** 2)

    with salida_resultados.open(
        mode="w",
        encoding="utf-8",
        newline="",
    ) as archivo_salida:

        columnas = [
            "CODE",
            "n_numeric",
            "suma_numeric",
            "n_total",
            "media_numeric",
        ]

        escritor = csv.DictWriter(
            archivo_salida,
            fieldnames=columnas,
        )
        escritor.writeheader()

        for codigo in sorted(n_total):
            cantidad_numerica = n_numeric[codigo]
            suma = suma_numeric[codigo]

            media = (
                suma / cantidad_numerica
                if cantidad_numerica > 0
                else ""
            )

            escritor.writerow(
                {
                    "CODE": codigo,
                    "n_numeric": cantidad_numerica,
                    "suma_numeric": suma,
                    "n_total": n_total[codigo],
                    "media_numeric": media,
                }
            )

    metricas = {
        "filas_procesadas": filas_procesadas,
        "metodo": "csv.reader fila por fila",
        "tiempo_s": tiempo_total,
        "memoria_inicial_mib": memoria_inicial_mib,
        "memoria_pico_mib": memoria_pico_mib,
        "incremento_pico_mib": incremento_pico_mib,
        "presupuesto_mib": args.presupuesto_mib,
        "cumple_presupuesto_absoluto": (
            memoria_pico_mib <= args.presupuesto_mib
        ),
    }

    with salida_metricas.open(
        mode="w",
        encoding="utf-8",
    ) as archivo_metricas:
        json.dump(
            metricas,
            archivo_metricas,
            indent=2,
            ensure_ascii=False,
        )

    print(json.dumps(
        metricas,
        indent=2,
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
