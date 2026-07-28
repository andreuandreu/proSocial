import unittest
from pathlib import Path

from simulation import load_config, simulate


class SimulationTests(unittest.TestCase):
    def test_simulation_returns_summary_history(self) -> None:
        config = load_config(Path("config.json"))
        config["ticks"] = 5
        config["N"] = 8
        config["seed"] = 11

        result = simulate(config, store_history=True, summary_window_size=5)

        self.assertIn("history", result)
        self.assertEqual(len(result["history"]), 5)
        self.assertIn("behavior_counts", result["history"][0])
        self.assertEqual(set(result["history"][0]["behavior_counts"].keys()), {"share", "hoard"})


if __name__ == "__main__":
    unittest.main()
