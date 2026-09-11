# proSocial Technical Documentation

## 1. Project Purpose

This project is an agent-based simulation of social behavior, resource availability, environmental change, reproduction, mortality, and social memory. Agents have one of two behaviors:

- `share`: transfer resources to another agent.
- `hoard`: retain resources and alter social-memory values differently from sharers.

The project can be used at three scales:

1. One simulation with one configuration.
2. A batch of stochastic runs for one parameter set.
3. A grid of batches that varies two parameters, currently `Chang` and `Decay`.

The main data directory is `data/`. Plot files are written to `data/plots/`.

## 2. Code Map

| File | Role |
| --- | --- |
| `config.json` | Parameters for a simulation.
| `simulation_slow.py` |  Writes `data/simulation_results.json`. Simulator imported by `run_batch_sims.py`.
| `run_batch_sims.py` | Runs repeated simulations for one parameter set and writes one batch JSON file.
| `run_grid_sims.py` | Runs batches over a Chang/Decay grid and writes an index.
| `plot_results.py` | Plots time series from an individual simulation.
| `plot_batch_results.py` | Plots one batch as a pie chart.
| `plot_grid_results.py` | Plots a matrix of pie charts, one per grid cell.
| `tests/test_simulation.py` | Basic tests for the `simulation.py` implementation.

## 2. Model Dynamics

The exact code is authoritative; the following is a practical interpretation of the main loop.

### 3.1 Resource production

At every tick, the environment is in one of three states:

- `neutral`: production is approximately the population's basic need plus a small supplement.
- `abundant`: production is sampled between a lower abundant bound and `MaxAbundant * Needed * N`.
- `scarce`: production is sampled between `MaxScarce * Needed * N` and approximately `Needed * N`.

`Needed` is the per-agent resource requirement. `N` is the initial population size used when calculating production.

### 3.2 Resource distribution

Produced resources are distributed among current agents. Resources are capped by `MaxStorage`. Young and older agents receive a protected amount based on reproductive and menopausal age thresholds. Other resources are distributed stochastically among eligible agents. In the slow simulator, the resulting adult overflow is used when selecting sharing targets.

### 3.3 Environmental change

The environment begins as `neutral`.

- While neutral, `Chang` is the probability that the environment changes to either `abundant` or `scarce`.
- While abundant or scarce, `ReNeutral` is the probability of returning to neutral.
- `MaxAbundant` and `MaxScarce` control the resource range in those states.

`Chang` therefore controls how readily neutral conditions become stressful or favorable, while `ReNeutral` controls recovery toward neutral conditions.

### 3.4 Sharing and hoarding

A sharing agent may transfer resources when it has more than its basic need. The transfer is limited by `ShareFraction` and the agent's available resources. The target is selected using the social-memory value `proSocial` and, in the slow simulator, the current adult resource overflow.

A hoarding agent does not make this transfer. Its `proSocial` value is updated in the opposite direction based on excess resources. Sharing updates `proSocial` positively for the donor; decay is then applied at each tick.

### 3.5 Social memory and `Decay`

Each agent has a `proSocial` value. At each tick, it is multiplied by `Decay`.

- A value closer to `1` retains more previous social information.
- A lower value forgets more quickly.

The memory value influences which agents are considered appropriate sharing targets. `Decay` is therefore a memory-retention parameter, not a direct probability of sharing.

### 3.6 Behavior switching

`probBeh` is the probability that an agent considers switching behavior in a tick. The current behavior receives an increased choice weight, so switching is probabilistic rather than guaranteed.

### 3.7 Reproduction and mortality

Agents reproduce only within the configured reproductive-age range and when their resources are above the basic need. In the slow simulator, reproduction usually creates a child with the parent's behavior; a small random chance creates twins.

Agents can die through age/resource/death-timer mechanisms. If the population reaches zero, a run is classified as extinct in batch summaries.

## 4. Configuring a Basic Individual Simulation

Edit `config.json` before running `simulation.py`. Keep the file valid JSON: use double quotes, commas between fields, and no comments.

### Population and time

| Key | Meaning |
| --- | --- |
| `N` | Initial number of agents.
| `ticks` | Number of simulation time steps.
| `seed` | Intended random seed field. Check the active simulator before assuming strict reproducibility.
| `Needed` | Basic resource need per agent per tick.
| `ReRate` | Reproduction-rate parameter required by the `simulation.py` implementation.
| `MaxChilds` | Maximum-child parameter required by the `simulation.py` implementation.

### Environment and resources

| Key | Meaning |
| --- | --- |
| `Chang` | Probability of leaving neutral conditions for abundant or scarce conditions.
| `ReNeutral` | Probability of returning to neutral from abundant or scarce conditions.
| `MaxAbundant` | Upper multiplier for abundant resource production.
| `MaxScarce` | Lower multiplier for scarce resource production.
| `MaxStorage` | Maximum stored resources per agent.

### Behavior and memory

| Key | Meaning |
| --- | --- |
| `probBeh` | Probability of considering a behavior switch each tick.
| `ShareFraction` | Upper control on the fraction/amount transferred by a sharer.
| `Decay` | Retention of `proSocial` memory after each tick.
| `weightIniShare` | Initial selection weight for share behavior.
| `weightIniHoard` | Initial selection weight for hoard behavior.

### Life history

