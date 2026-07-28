A stronger prompt would specify:

the target speedup,
the required constraints,
the verification method,
and the acceptable trade-offs.
For example:

Please optimize the Monte Carlo simulation in simulation.py and run_batch_sims.py so that it runs substantially faster while preserving the same output schema and scientific interpretation. Use numba for the inner loop, multiprocessing for independent seeds, and keep the implementation runnable in the project virtual environment. Measure performance with timeit before and after, target at least an order-of-magnitude speedup on the current hardware if feasible, and add clear academic-style documentation.