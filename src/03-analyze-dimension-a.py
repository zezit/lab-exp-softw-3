#!/usr/bin/env python3
"""
RQ01-RQ04 pipeline: pull request metrics vs. final feedback (MERGED/CLOSED).

This script reproduces the notebook flow in a regular Python script:
1. Load pull request data from data/pull_requests.csv
2. Validate the expected columns and clean numeric fields
3. Compare MERGED vs. CLOSED distributions with Mann-Whitney U tests
4. Generate box plots for each research question
5. Export summary CSV assets
"""

import argparse
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import matplotlib
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import mannwhitneyu


# Use a non-interactive backend so the script runs in terminal/CI.
matplotlib.use("Agg")
import matplotlib.pyplot as plt

STATUS_ORDER = ["MERGED", "CLOSED"]
STATUS_PALETTE = {"MERGED": "#2ca02c", "CLOSED": "#d62728"}
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
        "rq": "RQ01",
        "title": "Tamanho vs feedback final",
        "metrics": [
            ("changed_files", "Arquivos alterados"),
            ("additions", "Linhas adicionadas"),
            ("deletions", "Linhas removidas"),
        ],
        "figure": "rq01_size_vs_status.png",
    },
    {
        "rq": "RQ02",
        "title": "Tempo de analise vs feedback final",
        "metrics": [("time_to_close_hours", "Tempo para fechar (horas)")],
        "figure": "rq02_time_vs_status.png",
    },
    {
        "rq": "RQ03",
        "title": "Descricao vs feedback final",
        "metrics": [("body_length", "Tamanho da descricao (caracteres)")],
        "figure": "rq03_description_vs_status.png",
    },
    {
        "rq": "RQ04",
        "title": "Interacoes vs feedback final",
        "metrics": [
            ("participants_count", "Numero de participantes"),
            ("comments_count", "Numero de comentarios"),
        ],
        "figure": "rq04_interactions_vs_status.png",
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
    data = data[data["state"].isin(STATUS_ORDER)].copy()
    if data.empty:
        raise RuntimeError("No pull requests with state MERGED or CLOSED were found.")

    for col in NUMERIC_COLUMNS:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    return data


def mann_whitney_row(df: pd.DataFrame, rq: str, metric: str) -> Dict[str, float]:
    sub = df[["state", metric]].dropna().copy()
    merged = sub.loc[sub["state"] == "MERGED", metric]
    closed = sub.loc[sub["state"] == "CLOSED", metric]
    n_merged = int(len(merged))
    n_closed = int(len(closed))

    row: Dict[str, float] = {
        "rq": rq,
        "metric": metric,
        "merged_n": n_merged,
        "closed_n": n_closed,
        "merged_median": float(merged.median()) if n_merged else np.nan,
        "closed_median": float(closed.median()) if n_closed else np.nan,
        "u_statistic": np.nan,
        "p_value": np.nan,
        "rank_biserial_r": np.nan,
        "note": "",
    }

    if n_merged == 0 or n_closed == 0:
        row["note"] = "insufficient group data"
        return row

    if sub[metric].nunique(dropna=True) <= 1:
        total_pairs = n_merged * n_closed
        row["u_statistic"] = float(total_pairs / 2)
        row["p_value"] = 1.0
        row["rank_biserial_r"] = 0.0
        row["note"] = "all observations identical"
        return row

    try:
        result = mannwhitneyu(merged, closed, alternative="two-sided")
        total_pairs = n_merged * n_closed
        row["u_statistic"] = float(result.statistic)
        row["p_value"] = float(result.pvalue)
        row["rank_biserial_r"] = float(1 - (2 * result.statistic) / total_pairs)
        if merged.nunique(dropna=True) <= 1 or closed.nunique(dropna=True) <= 1:
            row["note"] = "constant values in at least one group"
    except ValueError as exc:
        row["note"] = str(exc)

    return row


def build_stats_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for rq_def in RQ_DEFINITIONS:
        for metric, _label in rq_def["metrics"]:
            rows.append(mann_whitney_row(df, rq_def["rq"], metric))
    return pd.DataFrame(rows)


def _style_axis(ax: plt.Axes, title: str, ylabel: str) -> None:
    ax.set_title(title)
    ax.set_xlabel("Status da PR")
    ax.set_ylabel(ylabel)
    ax.set_xticks(range(len(STATUS_ORDER)), STATUS_ORDER)


def _plot_empty_axis(ax: plt.Axes, title: str, ylabel: str, message: str) -> None:
    ax.set_title(title)
    ax.set_xlabel("Status da PR")
    ax.set_ylabel(ylabel)
    ax.text(0.5, 0.5, message, ha="center", va="center", transform=ax.transAxes)
    ax.set_xticks([])


def save_box_plots(df: pd.DataFrame, output_dir: Path) -> Iterable[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_paths: List[Path] = []

    for rq_def in RQ_DEFINITIONS:
        metrics: Sequence[tuple[str, str]] = rq_def["metrics"]
        fig, axes = plt.subplots(1, len(metrics), figsize=(6 * len(metrics), 5), squeeze=False)
        axes_flat = axes.flatten()

        for ax, (metric, label) in zip(axes_flat, metrics):
            plot_df = df[["state", metric]].dropna().copy()
            if plot_df.empty or plot_df["state"].nunique() < 2:
                _plot_empty_axis(ax, label, label, "Dados insuficientes para comparar MERGED e CLOSED")
                continue

            sns.boxplot(
                data=plot_df,
                x="state",
                y=metric,
                hue="state",
                order=STATUS_ORDER,
                hue_order=STATUS_ORDER,
                palette=STATUS_PALETTE,
                dodge=False,
                showfliers=False,
                width=0.55,
                ax=ax,
            )
            legend = ax.get_legend()
            if legend is not None:
                legend.remove()
            sns.stripplot(
                data=plot_df,
                x="state",
                y=metric,
                order=STATUS_ORDER,
                color="black",
                alpha=0.25,
                size=3,
                jitter=0.2,
                ax=ax,
            )
            _style_axis(ax, label, label)

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
    print("\nStatus distribution:")
    print(df["state"].value_counts().reindex(STATUS_ORDER, fill_value=0).to_string())

    print("\nOverall medians by status:")
    median_table = df.groupby("state")[NUMERIC_COLUMNS].median(numeric_only=True)
    median_table = median_table.reindex(STATUS_ORDER)
    print(median_table.to_string(float_format=lambda value: f"{value:.3f}"))

    print("\nMann-Whitney results:")
    display_cols = [
        "rq",
        "metric",
        "merged_n",
        "closed_n",
        "merged_median",
        "closed_median",
        "u_statistic",
        "p_value",
        "rank_biserial_r",
        "note",
    ]
    print(stats_df[display_cols].to_string(index=False, float_format=lambda value: f"{value:.6f}"))


def parse_args() -> argparse.Namespace:
    script_root = Path(__file__).resolve().parent.parent

    parser = argparse.ArgumentParser(
        description="Analyze pull request metrics vs. final PR status (MERGED/CLOSED)."
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

    print("Running Mann-Whitney U tests...")
    stats_df = build_stats_table(data)
    stats_path = summary_dir / "dimension_a_stats.csv"
    stats_df.to_csv(stats_path, index=False)

    print(f"Generating figures in {output_dir}...")
    figure_paths = list(save_box_plots(data, output_dir))

    print_overview(data, stats_df)
    print(f"\nStatistical summary saved: {stats_path}")
    print(f"Figures saved: {output_dir} ({len(figure_paths)} files)")


if __name__ == "__main__":
    main()
