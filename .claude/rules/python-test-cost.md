---
paths:
  - "tests/**"
  - ".github/workflows/**"
---
<!-- Adapted on 2026-11-02 from Server Startup's shared Python and CLI rules; edit here, this copy is alfabeta's own. -->

# The Cost of a pytest CI Job

Applies when the `quality-gate` job of `.github/workflows/ci.yml` is too slow or too expensive,
before adding xdist or sharding, or when writing a fixture that reuses a subprocess run (many
alfabeta tests run `python -m alfabeta` in a subprocess). `pytest-xdist` is **not declared**;
adopting it, or any other plugin, is a dev-group change justified in the plan (constitution IX).

- **Bill = runner minutes summed over jobs**: measure summed test time (CPU + sleep); shards/workers usually cut the wall, not the bill — a file split into its own job can cut both, so measure a split's bill. **State the ceiling** (measured removable work) before implementing.
- **xdist**: measure it in CI. On a 2-vCPU hosted runner it gave about −21 %, and the per-test sum grows ×1.1–1.6 when tests spawn multi-core subprocesses.
  - Use `--dist worksteal`, not `load`.
  - `-n auto` counts logical CPUs; `PYTEST_XDIST_AUTO_NUM_WORKERS` lowers it.
  - The flags go in the Makefile's `test` recipe, never in `addopts`.
  - A hook that writes a file guards on `hasattr(config, "workerinput")`, never on `PYTEST_XDIST_WORKER`, which `pytester` inherits. Test it without xdist: `runpytest(plugins=[obj])`, where `obj.pytest_configure` sets `config.workerinput`.
- **Sharing an expensive run**:
  - The key is a sha256 of the tmp tree (path, mode, bytes; tmp path masked), the args and the env less `PYTEST_*`. Never a hand list.
  - Keep only runs that succeeded. Store copies outside every `tmp_path`, and assert the copy exists.
  - The restore rewrites the tmp path in bytes, symlinks and the result, and restores directory modes.
  - A control test first asserts the restore happened, then compares restored with fresh (tmp path and timestamps masked); it is mutation-proven. One test runs `fresh=True`.
  - Mask wall-clock fields when counting repeats; merge what still repeats by addition, asserts diffed by AST.
- **Report**: a conftest sums `report.duration` per node id and prints the top files and tests, plus `GITHUB_STEP_SUMMARY` (controller only, `|` escaped).
- **Count the subprocesses per test**: each `python -m alfabeta` pays an interpreter start and the package import; a tool's own start-up can dominate on a runner and hide on a laptop. A test of a command's logic calls `main(argv)` in-process; a subprocess is for what only a process shows (exit code, streams, `--version`).
- **Instruments**: per-test CPU = `getrusage` SELF + CHILDREN around `pytest_runtest_protocol`; the subprocess inventory = a `Popen` wrapper plugin loaded with `-p`, never committed. CI numbers: the baseline's instrument, ≥ 3 runs vs a serial median, **arms launched in the same window** (runner speed moved ×1.5 between windows; a cross-window comparison once read xdist as slower where, paired, it won 17–27 %). Locally: ratios, alternating arms, `uptime`.
- **Never cut cost by dropping a gate**: the guardrail and the JS tests stay in `make ci`; a skipped gate is not green (constitution, *Development workflow*).
