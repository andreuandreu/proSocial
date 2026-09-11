from __future__ import annotations

import argparse
import csv
import gc
import json
from pathlib import Path
from typing import Any, Dict, List, Sequence

from run_batch_sims import S, make_param_label, run_batch
from simulation_slow import load_config

#explicityly enumerated grid values:
#python run_grid_sims.py  --chang 0.01 0.05 0.1 --decay 0.8 0.9 0.985 
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
GRID_DIR = DATA_DIR / "grid_runs"
DEFAULT_CHANG_VALUES = (0.01, 0.05, 0.1)
DEFAULT_DECAY_VALUES = (0.8, 0.9, 0.985)


def batch_path(config: Dict[str, object], data_dir: Path) -> Path:
    """Return the path used by run_batch_sims for one parameter pair."""
    return data_dir / (
        f"{make_param_label(float(config['Chang']), float(config['probBeh']), float(config['Decay']), float(config['ShareFraction']), float(config['BaseDeathTimer']), str(config.get('Tag', '')))}.json"
    )


def parse_values(values: Sequence[str]) -> List[float]:
    parsed = sorted({float(value) for value in values})
    if not parsed:
        raise ValueError("At least one grid value is required.")
    return parsed


def grid_index_stem(config: Dict[str, object], chang_values: Sequence[float], decay_values: Sequence[float]) -> str:
    """Return a stable index label for parameters held constant across the grid."""
    tag = str(config.get("Tag", ""))
    tag_prefix = f"{tag}_" if tag else ""
    return (
        f"grid_index_{tag_prefix}probBeh_{float(config.get('probBeh', 0.0)):.3f}"
        f"ChRan_{chang_values[0]}-{chang_values[-1]}_DeRan_{decay_values[0]}-{decay_values[-1]}"
        f"_shaFr_{float(config.get('ShareFraction', 0.0)):.1f}"
        f"_FamRes_{float(config.get('BaseDeathTimer', 0.0)):.0f}"
    )


def write_grid_index(
    rows: List[Dict[str, Any]],
    chang_values: Sequence[float],
    decay_values: Sequence[float],
    output_dir: Path,
    config: Dict[str, object],
) -> None:
    """Persist both a flat table and a row/column index for later plotting."""
    output_dir.mkdir(parents=True, exist_ok=True)
    columns = [f"Decay={decay:.6g}" for decay in decay_values]
    paths = {(row["Chang"], row["Decay"]): row["batch_file"] for row in rows}
    matrix = {
        f"Chang={chang:.6g}": {
            f"Decay={decay:.6g}": paths.get((chang, decay))
            for decay in decay_values
        }
        for chang in chang_values
    }

    index = {
        "parameters": {"row": "Chang", "column": "Decay"},
        "rows": list(chang_values),
        "columns": list(decay_values),
        "matrix": matrix,
        "batches": rows,
    }
    index_stem = grid_index_stem(config, chang_values, decay_values)
    with (output_dir / f"{index_stem}.json").open("w", encoding="utf-8") as handle:
        json.dump(index, handle, indent=2)

    with (output_dir / f"{index_stem}.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["Chang", "Decay", "status", "batch_file", "S", "N"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_grid(
    config_path: Path,
    chang_values: Sequence[float],
    decay_values: Sequence[float],
    output_dir: Path,
    force: bool = False,
    dry_run: bool = False,
) -> List[Dict[str, Any]]:
    """Run one batch for every Chang/Decay pair, reusing completed batches."""
    base_config = load_config(config_path)
    rows: List[Dict[str, Any]] = []
    total = len(chang_values) * len(decay_values)

    for index, chang in enumerate(chang_values, start=1):
        for decay in decay_values:
            config = dict(base_config)
            config["Chang"] = chang
            config["Decay"] = decay
            path = batch_path(config, DATA_DIR)
            relative_path = str(path.relative_to(BASE_DIR))

            if path.exists() and not force:
                status = "skipped_existing"
                with path.open("r", encoding="utf-8") as handle:
                    batch = json.load(handle)
            elif dry_run:
                status = "planned"
                batch = {}
            else:
                print(f"[{index}/{len(chang_values)}] Chang={chang}, Decay={decay}")
                run_batch(config)
                with path.open("r", encoding="utf-8") as handle:
                    batch = json.load(handle)
                status = "completed"

            rows.append(
                {
                    "Chang": chang,
                    "Decay": decay,
                    "status": status,
                    "batch_file": relative_path,
                    "S": batch.get("S", S),
                    "N": batch.get("N", config.get("N")),
                }
            )
            write_grid_index(rows, chang_values, decay_values, output_dir, base_config)
            gc.collect()

    print(f"Grid complete: {len(rows)}/{total} parameter combinations indexed in {output_dir}")
    return rows

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run run_batch_sims.py over a Chang/Decay grid.")
    parser.add_argument("--config", type=Path, default=BASE_DIR / "config.json")
    parser.add_argument("--chang", nargs="+", default=[str(value) for value in DEFAULT_CHANG_VALUES])
    parser.add_argument("--decay", nargs="+", default=[str(value) for value in DEFAULT_DECAY_VALUES])
    parser.add_argument("--output-dir", type=Path, default=GRID_DIR)
    parser.add_argument("--force", action="store_true", help="Re-run batches whose JSON output already exists.")
    parser.add_argument("--dry-run", action="store_true", help="List and index planned combinations without simulating.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    chang_values = parse_values(args.chang)
    decay_values = parse_values(args.decay)
    print('chang values',chang_values,'\n', decay_values)
    run_grid(args.config, chang_values, decay_values, args.output_dir, args.force, args.dry_run)


if __name__ == "__main__":
    main()