| Key | Meaning |
| --- | --- |
| `Under1DeathRate` | Mortality/reproduction threshold used by the slow simulator.
| `ReproductiveAge` | Mean or threshold for reproductive eligibility.
| `varReproductiveAge` | Variation in reproductive age.
| `MenopausalAge` | Mean or threshold for reproductive cessation.
| `varMenopausalAge` | Variation in menopausal age.
| `maxLife` | Maximum-life parameter used by the slow simulator.
| `BaseDeathTimer` | Initial/reset death-timer scale.

`Tag` is not a simulation mechanism. It is a label used in output filenames. `OutputDir` is retained in the configuration, but the current entry points use the repository's `data/` paths directly.

The current checked-in `config.json` does not include `ReRate` or `MaxChilds`, although `simulation.py` reads both keys. Add suitable values before running the individual simulator, or update the individual simulator to provide defaults. The batch simulator uses the separate `simulation_slow.py` implementation and has a different configuration contract.

## 5. Running One Simulation

From the repository root:

```bash
python simulation_slow.py
```

Using the project virtual environment is preferable when dependencies are installed there:

```bash
.venv/bin/python simulation_slow.py
```

The command writes:

```text
data/simulation_results.json
```

To plot its time series:

```bash
.venv/bin/python plot_results.py
```

This produces:

```text
data/plots/simulation_summary.png
```

The individual plot shows behavior counts over time, resources produced, and the environmental state.

## 6. Running a Batch

`run_batch_sims.py` runs the configured batch size `S` for one parameter set. It writes one JSON result to `data/`.

```bash
.venv/bin/python run_batch_sims.py
```

The filename follows the `make_param_label` convention:

```text
{Tag}_Chang_{Chang:.5f}_probBeh_{probBeh:.3f}_Decay_{Decay:.3f}_shaFr_{ShareFraction:.1f}_FamRes_{BaseDeathTimer:.0f}.json
```

For example:

```text
30maxAbu_00maxSca_reNe05_Chang_0.40000_probBeh_0.005_Decay_0.825_shaFr_0.5_FamRes_2.json
```

A batch JSON contains:

- `S`: number of runs.
- `N`: initial population size.
- `parameters`: selected parameter values.
- `summary`: sums of share, hoard, and extinction values across runs.
- `runs`: one late-window summary per run.

Plot one batch with:

```bash
.venv/bin/python plot_batch_results.py data/<batch-file>.json
```

The batch pie chart classifies each run as:

- `share`: share proportion above the current threshold in the plotting script.
- `hoard`: hoard proportion above the current threshold.
- `mix`: every other run, including extinct runs.

The pie size represents total observed population relative to the expected `N * S`. Its center is black when any run is extinct and white with a black outline when none are extinct.

## 7. Running a Parameter Grid

`run_grid_sims.py` varies `Chang` and `Decay`, while retaining all other values from `config.json`.

Example:

```bash
.venv/bin/python run_grid_sims.py \
  --chang 0.01 0.05 0.1 \
  --decay 0.825 0.9 0.985
```

Useful options:

```bash
--dry-run     Create/index planned combinations without simulating.
--force       Re-run batches whose output JSON already exists.
--config      Use another configuration JSON file.
--output-dir  Store the grid index in another directory.
```

The runner skips existing batch files by default. This makes interrupted grids resumable and avoids unnecessary computation.

The index filename includes the fixed parameters and the grid ranges, for example:

```text
data/grid_runs/grid_index_30maxAbu_00maxSca_reNe05_probBeh_0.005ChRan_1e-05-0.3_DeRan_0.001-0.95_shaFr_0.5_FamRes_2.json
```

The matching CSV has the same stem. The JSON index stores `rows`, `columns`, `matrix`, and `batches`; `rows` are Chang values and `columns` are Decay values.

## 8. Plotting a Grid

Plot a specific grid index:

```bash
.venv/bin/python plot_grid_results.py \
  --index data/grid_runs/<grid-index>.json
```

If exactly one renamed grid index exists, the `--index` argument can be omitted:

```bash
.venv/bin/python plot_grid_results.py
```

The output is:

```text
data/plots/grid_results_pies.png
```

In the grid figure:

- Columns vary `Decay` from left to right.
- Rows vary `Chang`; the largest Chang value is displayed at the top.
- Each panel is the same type of batch pie chart.
- Pie radius reflects total population for that parameter combination.
- A black center indicates that at least one run became extinct.
- A white center with a black outline indicates no extinction in that batch.
- The pie slices show the proportions of runs classified as share, hoard, or mix.

## 9. Minimal Workflow

A researcher can follow this sequence:

1. Adjust the assumptions in `config.json`.
2. Run one individual simulation to inspect the time dynamics.
3. Run a batch for the same settings to see how often the outcome repeats.
4. Run a grid varying `Chang` and `Decay` to see how the pattern depends on environmental change and memory retention.
5. Interpret the plots as evidence about the model's assumptions and dynamics, not as direct evidence about human beings.

## 10. Interpreting Results Carefully

These are stochastic simulations, not measurements of real populations. A difference between parameter cells should be evaluated across repeated runs and, ideally, with additional sensitivity analysis.

Keep fixed when comparing cells:

- `N`, `ticks`, and `S`.
- Initial behavior weights.
- Life-history parameters.
- Resource-production bounds.
- The simulator implementation.

Do not interpret a larger pie as a larger share percentage. Pie size and slice composition encode different quantities: total observed population versus outcome-category frequency.

## 11. Basic Checks

Compile the main scripts:

```bash
.venv/bin/python -m py_compile simulation.py run_batch_sims.py run_grid_sims.py plot_results.py plot_batch_results.py plot_grid_results.py
```

Run the existing tests:

```bash
.venv/bin/python -m unittest discover -s tests
```
