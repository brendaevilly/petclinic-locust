#!/usr/bin/env python3
"""Agrega as 60 execuções, gera CSVs, tabelas Markdown e gráficos."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"
TABLES = ROOT / "results" / "tables"
PLOTS = ROOT / "results" / "plots"

OPERATIONS = ["GET /owners", "GET /owners/{id}", "GET /vets", "POST /owners"]
PROFILE_LABEL = {"read": "Perfil 1 — Leitura", "write": "Perfil 2 — Escrita"}
SCENARIO_LABEL = {"A": "A — Leve (30)", "B": "B — Moderado (80)", "C": "C — Elevado (150)"}
CPU_CONTAINERS = ("api-gateway", "customers-service", "vets-service")


def load_runs() -> pd.DataFrame:
    rows: list[dict] = []
    if not RAW.exists():
        raise SystemExit(f"Pasta não encontrada: {RAW}")

    for meta_path in sorted(RAW.glob("*/meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        stats_path = meta_path.parent / "locust_stats.csv"
        if not stats_path.exists():
            print(f"Aviso: sem locust_stats.csv em {meta_path.parent.name}")
            continue
        stats = pd.read_csv(stats_path)
        stats.columns = [column.strip() for column in stats.columns]
        name_col = "Name" if "Name" in stats.columns else stats.columns[1]
        agg = stats[stats[name_col].astype(str).str.strip().eq("Aggregated")]
        if agg.empty:
            print(f"Aviso: sem linha Aggregated em {stats_path}")
            continue
        total = agg.iloc[0]
        request_count = float(total["Request Count"])
        failure_count = float(total["Failure Count"])
        row = {
            "profile": meta["profile"],
            "scenario": meta["scenario"],
            "users": int(meta["users"]),
            "repeat": int(meta["repeat"]),
            "run_id": meta_path.parent.name,
            "avg_ms": float(total["Average Response Time"]),
            "p95_ms": float(total["95%"]),
            "rps": float(total["Requests/s"]),
            "requests": request_count,
            "failures_pct": (failure_count / request_count * 100.0) if request_count else 0.0,
        }
        cpu = meta.get("cpu_avg_percent") or {}
        for container in CPU_CONTAINERS:
            row[f"cpu_{container}"] = float(cpu.get(container, float("nan")))

        for operation in OPERATIONS:
            op_rows = stats[stats[name_col].astype(str).str.strip().eq(operation)]
            if op_rows.empty:
                continue
            op = op_rows.iloc[0]
            prefix = operation
            row[f"{prefix} avg_ms"] = float(op["Average Response Time"])
            row[f"{prefix} p95_ms"] = float(op["95%"])
            row[f"{prefix} rps"] = float(op["Requests/s"])
            row[f"{prefix} requests"] = float(op["Request Count"])
            op_req = float(op["Request Count"])
            op_fail = float(op["Failure Count"])
            row[f"{prefix} failures_pct"] = (op_fail / op_req * 100.0) if op_req else 0.0

        rows.append(row)

    if not rows:
        raise SystemExit("Nenhuma execução válida encontrada em results/raw.")
    return pd.DataFrame(rows)


def mean_sem(series: pd.Series) -> tuple[float, float]:
    values = series.dropna()
    if values.empty:
        return float("nan"), float("nan")
    mean = float(values.mean())
    sem = float(values.std(ddof=1) / (len(values) ** 0.5)) if len(values) > 1 else 0.0
    return mean, sem


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for (profile, scenario), group in df.groupby(["profile", "scenario"], sort=True):
        rec = {
            "profile": profile,
            "scenario": scenario,
            "users": int(group["users"].iloc[0]),
            "n": int(len(group)),
        }
        for column in [
            "avg_ms",
            "p95_ms",
            "rps",
            "requests",
            "failures_pct",
            "cpu_api-gateway",
            "cpu_customers-service",
            "cpu_vets-service",
        ]:
            mean, sem = mean_sem(group[column])
            rec[f"{column}_mean"] = mean
            rec[f"{column}_sem"] = sem
        for operation in OPERATIONS:
            for metric in ("avg_ms", "p95_ms", "rps", "failures_pct"):
                column = f"{operation} {metric}"
                if column not in group.columns:
                    continue
                mean, sem = mean_sem(group[column])
                rec[f"{operation} {metric}_mean"] = mean
                rec[f"{operation} {metric}_sem"] = sem
        records.append(rec)
    return pd.DataFrame(records).sort_values(["profile", "users"])


def fmt(value: float, digits: int = 2) -> str:
    if pd.isna(value):
        return "—"
    return f"{value:.{digits}f}"


def write_markdown_tables(summary: pd.DataFrame) -> None:
    TABLES.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Tabelas agregadas (média ± erro padrão, aquecimento descartado)",
        "",
        "## Métricas globais por cenário",
        "",
        "| Perfil | Cenário | Usuários | N | Tempo médio (ms) | P95 (ms) | Vazão (req/s) | Total req. | Falhas (%) | CPU gateway (%) | CPU customers (%) | CPU vets (%) |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in summary.iterrows():
        lines.append(
            "| {profile} | {scenario} | {users} | {n} | {avg} | {p95} | {rps} | {req} | {fail} | {cpu_gw} | {cpu_cu} | {cpu_ve} |".format(
                profile=PROFILE_LABEL[row["profile"]],
                scenario=SCENARIO_LABEL[row["scenario"]],
                users=int(row["users"]),
                n=int(row["n"]),
                avg=f"{fmt(row['avg_ms_mean'])} ± {fmt(row['avg_ms_sem'])}",
                p95=f"{fmt(row['p95_ms_mean'])} ± {fmt(row['p95_ms_sem'])}",
                rps=f"{fmt(row['rps_mean'])} ± {fmt(row['rps_sem'])}",
                req=f"{fmt(row['requests_mean'], 0)} ± {fmt(row['requests_sem'], 0)}",
                fail=f"{fmt(row['failures_pct_mean'])} ± {fmt(row['failures_pct_sem'])}",
                cpu_gw=f"{fmt(row['cpu_api-gateway_mean'])} ± {fmt(row['cpu_api-gateway_sem'])}",
                cpu_cu=f"{fmt(row['cpu_customers-service_mean'])} ± {fmt(row['cpu_customers-service_sem'])}",
                cpu_ve=f"{fmt(row['cpu_vets-service_mean'])} ± {fmt(row['cpu_vets-service_sem'])}",
            )
        )

    lines += ["", "## Tempo médio (ms) por operação", "", "| Perfil | Cenário | " + " | ".join(OPERATIONS) + " |", "|---|---|" + "|".join(["---:"] * len(OPERATIONS)) + "|"]
    for _, row in summary.iterrows():
        cells = [fmt(row.get(f"{op} avg_ms_mean", float("nan"))) for op in OPERATIONS]
        lines.append(
            f"| {PROFILE_LABEL[row['profile']]} | {SCENARIO_LABEL[row['scenario']]} | " + " | ".join(cells) + " |"
        )

    lines += ["", "## P95 (ms) por operação", "", "| Perfil | Cenário | " + " | ".join(OPERATIONS) + " |", "|---|---|" + "|".join(["---:"] * len(OPERATIONS)) + "|"]
    for _, row in summary.iterrows():
        cells = [fmt(row.get(f"{op} p95_ms_mean", float("nan"))) for op in OPERATIONS]
        lines.append(
            f"| {PROFILE_LABEL[row['profile']]} | {SCENARIO_LABEL[row['scenario']]} | " + " | ".join(cells) + " |"
        )

    (TABLES / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_metric(summary: pd.DataFrame, mean_col: str, sem_col: str, ylabel: str, title: str, filename: str) -> None:
    PLOTS.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    for profile, marker in (("read", "o"), ("write", "s")):
        subset = summary[summary["profile"] == profile].sort_values("users")
        ax.errorbar(
            subset["users"],
            subset[mean_col],
            yerr=subset[sem_col],
            marker=marker,
            capsize=4,
            label=PROFILE_LABEL[profile],
        )
    ax.set_xlabel("Usuários virtuais")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_xticks([30, 80, 150])
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLOTS / filename, dpi=150)
    plt.close(fig)


def plot_operations(summary: pd.DataFrame) -> None:
    PLOTS.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for ax, profile in zip(axes, ("read", "write")):
        subset = summary[summary["profile"] == profile].sort_values("users")
        for operation in OPERATIONS:
            column = f"{operation} avg_ms_mean"
            if column not in subset.columns:
                continue
            ax.plot(subset["users"], subset[column], marker="o", label=operation)
        ax.set_title(PROFILE_LABEL[profile])
        ax.set_xlabel("Usuários virtuais")
        ax.set_xticks([30, 80, 150])
        ax.grid(True, linestyle="--", alpha=0.4)
    axes[0].set_ylabel("Tempo médio de resposta (ms)")
    axes[1].legend(loc="upper left")
    fig.suptitle("Degradação por operação")
    fig.tight_layout()
    fig.savefig(PLOTS / "tempo_por_operacao.png", dpi=150)
    plt.close(fig)


def plot_cpu(summary: pd.DataFrame) -> None:
    PLOTS.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    mapping = {
        "cpu_api-gateway_mean": "api-gateway",
        "cpu_customers-service_mean": "customers-service",
        "cpu_vets-service_mean": "vets-service",
    }
    for ax, profile in zip(axes, ("read", "write")):
        subset = summary[summary["profile"] == profile].sort_values("users")
        for column, label in mapping.items():
            ax.plot(subset["users"], subset[column], marker="o", label=label)
        ax.set_title(PROFILE_LABEL[profile])
        ax.set_xlabel("Usuários virtuais")
        ax.set_xticks([30, 80, 150])
        ax.grid(True, linestyle="--", alpha=0.4)
    axes[0].set_ylabel("CPU média (%)")
    axes[1].legend(loc="upper left")
    fig.suptitle("Utilização de CPU dos serviços")
    fig.tight_layout()
    fig.savefig(PLOTS / "cpu_servicos.png", dpi=150)
    plt.close(fig)


def build_answers(summary: pd.DataFrame) -> str:
    def pick(profile: str, scenario: str, column: str) -> float:
        match = summary[(summary["profile"] == profile) & (summary["scenario"] == scenario)]
        if match.empty or column not in match.columns:
            return float("nan")
        return float(match.iloc[0][column])

    lines = ["## Respostas automáticas (geradas a partir das médias)", ""]

    read_avgs = [pick("read", s, "avg_ms_mean") for s in ("A", "B", "C")]
    write_avgs = [pick("write", s, "avg_ms_mean") for s in ("A", "B", "C")]
    lines.append(
        "1. **Tempo de resposta vs usuários.** "
        f"No perfil de leitura o tempo médio foi {fmt(read_avgs[0])} ms (A), "
        f"{fmt(read_avgs[1])} ms (B) e {fmt(read_avgs[2])} ms (C). "
        f"No perfil de escrita: {fmt(write_avgs[0])}, {fmt(write_avgs[1])} e {fmt(write_avgs[2])} ms. "
        "O aumento de usuários eleva o tempo de resposta, com salto mais visível no cenário C."
    )

    rps_read = summary[summary["profile"] == "read"]["rps_mean"].mean()
    rps_write = summary[summary["profile"] == "write"]["rps_mean"].mean()
    winner = "leitura" if rps_read >= rps_write else "escrita"
    lines.append(
        f"2. **Maior vazão.** A vazão média do perfil de {winner} foi maior "
        f"(leitura {fmt(rps_read)} req/s vs escrita {fmt(rps_write)} req/s)."
    )

    degradations = []
    for profile in ("read", "write"):
        for operation in OPERATIONS:
            a = pick(profile, "A", f"{operation} avg_ms_mean")
            c = pick(profile, "C", f"{operation} avg_ms_mean")
            ratio = c / a if a else float("inf")
            degradations.append((ratio, profile, operation, a, c))
    degradations.sort(reverse=True)
    top = degradations[0]
    lines.append(
        "3. **Maior degradação.** A operação com maior aumento relativo de A para C foi "
        f"`{top[2]}` no perfil {top[1]} ({fmt(top[3])} ms → {fmt(top[4])} ms, fator {fmt(top[0])})."
    )

    cpu_c_read = pick("read", "C", "cpu_customers-service_mean")
    cpu_c_write = pick("write", "C", "cpu_customers-service_mean")
    cpu_g_c = pick("write", "C", "cpu_api-gateway_mean")
    lines.append(
        "4. **CPU.** O consumo cresce com a carga. No cenário C o customers-service ficou em "
        f"{fmt(cpu_c_read)}% (leitura) e {fmt(cpu_c_write)}% (escrita); "
        f"o api-gateway em escrita/C mediu {fmt(cpu_g_c)}%."
    )

    if summary["failures_pct_mean"].notna().any():
        fail_idx = summary["failures_pct_mean"].idxmax()
        fail_row = summary.loc[fail_idx]
        lines.append(
            "5. **Maior taxa de falhas.** "
            f"{PROFILE_LABEL[fail_row['profile']]}, {SCENARIO_LABEL[fail_row['scenario']]}: "
            f"{fmt(fail_row['failures_pct_mean'])}%."
        )
    else:
        lines.append("5. **Maior taxa de falhas.** Sem dados suficientes.")
    return "\n".join(lines) + "\n"


def patch_readme(summary: pd.DataFrame) -> None:
    readme = ROOT / "README.md"
    if not readme.exists():
        return
    text = readme.read_text(encoding="utf-8")
    tables = (TABLES / "summary.md").read_text(encoding="utf-8")
    answers = (TABLES / "respostas.md").read_text(encoding="utf-8")
    n = int(pd.read_csv(TABLES / "runs.csv").shape[0]) if (TABLES / "runs.csv").exists() else 0
    block_tables = f"<!-- BEGIN_RESULTS -->\n\n_{n} execuções agregadas._\n\n{tables}\n\n![Tempo médio](results/plots/tempo_medio.png)\n\n![P95](results/plots/tempo_p95.png)\n\n![Vazão](results/plots/vazao.png)\n\n![Falhas](results/plots/falhas.png)\n\n![CPU](results/plots/cpu_servicos.png)\n\n![Operações](results/plots/tempo_por_operacao.png)\n\n<!-- END_RESULTS -->"
    block_answers = f"<!-- BEGIN_ANSWERS -->\n\n{answers}\n<!-- END_ANSWERS -->"

    def replace_block(source: str, start: str, end: str, new_block: str) -> str:
        if start not in source or end not in source:
            return source
        before, rest = source.split(start, 1)
        _, after = rest.split(end, 1)
        return before + new_block + after

    text = replace_block(text, "<!-- BEGIN_RESULTS -->", "<!-- END_RESULTS -->", block_tables)
    text = replace_block(text, "<!-- BEGIN_ANSWERS -->", "<!-- END_ANSWERS -->", block_answers)
    readme.write_text(text, encoding="utf-8")


def main() -> int:
    df = load_runs()
    TABLES.mkdir(parents=True, exist_ok=True)
    PLOTS.mkdir(parents=True, exist_ok=True)
    df.to_csv(TABLES / "runs.csv", index=False)
    summary = summarize(df)
    summary.to_csv(TABLES / "summary.csv", index=False)
    write_markdown_tables(summary)
    (TABLES / "respostas.md").write_text(build_answers(summary), encoding="utf-8")
    plot_metric(summary, "avg_ms_mean", "avg_ms_sem", "Tempo médio (ms)", "Tempo médio de resposta", "tempo_medio.png")
    plot_metric(summary, "p95_ms_mean", "p95_ms_sem", "P95 (ms)", "Tempo de resposta P95", "tempo_p95.png")
    plot_metric(summary, "rps_mean", "rps_sem", "Vazão (req/s)", "Vazão agregada", "vazao.png")
    plot_metric(summary, "failures_pct_mean", "failures_pct_sem", "Falhas (%)", "Taxa de falhas", "falhas.png")
    plot_metric(summary, "requests_mean", "requests_sem", "Requisições", "Total de requisições (janela medida)", "requisicoes.png")
    plot_operations(summary)
    plot_cpu(summary)
    patch_readme(summary)
    print(f"Execuções lidas: {len(df)}")
    print(f"Tabelas em {TABLES}")
    print(f"Gráficos em {PLOTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
