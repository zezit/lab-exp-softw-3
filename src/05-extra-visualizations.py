#!/usr/bin/env python3
"""Generate extra presentation-ready visualizations for the pull request dataset."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.lines import Line2D

matplotlib.use("Agg")
import matplotlib.pyplot as plt

STATUS_ORDER = ["MERGED", "CLOSED"]
STATUS_PALETTE = {"MERGED": "#2ca02c", "CLOSED": "#d62728"}
NUMERIC_COLUMNS = [
    "changed_files",
    "additions",
    "deletions",
    "time_to_close_hours",
    "body_length",
    "participants_count",
    "comments_count",
    "reviews_count",
]
DIMENSION_A_METRICS = [
    "changed_files",
    "additions",
    "deletions",
    "time_to_close_hours",
    "body_length",
    "participants_count",
    "comments_count",
]
LOG_SCALE_METRICS = {"additions", "deletions", "time_to_close_hours", "body_length"}
METRIC_LABELS = {
    "changed_files": "Arquivos alterados",
    "additions": "Linhas adicionadas",
    "deletions": "Linhas removidas",
    "time_to_close_hours": "Tempo para fechar (horas)",
    "body_length": "Tamanho da descrição (caracteres)",
    "participants_count": "Número de participantes",
    "comments_count": "Número de comentários",
    "reviews_count": "Número de revisões",
}
FIGURE_FILENAMES = [
    "dataset_overview.png",
    "violin_plots_dim_a.png",
    "correlation_heatmap.png",
    "summary_table_dim_a.png",
    "summary_table_dim_b.png",
    "metric_distributions.png",
    "effect_sizes_dim_a.png",
    "correlation_bars_dim_b.png",
]
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


def _resolve_path(project_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return project_root / path


def _format_number(value: float) -> str:
    if pd.isna(value):
        return "-"
    return f"{value:.2f}"


def _format_p_value(value: float) -> str:
    if pd.isna(value):
        return "-"
    return f"{value:.2e}"


def load_pull_requests(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"Arquivo de entrada não encontrado: {csv_path}")

    data = pd.read_csv(csv_path)
    missing = REQUIRED_COLUMNS.difference(data.columns)
    if missing:
        missing_cols = ", ".join(sorted(missing))
        raise ValueError(f"Colunas obrigatórias ausentes em {csv_path}: {missing_cols}")

    data = data.copy()
    data["state"] = data["state"].astype("string").str.upper().str.strip()
    data = data[data["state"].isin(STATUS_ORDER)].copy()
    if data.empty:
        raise RuntimeError("Nenhuma PR com estado MERGED ou CLOSED foi encontrada.")

    for column in NUMERIC_COLUMNS:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    return data


def load_summary(csv_path: Path, required_columns: Sequence[str]) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"Arquivo de resumo não encontrado: {csv_path}")

    df = pd.read_csv(csv_path)
    missing = set(required_columns).difference(df.columns)
    if missing:
        missing_cols = ", ".join(sorted(missing))
        raise ValueError(f"Colunas obrigatórias ausentes em {csv_path}: {missing_cols}")
    return df


def save_dataset_overview(df: pd.DataFrame, output_path: Path) -> Path:
    counts = df["state"].value_counts().reindex(STATUS_ORDER, fill_value=0)
    colors = [STATUS_PALETTE[state] for state in STATUS_ORDER]

    fig, ax = plt.subplots(figsize=(8, 6))

    bars = ax.bar(STATUS_ORDER, counts.values, color=colors, width=0.5)
    ax.set_title("Distribuição de PRs por Estado", fontsize=14, fontweight="bold")
    ax.set_xlabel("Estado")
    ax.set_ylabel("Número de PRs")
    ax.set_ylim(0, counts.max() * 1.18)
    total = counts.sum()
    for bar, count in zip(bars, counts.values):
        pct = count / total * 100
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + counts.max() * 0.02,
            f"{int(count):,} ({pct:.1f}%)".replace(",", "."),
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold",
        )

    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return output_path


def save_violin_plots(df: pd.DataFrame, output_path: Path) -> Path:
    fig, axes = plt.subplots(2, 4, figsize=(16, 9))
    axes_flat = axes.flatten()

    for ax, metric in zip(axes_flat, DIMENSION_A_METRICS):
        plot_df = df[["state", metric]].dropna().copy()
        sns.violinplot(
            data=plot_df,
            x="state",
            y=metric,
            hue="state",
            order=STATUS_ORDER,
            hue_order=STATUS_ORDER,
            palette=STATUS_PALETTE,
            inner=None,
            cut=0,
            linewidth=1,
            dodge=False,
            legend=False,
            ax=ax,
        )
        legend = ax.get_legend()
        if legend is not None:
            legend.remove()

        for idx, state in enumerate(STATUS_ORDER):
            median_value = plot_df.loc[plot_df["state"] == state, metric].median()
            if pd.notna(median_value):
                ax.hlines(median_value, idx - 0.20, idx + 0.20, color="black", linewidth=2.2)

        ax.set_title(METRIC_LABELS[metric])
        ax.set_xlabel("Estado")
        ax.set_ylabel(METRIC_LABELS[metric])

    for ax in axes_flat[len(DIMENSION_A_METRICS):]:
        ax.axis("off")

    fig.suptitle("Distribuições por estado da PR (violino com mediana)", fontsize=16)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return output_path


def save_violin_plots_trimmed(df: pd.DataFrame, output_path: Path) -> Path:
    """Violin plots with y-axis clipped to IQR*1.5 for better readability."""
    fig, axes = plt.subplots(2, 4, figsize=(16, 9))
    axes_flat = axes.flatten()

    for ax, metric in zip(axes_flat, DIMENSION_A_METRICS):
        plot_df = df[["state", metric]].dropna().copy()
        q1 = plot_df[metric].quantile(0.25)
        q3 = plot_df[metric].quantile(0.75)
        iqr = q3 - q1
        lower = max(plot_df[metric].min(), q1 - 1.5 * iqr)
        upper = q3 + 1.5 * iqr
        clipped = plot_df[plot_df[metric].between(lower, upper)]

        sns.violinplot(
            data=clipped,
            x="state",
            y=metric,
            hue="state",
            order=STATUS_ORDER,
            hue_order=STATUS_ORDER,
            palette=STATUS_PALETTE,
            inner=None,
            cut=0,
            linewidth=1,
            dodge=False,
            legend=False,
            ax=ax,
        )
        legend = ax.get_legend()
        if legend is not None:
            legend.remove()

        for idx, state in enumerate(STATUS_ORDER):
            median_value = clipped.loc[clipped["state"] == state, metric].median()
            if pd.notna(median_value):
                ax.hlines(median_value, idx - 0.20, idx + 0.20, color="black", linewidth=2.2)

        ax.set_title(METRIC_LABELS[metric])
        ax.set_xlabel("Estado")
        ax.set_ylabel(METRIC_LABELS[metric])

    for ax in axes_flat[len(DIMENSION_A_METRICS):]:
        ax.axis("off")

    fig.suptitle("Distribuições por estado (sem outliers — IQR×1.5)", fontsize=16)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return output_path


def save_correlation_heatmap(df: pd.DataFrame, output_path: Path) -> Path:
    corr = df[NUMERIC_COLUMNS].corr(method="spearman")

    fig, ax = plt.subplots(figsize=(12, 9))
    sns.heatmap(
        corr,
        cmap="RdBu_r",
        vmin=-1,
        vmax=1,
        center=0,
        annot=True,
        fmt=".2f",
        linewidths=0.5,
        cbar_kws={"label": "Correlação de Spearman"},
        xticklabels=[METRIC_LABELS[col] for col in corr.columns],
        yticklabels=[METRIC_LABELS[col] for col in corr.index],
        ax=ax,
    )
    ax.set_title("Mapa de calor das correlações entre métricas numéricas")
    plt.setp(ax.get_xticklabels(), rotation=35, ha="right")
    plt.setp(ax.get_yticklabels(), rotation=0)

    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return output_path


def _render_table_image(
    df: pd.DataFrame,
    output_path: Path,
    title: str,
    highlight_mask: pd.Series,
) -> Path:
    fig_height = 1.4 + (len(df) + 1) * 0.5
    fig, ax = plt.subplots(figsize=(16, fig_height))
    ax.axis("off")
    ax.set_title(title, fontsize=16, pad=18)

    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        cellLoc="center",
        loc="center",
        bbox=[0, 0, 1, 0.88],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.7)

    header_color = "#d9e2f3"
    highlight_color = "#e6f4ea"

    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#b0b0b0")
        if row == 0:
            cell.set_facecolor(header_color)
            cell.set_text_props(weight="bold")
        elif highlight_mask.iloc[row - 1]:
            cell.set_facecolor(highlight_color)

    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return output_path


def save_summary_table_dim_a(stats_df: pd.DataFrame, output_path: Path) -> Path:
    table_df = pd.DataFrame(
        {
            "RQ": stats_df["rq"],
            "Métrica": stats_df["metric"].map(METRIC_LABELS),
            "Mediana MERGED": stats_df["merged_median"].map(_format_number),
            "Mediana CLOSED": stats_df["closed_median"].map(_format_number),
            "U": stats_df["u_statistic"].map(_format_number),
            "p-valor": stats_df["p_value"].map(_format_p_value),
            "r (efeito)": stats_df["rank_biserial_r"].map(_format_number),
        }
    )
    highlight_mask = stats_df["p_value"].fillna(1.0) < 0.05
    return _render_table_image(
        table_df,
        output_path,
        "Resumo dos resultados da Dimensão A",
        highlight_mask,
    )


def save_summary_table_dim_b(stats_df: pd.DataFrame, output_path: Path) -> Path:
    table_df = pd.DataFrame(
        {
            "RQ": stats_df["rq"],
            "Métrica": stats_df["metric"].map(METRIC_LABELS),
            "n": stats_df["n"].fillna(0).astype(int).astype(str),
            "Mediana Métrica": stats_df["metric_median"].map(_format_number),
            "Mediana Reviews": stats_df["reviews_median"].map(_format_number),
            "ρ (Spearman)": stats_df["spearman_rho"].map(_format_number),
            "p-valor": stats_df["p_value"].map(_format_p_value),
        }
    )
    highlight_mask = stats_df["p_value"].fillna(1.0) < 0.05
    return _render_table_image(
        table_df,
        output_path,
        "Resumo dos resultados da Dimensão B",
        highlight_mask,
    )


def save_metric_distributions(df: pd.DataFrame, output_path: Path) -> Path:
    fig, axes = plt.subplots(2, 4, figsize=(16, 9))
    axes_flat = axes.flatten()

    for ax, metric in zip(axes_flat, NUMERIC_COLUMNS):
        valid = df[metric].dropna()
        sns.histplot(valid, bins=35, color="#4c72b0", edgecolor="white", ax=ax)
        median_value = valid.median()
        ax.axvline(median_value, color="#d62728", linestyle="--", linewidth=2)
        ax.set_title(METRIC_LABELS[metric])
        ax.set_xlabel(METRIC_LABELS[metric])
        ax.set_ylabel("Frequência")
        if metric in LOG_SCALE_METRICS:
            ax.set_xscale("symlog", linthresh=1)

    fig.suptitle("Distribuição das métricas numéricas", fontsize=16)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return output_path


def save_effect_sizes_dim_a(stats_df: pd.DataFrame, output_path: Path) -> Path:
    plot_df = stats_df.copy()
    plot_df["label"] = plot_df["rq"] + " — " + plot_df["metric"].map(METRIC_LABELS)
    plot_df = plot_df.sort_values("rank_biserial_r")
    plot_df["color"] = np.where(plot_df["p_value"] < 0.05, "#2ca02c", "#9e9e9e")

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.barh(plot_df["label"], plot_df["rank_biserial_r"], color=plot_df["color"])
    ax.axvline(0, color="black", linewidth=1.2)
    ax.set_title("Tamanhos de efeito da Dimensão A")
    ax.set_xlabel("r bisserial de postos")
    ax.set_ylabel("Métrica")

    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return output_path


def _strength_category(rho: float) -> str:
    absolute = abs(rho)
    if absolute >= 0.5:
        return "Forte"
    if absolute >= 0.3:
        return "Moderada"
    return "Fraca"


def save_correlation_bars_dim_b(stats_df: pd.DataFrame, output_path: Path) -> Path:
    colors = {"Fraca": "#9ecae1", "Moderada": "#3182bd", "Forte": "#08519c"}
    plot_df = stats_df.copy()
    plot_df["label"] = plot_df["rq"] + " — " + plot_df["metric"].map(METRIC_LABELS)
    plot_df["strength"] = plot_df["spearman_rho"].map(_strength_category)
    plot_df = plot_df.sort_values("spearman_rho")

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.barh(
        plot_df["label"],
        plot_df["spearman_rho"],
        color=plot_df["strength"].map(colors),
    )
    for value in [0.1, 0.3, 0.5]:
        ax.axvline(value, color="#6b6b6b", linestyle="--", linewidth=1)
    ax.axvline(0, color="black", linewidth=1.2)
    ax.set_title("Correlação entre métricas e número de revisões")
    ax.set_xlabel("ρ de Spearman")
    ax.set_ylabel("Métrica")

    legend_handles = [
        Line2D([0], [0], color=color, lw=8, label=label) for label, color in colors.items()
    ]
    ax.legend(handles=legend_handles, title="Força", loc="lower right")

    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return output_path


def verify_outputs(paths: Iterable[Path]) -> None:
    missing_or_empty = [path for path in paths if not path.exists() or path.stat().st_size <= 0]
    if missing_or_empty:
        details = ", ".join(str(path) for path in missing_or_empty)
        raise RuntimeError(f"Arquivos ausentes ou vazios: {details}")


def parse_args() -> argparse.Namespace:
    script_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Gerar visualizações extras para apresentação.")
    parser.add_argument("--input", default="data/pull_requests.csv", help="CSV principal das pull requests.")
    parser.add_argument(
        "--dimension-a-stats",
        default="data/summary/dimension_a_stats.csv",
        help="CSV resumo da Dimensão A.",
    )
    parser.add_argument(
        "--dimension-b-stats",
        default="data/summary/dimension_b_stats.csv",
        help="CSV resumo da Dimensão B.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/figures",
        help="Diretório de saída das figuras.",
    )
    parser.add_argument(
        "--project-root",
        default=str(script_root),
        help=f"Diretório raiz do projeto (padrão: {script_root})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    input_path = _resolve_path(project_root, args.input)
    dimension_a_stats_path = _resolve_path(project_root, args.dimension_a_stats)
    dimension_b_stats_path = _resolve_path(project_root, args.dimension_b_stats)
    output_dir = _resolve_path(project_root, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    sns.set_theme(style="whitegrid")
    pd.options.display.float_format = "{:.3f}".format

    print(f"Carregando dados de {input_path}...")
    data = load_pull_requests(input_path)
    dim_a_stats = load_summary(
        dimension_a_stats_path,
        ["rq", "metric", "merged_median", "closed_median", "u_statistic", "p_value", "rank_biserial_r"],
    )
    dim_b_stats = load_summary(
        dimension_b_stats_path,
        ["rq", "metric", "n", "metric_median", "reviews_median", "spearman_rho", "p_value"],
    )

    output_paths = [
        save_dataset_overview(data, output_dir / "dataset_overview.png"),
        save_violin_plots(data, output_dir / "violin_plots_dim_a.png"),
        save_correlation_heatmap(data, output_dir / "correlation_heatmap.png"),
        save_summary_table_dim_a(dim_a_stats, output_dir / "summary_table_dim_a.png"),
        save_summary_table_dim_b(dim_b_stats, output_dir / "summary_table_dim_b.png"),
        save_metric_distributions(data, output_dir / "metric_distributions.png"),
        save_effect_sizes_dim_a(dim_a_stats, output_dir / "effect_sizes_dim_a.png"),
        save_correlation_bars_dim_b(dim_b_stats, output_dir / "correlation_bars_dim_b.png"),
    ]

    verify_outputs(output_paths)

    print("Visualizações geradas com sucesso:")
    for path in output_paths:
        print(f"- {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
