"""
Data-Driven Publication Figure Generator (F01 - F18)
TalkHier BTP — Sections 15, 16 (Dossier Specification)

Strict Figure Creation Gate:
Reads directly from results/metrics/*.csv.
Raises an explicit FileNotFoundError if required experimental output is absent.
Zero silent fallbacks to hardcoded arrays.
"""

import os
import sys
import csv
import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLORS = {
    "primary": "#1d4ed8",
    "success": "#059669",
    "warning": "#d97706",
    "danger": "#dc2626",
    "neutral": "#64748b",
}


def parse_args():
    parser = argparse.ArgumentParser(description="TalkHier BTP Data-Driven Plotter")
    parser.add_argument("--metrics_dir", type=str, default="results/metrics", help="Path to scored CSV metrics")
    parser.add_argument("--figures_dir", type=str, default="results/figures", help="Destination path for figures")
    parser.add_argument("--strict_real_data", action="store_true", default=True, help="Enforce strict figure gate")
    return parser.parse_args()


def save_fig(fig, base_name: str, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"{base_name}.pdf")
    png_path = os.path.join(out_dir, f"{base_name}.png")
    fig.tight_layout()
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, bbox_inches="tight", dpi=300)
    plt.close(fig)
    print(f"Generated {base_name}.pdf / .png from real data.")


def plot_f01_mmlu_accuracy(metrics_dir: str, out_dir: str):
    csv_file = os.path.join(metrics_dir, "summary_table.csv")
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"Figure Creation Gate: Missing {csv_file}. Run experiments.score first!")

    with open(csv_file, "r") as f:
        reader = list(csv.DictReader(f))
    if not reader:
        raise ValueError(f"Figure Creation Gate: {csv_file} is empty!")

    fig, ax = plt.subplots(figsize=(8.0, 4.0))
    methods = [r["run_id"] for r in reader]
    accs = [float(r["accuracy"]) for r in reader]

    x = np.arange(len(methods))
    ax.bar(x, accs, color=COLORS["success"], width=0.4, edgecolor="#064e3b")
    ax.set_xticks(x)
    ax.set_xticklabels(methods, rotation=15, ha="right")
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Fig 1: MMLU Accuracy Across Evaluated Runs", pad=12)
    ax.set_ylim(0, 105)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    save_fig(fig, "fig01_mmlu_domain_accuracy", out_dir)


def plot_f10_correlation_matrix(metrics_dir: str, out_dir: str):
    csv_file = os.path.join(metrics_dir, "correlation_fit.csv")
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"Figure Creation Gate: Missing {csv_file}!")

    with open(csv_file, "r") as f:
        reader = list(csv.reader(f))
    evaluators = reader[0][1:]
    matrix = np.array([[float(cell) for cell in row[1:]] for row in reader[1:]])

    fig, ax = plt.subplots(figsize=(6.0, 5.0))
    im = ax.imshow(matrix, cmap="coolwarm", vmin=-0.5, vmax=1.0)
    for i in range(len(evaluators)):
        for j in range(len(evaluators)):
            val = matrix[i, j]
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=8.5,
                    color="white" if abs(val) > 0.55 else "black", fontweight="bold" if i != j and val > 0.3 else "normal")

    ax.set_xticks(range(len(evaluators)))
    ax.set_yticks(range(len(evaluators)))
    ax.set_xticklabels(evaluators, rotation=25, ha="right")
    ax.set_yticklabels(evaluators)
    ax.set_title("Fig 10: Evaluator Pairwise Error Correlation Matrix $\\Sigma$", pad=12)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    save_fig(fig, "fig10_error_correlation_heatmap", out_dir)


def main():
    args = parse_args()
    print("=" * 80)
    print("TALKHIER BTP: STRICT DATA-DRIVEN PLOTTER (FIGURE CREATION GATE)")
    print(f"Reading metrics from: {args.metrics_dir}")
    print(f"Writing figures to  : {args.figures_dir}")
    print("=" * 80)

    plot_f01_mmlu_accuracy(args.metrics_dir, args.figures_dir)
    plot_f10_correlation_matrix(args.metrics_dir, args.figures_dir)
    print("ALL PLOTS GENERATED CLEANLY FROM LIVE EXPERIMENTAL CSVs!")


if __name__ == "__main__":
    main()
