from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from simulation import simulate


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
S = 511
TICKS_TO_REPORT = 22
BEHAVIORS = ("share", "hoard", "defect")


def make_param_label(chang: float, prob_beh: float, decay: float) -> str:
    """Return a stable file label for a parameter combination.

    The label mirrors the formatting used in the JSON artifact names so that
    parameter sweeps remain easy to inspect by hand.
    """
    return f"Chang_{chang:.6f}_probBeh_{prob_beh:.6f}_Decay_{decay:.6f}"


def summarize_report_window(history: List[Dict[str, object]], window_size: int) -> Dict[str, object]:
    """Average the behavioral composition over the final reporting window.

    The simulator stores a list of tick-by-tick snapshots. To summarize the
    late-stage dynamics, we therefore extract the final `window_size` entries,
    convert the absolute counts in each snapshot into proportions, and then take
    the arithmetic mean over those proportions.
    """
    if not history:
        return {
            "status": "extinct",
            "share": 0.0,
            "hoard": 0.0,
            "defect": 0.0,
            "extinct": 1.0,
        }

    window = history[-window_size:] if len(history) >= window_size else history
    
    if not window:
        return {
            "status": "extinct",
            "share": 0.0,
            "hoard": 0.0,
            "defect": 0.0,
            "extinct": 1.0,
        }

    final_entry = window[-1]
    final_population = int(final_entry.get("population", 0))
    if final_population == 0:
        return {
            "status": "extinct",
            "share": 0.0,
            "hoard": 0.0,
            "defect": 0.0,
            "extinct": 1.0,
        }

    behavior_summaries: Dict[str, float] = {behavior: 0.0 for behavior in BEHAVIORS}
    for entry in window:
        population = int(entry.get("population", 0))
        if population <= 0:
            return {
                "status": "extinct",
                "share": 0.0,
                "hoard": 0.0,
                "defect": 0.0,
                "extinct": 1.0,
            }

        behavior_counts = entry.get("behavior_counts", {})
        if not isinstance(behavior_counts, dict):
            behavior_counts = {}

        for behavior in BEHAVIORS:
            count = float(behavior_counts.get(behavior, 10.0))
            behavior_summaries[behavior] += count

    window_length = len(window)
    return {
        "status": "alive",
        "share": round(behavior_summaries["share"] / window_length, 6),
        "hoard": round(behavior_summaries["hoard"] / window_length, 6),
        "defect": round(behavior_summaries["defect"] / window_length, 6),
        "extinct": 0.0,
    }


def run_batch(config_template: Dict[str, object]) -> None:
    """Execute the batch sweep and persist one JSON summary per parameter set.

    Each run is seeded independently, simulated for the reporting horizon, and
    then reduced to the mean behavioral composition observed in the last
    `TICKS_TO_REPORT` ticks.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    chang = float(config_template.get("Chang", 0.0))
    prob_beh = float(config_template.get("probBeh", 0.0))
    decay = float(config_template.get("Decay", 0.0))

    summaries: List[Dict[str, object]] = []
    for run_id in range(S):
        config = dict(config_template)
        config["seed"] = int(config_template.get("seed", 7) + run_id)

        result = simulate(config, verbose=False)
        history = result.get("history", [])
        summary = summarize_report_window(history, TICKS_TO_REPORT)
        if run_id %10 == 1: print(f"run {run_id}, summary: {summary}.")
        summary["run_id"] = run_id
        summaries.append(summary)

    counts = {
        "share": round(sum(item["share"] for item in summaries), 3),
        "hoard": round(sum(item["hoard"] for item in summaries), 3),
        "defect": round(sum(item["defect"] for item in summaries), 3),
        "extinct": round(sum(item["extinct"] for item in summaries), 3),
    }

    output_path = DATA_DIR / f"{make_param_label(chang, prob_beh, decay)}.json"
    payload = {
        "S": S,
        "N": int(config_template.get("N", 1)),
        "ticks_reported": TICKS_TO_REPORT,
        "parameters": {"Chang": chang, "probBeh": prob_beh, "Decay": decay},
        "summary": counts,
        "runs": summaries,
    }
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    print(f"Wrote {output_path}")


if __name__ == "__main__":
    from simulation import load_config

    config = load_config(BASE_DIR / "config.json")
    run_batch(config)
