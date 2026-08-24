
import argparse
import json
import threading
import time
from pathlib import Path

import pandas as pd
import psutil


def bytes_a_mib(numero_bytes):
    return numero_bytes / (1024 ** 2)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--metrics", required=True)
    parser.add_argument("--chunksize", type=int, default=100_000)
    parser.add_argument("--budget-mib", type=float, default=200)

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    metrics_path = Path(args.metrics)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    metrics_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    process = psutil.Process()

    baseline_bytes = process.memory_info().rss
    peak_bytes = baseline_bytes

    stop_monitor = threading.Event()

    def monitor_memory():
        nonlocal peak_bytes

        while not stop_monitor.is_set():
            current_bytes = process.memory_info().rss
            peak_bytes = max(
                peak_bytes,
                current_bytes,
            )
            time.sleep(0.01)

    monitor_thread = threading.Thread(
        target=monitor_memory,
        daemon=True,
    )

    monitor_thread.start()

    acumulado = None
    total_filas = 0
    total_bloques = 0

    inicio = time.perf_counter()

    lector = pd.read_csv(
        input_path,
        usecols=["CODE", "VALUE"],
        dtype={
            "CODE": "string",
            "VALUE": "string",
        },
        chunksize=args.chunksize,
    )

    for numero_bloque, chunk in enumerate(
        lector,
        start=1,
    ):
        value_numeric = pd.to_numeric(
            chunk["VALUE"],
            errors="coerce",
        ).astype("float64")

        datos_numericos = pd.DataFrame(
            {
                "CODE": chunk["CODE"],
                "VALUE_NUMERIC": value_numeric,
            }
        )

        grupo = datos_numericos.groupby(
            "CODE",
            observed=True,
        )

        resumen_bloque = grupo[
            "VALUE_NUMERIC"
        ].agg(
            n_numeric="count",
            suma_numeric="sum",
        )

        resumen_bloque["n_total"] = grupo.size()

        if acumulado is None:
            acumulado = resumen_bloque.copy()
        else:
            acumulado = acumulado.add(
                resumen_bloque,
                fill_value=0,
            )

        total_filas += len(chunk)
        total_bloques = numero_bloque

        if numero_bloque % 20 == 0:
            print(
                f"Bloque {numero_bloque:03d} | "
                f"filas: {total_filas:,}",
                flush=True,
            )

        del (
            chunk,
            value_numeric,
            datos_numericos,
            grupo,
            resumen_bloque,
        )

    tiempo_s = time.perf_counter() - inicio

    resultado = acumulado.reset_index()

    resultado["n_total"] = (
        resultado["n_total"].astype("int64")
    )

    resultado["n_numeric"] = (
        resultado["n_numeric"].astype("int64")
    )

    resultado["media_numeric"] = (
        resultado["suma_numeric"]
        / resultado["n_numeric"].where(
            resultado["n_numeric"] > 0
        )
    )

    resultado = resultado.sort_values(
        "n_total",
        ascending=False,
    )

    resultado.to_csv(
        output_path,
        index=False,
    )

    stop_monitor.set()
    monitor_thread.join()

    peak_mib = bytes_a_mib(peak_bytes)
    baseline_mib = bytes_a_mib(baseline_bytes)

    metricas = {
        "filas_procesadas": total_filas,
        "bloques_procesados": total_bloques,
        "chunksize": args.chunksize,
        "tiempo_s": tiempo_s,
        "memoria_inicial_mib": baseline_mib,
        "memoria_pico_mib": peak_mib,
        "incremento_pico_mib": (
            peak_mib - baseline_mib
        ),
        "presupuesto_mib": args.budget_mib,
        "cumple_presupuesto_absoluto": (
            peak_mib <= args.budget_mib
        ),
    }

    metrics_path.write_text(
        json.dumps(
            metricas,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            metricas,
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
