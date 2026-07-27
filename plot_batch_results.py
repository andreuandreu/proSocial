from __future__ import annotations

import json
import math
from pathlib import Path
import sys
from typing import Any, Dict

import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def find_latest_batch_file(data_dir: Path) -> Path:
    files = sorted(data_dir.glob("*.json"))
    if not files:
        raise FileNotFoundError("No batch result files were found in the data directory.")
    return files[-1]


def load_batch_result(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def plot_batch_result(result: Dict[str, Any], output_path: Path) -> None:
    s = int(result.get("S", 1))
    n = int(result.get("N", result.get("config", {}).get("N", 1)))
    runs = result.get("runs", [])

    share_total = 0.0
    hoard_total = 0.0
    defect_total = 0.0
    extinct_runs = 0
    total_population = 0.0

    for run in runs:
        share = float(run.get("share", 0.0))
        hoard = float(run.get("hoard", 0.0))
        defect = float(run.get("defect", 0.0))
        population = share + hoard + defect
        total_population += population

        share_total += share
        hoard_total += hoard
        defect_total += defect

        if run.get("status") == "extinct" or population <= 0.0:
            extinct_runs += 1

    values = [share_total, hoard_total, defect_total]
    labels = ["share", "hoard", "defect"]

    if sum(values) <= 0:
        values = [1.0, 1.0, 1.0]

    default_total_population = max(1, n * s)
    pie_radius = math.sqrt(max(total_population, 1.0) / default_total_population)
    extinct_fraction = extinct_runs / max(len(runs), 1)

    if extinct_fraction <= 0.0:
        center_radius = 0.10
    else:
        center_radius = math.sqrt(extinct_fraction)

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.pie(
        values,
        labels=labels,
        autopct="%1.1f%%",
        startangle=90,
        radius=pie_radius,
        wedgeprops={"linewidth": 1.0, "edgecolor": "white"},
        textprops={"fontsize": 10},
    )

    ax.set_aspect("equal")
    ax.set_title(
        f"Behavior composition across {len(runs)} runs\nTotal population={total_population:.1f}, extinct={extinct_runs}/{len(runs)}",
        fontsize=12,
    )

    if extinct_fraction > 0.0:
        circle = plt.Circle((0, 0), center_radius, color="black", alpha=1.0)
        ax.add_patch(circle)
    else:
        circle = plt.Circle((0, 0), 0.10, color="white", edgecolor="black", linewidth=1.2)
        ax.add_patch(circle)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved plot to {output_path}")


def main() -> None:
    batch_file = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if batch_file is None:
        batch_file = find_latest_batch_file(DATA_DIR)
    else:
        batch_file = batch_file if batch_file.exists() else (DATA_DIR / batch_file.name)

    print(f"Loading batch result from {batch_file}")
    result = load_batch_result(batch_file)
    print(f"Batch result summary: {result.get('summary', {})}")
    output_path = DATA_DIR / "plots" / f"{batch_file.stem}_pie.png"
    plot_batch_result(result, output_path)


if __name__ == "__main__":
    main()
