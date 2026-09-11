from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
from matplotlib import patches


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_INDEX_PATH = DATA_DIR / "grid_runs" / "grid_index.json"
DEFAULT_OUTPUT_PATH = DATA_DIR / "plots" / "grid_results_pies.png"


COLORS = {
    "share": "tab:blue",
    "hoard": "tab:orange",
    "mix": "tab:green",
}

fs = 20

def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def find_grid_index() -> Path:
    """Find the renamed grid index when no explicit path is provided."""
    candidates = sorted((DATA_DIR / "grid_runs").glob("grid_index_*.json"))
    if len(candidates) == 1:
        return candidates[0]
    if not candidates and DEFAULT_INDEX_PATH.exists():
        return DEFAULT_INDEX_PATH
    if not candidates:
        raise FileNotFoundError("No grid index JSON file was found.")
    raise ValueError("Multiple grid index files found; pass one with --index.")


def classify_batch(result: Dict[str, Any]) -> Tuple[List[int], int, float]:
    """Count outcomes and population in one batch."""
    counts = {"share": 0, "hoard": 0, "mix": 0}
    extinct_runs = 0
    total_population = 0.0

    for run in result.get("runs", []):
        share = float(run.get("share", 0.0))
        hoard = float(run.get("hoard", 0.0))
        population = share + hoard
        total_population += population

        if run.get("status") == "extinct" or population <= 0.0:
            extinct_runs += 1
            counts["mix"] += 1
            continue

        share_fraction = share / population
        hoard_fraction = hoard / population
        if share_fraction > 0.66:
            counts["share"] += 1
        elif hoard_fraction > 0.66:
            counts["hoard"] += 1
        else:
            counts["mix"] += 1

    return [counts["share"], counts["hoard"], counts["mix"]], extinct_runs, total_population


def format_value(value: float) -> str:
    return f"{value:g}"


def plot_grid(index_path: Path, output_path: Path) -> None:
    index = load_json(index_path)
    chang_values = [float(value) for value in index.get("rows", [])]
    decay_values = [float(value) for value in index.get("columns", [])]
    matrix = index.get("matrix", {})

    if not chang_values or not decay_values:
        raise ValueError(f"Grid index contains no rows or columns: {index_path}")

    figure_width = max(4.0 * len(decay_values), 8.0)
    figure_height = max(3.8 * len(chang_values), 5.0)
    fig, axes = plt.subplots(
        len(chang_values),
        len(decay_values),
        figsize=(figure_width, figure_height),
        squeeze=False,
    )

    legend_handles = []
    legend_labels = []
    for row_index, chang in enumerate(reversed(chang_values)):
        row_key = f"Chang={format_value(chang)}"
        row_data = matrix.get(row_key, {})
        for column_index, decay in enumerate(decay_values):
            ax = axes[row_index][column_index]
            column_key = f"Decay={format_value(decay)}"
            batch_reference = row_data.get(column_key)

            if not batch_reference:
                ax.text(0.5, 0.5, "No result", ha="center", va="center")
                ax.set_title(f"Decay={format_value(decay)}")
                ax.set_axis_off()
                continue

            batch_path = (BASE_DIR / batch_reference).resolve()
            if not batch_path.exists():
                ax.text(0.5, 0.5, "Missing result", ha="center", va="center")
                ax.set_title(f"Decay={format_value(decay)}")
                ax.set_axis_off()
                continue

            batch = load_json(batch_path)
            values, extinct_runs, total_population = classify_batch(batch)
            total_runs = sum(values)
            if total_runs == 0:
                ax.text(0.5, 0.5, "No runs", ha="center", va="center")
                ax.set_axis_off()
                continue

            batch_population = max(1, int(batch.get("N", 1)) * int(batch.get("S", total_runs)))
            pie_radius = math.sqrt(max(total_population, 1.0) / batch_population)*1.55
            extinct_fraction = extinct_runs / max(total_runs, 1)

            wedges, _, _ = ax.pie(
                values,
                labels=None,
                colors=[COLORS["share"], COLORS["hoard"], COLORS["mix"]],
                autopct="%1.0f%%",
                startangle=90,
                radius=pie_radius,
                wedgeprops={"linewidth": 0.8, "edgecolor": "white"},
                textprops={"fontsize": fs-2},
            )
            if row_index == 0:
                ax.set_title(f"Decay={format_value(1-decay)}", fontsize=fs)
            ax.set_aspect("equal")
            ax.add_patch(patches.Circle((0, 0), 1.3, facecolor="none",  edgecolor='k', linewidth=0.9))

            if not legend_handles:
                legend_handles = wedges
                legend_labels = ["share", "hoard", "mix"]

            if column_index == 0:
                ax.set_ylabel(f"Chang={format_value(chang)}", fontsize=fs)
            if extinct_runs:
                center_radius = math.sqrt(extinct_fraction)/1.2
                ax.add_patch(patches.Circle((0, 0), center_radius, color="black", alpha=1.0))
                #ax.text(0.5, -0.12, f"extinct: {extinct_runs}", transform=ax.transAxes, ha="center", va="top", fontsize=8)
                if extinct_fraction > 0.04:
                    ax.text(0.5, 0.5, f"{extinct_fraction:.0%}", transform=ax.transAxes, ha="center", va="center", color = "white", fontsize=fs-2)
            else:
                ax.add_patch(
                    patches.Circle(
                        (0, 0),
                        0.10,
                        facecolor="white",
                        edgecolor="white",
                        linewidth=0.1,
                    )
                )
        
                
    #fig.supxlabel("Decay", fontsize=12, y=0.055)
    #fig.supylabel("Chang", fontsize=12)
    fig.suptitle("Summary outcomes for Chang/Decay parameters", fontsize=fs+22)
    if legend_handles:
        fig.legend(legend_handles, legend_labels, loc="lower center", bbox_to_anchor=(0.5, 0.895),  ncol=3, frameon = False, fontsize=fs+8)
    fig.tight_layout(rect=(0.03, 0.12, 1.0, 0.94))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved grid plot to {output_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plot one share/hoard/mix pie chart for every Chang/Decay grid cell."
    )
    parser.add_argument("--index", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    plot_grid(args.index or find_grid_index(), args.output)


if __name__ == "__main__":
    main()
