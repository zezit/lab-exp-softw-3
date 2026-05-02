#!/usr/bin/env python3
"""
RQ05-RQ08 pipeline: pull request metrics vs. number of reviews.

This script reproduces the notebook flow in a regular Python script:
1. Load pull request data from data/pull_requests.csv
2. Validate the expected columns and clean numeric fields
3. Measure association with reviews_count using Spearman correlation
4. Generate scatter plots with LOWESS trend lines
5. Export summary CSV assets
"""

import argparse
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import matplotlib
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import spearmanr


# Use a non-interactive backend so the script runs in terminal/CI.
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REQUIRED_COLUMNS = {
    "repo",
    "state",
    "created_at",
    "closed_at",
    "time_to_close_hours",
    "changed_files",
    "additions",
    "deletions",
    "body_length",
    "participants_count",
    "comments_count",
    "reviews_count",
}
NUMERIC_COLUMNS = [
    "time_to_close_hours",
    "changed_files",
    "additions",
    "deletions",
    "body_length",
    "participants_count",
    "comments_count",
    "reviews_count",
]
RQ_DEFINITIONS = [
    {
        "rq": "RQ05",
        "title": "Tamanho vs numero de revisoes",
        "metrics": [
            ("changed_files", "Arquivos alterados"),
            ("additions", "Linhas adicionadas"),
            ("deletions", "Linhas removidas"),
        ],
        "figure": "rq05_size_vs_reviews.png",
    },
    {
        "rq": "RQ06",
        "title": "Tempo de analise vs numero de revisoes",
        "metrics": [("time_to_close_hours", "Tempo para fechar (horas)")],
        "figure": "rq06_time_vs_reviews.png",
    },
    {
        "rq": "RQ07",
        "title": "Descricao vs numero de revisoes",
        "metrics": [("body_length", "Tamanho da descricao (caracteres)")],
        "figure": "rq07_description_vs_reviews.png",
    },
    {
        "rq": "RQ08",
        "title": "Interacoes vs numero de revisoes",
        "metrics": [
            ("participants_count", "Numero de participantes"),
            ("comments_count", "Numero de comentarios"),
        ],
        "figure": "rq08_interactions_vs_reviews.png",
    },
]


