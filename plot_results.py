from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np



BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "simulation_results.json"
OUTPUT_DIR = BASE_DIR / "data" / "plots"

window_size = 1  # Size of the moving average window


def load_results(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
    
def movingaverage(interval, window_size):
    window= np.ones(int(window_size))/float(window_size)
    return np.convolve(interval, window, 'same')


def plot_results(results: dict) -> None:
    history = results.get("history", [])
    if not history:
        raise ValueError("No simulation history found in the results file.")

    ticks = [entry["tick"] for entry in history]
    environments = [entry["environment"] for entry in history]
    resources = [entry["resources_produced"] for entry in history]
    behavior_counts = [entry.get("behavior_counts", {}) for entry in history]

    env_to_num = {"scarce": 0, "neutral": 1, "abundant": 2}
    env_series = [env_to_num[env] for env in environments]

    share_counts = [counts.get("share", 0) for counts in behavior_counts]
    hoard_counts = [counts.get("hoard", 0) for counts in behavior_counts]
    defect_counts = [counts.get("defect", 0) for counts in behavior_counts]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    ax1 = axes[0]
    share_counts = movingaverage(share_counts, window_size)
    hoard_counts = movingaverage(hoard_counts, window_size)
    defect_counts = movingaverage(defect_counts, window_size)
    ax1.plot(ticks, share_counts, label="share", ls = "--",  linewidth=1.5)
    ax1.plot(ticks, hoard_counts, label="hoard", ls = "-.",  linewidth=1.5)
    ax1.plot(ticks, defect_counts, label="defect", ls = "-",  linewidth=1.5)
    ax1.set_ylabel("Agent count")
    ax1.set_title("Behavior distribution over time")
    ax1.legend()
    ax1.grid(alpha=0.3)

    ax2 = axes[1]
    ax2.plot(ticks, resources, color="tab:green", linewidth=1.8, label="resources produced")
    ax2.set_ylabel("Resources produced")
    ax2.set_xlabel("Tick")
    ax2.set_title("Environment resources and regime")
    ax2.grid(alpha=0.3)

    ax2_twin = ax2.twinx()
    ax2_twin.plot(ticks, env_series, color="tab:red", linewidth=1.2, label="environment")
    ax2_twin.set_ylabel("Environment code\n abundant=2, neutral=1, scarce=0")
    ax2_twin.set_ylim(-0.2, 2.2)
    ax2_twin.set_yticks([0, 1, 2])
    ax2_twin.set_yticklabels(["scarce", "neutral", "abundant"])

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "simulation_summary.png", dpi=200)
    
    #plt.show()
    plt.close(fig)

    print(f"Saved plots to {OUTPUT_DIR / 'simulation_summary.png'}")


def main() -> None:
    results = load_results(DATA_PATH)
    plot_results(results)


if __name__ == "__main__":
    main()