def _resolve_path(project_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return project_root / path


def load_pull_requests(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {csv_path}")

    data = pd.read_csv(csv_path)
    missing = REQUIRED_COLUMNS.difference(data.columns)
    if missing:
        cols = ", ".join(sorted(missing))
        raise ValueError(f"Missing required columns in {csv_path}: {cols}")

    if data.empty:
        raise RuntimeError(f"Input CSV is empty: {csv_path}")

    data = data.copy()
    data["created_at"] = pd.to_datetime(data["created_at"], errors="coerce")
    data["closed_at"] = pd.to_datetime(data["closed_at"], errors="coerce")
    data["state"] = data["state"].astype("string").str.upper().str.strip()
    data = data[data["state"].isin(["MERGED", "CLOSED"])].copy()
    if data.empty:
        raise RuntimeError("No pull requests with state MERGED or CLOSED were found.")

    for col in NUMERIC_COLUMNS:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    return data


def spearman_row(df: pd.DataFrame, rq: str, metric: str) -> Dict[str, float]:
    sub = df[[metric, "reviews_count"]].dropna().copy()
    n = int(len(sub))
    row: Dict[str, float] = {
        "rq": rq,
        "metric": metric,
        "n": n,
        "metric_median": float(sub[metric].median()) if n else np.nan,
        "reviews_median": float(sub["reviews_count"].median()) if n else np.nan,
        "spearman_rho": np.nan,
        "p_value": np.nan,
        "note": "",
    }

    if n < 2:
        row["note"] = "insufficient data"
        return row

    if sub[metric].nunique(dropna=True) <= 1:
        row["note"] = f"{metric} has zero variance"
        return row

    if sub["reviews_count"].nunique(dropna=True) <= 1:
        row["note"] = "reviews_count has zero variance"
        return row

    rho, p_value = spearmanr(sub[metric], sub["reviews_count"])
    row["spearman_rho"] = float(rho)
    row["p_value"] = float(p_value)
    return row


def build_stats_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for rq_def in RQ_DEFINITIONS:
        for metric, _label in rq_def["metrics"]:
            rows.append(spearman_row(df, rq_def["rq"], metric))
    return pd.DataFrame(rows)


def _plot_empty_axis(ax: plt.Axes, title: str, xlabel: str, message: str) -> None:
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Numero de revisoes")
    ax.text(0.5, 0.5, message, ha="center", va="center", transform=ax.transAxes)
    ax.set_xticks([])
    ax.set_yticks([])


def save_scatter_plots(df: pd.DataFrame, output_dir: Path) -> Iterable[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_paths: List[Path] = []

    for rq_def in RQ_DEFINITIONS:
        metrics: Sequence[tuple[str, str]] = rq_def["metrics"]
        fig, axes = plt.subplots(1, len(metrics), figsize=(6 * len(metrics), 5), squeeze=False)
        axes_flat = axes.flatten()

        for ax, (metric, label) in zip(axes_flat, metrics):
            plot_df = df[[metric, "reviews_count"]].dropna().copy()
            if plot_df.empty:
                _plot_empty_axis(ax, label, label, "Nao ha dados suficientes para o grafico")
                continue

            if plot_df[metric].nunique(dropna=True) <= 1 or plot_df["reviews_count"].nunique(dropna=True) <= 1:
                sns.scatterplot(
                    data=plot_df,
                    x=metric,
                    y="reviews_count",
                    color="#1f77b4",
                    alpha=0.45,
                    s=36,
                    ax=ax,
                )
                ax.text(
                    0.05,
                    0.95,
                    "Variacao insuficiente para LOWESS",
                    transform=ax.transAxes,
                    ha="left",
                    va="top",
                )
            else:
                sns.regplot(
                    data=plot_df,
                    x=metric,
                    y="reviews_count",
                    lowess=True,
                    scatter_kws={"s": 28, "alpha": 0.35, "color": "#1f77b4"},
                    line_kws={"color": "#ff7f0e", "linewidth": 2},
                    ax=ax,
                )

            ax.set_title(label)
            ax.set_xlabel(label)
            ax.set_ylabel("Numero de revisoes")

        fig.suptitle(f"{rq_def['rq']} - {rq_def['title']}", fontsize=14)
        fig.tight_layout()
        fig.subplots_adjust(top=0.86)

        fig_path = output_dir / rq_def["figure"]
        fig.savefig(fig_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        saved_paths.append(fig_path)

    return saved_paths


def print_overview(df: pd.DataFrame, stats_df: pd.DataFrame) -> None:
    print(f"Loaded {len(df)} pull requests.")
    print("\nDescriptive summary:")
    describe_cols = [
        "reviews_count",
        "changed_files",
        "additions",
        "deletions",
        "time_to_close_hours",
        "body_length",
        "participants_count",
        "comments_count",
    ]
    print(df[describe_cols].describe().to_string(float_format=lambda value: f"{value:.3f}"))

    print("\nSpearman results:")
    display_cols = [
        "rq",
        "metric",
        "n",
        "metric_median",
        "reviews_median",
        "spearman_rho",
        "p_value",
        "note",
    ]
    print(stats_df[display_cols].to_string(index=False, float_format=lambda value: f"{value:.6f}"))


def parse_args() -> argparse.Namespace:
    script_root = Path(__file__).resolve().parent.parent

    parser = argparse.ArgumentParser(
        description="Analyze pull request metrics vs. number of reviews."
    )
    parser.add_argument(
        "--input",
        default="data/pull_requests.csv",
        help="Pull requests CSV path (relative to project root by default).",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/figures",
        help="Directory to write figure files.",
    )
    parser.add_argument(
        "--project-root",
        default=str(script_root),
        help=f"Project root directory (default: {script_root})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    input_path = _resolve_path(project_root, args.input)
    output_dir = _resolve_path(project_root, args.output_dir)
    summary_dir = project_root / "data" / "summary"

    summary_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    pd.options.display.float_format = "{:.3f}".format
    sns.set_theme(style="whitegrid")

    print(f"Loading dataset from {input_path}...")
    data = load_pull_requests(input_path)

    print("Running Spearman correlations...")
    stats_df = build_stats_table(data)
    stats_path = summary_dir / "dimension_b_stats.csv"
    stats_df.to_csv(stats_path, index=False)

    print(f"Generating figures in {output_dir}...")
    figure_paths = list(save_scatter_plots(data, output_dir))

    print_overview(data, stats_df)
    print(f"\nStatistical summary saved: {stats_path}")
    print(f"Figures saved: {output_dir} ({len(figure_paths)} files)")


if __name__ == "__main__":
    main()
